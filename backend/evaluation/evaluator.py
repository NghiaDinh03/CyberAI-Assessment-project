"""Core evaluation coordinator for RAG and LLM Assessment Verdicts.

Integrates:
- ChromaDB VectorStore retrieval (using local BGE-M3 embeddings, zero cloud dependencies)
- AuditFeedbackStore & fixture datasets
- Strict metric computations
- Desensitized JSON and CSV artefact generation
"""

import os
import csv
import json
import uuid
import datetime
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple

from .schemas import (
    EvaluationArtefact,
    RagMetrics,
    VerdictMetrics,
    to_dict,
)
from .metrics import evaluate_rag_retrieval, evaluate_verdict_predictions
from .dataset import load_rag_evaluation_dataset, load_verdict_evaluation_dataset
from repositories.vector_store import vector_store

logger = logging.getLogger(__name__)

METRIC_DEFINITIONS = {
    "Recall@k": "Tỷ lệ query có ít nhất một relevant_chunk_id trong top-k / tổng số query hợp lệ có nhãn.",
    "MRR@k": "Trung bình nghịch đảo thứ hạng (1/rank) của relevant chunk đầu tiên trong top-k. Nếu không có trong top-k thì query nhận giá trị 0.0.",
    "Accuracy": "Tỷ lệ dự đoán verdict khớp chính xác nhãn chuyên gia chuẩn hóa / tổng số sample hợp lệ.",
    "Macro-F1": "Trung bình không trọng số của F1-score trên các lớp có xuất hiện (support > 0). Báo undefined nếu dataset rỗng hoặc chỉ có 1 lớp.",
    "Anti-Leakage": "Mẫu test tuyệt đối không được inject vào prompt few-shot của Agent 2.",
    "Legacy-Protection": "Nhãn legacy non_compliant không được tự ý ánh xạ sang missing hoặc not_evidenced; phải mang trạng thái needs_label_review và loại khỏi mẫu đánh giá tự động.",
}


def _get_git_info() -> Tuple[str, str]:
    """Retrieve code version and git commit SHA safely without crashing."""
    code_version = os.getenv("CODE_VERSION", "v1.2.0-eval")
    git_sha = os.getenv("GIT_COMMIT_SHA")

    if not git_sha:
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                cwd=str(Path(__file__).parent.parent),
            )
            if res.returncode == 0:
                git_sha = res.stdout.strip()
        except Exception:
            pass

    return code_version, git_sha or "unknown"


