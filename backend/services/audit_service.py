"""Audit Service — Verifiable technical runtime telemetry & RAG/LLM pipeline audit trace."""

import hashlib
import json
import logging
import os
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from repositories.audit_store import audit_store, hash_sha256

logger = logging.getLogger(__name__)

# Cached code version to avoid redundant subprocess calls
_CACHED_CODE_VERSION: Optional[str] = None


def get_code_version() -> str:
    """Retrieve Git commit SHA or environment version safely without subprocess hangs."""
    global _CACHED_CODE_VERSION
    if _CACHED_CODE_VERSION is not None:
        return _CACHED_CODE_VERSION

    env_version = os.getenv("GIT_COMMIT_SHA") or os.getenv("CODE_VERSION") or os.getenv("APP_VERSION")
    if env_version:
        _CACHED_CODE_VERSION = env_version.strip()
        return _CACHED_CODE_VERSION

    # Try reading .git/HEAD directly without running subprocess
    try:
        git_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".git")
        head_file = os.path.join(git_dir, "HEAD")
        if os.path.exists(head_file):
            with open(head_file, "r", encoding="utf-8") as f:
                ref = f.read().strip()
            if ref.startswith("ref:"):
                ref_path = os.path.join(git_dir, ref.split(" ", 1)[1].strip())
                if os.path.exists(ref_path):
                    with open(ref_path, "r", encoding="utf-8") as f:
                        _CACHED_CODE_VERSION = f"git-{f.read().strip()[:8]}"
                        return _CACHED_CODE_VERSION
            elif len(ref) >= 7:
                _CACHED_CODE_VERSION = f"git-{ref[:8]}"
                return _CACHED_CODE_VERSION
    except Exception:
        pass

    _CACHED_CODE_VERSION = "v1.2.0-rel"
    return _CACHED_CODE_VERSION


@dataclass
class AuditContext:
    """Thread-safe and async-safe context object passed through assessment & chat pipelines."""
    assessment_id: Optional[str] = None
    chat_session_id: Optional[str] = None
    request_id: Optional[str] = None
    run_id: str = field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    code_version: str = field(default_factory=get_code_version)


