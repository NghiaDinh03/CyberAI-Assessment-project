"""Tests for PDF priority breakdown table consistency, invariant enforcement, and audit trace manifest provenance.
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import sys
import pytest
from pypdf import PdfReader
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from api.routes.iso27001 import router, save_assessment, load_assessment, export_pdf
from schemas.assessment_schema import (
    UnifiedAssessmentResult,
    ControlItem,
    ControlCoverage,
    WeightedCompliance,
)
from services.controls_catalog import get_flat_controls, calc_weighted_compliance
from services.assessment_helpers import aggregate_priority_breakdown, get_control_weight_level
from services.audit_service import AuditService, AuditContext
from repositories.audit_store import audit_store


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    from api.routes import iso27001
    iso27001.DATA_DIR = str(tmp_path)
    iso27001.ASSESSMENTS_DIR = str(tmp_path / "assessments")
    iso27001.EVIDENCE_DIR = str(tmp_path / "evidence")
    iso27001.EXPORTS_DIR = str(tmp_path / "exports")
    os.makedirs(iso27001.ASSESSMENTS_DIR, exist_ok=True)
    os.makedirs(iso27001.EVIDENCE_DIR, exist_ok=True)
    os.makedirs(iso27001.EXPORTS_DIR, exist_ok=True)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_priority_breakdown_aggregation_invariants():
    """Verify aggregate_priority_breakdown correctly aggregates ISO controls and checks invariants."""
    flat_iso = get_flat_controls("iso27001")
    controls = []
    for idx, c in enumerate(flat_iso):
        verdict = "satisfied" if idx < 45 else ("not_evidenced" if idx < 60 else "missing")
        decl = "implemented" if idx < 60 else "not_implemented"
        controls.append(
            ControlItem(
                control_id=c["id"],
                label=c["label"],
                category=c.get("category", "General"),
                weight=c["weight"],
                user_declaration=decl,
                assessment_verdict=verdict,
            )
        )

    scoring = calc_weighted_compliance([ctrl.model_dump() for ctrl in controls])
    wc = WeightedCompliance(**scoring)

    # Valid breakdown
    pb = aggregate_priority_breakdown(controls, wc, enforce_invariants=True)
    assert pb["total_applicable"] == 93
    assert pb["total_satisfied"] == 45
    assert pb["total_gaps"] == 48
    assert abs(pb["total_weighted_score"] - wc.weighted_score) < 0.1
    assert abs(pb["total_weighted_max_score"] - wc.weighted_max_score) < 0.1

    # Verify each tier has non-zero controls
    for tier in ["critical", "high", "medium", "low"]:
        t_data = pb["tiers"][tier]
        assert t_data["total_controls"] > 0
        assert t_data["weighted_max_score"] > 0
        assert t_data["gap_controls"] >= 0

    # Invariant failure test: mismatched weighted score
    tampered_wc = WeightedCompliance(
        weighted_score=999.0,
        weighted_max_score=wc.weighted_max_score,
        percentage=99.9,
    )
    with pytest.raises(ValueError, match="does not match weighted_compliance.weighted_score"):
        aggregate_priority_breakdown(controls, tampered_wc, enforce_invariants=True)


def test_pdf_export_not_all_zeros_and_strictly_matches_json(client, tmp_path):
    """P0 Test: Export PDF and assert breakdown table does NOT contain all zeros when JSON score > 0."""
    aid = "test-pdf-non-zero-001"
    run_id = "run-pdf-001"

    flat_iso = get_flat_controls("iso27001")
    controls = []
    for idx, c in enumerate(flat_iso):
        verdict = "satisfied" if idx < 45 else "missing"
        controls.append(
            ControlItem(
                control_id=c["id"],
                label=c["label"],
                weight=c["weight"],
                user_declaration="implemented" if idx < 45 else "not_implemented",
                assessment_verdict=verdict,
            )
        )

    scoring = calc_weighted_compliance([ctrl.model_dump() for ctrl in controls])
    unified = UnifiedAssessmentResult(
        assessment_id=aid,
        run_id=run_id,
        standard="iso27001",
        created_at="2026-09-21T10:00:00Z",
        controls=controls,
        weighted_compliance=WeightedCompliance(**scoring),
        organization={"name": "Công ty Thẩm định Quốc gia", "industry": "Tài chính"},
    )

    asm_dict = unified.model_dump()
    asm_record = {
        "id": aid,
        "assessment_id": aid,
        "run_id": run_id,
        "status": "completed",
        "created_at": unified.created_at,
        "compliance_percent": scoring["percentage"],
        "system_info": {"org_name": "Công ty Thẩm định Quốc gia", "assessment_standard": "iso27001"},
        "result": {
            "report": f"# BÁO CÁO ĐÁNH GIÁ\nTỷ lệ Tuân thủ có trọng số: {scoring['percentage']}%\n",
            "percentage": scoring["percentage"],
        },
        "json_data": asm_dict,
        "weighted_compliance": asm_dict["weighted_compliance"],
        "control_coverage": asm_dict.get("control_coverage", {}),
    }
    save_assessment(aid, asm_record)

    import asyncio
    import re
    pdf_resp = asyncio.run(export_pdf(aid))
    assert os.path.exists(pdf_resp.path)

    # Scan PDF text via pypdf
    reader = PdfReader(pdf_resp.path)
    full_text = " ".join([page.extract_text() or "" for page in reader.pages])
    clean_text = re.sub(r"[\x00\s]+", "", full_text)

    # Assert Table Header and Priority labels are present
    assert "Bảngphântíchtheomứcđộưutiên" in clean_text
    assert "Critical" in clean_text
    assert "High" in clean_text
    assert "Medium" in clean_text
    assert "Low" in clean_text
    assert "Tổngcộng" in clean_text

    # Assert it is NOT all zeros for Critical
    # Critical in ISO 27001 has ~18 controls, of which a portion are satisfied
    pb = aggregate_priority_breakdown(controls, unified.weighted_compliance)
    crit = pb["tiers"]["critical"]
    assert crit["total_controls"] > 0
    assert crit["satisfied_verified"] > 0
    # The formatted numbers should appear in the extracted text
    assert str(crit["total_controls"]) in clean_text
    assert str(crit["satisfied_verified"]) in clean_text
    assert f"{crit['weighted_score']:.1f}" in clean_text


def test_pdf_export_blocks_when_summary_and_breakdown_conflict(client):
    """P0 Test: System refuses to export PDF (HTTP 422) if summary contradicts controls."""
    aid = "test-pdf-conflict-001"
    run_id = "run-conflict-001"

    flat_iso = get_flat_controls("iso27001")[:10]
    controls = [
        ControlItem(
            control_id=c["id"],
            label=c["label"],
            weight=c["weight"],
            assessment_verdict="satisfied",
        )
        for c in flat_iso
    ]

    unified = UnifiedAssessmentResult(
        assessment_id=aid,
        run_id=run_id,
        standard="iso27001",
        controls=controls,
    )

    # Deliberately supply conflicting summary in asm_record
    asm_record = {
        "id": aid,
        "assessment_id": aid,
        "run_id": run_id,
        "status": "completed",
        "result": {"report": "Conflicting report"},
        "json_data": unified.model_dump(),
        "weighted_compliance": {"weighted_score": 500.0},  # Conflicts with controls breakdown!
    }
    save_assessment(aid, asm_record)

    import asyncio
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(export_pdf(aid))

    assert exc_info.value.status_code == 422
    assert "Invariant Violation" in exc_info.value.detail



def test_audit_trace_must_contain_manifest_hash_and_mapping_when_files_uploaded():
    """Test 8: Audit trace must fail verification if total_files > 0 but manifest/hash/mapping is missing."""
    ctx = AuditContext(assessment_id="asm_test_audit_001", run_id="run_audit_001")

    # Record complete evidence parsed event
    test_files = [
        {
            "evidence_id": "file_a51",
            "file_name": "A.5.1_satisfied_policy.txt",
            "sha256": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "parser_status": "native_parser",
            "size_bytes": 1024,
            "control_mapping": ["A.5.1"],
        }
    ]
    AuditService.record_evidence_parsed(
        ctx=ctx,
        evidence_controls_count=1,
        total_files=1,
        file_extensions=[".txt"],
        evidence_manifest_id="manifest_asm_test_audit_001",
        control_mapping={"A.5.1": ["A.5.1_satisfied_policy.txt"]},
        file_hashes={"A.5.1_satisfied_policy.txt": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"},
        evidence_source="uploaded_evidence",
        files=test_files,
    )

    events = audit_store.get_events_by_assessment(ctx.assessment_id)
    ev_parsed = next(e for e in events if e["event_type"] == "evidence_parsed")
    payload = ev_parsed["payload"]

    # Verify presence of manifest_id, total_files, file_hashes, control_mapping, and files details
    assert payload["total_files"] == 1
    assert payload["evidence_manifest_id"] == "manifest_asm_test_audit_001"
    assert "A.5.1_satisfied_policy.txt" in payload["file_hashes"]
    assert "A.5.1" in payload["control_mapping"]
    assert len(payload["files"]) == 1
    assert payload["files"][0]["evidence_id"] == "file_a51"
    assert payload["evidence_source"] == "uploaded_evidence"

    # Validation check: If uploaded files > 0 but manifest is missing, validation rule fails
    invalid_payload = dict(payload)
    invalid_payload["evidence_manifest_id"] = None
    invalid_payload["file_hashes"] = {}
    invalid_payload["control_mapping"] = {}

    def verify_audit_trace_evidence_integrity(p: dict) -> bool:
        if p.get("total_files", 0) > 0:
            if not p.get("evidence_manifest_id"):
                return False
            if not p.get("file_hashes") or not p.get("control_mapping"):
                return False
        return True

    assert verify_audit_trace_evidence_integrity(payload) is True
    assert verify_audit_trace_evidence_integrity(invalid_payload) is False