def run_rag_evaluation(
    standard: str = "iso27001",
    split: str = "test",
    top_k: int = 5,
    custom_dataset_path: Optional[str] = None,
    mock_retriever: Optional[Callable[[str, int], List[str]]] = None,
) -> EvaluationArtefact:
    """Execute RAG retrieval evaluation against independent expert relevant_chunk_ids."""
    code_version, git_sha = _get_git_info()
    timestamp_str = datetime.datetime.utcnow().isoformat() + "Z"
    artefact_id = f"eval-rag-{uuid.uuid4().hex[:8]}"

    records, dataset_source, dataset_hash = load_rag_evaluation_dataset(
        standard=standard,
        split=split,
        custom_path=custom_dataset_path,
    )

    if not records:
        return EvaluationArtefact(
            artefact_id=artefact_id,
            timestamp=timestamp_str,
            mode="rag",
            standard=standard,
            split=split,
            code_version=code_version,
            git_commit_sha=git_sha,
            dataset_source=dataset_source,
            dataset_hash=dataset_hash,
            rag_metrics=None,
            verdict_metrics=None,
            metric_definitions=METRIC_DEFINITIONS,
            status="insufficient_data",
            status_message="Dataset RAG trống hoặc không có mẫu hợp lệ cho standard/split chỉ định.",
            source_record_ids=[],
        )

    retrieved_by_case: Dict[str, List[str]] = {}
    collection_domain = "iso_documents" if standard.lower() in ("iso27001", "all") else "tcvn11930"

    for rec in records:
        if mock_retriever is not None:
            retrieved_chunk_ids = mock_retriever(rec.query, top_k)
        else:
            try:
                # Real ChromaDB search using local BGE-M3 (no cloud LLM)
                search_results = vector_store.search(
                    query=rec.query,
                    top_k=top_k,
                    domain=collection_domain,
                )
                retrieved_chunk_ids = [doc.get("id", "") for doc in search_results if doc.get("id")]
            except Exception as e:
                logger.error(f"Error querying vector_store for case {rec.case_id}: {e}")
                retrieved_chunk_ids = []

        retrieved_by_case[rec.case_id] = retrieved_chunk_ids

    metrics = evaluate_rag_retrieval(
        records=records,
        retrieved_chunks_by_case=retrieved_by_case,
        top_k=top_k,
        collection_version=collection_domain,
        embedding_model=os.getenv("EMBEDDING_MODEL_NAME", "bge-m3"),
    )

    status = "success" if metrics.valid_queries > 0 else "insufficient_data"
    status_msg = (
        f"Hoàn tất đánh giá RAG: {metrics.valid_queries}/{metrics.total_queries} queries hợp lệ. Recall@{top_k}={metrics.recall_at_k}, MRR@{top_k}={metrics.mrr_at_k}."
        if metrics.valid_queries > 0
        else "Tất cả các query trong dataset đều thiếu relevant_chunk_ids hợp lệ (chưa gán nhãn)."
    )

    return EvaluationArtefact(
        artefact_id=artefact_id,
        timestamp=timestamp_str,
        mode="rag",
        standard=standard,
        split=split,
        code_version=code_version,
        git_commit_sha=git_sha,
        dataset_source=dataset_source,
        dataset_hash=dataset_hash,
        rag_metrics=metrics,
        verdict_metrics=None,
        metric_definitions=METRIC_DEFINITIONS,
        status=status,
        status_message=status_msg,
        source_record_ids=[r.case_id for r in records],
    )


def run_verdict_evaluation(
    standard: str = "iso27001",
    split: str = "test",
    custom_dataset_path: Optional[str] = None,
    predictions: Optional[Dict[str, str]] = None,
    mock_predictor: Optional[Callable[[Any], str]] = None,
    model_runtime: str = "local-audit-evaluator",
) -> EvaluationArtefact:
    """Execute LLM Assessment Verdict evaluation against expert ground truth verdicts."""
    code_version, git_sha = _get_git_info()
    timestamp_str = datetime.datetime.utcnow().isoformat() + "Z"
    artefact_id = f"eval-verdict-{uuid.uuid4().hex[:8]}"

    records, dataset_source, dataset_hash = load_verdict_evaluation_dataset(
        standard=standard,
        split=split,
        custom_path=custom_dataset_path,
    )

    if not records:
        return EvaluationArtefact(
            artefact_id=artefact_id,
            timestamp=timestamp_str,
            mode="verdict",
            standard=standard,
            split=split,
            code_version=code_version,
            git_commit_sha=git_sha,
            dataset_source=dataset_source,
            dataset_hash=dataset_hash,
            rag_metrics=None,
            verdict_metrics=None,
            metric_definitions=METRIC_DEFINITIONS,
            status="insufficient_data",
            status_message="Dataset verdict trống hoặc chưa có mẫu nhãn chuyên gia hợp lệ.",
            source_record_ids=[],
        )

    preds_by_case: Dict[str, str] = {}
    if predictions:
        preds_by_case.update(predictions)
    elif mock_predictor:
        for rec in records:
            preds_by_case[rec.case_id] = mock_predictor(rec)
    else:
        for rec in records:
            if rec.predicted_verdict:
                preds_by_case[rec.case_id] = rec.predicted_verdict

    metrics = evaluate_verdict_predictions(
        records=records,
        predictions_by_case=preds_by_case,
        model_runtime=model_runtime,
    )

    status = "success" if metrics.valid_samples > 0 else "insufficient_data"
    status_msg = (
        f"Hoàn tất đánh giá Verdict: {metrics.valid_samples} samples hợp lệ, {metrics.excluded_samples} bị loại (do non_compliant/lỗi nhãn). "
        f"Accuracy={metrics.accuracy}, Macro-F1={metrics.macro_f1}."
        if metrics.valid_samples > 0
        else "Không có mẫu đánh giá hợp lệ (tất cả bị loại do nhãn không chuẩn hoặc thiếu dự đoán)."
    )

    return EvaluationArtefact(
        artefact_id=artefact_id,
        timestamp=timestamp_str,
        mode="verdict",
        standard=standard,
        split=split,
        code_version=code_version,
        git_commit_sha=git_sha,
        dataset_source=dataset_source,
        dataset_hash=dataset_hash,
        rag_metrics=None,
        verdict_metrics=metrics,
        metric_definitions=METRIC_DEFINITIONS,
        status=status,
        status_message=status_msg,
        source_record_ids=[r.case_id for r in records],
    )


