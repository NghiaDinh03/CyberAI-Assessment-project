"""Automated Verification & Integrity Tests for Verifiable Audit Trace System."""

import json
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
import pytest

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from repositories.audit_store import AuditStore, hash_sha256
from services.audit_service import AuditService, AuditContext


@pytest.fixture
def isolated_audit_store():
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    store = AuditStore(db_path=temp_db.name)
    yield store
    if os.path.exists(temp_db.name):
        try:
            os.unlink(temp_db.name)
        except Exception:
            pass


def test_append_only_event_creation(isolated_audit_store):
    """Verify audit events are recorded idempotently and chronologically."""
    aid = "test-assess-101"
    run_id = "run-abc-123"
    ctx = AuditContext(assessment_id=aid, run_id=run_id, code_version="v1.2.0-test")

    # 1. assessment_created
    evt1 = isolated_audit_store.record_event(
        event_type="assessment_created",
        status="completed",
        payload={"standard": "iso27001", "implemented_count": 45, "total_controls": 93},
        run_id=ctx.run_id,
        assessment_id=ctx.assessment_id,
        code_version=ctx.code_version,
    )
    assert evt1.startswith("evt_")

    # 2. rag_query_completed
    evt2 = isolated_audit_store.record_event(
        event_type="rag_query_completed",
        status="completed",
        payload={
            "collection_name": "iso27001",
            "top_k": 2,
            "query_hash": f"sha256:{hash_sha256('A.5 Org controls')}",
            "ranked_results": [
                {"rank": 1, "record_id": "iso_0", "score": 0.895}
            ]
        },
        run_id=ctx.run_id,
        assessment_id=ctx.assessment_id,
        code_version=ctx.code_version,
    )
    assert evt2.startswith("evt_")

    events = isolated_audit_store.get_events_by_assessment(aid)
    assert len(events) == 2
    assert events[0]["event_type"] == "assessment_created"
    assert events[1]["event_type"] == "rag_query_completed"
    assert events[0]["assessment_id"] == aid
    assert events[1]["assessment_id"] == aid
    assert events[0]["run_id"] == run_id
    assert events[1]["run_id"] == run_id


def test_pii_and_secret_redaction(isolated_audit_store):
    """Verify prompt, response, password, token, API keys and raw contents are strictly redacted/hashed."""
    aid = "test-redact-202"
    run_id = "run-xyz-789"
    ctx = AuditContext(assessment_id=aid, run_id=run_id)

    raw_sensitive_payload = {
        "prompt": "Here is confidential password123 and user@company.com",
        "response": "The private server IP is 192.168.1.50 with token secret-jwt-xyz",
        "api_key": "sk-1234567890abcdef",
        "authorization": "Bearer eyJhbGciOi...",
        "safe_metadata": {
            "top_k": 5,
            "status": "ok",
            "nested_token": "bearer-token-val"
        }
    }

    isolated_audit_store.record_event(
        event_type="llm_inference_completed",
        status="completed",
        payload=raw_sensitive_payload,
        run_id=ctx.run_id,
        assessment_id=ctx.assessment_id,
    )

    events = isolated_audit_store.get_events_by_assessment(aid)
    assert len(events) == 1
    payload = events[0]["payload"]

    # Confirm sensitive strings are redacted or hashed
    assert "password123" not in json.dumps(payload)
    assert "user@company.com" not in json.dumps(payload)
    assert "192.168.1.50" not in json.dumps(payload)
    assert "sk-1234567890abcdef" not in json.dumps(payload)
    assert "secret-jwt-xyz" not in json.dumps(payload)
    assert "REDACTED" in str(payload.get("prompt"))
    assert "REDACTED" in str(payload.get("response"))
    assert "REDACTED" in str(payload.get("api_key"))