class AuditService:
    @staticmethod
    def record_event(
        ctx: AuditContext,
        event_type: str,
        status: str,
        payload: Dict[str, Any]
    ) -> str:
        """Record an arbitrary audit event with context."""
        try:
            return audit_store.record_event(
                event_type=event_type,
                status=status,
                payload=payload,
                run_id=ctx.run_id,
                assessment_id=ctx.assessment_id,
                chat_session_id=ctx.chat_session_id,
                request_id=ctx.request_id,
                code_version=ctx.code_version or get_code_version(),
            )
        except Exception as e:
            logger.error(f"[AuditService] Failed to record event {event_type}: {e}")
            return ""

    @staticmethod
    def record_assessment_created(
        ctx: AuditContext,
        standard: str,
        model_mode: str,
        org_name: str,
        implemented_controls_count: int,
        total_controls: int,
        has_evidence: bool,
    ) -> str:
        payload = {
            "standard": standard,
            "model_mode": model_mode,
            "org_name_redacted": org_name[:3] + "***" if len(org_name) > 3 else "***",
            "implemented_controls_count": implemented_controls_count,
            "total_controls": total_controls,
            "has_evidence": has_evidence,
        }
        return AuditService.record_event(ctx, "assessment_created", "completed", payload)

    @staticmethod
    def record_evidence_parsed(
        ctx: AuditContext,
        evidence_controls_count: int,
        total_files: int,
        file_extensions: List[str],
    ) -> str:
        payload = {
            "evidence_controls_count": evidence_controls_count,
            "total_files": total_files,
            "file_extensions": list(set(file_extensions or [])),
            "parser_engine": "tesseract_ocr_and_native_parsers",
        }
        return AuditService.record_event(ctx, "evidence_parsed", "completed", payload)

    @staticmethod
    def record_privacy_filter(
        ctx: AuditContext,
        mode: str,
        redaction_applied: bool,
        char_count_before: int,
        char_count_after: int,
    ) -> str:
        payload = {
            "privacy_mode": mode,
            "redaction_applied": redaction_applied,
            "char_count_before": char_count_before,
            "char_count_after": char_count_after,
            "sanitizers": ["indirect_injection_sanitizer", "pii_regex_scrubber"],
        }
        return AuditService.record_event(ctx, "privacy_filter_completed", "completed", payload)

    @staticmethod
    def record_rag_query(
        ctx: AuditContext,
        collection_name: str,
        query_text: str,
        top_k: int,
        results: List[Dict[str, Any]],
        knowledge_base_version: str = "kb_v2026.08",
        embedding_provider: str = "ollama",
        embedding_model: str = "bge-m3:latest",
        embedding_dimensions: int = 1024,
        distance_metric: str = "cosine",
    ) -> str:
        ranked_results = []
        for rank, r in enumerate(results or [], start=1):
            ranked_results.append({
                "rank": rank,
                "record_id": f"{r.get('source', 'unknown')}_{r.get('chunk_index', 0)}",
                "source_file": r.get("file", ""),
                "clause_or_title": r.get("doc_title", "")[:80],
                "score": round(float(r.get("score", 0.0)), 4),
            })

        payload = {
            "assessment_id": ctx.assessment_id or "",
            "run_id": ctx.run_id or "",
            "code_version": ctx.code_version or get_code_version(),
            "collection_name": collection_name,
            "knowledge_base_version": knowledge_base_version,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "embedding_dimensions": embedding_dimensions,
            "distance_metric": distance_metric,
            "top_k": top_k,
            "results_count": len(ranked_results),
            "query_hash": f"sha256:{hash_sha256(query_text)}",
            "ranked_results": ranked_results,
        }
        return AuditService.record_event(ctx, "rag_query_completed", "completed", payload)

    @staticmethod
    def record_llm_inference_start(
        ctx: AuditContext,
        phase: str,
        requested_model: str,
        provider: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        payload = {
            "phase": phase,
            "requested_model": requested_model,
            "provider": provider,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        return AuditService.record_event(ctx, "llm_inference_started", "started", payload)

    @staticmethod
    def record_llm_inference_completed(
        ctx: AuditContext,
        phase: str,
        requested_model: str,
        actual_model: str,
        provider: str,
        started_at: str,
        completed_at: str,
        prompt_text: str,
        response_text: str,
        fallback_used: bool = False,
        fallback_reason: Optional[str] = None,
        usage_metrics: Optional[Dict[str, Any]] = None,
        output_schema_valid: bool = True,
    ) -> str:
        payload = {
            "phase": phase,
            "requested_model": requested_model,
            "actual_model": actual_model or requested_model,
            "provider": provider,
            "started_at": started_at,
            "completed_at": completed_at,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
            "prompt_hash": f"sha256:{hash_sha256(prompt_text)}",
            "response_hash": f"sha256:{hash_sha256(response_text)}",
            "response_chars_length": len(response_text or ""),
            "usage_metrics": usage_metrics or {},
            "output_schema_valid": output_schema_valid,
        }
        return AuditService.record_event(ctx, "llm_inference_completed", "completed", payload)

    @staticmethod
    def record_json_validation(
        ctx: AuditContext,
        phase: str,
        valid: bool,
        items_count: int,
        repaired_by_ast: bool = False,
        schema_version: str = "1.0",
    ) -> str:
        payload = {
            "phase": phase,
            "output_schema_valid": valid,
            "items_count": items_count,
            "repaired_by_ast": repaired_by_ast,
            "schema_version": schema_version,
        }
        return AuditService.record_event(ctx, "json_schema_validated", "completed" if valid else "warning", payload)

    @staticmethod
    def record_score_calculated(
        ctx: AuditContext,
        standard: str,
        score: float,
        max_score: float,
        percentage: float,
        scoring_algorithm: str = "hierarchical_weighted",
    ) -> str:
        payload = {
            "standard": standard,
            "score": score,
            "max_score": max_score,
            "compliance_percentage": percentage,
            "scoring_algorithm": scoring_algorithm,
        }
        return AuditService.record_event(ctx, "score_calculated", "completed", payload)

    @staticmethod
    def record_assessment_completed(
        ctx: AuditContext,
        standard: str,
        compliance_percentage: float,
        total_duration_seconds: float,
    ) -> str:
        payload = {
            "standard": standard,
            "compliance_percentage": compliance_percentage,
            "total_duration_seconds": round(total_duration_seconds, 3),
        }
        evt_id = AuditService.record_event(ctx, "assessment_completed", "completed", payload)
        if ctx.assessment_id:
            try:
                AuditService.export_audit_trace_json(ctx.assessment_id)
            except Exception as e:
                logger.warning(f"Failed to auto-export audit trace JSON for {ctx.assessment_id}: {e}")
        return evt_id

    @staticmethod
    def record_assessment_failed(
        ctx: AuditContext,
        error_type: str,
        error_stage: str,
        message_redacted: str,
    ) -> str:
        payload = {
            "error_type": error_type,
            "error_stage": error_stage,
            "message": message_redacted[:200],
        }
        return AuditService.record_event(ctx, "assessment_failed", "failed", payload)

    @staticmethod
    def record_report_exported(
        ctx: AuditContext,
        export_format: str,
        file_size_bytes: int,
        file_hash: Optional[str] = None,
    ) -> str:
        payload = {
            "assessment_id": ctx.assessment_id,
            "run_id": ctx.run_id,
            "code_version": ctx.code_version,
            "export_format": export_format,
            "file_size_bytes": file_size_bytes,
            "file_hash": file_hash or "",
        }
        return AuditService.record_event(ctx, "report_exported", "completed", payload)

    @staticmethod
    def export_audit_trace_json(assessment_id: str, output_path: Optional[str] = None) -> str:
        """Export all recorded audit events for an assessment to a standardized JSON artifact."""
        events = audit_store.get_events_by_assessment(assessment_id)
        trace_data = {
            "assessment_id": assessment_id,
            "run_id": events[0].get("run_id") if events else "run_default",
            "code_version": events[0].get("code_version") if events else get_code_version(),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_events": len(events),
            "events": events,
        }
        data_dir = os.getenv("DATA_PATH", "./data")
        target_path = output_path or os.path.join(data_dir, "audit_traces", f"{assessment_id}.json")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, ensure_ascii=False, indent=2)
        return target_path


audit_service = AuditService()

