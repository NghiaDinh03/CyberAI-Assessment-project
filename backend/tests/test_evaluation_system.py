"""Unit tests for RAG Retrieval & LLM Assessment Verdict Evaluation System.

Tests cover all 9 mandatory requirements:
1. Recall@k correct when relevant chunk is at rank 1, rank k, and outside top-k.
2. MRR@k correct when there are multiple relevant chunks (takes first relevant rank).
3. Records missing relevance labels are excluded without skewing the denominator.
4. Accuracy / Macro-F1 / confusion matrix correct on multi-class fixture.
5. Legacy 'non_compliant' records are not erroneously mapped (flagged as needs_label_review).
6. few_shot records are strictly isolated from test evaluation (anti-leakage).
7. Empty dataset or unlabeled dataset returns controlled insufficient_data status without fake metrics.
8. Evaluation artefacts do not contain raw evidence strings, enterprise prompts, or PII.
9. Integration with AuditFeedbackStore idempotent SQLite migrations and few-shot filtering.
"""

import os
import json
import pytest
import tempfile
from pathlib import Path

from evaluation.schemas import (
    RagEvalRecord,
    VerdictEvalRecord,
    CANONICAL_VERDICTS,
)
from evaluation.normalizer import (
    normalize_expert_verdict,
    is_valid_canonical_verdict,
)
from evaluation.metrics import (
    evaluate_rag_retrieval,
    evaluate_verdict_predictions,
)
from evaluation.dataset import (
    load_rag_evaluation_dataset,
    load_verdict_evaluation_dataset,
)
from evaluation.evaluator import (
    run_rag_evaluation,
    run_verdict_evaluation,
    save_evaluation_artefact,
)
from repositories.feedback_store import AuditFeedbackStore


# ---------------------------------------------------------------------------
# Scenario 1: Recall@k at rank 1, rank k, and outside top-k
# ---------------------------------------------------------------------------
def test_recall_at_k_ranks():
    records = [
        # Rank 1 hit
        RagEvalRecord(case_id="q1", standard="iso27001", query="query 1", relevant_chunk_ids=["chunk_a"]),
        # Rank k hit (k=3, hit at index 3)
        RagEvalRecord(case_id="q2", standard="iso27001", query="query 2", relevant_chunk_ids=["chunk_c"]),
        # Outside top-k (hit at index 4, but k=3)
        RagEvalRecord(case_id="q3", standard="iso27001", query="query 3", relevant_chunk_ids=["chunk_d"]),
    ]

    retrieved = {
        "q1": ["chunk_a", "other_1", "other_2"],  # rank 1
        "q2": ["other_1", "other_2", "chunk_c"],  # rank 3 (rank k)
        "q3": ["other_1", "other_2", "other_3", "chunk_d"],  # rank 4 (outside k=3)
    }

    metrics = evaluate_rag_retrieval(records, retrieved, top_k=3)

    assert metrics.total_queries == 3
    assert metrics.valid_queries == 3
    # 2 out of 3 had a hit in top-3
    assert metrics.recall_at_k == round(2 / 3, 4)  # 0.6667


# ---------------------------------------------------------------------------
# Scenario 2: MRR@k when multiple relevant chunks exist (uses first hit rank)
# ---------------------------------------------------------------------------
def test_mrr_at_k_multiple_relevant_chunks():
    records = [
        # Case 1: relevant chunks at rank 2 and rank 3 -> first hit is rank 2 -> RR = 1/2 = 0.5
        RagEvalRecord(case_id="q1", standard="iso27001", query="query 1", relevant_chunk_ids=["rel_b", "rel_c"]),
        # Case 2: relevant chunk at rank 1 -> first hit is rank 1 -> RR = 1/1 = 1.0
        RagEvalRecord(case_id="q2", standard="iso27001", query="query 2", relevant_chunk_ids=["rel_a"]),
        # Case 3: no relevant chunk in top-k -> RR = 0.0
        RagEvalRecord(case_id="q3", standard="iso27001", query="query 3", relevant_chunk_ids=["rel_z"]),
    ]

    retrieved = {
        "q1": ["other_1", "rel_b", "rel_c"],  # hits at 2 and 3 -> first hit rank 2
        "q2": ["rel_a", "other_2", "other_3"],  # hit at 1
        "q3": ["other_4", "other_5", "other_6"],  # no hit
    }

    metrics = evaluate_rag_retrieval(records, retrieved, top_k=3)

    # Sum of reciprocal ranks = 1/2 (0.5) + 1/1 (1.0) + 0.0 = 1.5
    # MRR = 1.5 / 3 = 0.5000
    assert metrics.mrr_at_k == 0.5000
    assert metrics.query_details[0].first_relevant_rank == 2
    assert metrics.query_details[0].reciprocal_rank == 0.5
    assert metrics.query_details[1].first_relevant_rank == 1
    assert metrics.query_details[1].reciprocal_rank == 1.0
    assert metrics.query_details[2].first_relevant_rank is None
    assert metrics.query_details[2].reciprocal_rank == 0.0