def test_rag_and_llm_event_schema(isolated_audit_store):
    """Verify RAG query and LLM inference events store required audit telemetry."""
    aid = "assess-schema-404"
    run_id = "run-schema-505"
    ctx = AuditContext(assessment_id=aid, run_id=run_id)

    # 1. RAG query completed
    rag_results = [
        {"source": "iso27001", "chunk_index": 1, "file": "iso27001.md", "doc_title": "A.5 Org", "score": 0.942},
        {"source": "iso27001", "chunk_index": 2, "file": "iso27001.md", "doc_title": "A.6 People", "score": 0.881}
    ]
    with patch("services.audit_service.audit_store", isolated_audit_store):
        AuditService.record_rag_query(
            ctx=ctx,
            collection_name="iso27001",
            query_text="A.5 Information security policies",
            top_k=2,
            results=rag_results,
            knowledge_base_version="kb_v2026.08",
        )

        # 2. LLM Inference completed
        AuditService.record_llm_inference_completed(
            ctx=ctx,
            phase="phase1_gap_analysis",
            requested_model="gemma4:latest",
            actual_model="gemma4:latest",
            provider="ollama",
            started_at="2026-08-26T00:00:00Z",
            completed_at="2026-08-26T00:00:03Z",
            prompt_text="Detailed confidential prompt",
            response_text='[{"id":"A.5.1","severity":"medium"}]',
            fallback_used=False,
            usage_metrics={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "total_duration_ns": 3000000000
            },
            output_schema_valid=True
        )

    events = isolated_audit_store.get_events_by_assessment(aid)
    assert len(events) == 2

    # Verify RAG event
    rag_ev = events[0]
    assert rag_ev["event_type"] == "rag_query_completed"
    assert rag_ev["payload"]["collection_name"] == "iso27001"
    assert rag_ev["payload"]["knowledge_base_version"] == "kb_v2026.08"
    assert rag_ev["payload"]["query_hash"].startswith("sha256:")
    assert len(rag_ev["payload"]["ranked_results"]) == 2
    assert rag_ev["payload"]["ranked_results"][0]["rank"] == 1
    assert rag_ev["payload"]["ranked_results"][0]["score"] == 0.942

    # Verify LLM event
    llm_ev = events[1]
    assert llm_ev["event_type"] == "llm_inference_completed"
    assert llm_ev["payload"]["actual_model"] == "gemma4:latest"
    assert llm_ev["payload"]["provider"] == "ollama"
    assert "REDACTED_HASH:" in llm_ev["payload"]["prompt_hash"]
    assert "REDACTED_HASH:" in llm_ev["payload"]["response_hash"]
    assert llm_ev["payload"]["usage_metrics"]["total_tokens"] == 150
    assert llm_ev["payload"]["output_schema_valid"] is True


def test_full_pipeline_lifecycle_tracing(isolated_audit_store):
    """Verify complete assessment lifecycle sequence, same assessment_id, and completed order."""
    aid = "assess-full-lifecycle-777"
    run_id = "run-lifecycle-888"
    ctx = AuditContext(assessment_id=aid, run_id=run_id)

    with patch("services.audit_service.audit_store", isolated_audit_store):
        # 1. Created
        AuditService.record_assessment_created(
            ctx=ctx, standard="iso27001", model_mode="local", org_name="Acme Corp",
            implemented_controls_count=10, total_controls=93, has_evidence=True
        )
        # 2. Evidence parsed
        AuditService.record_evidence_parsed(
            ctx=ctx, evidence_controls_count=5, total_files=3, file_extensions=[".png", ".pdf"]
        )
        # 3. Privacy filter
        AuditService.record_privacy_filter(
            ctx=ctx, mode="local", redaction_applied=True, char_count_before=500, char_count_after=420
        )
        # 4. RAG query
        AuditService.record_rag_query(
            ctx=ctx, collection_name="iso27001", query_text="ISO controls", top_k=2, results=[]
        )
        # 5. LLM start
        AuditService.record_llm_inference_start(
            ctx=ctx, phase="phase1", requested_model="gemma4:latest", provider="ollama", temperature=0.1, max_tokens=4096
        )
        # 6. LLM completed
        AuditService.record_llm_inference_completed(
            ctx=ctx, phase="phase1", requested_model="gemma4:latest", actual_model="gemma4:latest",
            provider="ollama", started_at="2026-08-26T00:00:00Z", completed_at="2026-08-26T00:00:02Z",
            prompt_text="prompt", response_text="response"
        )
        # 7. JSON validation
        AuditService.record_json_validation(
            ctx=ctx, phase="phase1", valid=True, items_count=5
        )
        # 8. Score calculation
        AuditService.record_score_calculated(
            ctx=ctx, standard="iso27001", score=10, max_score=93, percentage=10.8
        )
        # 9. Assessment completed
        AuditService.record_assessment_completed(
            ctx=ctx, standard="iso27001", compliance_percentage=10.8, total_duration_seconds=2.4
        )

    events = isolated_audit_store.get_events_by_assessment(aid)
    assert len(events) == 9

    expected_types = [
        "assessment_created",
        "evidence_parsed",
        "privacy_filter_completed",
        "rag_query_completed",
        "llm_inference_started",
        "llm_inference_completed",
        "json_schema_validated",
        "score_calculated",
        "assessment_completed",
    ]
    actual_types = [e["event_type"] for e in events]
    assert actual_types == expected_types

    # Confirm all events have the same assessment_id and run_id
    for ev in events:
        assert ev["assessment_id"] == aid
        assert ev["run_id"] == run_id

    # Confirm assessment_completed occurs strictly after JSON validation and score calculation
    val_idx = actual_types.index("json_schema_validated")
    score_idx = actual_types.index("score_calculated")
    comp_idx = actual_types.index("assessment_completed")
    assert comp_idx > val_idx
    assert comp_idx > score_idx


if __name__ == "__main__":
    t_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    t_db.close()
    t_store = AuditStore(db_path=t_db.name)
    test_append_only_event_creation(t_store)
    test_pii_and_secret_redaction(t_store)
    test_rag_and_llm_event_schema(t_store)
    test_full_pipeline_lifecycle_tracing(t_store)
    try:
        os.unlink(t_db.name)
    except Exception:
        pass
    print("ALL 4 AUDIT TRACE INTEGRITY TESTS PASSED (100% OK)!")

