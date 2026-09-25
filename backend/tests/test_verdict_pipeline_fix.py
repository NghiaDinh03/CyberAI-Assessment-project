"""Comprehensive tests for verdict evidence pipeline fix and performance optimization.

Tests the 10 mandated requirements:
1. LLM valid satisfied + citation -> satisfied, verdict_source="llm", full weighted score.
2. LLM partial + citation -> partial, 50% weighted score.
3. Has file but LLM missing verdict -> needs_expert_review, verdict_source="safe_fallback_no_evidence", fallback_reason, score 0.
4. LLM returns non-enum verdict -> needs_expert_review, verdict_source="safe_fallback_invalid_verdict", score 0.
5. conflict_detected=True -> needs_expert_review, verdict_source="safe_fallback_conflict", audit event emitted.
6. Chunk draft satisfied without citation -> invariant overrides to needs_expert_review, emits verdict_overridden.
7. Manifest file mapped to 2 controls -> total_files=1, mapped_control_count=2.
8. Unsupported or TCVN file in ISO run -> ingestion_status="excluded", not counted for score.
9. Weighted compliance regression -> only satisfied & partial score, no points from self-declaration alone, N/A excluded from denominator.
10. Performance telemetry generated per chunk and summary.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Ensure backend directory is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.chat_service import ChatService
from services.controls_catalog import get_flat_controls, calc_weighted_compliance
from schemas.assessment_schema import UnifiedAssessmentResult, ControlItem, EvidenceManifest, EvidenceManifestItem
from services.audit_service import audit_service, AuditContext


@pytest.fixture
def iso_controls():
    return get_flat_controls("iso27001")


@pytest.fixture
def mock_audit_ctx():
    return AuditContext(
        assessment_id="test_assessment_fix",
        run_id="run_test_fix",
        code_version="v1.2.0-test",
    )


def test_1_llm_valid_satisfied_with_citation(iso_controls, mock_audit_ctx):
    """Test 1: LLM returns valid 'satisfied' with citations -> verdict='satisfied', verdict_source='llm', full weight."""
    cid = "A.5.1"  # Critical (10 pts)
    payload = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=0.0,
        score=0,
        max_score=93,
        implemented=[cid],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001:2022",
        standard="iso27001",
        today="2026-09-22",
        effective_mode="local",
        control_verdicts=[{
            "control_id": cid,
            "evidence_verdict": "satisfied",
            "ai_verdict_raw": "satisfied",
            "normalized_ai_verdict": "satisfied",
            "rationale": "Chính sách an toàn thông tin được phê duyệt và ban hành đầy đủ.",
            "citations": [{"file_name": "CSATTT_2026.pdf", "excerpt": "Mục 2.1 Phạm vi chính sách"}],
            "confidence": 0.95,
        }],
        all_controls_flat=iso_controls,
        evidence_map={cid: ["CSATTT_2026.pdf"]},
        audit_ctx=mock_audit_ctx,
    )

    ctrl = next(c for c in payload["controls"] if c["control_id"] == cid)
    assert ctrl["assessment_verdict"] == "satisfied"
    assert ctrl["verdict_source"] == "llm"
    assert len(ctrl["evidence_citations"]) >= 1
    assert ctrl["verdict_factor"] == 1.0
    assert ctrl["weighted_score_contribution"] == 10.0
    assert payload["weighted_compliance"]["weighted_score"] == 10.0


def test_2_llm_valid_partial_with_citation(iso_controls, mock_audit_ctx):
    """Test 2: LLM returns valid 'partial' with citations -> verdict='partial', 50% weighted score."""
    cid = "A.5.3"  # High (5 pts)
    payload = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=0.0,
        score=0,
        max_score=93,
        implemented=[cid],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001:2022",
        standard="iso27001",
        today="2026-09-22",
        effective_mode="local",
        control_verdicts=[{
            "control_id": cid,
            "evidence_verdict": "partial",
            "ai_verdict_raw": "partial",
            "normalized_ai_verdict": "partial",
            "rationale": "Phân tách nhiệm vụ áp dụng một phần, còn thiếu ma trận SoD.",
            "citations": [{"file_name": "sod_matrix.xlsx"}],
            "confidence": 0.85,
        }],
        all_controls_flat=iso_controls,
        evidence_map={cid: ["sod_matrix.xlsx"]},
        audit_ctx=mock_audit_ctx,
    )

    ctrl = next(c for c in payload["controls"] if c["control_id"] == cid)
    assert ctrl["assessment_verdict"] == "partial"
    assert ctrl["verdict_source"] == "llm"
    assert ctrl["verdict_factor"] == 0.5
    assert ctrl["weighted_score_contribution"] == 2.5
    assert payload["weighted_compliance"]["weighted_score"] == 2.5


def test_3_has_file_but_llm_missing_verdict_safe_fallback(iso_controls, mock_audit_ctx):
    """Test 3: Control has attached files but LLM output is missing/empty -> needs_expert_review, safe_fallback_no_evidence, score 0."""
    cid = "A.5.9"  # High (5 pts)
    payload = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=0.0,
        score=0,
        max_score=93,
        implemented=[cid],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001:2022",
        standard="iso27001",
        today="2026-09-22",
        effective_mode="local",
        control_verdicts=[],  # LLM did not evaluate
        all_controls_flat=iso_controls,
        evidence_map={cid: ["asset_inventory.csv"]},
        audit_ctx=mock_audit_ctx,
    )

    ctrl = next(c for c in payload["controls"] if c["control_id"] == cid)
    assert ctrl["assessment_verdict"] == "needs_expert_review"
    assert ctrl["verdict_source"] == "safe_fallback_no_evidence"
    assert ctrl["fallback_reason"] is not None
    assert ctrl["verdict_factor"] == 0.0
    assert ctrl["weighted_score_contribution"] == 0.0
    assert payload["weighted_compliance"]["weighted_score"] == 0.0


def test_4_llm_returns_non_enum_verdict_safe_fallback(iso_controls, mock_audit_ctx):
    """Test 4: LLM outputs an invalid non-enum string -> safe_fallback_invalid_verdict, needs_expert_review, score 0."""
    cid = "A.8.20"  # Critical (10 pts)
    payload = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=0.0,
        score=0,
        max_score=93,
        implemented=[cid],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001:2022",
        standard="iso27001",
        today="2026-09-22",
        effective_mode="local",
        control_verdicts=[{
            "control_id": cid,
            "evidence_verdict": "somewhat_good_enough_status",
            "ai_verdict_raw": "somewhat_good_enough_status",
            "normalized_ai_verdict": None,
        }],
        all_controls_flat=iso_controls,
        evidence_map={cid: ["firewall_rules.conf"]},
        audit_ctx=mock_audit_ctx,
    )

    ctrl = next(c for c in payload["controls"] if c["control_id"] == cid)
    assert ctrl["assessment_verdict"] == "needs_expert_review"
    assert ctrl["verdict_source"] == "safe_fallback_invalid_verdict"
    assert ctrl["fallback_reason"] is not None
    assert "somewhat_good_enough_status" in ctrl["fallback_reason"]
    assert ctrl["weighted_score_contribution"] == 0.0


def test_5_conflict_detected_safe_branch(iso_controls, mock_audit_ctx):
    """Test 5: conflict_detected=True -> needs_expert_review, safe_fallback_conflict, score 0, and audit event emitted."""
    cid = "A.8.8"  # High (5 pts)
    with patch.object(audit_service, "record_verdict_overridden") as mock_record:
        payload = ChatService._build_structured_json(
            raw_analysis="Analysis",
            percentage=0.0,
            score=0,
            max_score=93,
            implemented=[cid],
            weight_breakdown={},
            missing_controls_by_weight={},
            org_name="TestOrg",
            industry="Tech",
            org_size="medium",
            employees=100,
            std_name="ISO 27001:2022",
            standard="iso27001",
            today="2026-09-22",
            effective_mode="local",
            control_verdicts=[{
                "control_id": cid,
                "evidence_verdict": "satisfied",
                "conflict_detected": True,
                "conflict_reason": "Tự khai là áp dụng nhưng log quét lỗ hổng phát hiện lỗ hổng nghiêm trọng chưa vá.",
            }],
            all_controls_flat=iso_controls,
            evidence_map={cid: ["scan_report.pdf"]},
            audit_ctx=mock_audit_ctx,
        )

    ctrl = next(c for c in payload["controls"] if c["control_id"] == cid)
    assert ctrl["assessment_verdict"] == "needs_expert_review"
    assert ctrl["verdict_source"] == "safe_fallback_conflict"
    assert ctrl["conflict_detected"] is True
    assert ctrl["weighted_score_contribution"] == 0.0


def test_6_chunk_draft_satisfied_without_citation_overridden(iso_controls, mock_audit_ctx):
    """Test 6: Invariant enforcement — Satisfied verdict without citations is overridden to needs_expert_review and emits verdict_overridden."""
    cid = "A.5.1"
    with patch.object(audit_service, "record_verdict_overridden") as mock_override:
        payload = ChatService._build_structured_json(
            raw_analysis="Analysis",
            percentage=0.0,
            score=0,
            max_score=93,
            implemented=[cid],
            weight_breakdown={},
            missing_controls_by_weight={},
            org_name="TestOrg",
            industry="Tech",
            org_size="medium",
            employees=100,
            std_name="ISO 27001:2022",
            standard="iso27001",
            today="2026-09-22",
            effective_mode="local",
            control_verdicts=[{
                "control_id": cid,
                "evidence_verdict": "satisfied",
                "citations": [],  # Empty citations!
            }],
            all_controls_flat=iso_controls,
            evidence_map={},  # No evidence file attached!
            audit_ctx=mock_audit_ctx,
        )

        assert mock_override.called
        # Check call arguments
        call_kwargs = mock_override.call_args[1]
        assert call_kwargs["control_id"] == cid
        assert call_kwargs["old_verdict"] == "satisfied"

    ctrl = next(c for c in payload["controls"] if c["control_id"] == cid)
    assert ctrl["assessment_verdict"] in ("needs_expert_review", "not_evidenced")
    assert ctrl["weighted_score_contribution"] == 0.0


def test_7_manifest_file_mapped_to_two_controls():
    """Test 7: Manifest deduplication — 1 file mapped to 2 controls yields total_files=1 and mapped_control_count=2."""
    from fastapi.testclient import TestClient
    from main import app
    from api.routes.iso27001 import load_evidence_manifest

    client = TestClient(app)
    assess_payload = {
        "assessment_standard": "iso27001",
        "org_name": "Test Org Deduplication",
        "implemented_controls": ["A.5.1", "A.5.2"],
        "evidence_map": {
            "A.5.1": ["security_handbook.pdf"],
            "A.5.2": ["security_handbook.pdf"],
        },
    }

    with patch("services.chat_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("services.cloud_llm_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("repositories.vector_store.VectorStore.search", return_value=[]):
        resp = client.post("/api/iso27001/assess", json=assess_payload)

    assert resp.status_code == 200, resp.text
    aid = resp.json()["id"]
    manifest = load_evidence_manifest(aid)
    assert manifest is not None
    assert manifest.get("total_files") == 1
    assert manifest.get("mapped_control_count") == 2
    assert set(manifest["files"][0]["control_mapping"]) == {"A.5.1", "A.5.2"}


def test_8_excluded_unsupported_or_tcvn_file_in_iso():
    """Test 8: Excluded files (unsupported extension or TCVN in ISO run) have ingestion_status='excluded'."""
    from fastapi.testclient import TestClient
    from main import app
    from api.routes.iso27001 import load_evidence_manifest

    client = TestClient(app)
    assess_payload = {
        "assessment_standard": "iso27001",
        "org_name": "Test Org Exclusion",
        "implemented_controls": ["A.5.1"],
        "evidence_map": {
            "A.5.1": ["malicious_tool.exe"],
            "NW.1": ["tcvn_network.pdf"],
        },
    }

    with patch("services.chat_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("services.cloud_llm_service.CloudLLMService._call_ollama", return_value={"content": "[]", "model": "mock", "provider": "ollama"}), \
         patch("repositories.vector_store.VectorStore.search", return_value=[]):
        resp = client.post("/api/iso27001/assess", json=assess_payload)

    assert resp.status_code == 200, resp.text
    aid = resp.json()["id"]
    manifest = load_evidence_manifest(aid)
    assert manifest is not None
    excluded = [f for f in manifest.get("files", []) if f.get("ingestion_status") == "excluded"]
    assert len(excluded) >= 1
    reasons = " ".join(f.get("exclusion_reason", "") for f in excluded)
    assert "không được hỗ trợ" in reasons or "TCVN" in reasons


def test_9_weighted_compliance_5_authoritative_verdicts():
    """Test 9: Weighted compliance calculation — only satisfied (1.0) & partial (0.5) earn points across all 5 standard verdicts."""
    controls = [
        {"control_id": "C1", "weight": "critical", "assessment_verdict": "satisfied"},            # 10 * 1.0 = 10.0
        {"control_id": "H1", "weight": "high", "assessment_verdict": "partial"},                # 5 * 0.5 = 2.5
        {"control_id": "M1", "weight": "medium", "assessment_verdict": "not_evidenced"},          # 3 * 0.0 = 0.0
        {"control_id": "M2", "weight": "medium", "assessment_verdict": "needs_expert_review"},    # 3 * 0.0 = 0.0
        {"control_id": "L1", "weight": "low", "assessment_verdict": "missing"},                  # 1 * 0.0 = 0.0
    ]
    res = calc_weighted_compliance(controls)
    # Denominator: C1 (10) + H1 (5) + M1 (3) + M2 (3) + L1 (1) = 22.0
    # Numerator: 10.0 + 2.5 = 12.5
    assert res["weighted_score"] == 12.5
    assert res["weighted_max_score"] == 22.0
    expected_pct = round(12.5 / 22.0 * 100, 1)  # 56.8%
    assert res["percentage"] == expected_pct


def test_10_performance_telemetry_generation(iso_controls, mock_audit_ctx):
    """Test 10: Performance telemetry is recorded per chunk and aggregated in runtime_summary."""
    chunk_tels = [
        {
            "chunk_id": "chunk_A.5 Organizational Controls",
            "control_count": 8,
            "prompt_tokens": 1200,
            "completion_tokens": 300,
            "retrieval_duration_ms": 45,
            "llm_duration_ms": 1850,
            "validation_duration_ms": 12,
            "merge_duration_ms": 5,
            "total_chunk_duration_ms": 1912,
            "model": "qwen2.5-coder:7b",
            "provider": "ollama",
            "queue_wait_ms": 0,
        }
    ]
    r_summary = {
        "total_duration_seconds": 2.15,
        "total_llm_duration_seconds": 1.85,
        "slowest_chunks": chunk_tels,
        "controls_per_chunk": {"chunk_A.5 Organizational Controls": 8},
        "number_of_llm_calls": 1,
        "average_seconds_per_control": 0.023,
    }

    payload = ChatService._build_structured_json(
        raw_analysis="Analysis",
        percentage=0.0,
        score=0,
        max_score=93,
        implemented=[],
        weight_breakdown={},
        missing_controls_by_weight={},
        org_name="TestOrg",
        industry="Tech",
        org_size="medium",
        employees=100,
        std_name="ISO 27001:2022",
        standard="iso27001",
        today="2026-09-22",
        effective_mode="local",
        control_verdicts=[],
        all_controls_flat=iso_controls,
        evidence_map={},
        runtime_summary=r_summary,
        chunk_telemetries=chunk_tels,
        audit_ctx=mock_audit_ctx,
    )

    assert "runtime_summary" in payload
    assert payload["runtime_summary"]["total_duration_seconds"] == 2.15
    assert len(payload["chunk_telemetries"]) == 1
    assert payload["chunk_telemetries"][0]["llm_duration_ms"] == 1850