# ---------------------------------------------------------------------------
# Scenario 3: Missing/empty relevance label excluded without skewing denominator
# ---------------------------------------------------------------------------
def test_rag_unlabeled_records_excluded_from_denominator():
    records = [
        RagEvalRecord(case_id="q1", standard="iso27001", query="valid query", relevant_chunk_ids=["chunk_a"]),
        RagEvalRecord(case_id="q2", standard="iso27001", query="unlabeled query 1", relevant_chunk_ids=[]),
        RagEvalRecord(case_id="q3", standard="iso27001", query="unlabeled query 2", relevant_chunk_ids=["   "]),
    ]

    retrieved = {
        "q1": ["chunk_a", "chunk_b"],
        "q2": ["chunk_a"],
        "q3": ["chunk_a"],
    }

    metrics = evaluate_rag_retrieval(records, retrieved, top_k=2)

    assert metrics.total_queries == 3
    assert metrics.valid_queries == 1
    assert metrics.unlabeled_or_empty_queries == 2
    # Denominator is 1 (not 3), so 1 hit out of 1 valid query = 1.0
    assert metrics.recall_at_k == 1.0
    assert metrics.mrr_at_k == 1.0


# ---------------------------------------------------------------------------
# Scenario 4: Accuracy, Macro-F1, confusion matrix on multi-class fixture
# ---------------------------------------------------------------------------
def test_verdict_multiclass_metrics_and_confusion_matrix():
    # 5 classes with diverse distribution
    records = [
        VerdictEvalRecord(case_id="c1", standard="iso27001", control_id="A.5.1", input_ref="h1", expert_verdict="satisfied"),
        VerdictEvalRecord(case_id="c2", standard="iso27001", control_id="A.5.2", input_ref="h2", expert_verdict="satisfied"),
        VerdictEvalRecord(case_id="c3", standard="iso27001", control_id="A.5.3", input_ref="h3", expert_verdict="partial"),
        VerdictEvalRecord(case_id="c4", standard="iso27001", control_id="A.5.4", input_ref="h4", expert_verdict="partial"),
        VerdictEvalRecord(case_id="c5", standard="iso27001", control_id="A.5.5", input_ref="h5", expert_verdict="missing"),
        VerdictEvalRecord(case_id="c6", standard="iso27001", control_id="A.5.6", input_ref="h6", expert_verdict="not_evidenced"),
    ]

    preds = {
        "c1": "satisfied",  # TP satisfied
        "c2": "satisfied",  # TP satisfied
        "c3": "partial",    # TP partial
        "c4": "missing",    # FN partial, FP missing
        "c5": "missing",    # TP missing
        "c6": "not_evidenced",  # TP not_evidenced
    }

    metrics = evaluate_verdict_predictions(records, preds)

    # Total valid: 6. Correct: 5 (c1, c2, c3, c5, c6).
    assert metrics.valid_samples == 6
    assert metrics.accuracy == round(5 / 6, 4)

    # Check confusion matrix
    cm = metrics.confusion_matrix
    assert cm["satisfied"]["satisfied"] == 2
    assert cm["partial"]["partial"] == 1
    assert cm["partial"]["missing"] == 1
    assert cm["missing"]["missing"] == 1
    assert cm["not_evidenced"]["not_evidenced"] == 1

    # Per-class checks
    assert metrics.per_class["satisfied"].precision == 1.0
    assert metrics.per_class["satisfied"].recall == 1.0
    assert metrics.per_class["satisfied"].f1 == 1.0

    # partial: TP=1, FP=0 -> Prec=1.0. FN=1 -> Rec = 1/2 = 0.5. F1 = 2*(1*0.5)/(1.5) = 2/3 = 0.6667
    assert metrics.per_class["partial"].precision == 1.0
    assert metrics.per_class["partial"].recall == 0.5
    assert metrics.per_class["partial"].f1 == 0.6667

    # missing: TP=1, FP=1 (from c4), FN=0 -> Prec=0.5, Rec=1.0, F1=0.6667
    assert metrics.per_class["missing"].precision == 0.5
    assert metrics.per_class["missing"].recall == 1.0
    assert metrics.per_class["missing"].f1 == 0.6667

    # Macro-F1 across 4 classes with support: (1.0 + 0.6667 + 0.6667 + 1.0) / 4 = 3.3334 / 4 = 0.8334
    assert metrics.macro_f1 is not None
    assert round(metrics.macro_f1, 2) == 0.83