def save_evaluation_artefact(
    artefact: EvaluationArtefact,
    output_dir: Optional[str] = None,
) -> Tuple[Path, Optional[Path]]:
    """Save evaluation artefact as JSON and tabular CSV without raw evidence/PII."""
    if output_dir:
        out_path = Path(output_dir)
    else:
        # Default path
        candidates = [
            Path("/data/evaluations"),
            Path("data/evaluations"),
            Path(__file__).parent.parent.parent / "data" / "evaluations",
        ]
        out_path = candidates[1]
        for c in candidates:
            if c.parent.exists():
                out_path = c
                break

    out_path.mkdir(parents=True, exist_ok=True)

    ts_clean = artefact.timestamp.replace(":", "-").replace(".", "-").replace("Z", "")
    json_filename = f"eval_{ts_clean}_{artefact.mode}.json"
    csv_filename = f"eval_{ts_clean}_{artefact.mode}.csv"

    json_path = out_path / json_filename
    csv_path = out_path / csv_filename

    # Write JSON
    json_path.write_text(
        json.dumps(to_dict(artefact), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write CSV summary
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Artefact ID", artefact.artefact_id])
        writer.writerow(["Timestamp", artefact.timestamp])
        writer.writerow(["Mode", artefact.mode])
        writer.writerow(["Standard", artefact.standard])
        writer.writerow(["Split", artefact.split])
        writer.writerow(["Status", artefact.status])
        writer.writerow(["Status Message", artefact.status_message])
        writer.writerow(["Dataset Source", artefact.dataset_source])
        writer.writerow(["Dataset Hash", artefact.dataset_hash])
        writer.writerow(["Git Commit SHA", artefact.git_commit_sha or ""])

        if artefact.rag_metrics:
            writer.writerow([])
            writer.writerow(["--- RAG METRICS ---"])
            writer.writerow(["Top-K", artefact.rag_metrics.k])
            writer.writerow(["Recall@k", artefact.rag_metrics.recall_at_k])
            writer.writerow(["MRR@k", artefact.rag_metrics.mrr_at_k])
            writer.writerow(["Valid Queries", artefact.rag_metrics.valid_queries])
            writer.writerow(["Unlabeled Queries", artefact.rag_metrics.unlabeled_or_empty_queries])
            writer.writerow(["Total Queries", artefact.rag_metrics.total_queries])
            writer.writerow(["Embedding Model", artefact.rag_metrics.embedding_model])

        if artefact.verdict_metrics:
            writer.writerow([])
            writer.writerow(["--- VERDICT METRICS ---"])
            writer.writerow(["Accuracy", artefact.verdict_metrics.accuracy])
            writer.writerow(["Macro-F1", artefact.verdict_metrics.macro_f1])
            writer.writerow(["Valid Samples", artefact.verdict_metrics.valid_samples])
            writer.writerow(["Excluded Samples", artefact.verdict_metrics.excluded_samples])
            writer.writerow(["Schema Valid Rate", artefact.verdict_metrics.schema_valid_rate])
            writer.writerow(["Model Runtime", artefact.verdict_metrics.model_runtime])

    logger.info(f"Saved evaluation artefact to {json_path} and {csv_path}")
    return json_path, csv_path
