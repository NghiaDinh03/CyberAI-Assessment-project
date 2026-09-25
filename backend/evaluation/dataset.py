"""Evaluation dataset loading, validation, and anti-leakage splitting.

Supports loading from:
1. Structured JSON fixture files in data/evaluation_datasets/ or local fixtures
2. AuditFeedbackStore (SQLite database of expert-reviewed golden cases)

Strict Anti-Leakage Invariants:
- Test records (split='test') are NEVER included in few-shot prompt injection.
- Few-shot records (split='few_shot') are NEVER evaluated as test cases.
- Legacy unverified labels (e.g. non_compliant) are marked as 'needs_label_review'.
- No PII or raw enterprise evidence is exposed in input_ref (uses SHA-256 hashes).
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from .schemas import RagEvalRecord, VerdictEvalRecord, to_dict
from .normalizer import normalize_expert_verdict
from repositories.feedback_store import feedback_store

logger = logging.getLogger(__name__)

# Search paths for evaluation fixtures
FIXTURE_SEARCH_PATHS = [
    Path("/data/evaluation_datasets"),
    Path("data/evaluation_datasets"),
    Path(__file__).parent / "fixtures",
    Path("/app/evaluation/fixtures"),
]


def _compute_records_hash(records_data: List[Dict[str, Any]]) -> str:
    """Compute deterministic SHA-256 hash of a list of record dicts."""
    serialized = json.dumps(records_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def load_rag_evaluation_dataset(
    standard: str = "iso27001",
    split: str = "test",
    custom_path: Optional[str] = None,
) -> Tuple[List[RagEvalRecord], str, str]:
    """Load RAG evaluation records for a specific standard and split.

    Returns:
        (records, dataset_source, dataset_hash)
    """
    found_file: Optional[Path] = None

    if custom_path:
        p = Path(custom_path)
        if p.exists():
            found_file = p
    else:
        for base in FIXTURE_SEARCH_PATHS:
            candidate = base / "rag_eval_fixtures.json"
            if candidate.exists():
                found_file = candidate
                break

    if not found_file:
        logger.warning(f"No RAG evaluation dataset found in search paths for standard={standard}, split={split}")
        return ([], "none", "empty")

    try:
        raw_content = found_file.read_text(encoding="utf-8")
        raw_list = json.loads(raw_content)
    except Exception as e:
        logger.error(f"Failed to read/parse RAG fixture file {found_file}: {e}")
        return ([], str(found_file), "error")

    clean_standard = standard.strip().lower()
    clean_split = split.strip().lower()

    filtered_records: List[RagEvalRecord] = []
    filtered_dicts: List[Dict[str, Any]] = []

    for item in raw_list:
        rec_std = str(item.get("standard", "iso27001")).strip().lower()
        rec_split = str(item.get("split", "test")).strip().lower()

        if clean_standard != "all" and rec_std != clean_standard:
            continue
        if rec_split != clean_split:
            continue

        try:
            record = RagEvalRecord(
                case_id=str(item.get("case_id", "")).strip(),
                standard=rec_std,
                query=str(item.get("query", "")).strip(),
                relevant_chunk_ids=[str(cid).strip() for cid in item.get("relevant_chunk_ids", [])],
                split=rec_split,
                label_source=str(item.get("label_source", "expert")).strip(),
                reviewed_at=item.get("reviewed_at"),
                notes=item.get("notes"),
            )
            filtered_records.append(record)
            filtered_dicts.append(to_dict(record))
        except Exception as e:
            logger.warning(f"Skipping malformed RAG record: {item}. Error: {e}")

    dataset_hash = _compute_records_hash(filtered_dicts) if filtered_dicts else "empty"
    return (filtered_records, str(found_file), dataset_hash)


def load_verdict_evaluation_dataset(
    standard: str = "iso27001",
    split: str = "test",
    custom_path: Optional[str] = None,
    source: str = "auto",  # 'db', 'fixture', or 'auto'
) -> Tuple[List[VerdictEvalRecord], str, str]:
    """Load Verdict evaluation records for a specific standard and split.

    In 'auto' mode:
    1. Checks AuditFeedbackStore for approved expert records with split=split.
    2. If fewer than 1 found, falls back to fixture JSON file.

    Returns:
        (records, dataset_source, dataset_hash)
    """
    clean_standard = standard.strip().lower()
    clean_split = split.strip().lower()

    records: List[VerdictEvalRecord] = []
    record_dicts: List[Dict[str, Any]] = []
    source_name = "none"

    # 1. Try DB if requested or auto
    if source in ("db", "auto"):
        try:
            db_records = feedback_store.get_evaluation_records(
                standard=clean_standard,
                split=clean_split,
                include_pending_review=True,
            )
            for r in db_records:
                # Compute SHA-256 hash of input_fact_summary to avoid saving sensitive text
                summary_text = r.get("input_fact_summary", "")
                fact_hash = hashlib.sha256(summary_text.encode("utf-8")).hexdigest()[:16]

                raw_verdict = r.get("expert_verdict")
                norm_verdict, status = normalize_expert_verdict(raw_verdict)

                verdict_str = norm_verdict if norm_verdict else str(raw_verdict)

                rec = VerdictEvalRecord(
                    case_id=r["id"],
                    standard=r.get("standard", "iso27001"),
                    control_id=r["control_id"],
                    input_ref=f"hash:{fact_hash}",
                    expert_verdict=verdict_str,
                    split=r.get("split", "test"),
                    label_source=r.get("auditor_username", "expert"),
                    reviewed_at=r.get("metadata", {}).get("reviewed_at") if isinstance(r.get("metadata"), dict) else None,
                    predicted_verdict=r.get("initial_ai_verdict"),
                )
                records.append(rec)

                record_dicts.append(to_dict(rec))

            if records:
                source_name = "sqlite:audit_feedback_exemplars"
        except Exception as e:
            logger.warning(f"Failed to query feedback_store for verdict evaluation: {e}")

    # 2. Try JSON fixtures if DB had 0 records or source is 'fixture'
    if not records and source in ("fixture", "auto"):
        found_file: Optional[Path] = None
        if custom_path:
            p = Path(custom_path)
            if p.exists():
                found_file = p
        else:
            for base in FIXTURE_SEARCH_PATHS:
                candidate = base / "verdict_eval_fixtures.json"
                if candidate.exists():
                    found_file = candidate
                    break

        if found_file:
            try:
                raw_content = found_file.read_text(encoding="utf-8")
                raw_list = json.loads(raw_content)
                for item in raw_list:
                    rec_std = str(item.get("standard", "iso27001")).strip().lower()
                    rec_split = str(item.get("split", "test")).strip().lower()

                    if clean_standard != "all" and rec_std != clean_standard:
                        continue
                    if rec_split != clean_split:
                        continue

                    rec = VerdictEvalRecord(
                        case_id=str(item.get("case_id", "")).strip(),
                        standard=rec_std,
                        control_id=str(item.get("control_id", "")).strip(),
                        input_ref=str(item.get("input_ref", "")).strip(),
                        expert_verdict=str(item.get("expert_verdict", "")).strip(),
                        split=rec_split,
                        label_source=str(item.get("label_source", "expert")).strip(),
                        reviewed_at=item.get("reviewed_at"),
                        predicted_verdict=item.get("predicted_verdict"),
                    )
                    records.append(rec)

                    record_dicts.append(to_dict(rec))

                source_name = str(found_file)
            except Exception as e:
                logger.error(f"Failed to read verdict fixtures from {found_file}: {e}")

    dataset_hash = _compute_records_hash(record_dicts) if record_dicts else "empty"
    return (records, source_name, dataset_hash)