# ---------------------------------------------------------------------------
# Scenario 5: Legacy 'non_compliant' is NOT mapped to missing or not_evidenced
# ---------------------------------------------------------------------------
def test_legacy_non_compliant_not_auto_mapped():
    # Canonical verdicts pass
    v, status = normalize_expert_verdict("satisfied")
    assert v == "satisfied" and status == "approved"

    # Legacy compliant maps safely to satisfied
    v, status = normalize_expert_verdict("compliant")
    assert v == "satisfied" and status == "approved"

    # Legacy non_compliant MUST NOT map to missing or not_evidenced
    v, status = normalize_expert_verdict("non_compliant")
    assert v is None
    assert status == "needs_label_review"
    assert v not in ("missing", "not_evidenced")

    # In evaluation, non_compliant must be excluded from automated metrics
    records = [
        VerdictEvalRecord(case_id="c1", standard="iso27001", control_id="A.5.1", input_ref="h1", expert_verdict="satisfied"),
        VerdictEvalRecord(case_id="c2", standard="iso27001", control_id="A.5.2", input_ref="h2", expert_verdict="non_compliant"),
    ]
    preds = {"c1": "satisfied", "c2": "missing"}
    metrics = evaluate_verdict_predictions(records, preds)

    assert metrics.valid_samples == 1
    assert metrics.excluded_samples == 1
    assert metrics.excluded_details[0]["case_id"] == "c2"
    assert metrics.excluded_details[0]["raw_verdict"] == "non_compliant"
    assert "needs_label_review" in metrics.excluded_details[0]["reason"]


# ---------------------------------------------------------------------------
# Scenario 6: Anti-Leakage (few_shot records strictly isolated from test split)
# ---------------------------------------------------------------------------
def test_anti_leakage_split_isolation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test_feedback.db")
        store = AuditFeedbackStore(db_path=db_path)

        # 1. Save a few-shot record
        store.save_feedback(
            control_id="A.5.1",
            expert_verdict="satisfied",
            expert_rationale="Few shot exemplar rationale",
            split="few_shot",
            label_status="approved",
        )

        # 2. Save a test record
        store.save_feedback(
            control_id="A.5.1",
            expert_verdict="satisfied",
            expert_rationale="Test record rationale",
            split="test",
            label_status="approved",
        )

        # Few-shot injection for prompts MUST NEVER return the test record
        few_shot_exemplars = store.get_few_shot_exemplars(control_id="A.5.1")
        assert len(few_shot_exemplars) == 1
        assert few_shot_exemplars[0]["split"] == "few_shot"
        assert few_shot_exemplars[0]["expert_rationale"] == "Few shot exemplar rationale"

        # Evaluation query for split='test' MUST NOT return the few_shot record
        test_eval_records = store.get_evaluation_records(standard="iso27001", split="test")
        assert len(test_eval_records) == 1
        assert test_eval_records[0]["split"] == "test"
        assert test_eval_records[0]["expert_rationale"] == "Test record rationale"


