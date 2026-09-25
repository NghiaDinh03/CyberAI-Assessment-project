"""Mathematical evaluation metrics for RAG retrieval and LLM verdict classification.

Strict adherence to evaluation standards:
1. RAG:
   - Recall@k: Proportion of valid queries having at least one relevant_chunk_id in top-k retrieved chunks.
   - MRR@k: Mean Reciprocal Rank (1/rank) of the first relevant chunk in top-k. If no relevant chunk in top-k, 0.0.
   - Queries without valid relevant_chunk_ids are excluded from the denominator and tallied separately.
2. Verdict:
   - Accuracy: exact matches / valid_samples.
   - Macro-F1: unweighted mean of per-class F1 across classes with support > 0.
     Undefined/None if valid_samples == 0 or if only 1 class is present.
   - Confusion matrix: structured as [true_class][pred_class].
   - Exclusions: untrusted/legacy labels (e.g. non_compliant) are explicitly tracked with reasons.
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from .schemas import (
    RagEvalRecord,
    RagMetrics,
    RagQueryResult,
    VerdictEvalRecord,
    VerdictMetrics,
    ClassMetric,
    CANONICAL_VERDICTS,
)
from .normalizer import normalize_expert_verdict


def evaluate_rag_retrieval(
    records: List[RagEvalRecord],
    retrieved_chunks_by_case: Dict[str, List[str]],
    top_k: int = 5,
    collection_version: str = "default",
    embedding_model: str = "bge-m3",
) -> RagMetrics:
    """Compute Recall@k and MRR@k for RAG queries against ground truth chunk IDs.

    Args:
        records: List of RagEvalRecord with ground truth relevant_chunk_ids.
        retrieved_chunks_by_case: Map from case_id -> ordered list of retrieved chunk_ids.
        top_k: Number of retrieved chunks to consider (k).
        collection_version: Identifier of corpus.
        embedding_model: Identifier of embedding model.

    Returns:
        RagMetrics containing Recall@k, MRR@k, query counts, and per-query details.
    """
    total_queries = len(records)
    valid_queries = 0
    unlabeled_or_empty_queries = 0
    query_details: List[RagQueryResult] = []

    hits_count = 0
    reciprocal_ranks_sum = 0.0

    for rec in records:
        # Check ground truth label validity
        if not rec.relevant_chunk_ids:
            unlabeled_or_empty_queries += 1
            continue

        valid_queries += 1
        relevant_set = set(str(cid).strip() for cid in rec.relevant_chunk_ids if str(cid).strip())
        if not relevant_set:
            unlabeled_or_empty_queries += 1
            valid_queries -= 1
            continue

        # Get retrieved chunks up to top_k
        raw_retrieved = retrieved_chunks_by_case.get(rec.case_id, [])
        top_retrieved = [str(c).strip() for c in raw_retrieved[:top_k]]

        # Find 1-indexed rank of first relevant chunk
        first_rank: Optional[int] = None
        for rank_idx, chunk_id in enumerate(top_retrieved, start=1):
            if chunk_id in relevant_set:
                first_rank = rank_idx
                break

        hit = first_rank is not None
        reciprocal_rank = (1.0 / first_rank) if hit and first_rank is not None else 0.0

        if hit:
            hits_count += 1
        reciprocal_ranks_sum += reciprocal_rank

        query_details.append(
            RagQueryResult(
                case_id=rec.case_id,
                query_preview=(rec.query[:50] + "...") if len(rec.query) > 50 else rec.query,
                retrieved_chunk_ids=top_retrieved,
                relevant_chunk_ids=list(relevant_set),
                first_relevant_rank=first_rank,
                hit_at_k=hit,
                reciprocal_rank=round(reciprocal_rank, 4),
            )
        )

    if valid_queries > 0:
        recall_at_k = round(hits_count / valid_queries, 4)
        mrr_at_k = round(reciprocal_ranks_sum / valid_queries, 4)
    else:
        recall_at_k = 0.0
        mrr_at_k = 0.0

    return RagMetrics(
        recall_at_k=recall_at_k,
        mrr_at_k=mrr_at_k,
        k=top_k,
        total_queries=total_queries,
        valid_queries=valid_queries,
        unlabeled_or_empty_queries=unlabeled_or_empty_queries,
        collection_version=collection_version,
        embedding_model=embedding_model,
        query_details=query_details,
    )


def evaluate_verdict_predictions(
    records: List[VerdictEvalRecord],
    predictions_by_case: Dict[str, str],
    model_runtime: str = "local-runtime",
) -> VerdictMetrics:
    """Compute Accuracy, Macro-F1, per-class metrics, and confusion matrix.

    Legacy labels (e.g. non_compliant) and unmapped records are excluded and logged.
    If valid samples == 0 or only 1 class is present, Macro-F1 is reported as None.
    """
    valid_true: List[str] = []
    valid_pred: List[str] = []
    excluded_samples = 0
    excluded_details: List[Dict[str, str]] = []
    schema_valid_count = 0

    for rec in records:
        norm_verdict, status = normalize_expert_verdict(rec.expert_verdict)
        if status != "approved" or not norm_verdict:
            excluded_samples += 1
            excluded_details.append({
                "case_id": rec.case_id,
                "control_id": rec.control_id,
                "raw_verdict": str(rec.expert_verdict),
                "reason": f"Label status '{status}' is not canonical approved",
            })
            continue

        pred = predictions_by_case.get(rec.case_id)
        if pred is None:
            excluded_samples += 1
            excluded_details.append({
                "case_id": rec.case_id,
                "control_id": rec.control_id,
                "raw_verdict": norm_verdict,
                "reason": "Missing prediction for case_id",
            })
            continue

        clean_pred = str(pred).strip().lower()
        if clean_pred in CANONICAL_VERDICTS:
            schema_valid_count += 1
        elif clean_pred == "compliant":
            clean_pred = "satisfied"
            schema_valid_count += 1

        valid_true.append(norm_verdict)
        valid_pred.append(clean_pred)

    valid_samples = len(valid_true)
    schema_valid_rate = round(schema_valid_count / valid_samples, 4) if valid_samples > 0 else None

    if valid_samples == 0:
        return VerdictMetrics(
            accuracy=None,
            macro_f1=None,
            per_class={},
            confusion_matrix={},
            valid_samples=0,
            excluded_samples=excluded_samples,
            excluded_details=excluded_details,
            model_runtime=model_runtime,
            schema_valid_rate=schema_valid_rate,
            classes=[],
        )

    # Calculate exact-match accuracy
    correct = sum(1 for t, p in zip(valid_true, valid_pred) if t == p)
    accuracy = round(correct / valid_samples, 4)

    # Classes present in ground truth or predictions
    classes = sorted(list(set(valid_true) | set(valid_pred)))

    # Confusion matrix: [true_class][pred_class]
    confusion_matrix: Dict[str, Dict[str, int]] = {
        c_true: {c_pred: 0 for c_pred in classes} for c_true in classes
    }
    for t, p in zip(valid_true, valid_pred):
        if p not in confusion_matrix[t]:
            confusion_matrix[t][p] = 0
        confusion_matrix[t][p] += 1

    # Per-class metrics
    per_class: Dict[str, ClassMetric] = {}
    f1_scores_with_support: List[float] = []

    for c in classes:
        tp = sum(1 for t, p in zip(valid_true, valid_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(valid_true, valid_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(valid_true, valid_pred) if t == c and p != c)
        support = tp + fn

        prec = (tp / (tp + fp)) if (tp + fp) > 0 else None
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else None

        if prec is not None and rec is not None and (prec + rec) > 0:
            f1 = 2 * (prec * rec) / (prec + rec)
        else:
            f1 = 0.0 if support > 0 else None

        per_class[c] = ClassMetric(
            precision=round(prec, 4) if prec is not None else None,
            recall=round(rec, 4) if rec is not None else None,
            f1=round(f1, 4) if f1 is not None else None,
            support=support,
        )

        if support > 0 and f1 is not None:
            f1_scores_with_support.append(f1)

    # Distinct ground truth classes
    distinct_true_classes = len(set(valid_true))
    # Rule: If only 1 class is present or no support, do NOT report representative Macro-F1
    if distinct_true_classes > 1 and f1_scores_with_support:
        macro_f1 = round(sum(f1_scores_with_support) / len(f1_scores_with_support), 4)
    else:
        macro_f1 = None

    return VerdictMetrics(
        accuracy=accuracy,
        macro_f1=macro_f1,
        per_class=per_class,
        confusion_matrix=confusion_matrix,
        valid_samples=valid_samples,
        excluded_samples=excluded_samples,
        excluded_details=excluded_details,
        model_runtime=model_runtime,
        schema_valid_rate=schema_valid_rate,
        classes=classes,
    )
