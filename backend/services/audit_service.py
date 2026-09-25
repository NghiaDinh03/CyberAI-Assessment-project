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


def get_git_short_sha() -> str:
    """Retrieve Git commit short SHA safely from env, .git_version, or .git repo."""
    env_sha = os.getenv("GIT_COMMIT_SHA")
    if env_sha:
        return env_sha.strip()[:8]
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ver_file = os.path.join(base_dir, ".git_version")
        if os.path.exists(ver_file):
            with open(ver_file, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    return c[:8]
    except Exception:
        pass
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
                        return f.read().strip()[:8]
            elif len(ref) >= 7:
                return ref[:8]
    except Exception:
        pass
    return "c79037e"


def get_code_version() -> str:
    """Retrieve canonical code version (v1.2.0-verdict)."""
    global _CACHED_CODE_VERSION
    if _CACHED_CODE_VERSION is not None:
        return _CACHED_CODE_VERSION

    env_version = os.getenv("CODE_VERSION") or os.getenv("APP_VERSION")
    if env_version and env_version.strip() != "v1.2.0-rel":
        _CACHED_CODE_VERSION = env_version.strip()
        return _CACHED_CODE_VERSION

    _CACHED_CODE_VERSION = "v1.2.0-verdict"
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
        evidence_manifest_id: Optional[str] = None,
        control_mapping: Optional[Any] = None,
        file_hashes: Optional[Dict[str, str]] = None,
        evidence_source: str = "uploaded_evidence",
        files: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        # Invariant: total_files counts unique evidence_id / SHA-256
        if files:
            unique_ids = {f.get("sha256") or f.get("evidence_id") or f.get("file_name") for f in files if isinstance(f, dict)}
            calc_total = len(unique_ids)
        elif file_hashes:
            calc_total = len(file_hashes)
        else:
            calc_total = total_files

        payload = {
            "evidence_controls_count": evidence_controls_count,
            "total_files": calc_total,
            "file_extensions": list(set(file_extensions or [])),
            "parser_engine": "tesseract_ocr_and_native_parsers",
            "evidence_manifest_id": evidence_manifest_id or f"manifest_{ctx.assessment_id}",
            "evidence_source": evidence_source,
            "control_mapping": control_mapping or {},
            "file_hashes": file_hashes or {},
            "files": files or [],
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
    def record_missing_control_verdict(
        ctx: AuditContext,
        control_id: str,
        phase: str,
        raw_response: str,
        parse_or_drop_reason: str,
        fallback_verdict: str = "needs_expert_review",
    ) -> str:
        payload = {
            "control_id": control_id,
            "phase": phase,
            "raw_response_hash": f"sha256:{hash_sha256(raw_response or '')}",
            "raw_response_chars": len(raw_response or ""),
            "parse_or_drop_reason": parse_or_drop_reason,
            "fallback_verdict": fallback_verdict,
        }
        return AuditService.record_event(ctx, "missing_control_verdict_from_llm", "warning", payload)

    @staticmethod
    def record_score_calculated(
        ctx: AuditContext,
        standard: str,
        weighted_score: float = None,
        weighted_max_score: float = None,
        weighted_compliance_percentage: float = None,
        raw_coverage_percentage: float = 0.0,
        satisfied_count: int = 0,
        partial_count: int = 0,
        not_evidenced_count: int = 0,
        missing_count: int = 0,
        needs_expert_review_count: int = 0,
        algorithm: str = "verdict_weighted_v2",
        # Legacy parameter compatibility:
        score: float = None,
        max_score: float = None,
        percentage: float = None,
        scoring_algorithm: str = None,
    ) -> str:
        eff_w_score = weighted_score if weighted_score is not None else (score if score is not None else 0.0)
        eff_w_max = weighted_max_score if weighted_max_score is not None else (max_score if max_score is not None else 0.0)
        eff_pct = weighted_compliance_percentage if weighted_compliance_percentage is not None else (percentage if percentage is not None else 0.0)
        eff_algo = algorithm or scoring_algorithm or "verdict_weighted_v2"

        payload = {
            "standard": standard,
            "algorithm": eff_algo,
            "raw_coverage_percentage": round(float(raw_coverage_percentage), 1),
            "weighted_score": round(float(eff_w_score), 1),
            "weighted_max_score": round(float(eff_w_max), 1),
            "weighted_compliance_percentage": round(float(eff_pct), 1),
            "satisfied_count": satisfied_count,
            "partial_count": partial_count,
            "not_evidenced_count": not_evidenced_count,
            "missing_count": missing_count,
            "needs_expert_review_count": needs_expert_review_count,
            # Legacy fields for backward compatibility
            "score": round(float(eff_w_score), 1),
            "max_score": round(float(eff_w_max), 1),
            "compliance_percentage": round(float(eff_pct), 1),
            "scoring_algorithm": eff_algo,
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
    def record_artifact_exported(
        ctx: AuditContext,
        export_format: str,
        filename: str,
        file_size_bytes: int,
        file_hash_sha256: str,
    ) -> str:
        payload = {
            "assessment_id": ctx.assessment_id,
            "run_id": ctx.run_id,
            "code_version": ctx.code_version,
            "export_format": export_format,
            "filename": filename,
            "file_size_bytes": file_size_bytes,
            "file_hash_sha256": file_hash_sha256,
            "file_hash": file_hash_sha256,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        eid = AuditService.record_event(ctx, "artifact_exported", "completed", payload)
        AuditService.record_event(ctx, "report_exported", "completed", payload)
        try:
            if ctx.assessment_id:
                AuditService.export_audit_trace_json(ctx.assessment_id, run_id=ctx.run_id)
        except Exception:
            pass
        return eid

    @staticmethod
    def record_report_exported(
        ctx: AuditContext,
        export_format: str,
        file_size_bytes: int,
        file_hash: Optional[str] = None,
        filename: Optional[str] = None,
        file_hash_sha256: Optional[str] = None,
    ) -> str:
        hash_val = file_hash_sha256 or file_hash or ""
        fn = filename or f"export_{export_format}"
        return AuditService.record_artifact_exported(
            ctx=ctx,
            export_format=export_format,
            filename=fn,
            file_size_bytes=file_size_bytes,
            file_hash_sha256=hash_val,
        )

    @staticmethod
    def record_control_verdict_resolved(
        ctx: AuditContext,
        control_id: str,
        chunk_id: Optional[str],
        ai_verdict_raw: Optional[str],
        normalized_ai_verdict: Optional[str],
        verdict: str,
        verdict_source: str,
        fallback_reason: Optional[str] = None,
        conflict_detected: bool = False,
        citation_count: int = 0,
        evidence_ids: Optional[List[str]] = None,
        duration_ms: int = 0,
    ) -> str:
        payload = {
            "control_id": control_id,
            "chunk_id": chunk_id or "phase1_synthesis",
            "ai_verdict_raw": ai_verdict_raw,
            "normalized_ai_verdict": normalized_ai_verdict,
            "verdict": verdict,
            "verdict_source": verdict_source,
            "fallback_reason": fallback_reason,
            "conflict_detected": conflict_detected,
            "citation_count": citation_count,
            "evidence_ids": evidence_ids or [],
            "duration_ms": duration_ms,
        }
        return AuditService.record_event(ctx, "control_verdict_resolved", "completed", payload)

    @staticmethod
    def record_verdict_overridden(
        ctx: AuditContext,
        control_id: str,
        old_verdict: str,
        new_verdict: str,
        reason: str,
        phase: str = "final_synthesis",
    ) -> str:
        payload = {
            "control_id": control_id,
            "old_verdict": old_verdict,
            "new_verdict": new_verdict,
            "reason": reason,
            "phase": phase,
        }
        return AuditService.record_event(ctx, "verdict_overridden", "warning", payload)

    @staticmethod
    def record_chunk_telemetry(
        ctx: AuditContext,
        chunk_id: str,
        control_count: int,
        prompt_tokens: int,
        completion_tokens: int,
        retrieval_duration_ms: int,
        llm_duration_ms: int,
        validation_duration_ms: int,
        merge_duration_ms: int,
        total_chunk_duration_ms: int,
        model: str,
        provider: str = "ollama",
        queue_wait_ms: int = 0,
    ) -> str:
        payload = {
            "chunk_id": chunk_id,
            "control_count": control_count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "retrieval_duration_ms": retrieval_duration_ms,
            "llm_duration_ms": llm_duration_ms,
            "validation_duration_ms": validation_duration_ms,
            "merge_duration_ms": merge_duration_ms,
            "total_chunk_duration_ms": total_chunk_duration_ms,
            "queue_wait_ms": queue_wait_ms,
            "model": model,
            "provider": provider,
        }
        return AuditService.record_event(ctx, "chunk_telemetry", "completed", payload)

    @staticmethod
    def record_runtime_summary(
        ctx: AuditContext,
        total_duration_seconds: float,
        total_llm_duration_seconds: float,
        slowest_chunks: List[Dict[str, Any]],
        controls_per_chunk: Dict[str, int],
        number_of_llm_calls: int,
        average_seconds_per_control: float,
    ) -> str:
        payload = {
            "total_duration_seconds": round(total_duration_seconds, 3),
            "total_llm_duration_seconds": round(total_llm_duration_seconds, 3),
            "slowest_chunks": slowest_chunks,
            "controls_per_chunk": controls_per_chunk,
            "number_of_llm_calls": number_of_llm_calls,
            "average_seconds_per_control": round(average_seconds_per_control, 3),
        }
        return AuditService.record_event(ctx, "runtime_summary", "completed", payload)

    @staticmethod
    def export_audit_trace_json(assessment_id: str, run_id: Optional[str] = None, output_path: Optional[str] = None) -> str:
        """Export recorded audit events strictly filtered by assessment_id AND run_id to a standardized JSON artifact."""
        trace_data = audit_store.export_trace_dict(assessment_id=assessment_id, run_id=run_id)
        data_dir = os.getenv("DATA_PATH", "./data")
        target_path = output_path or os.path.join(data_dir, "audit_traces", f"{assessment_id}.json")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, ensure_ascii=False, indent=2)
        return target_path


audit_service = AuditService()