# ---------------------------------------------------------------------------
# Scenario 7: Empty or unlabeled dataset returns controlled insufficient_data
# ---------------------------------------------------------------------------
def test_empty_or_unlabeled_dataset_no_fake_metrics():
    # RAG with 0 records
    artefact_rag = run_rag_evaluation(
        standard="iso27001",
        split="test",
        mock_retriever=lambda q, k: ["chunk_1"],
        custom_dataset_path="/non_existent/path.json",
    )
    assert artefact_rag.status == "insufficient_data"
    assert artefact_rag.rag_metrics is None
    assert "Dataset RAG trống" in artefact_rag.status_message

    # Verdict with 0 records
    artefact_verdict = run_verdict_evaluation(
        standard="iso27001",
        split="test",
        custom_dataset_path="/non_existent/path.json",
    )
    assert artefact_verdict.status == "insufficient_data"
    assert artefact_verdict.verdict_metrics is None
    assert "Dataset verdict trống" in artefact_verdict.status_message

    # Verdict with single class only -> Macro-F1 must be None (not representative)
    single_class_records = [
        VerdictEvalRecord(case_id="c1", standard="iso27001", control_id="A.5.1", input_ref="h1", expert_verdict="satisfied"),
    ]
    metrics = evaluate_verdict_predictions(single_class_records, {"c1": "satisfied"})
    assert metrics.accuracy == 1.0
    assert metrics.macro_f1 is None  # Must NOT report representative Macro-F1 for 1 class!


# ---------------------------------------------------------------------------
# Scenario 8: Evaluation artefacts contain zero sensitive raw evidence or PII
# ---------------------------------------------------------------------------
def test_artefact_desensitization_and_serialization():
    with tempfile.TemporaryDirectory() as tmp_dir:
        records = [
            VerdictEvalRecord(
                case_id="case-100",
                standard="iso27001",
                control_id="A.5.1",
                input_ref="hash:e3b0c44298fc1c14",  # Safe SHA-256 hash
                expert_verdict="satisfied",
                predicted_verdict="satisfied",
            )
        ]
        metrics = evaluate_verdict_predictions(records, {"case-100": "satisfied"})

        artefact = run_verdict_evaluation(
            standard="iso27001",
            split="test",
            predictions={"case-100": "satisfied"},
        )

        json_path, csv_path = save_evaluation_artefact(artefact, output_dir=tmp_dir)
        content = json_path.read_text(encoding="utf-8")

        # Invariant checks:
        assert "password" not in content.lower()
        assert "user_ip" not in content.lower()
        assert "minh chứng doanh nghiệp" not in content.lower()
        assert "prompt thô" not in content.lower()

        # Valid JSON parse
        parsed = json.loads(content)
        assert parsed["mode"] == "verdict"
        assert "git_commit_sha" in parsed
        assert "metric_definitions" in parsed


# ---------------------------------------------------------------------------
# Scenario 9: Idempotent DB migration flags legacy non_compliant
# ---------------------------------------------------------------------------
def test_feedback_store_migration_and_legacy_flagging():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "migration_test.db")

        # Create store instance
        store1 = AuditFeedbackStore(db_path=db_path)

        # Insert a record with non_compliant
        store1.save_feedback(
            control_id="A.8.1",
            expert_verdict="non_compliant",
            expert_rationale="Legacy verdict from older UI",
        )

        # Check that it got flagged as needs_label_review
        records = store1.get_evaluation_records(standard="iso27001", split="few_shot", include_pending_review=True)
        assert len(records) == 1
        assert records[0]["label_status"] == "needs_label_review"

        # Re-initialize store on same DB (idempotence)
        store2 = AuditFeedbackStore(db_path=db_path)
        records_after = store2.get_evaluation_records(standard="iso27001", split="few_shot", include_pending_review=True)
        assert len(records_after) == 1
        assert records_after[0]["label_status"] == "needs_label_review"
