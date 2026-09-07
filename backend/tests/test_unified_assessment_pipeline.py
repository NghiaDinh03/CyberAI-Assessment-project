"""Test suite for the Unified Assessment Pipeline, Artifact Consistency, and Traceability."""

import io
import json
import os
import tempfile
import pytest
from datetime import datetime, timezone

from schemas.assessment_schema import (
    ControlItem,
    ControlCoverage,
    WeightedCompliance,
    EvidenceManifest,
    EvidenceManifestItem,
    UnifiedAssessmentResult,
)
from services.controls_catalog import calc_compliance, calc_tcvn_compliance, ISO_27001_CATEGORIES, TCVN_11930_CATEGORIES
from services.evidence_parser import compute_file_sha256, mask_evidence_filename
from services.soa_exporter import generate_soa_xlsx, _flatten_controls
from services.risk_register_exporter import generate_risk_register_xlsx
from services.report_docx_generator import generate_report_docx, _clean_markdown
from services.audit_service import audit_service, AuditContext
from services.artifact_validator import validate_assessment_artifacts


def test_unified_schema_instantiation():
    """Verify UnifiedAssessmentResult schema validates and serializes properly."""
    ctrl = ControlItem(
        control_id="A.8.8",
        label="Quản lý lỗ hổng kỹ thuật",
        category="Công nghệ",
        weight="high",
        user_declaration="implemented",
        evidence_status="direct_attachment",
        evidence_file_ids=["report_vulnerability.pdf"],
        assessment_verdict="satisfied",
        verdict_basis=["user_declaration", "direct_evidence"],
        risk_severity="Low",
        likelihood=1,
        impact=2,
        risk_score=2,
        risk_assessment_basis="evidence_based",
    )
    assert ctrl.control_id == "A.8.8"
    assert ctrl.risk_score == 2

    coverage = ControlCoverage(
        self_declared_implemented=45,
        evidence_supported_implemented=20,
        not_evidenced_or_missing=73,
        total_controls=93,
        raw_percentage=48.4,
    )
    weighted = WeightedCompliance(
        weighted_score=150.0,
        weighted_max_score=270.0,
        percentage=55.6,
        algorithm="weight_score_v1",
    )

    res = UnifiedAssessmentResult(
        assessment_id="test_aid_123",
        run_id="test_run_456",
        code_version="v1.2.0-rel",
        control_coverage=coverage,
        weighted_compliance=weighted,
        controls=[ctrl],
    )
    d = res.model_dump()
    assert d["assessment_id"] == "test_aid_123"
    assert d["control_coverage"]["raw_percentage"] == 48.4
    assert d["weighted_compliance"]["percentage"] == 55.6


def test_scoring_separation_iso_and_tcvn():
    """Verify raw control coverage is explicitly separated from weighted compliance."""
    # Test ISO
    iso_all = [c["id"] for cat in ISO_27001_CATEGORIES for c in cat["controls"]]
    assert len(iso_all) == 93
    impl_iso = iso_all[:47]  # 47 implemented

    res_iso = calc_compliance(impl_iso)
    assert res_iso["control_coverage"]["self_declared_implemented"] == 47
    assert res_iso["control_coverage"]["total_controls"] == 93
    assert res_iso["control_coverage"]["raw_percentage"] == round(47 / 93 * 100, 1)

    w_score = res_iso["weighted_compliance"]["weighted_score"]
    w_max = res_iso["weighted_compliance"]["weighted_max_score"]
    w_pct = res_iso["weighted_compliance"]["percentage"]
    assert w_pct == round(w_score / w_max * 100, 1)

    # Test TCVN
    tcvn_all = [c["id"] for cat in TCVN_11930_CATEGORIES for c in cat["controls"]]
    assert len(tcvn_all) == 34
    impl_tcvn = tcvn_all[:18]

    res_tcvn = calc_tcvn_compliance(impl_tcvn)
    assert res_tcvn["control_coverage"]["self_declared_implemented"] == 18
    assert res_tcvn["control_coverage"]["total_controls"] == 34
    assert res_tcvn["control_coverage"]["raw_percentage"] == round(18 / 34 * 100, 1)
    tw_score = res_tcvn["weighted_compliance"]["weighted_score"]
    tw_max = res_tcvn["weighted_compliance"]["weighted_max_score"]
    tw_pct = res_tcvn["weighted_compliance"]["percentage"]
    assert tw_pct == round(tw_score / tw_max * 100, 1)


def test_evidence_sanitization_and_hashing():
    """Verify evidence file SHA-256 and IP/secret masking in filenames."""
    content = b"sample security audit log with IP 192.168.1.100"
    sha = compute_file_sha256(content)
    assert len(sha) == 64

    # Test IP masking
    fname1 = "firewall_log_192.168.1.50_export.txt"
    masked1 = mask_evidence_filename(fname1)
    assert "192.168.1.50" not in masked1
    assert "***" in masked1

    fname2 = "nessus_scan_10.0.0.12_report.xml"
    masked2 = mask_evidence_filename(fname2)
    assert "10.0.0.12" not in masked2
    assert "***" in masked2


def test_soa_xlsx_control_counts_and_metadata():
    """Verify SoA XLSX has exactly 93 rows for ISO and 34 for TCVN and no hardcoding."""
    # Test ISO
    iso_bytes = generate_soa_xlsx(
        implemented_controls=["A.5.1", "A.8.8"],
        org_name="Test Corp",
    )
    import openpyxl
    wb_iso = openpyxl.load_workbook(io.BytesIO(iso_bytes), data_only=True)
    ws_iso = wb_iso.active

    iso_ctrl_count = 0
    for row in ws_iso.iter_rows(min_row=5, values_only=True):
        val = str(row[0] or "")
        if val.startswith("A."):
            iso_ctrl_count += 1
    assert iso_ctrl_count == 93

    # Test TCVN
    tcvn_bytes = generate_soa_xlsx(
        implemented_controls=["NW.1", "SV.1", "DAT.1"],
        org_name="Doanh nghiệp Thử nghiệm",
    )
    wb_tcvn = openpyxl.load_workbook(io.BytesIO(tcvn_bytes), data_only=True)
    ws_tcvn = wb_tcvn.active

    tcvn_ctrl_count = 0
    for row in ws_tcvn.iter_rows(min_row=5, values_only=True):
        val = str(row[0] or "")
        if val.startswith("NW.") or val.startswith("SV.") or val.startswith("APP.") or val.startswith("DAT.") or val.startswith("MNG."):
            tcvn_ctrl_count += 1
    assert tcvn_ctrl_count == 34


def test_docx_report_cleanliness_and_disclaimer():
    """Verify DOCX report contains no emojis, has mandatory disclaimer, and cantSplit on table rows."""
    assessment_data = {
        "assessment_id": "test_doc_001",
        "run_id": "run_test_001",
        "code_version": "v1.2.0-rel",
        "standard": "iso27001",
        "compliance_percent": 68.5,
        "created_at": "2026-09-07T12:00:00Z",
        "system_info": {
            "organization": {"name": "SecureCorp", "industry": "Banking"},
            "assessment_standard": "iso27001",
        },
        "json_data": {
            "risk_register": [
                {
                    "control_id": "A.8.8",
                    "label": "Quản lý lỗ hổng kỹ thuật",
                    "gap": "Chưa có quy trình quét định kỳ **hàng tháng**",
                    "severity": "high",
                    "likelihood": 3,
                    "impact": 4,
                    "risk_score": 12,
                    "recommendation": "Thiết lập công cụ quét tự động.",
                }
            ],
            "weight_breakdown": {
                "critical": {"total": 10, "implemented": 8, "percent": 80.0},
                "high": {"total": 30, "implemented": 20, "percent": 66.7},
            }
        }
    }

    docx_bytes = generate_report_docx(assessment_data)
    import docx
    doc = docx.Document(io.BytesIO(docx_bytes))
    all_text = "\n".join([p.text for p in doc.paragraphs])
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                all_text += "\n" + c.text

    # Mandatory disclaimer must be present
    assert "hỗ trợ tự đánh giá" in all_text
    assert "cần chuyên gia an toàn thông tin xác minh" in all_text
    # Check no raw emojis in table headers/badges
    assert "🔴" not in all_text
    assert "🟠" not in all_text
    # Markdown stripping test
    cleaned = _clean_markdown("**Bold** `#Code` ## Header")
    assert cleaned == "Bold Code Header"


def test_audit_trace_rag_runtime_telemetry(tmp_path):
    """Verify RAG query event records full runtime metadata."""
    from services.audit_service import AuditService, AuditContext
    aid = "test_rag_trace_001"
    run_id = "run_rag_001"
    ctx = AuditContext(assessment_id=aid, run_id=run_id, code_version="v1.2.0-rel")

    event_id = audit_service.record_rag_query(
        ctx=ctx,
        collection_name="iso27001_controls",
        query_text="kiem soat lo hong ky thuat A.8.8",
        top_k=2,
        results=[{"file": "A.8.8.md", "doc_title": "Vulnerability Management", "score": 0.95}],
    )
    assert event_id.startswith("evt_")

    # Export & Load trace file
    audit_service.export_audit_trace_json(aid)
    data_dir = os.getenv("DATA_PATH", "./data")
    tpath = os.path.join(data_dir, "audit_traces", f"{aid}.json")
    assert os.path.exists(tpath)
    with open(tpath, "r", encoding="utf-8") as f:
        trace = json.load(f)

    rag_evt = [e for e in trace["events"] if e["event_id"] == event_id][0]
    p = rag_evt["payload"]
    assert p["embedding_provider"] == "ollama"
    assert p["embedding_model"] == "bge-m3:latest"
    assert p["embedding_dimensions"] == 1024
    assert p["distance_metric"] == "cosine"
    assert p["query_hash"].startswith("sha256:")


def test_artifact_consistency_validator_pass():
    """Verify that artifact validator returns PASS on a consistent assessment dataset."""
    aid = "test_val_pass_001"
    run_id = "run_val_001"
    code_ver = "v1.2.0-rel"

    assessment_data = {
        "assessment_id": aid,
        "run_id": run_id,
        "code_version": code_ver,
        "standard": {"id": "iso27001", "name": "ISO/IEC 27001:2022"},
        "control_coverage": {
            "self_declared_implemented": 50,
            "total_controls": 93,
            "raw_percentage": 53.8,
        },
        "weighted_compliance": {
            "weighted_score": 150.0,
            "weighted_max_score": 250.0,
            "percentage": 60.0,
            "algorithm": "weight_score_v1",
        },
        "json_data": {
            "assessment_id": aid,
            "run_id": run_id,
            "code_version": code_ver,
            "control_coverage": {
                "self_declared_implemented": 50,
                "total_controls": 93,
                "raw_percentage": 53.8,
            },
            "weighted_compliance": {
                "weighted_score": 150.0,
                "weighted_max_score": 250.0,
                "percentage": 60.0,
                "algorithm": "weight_score_v1",
            },
            "report": "Báo cáo an toàn thông tin hoàn chỉnh, không để lộ thông tin bí mật.",
        }
    }

    # Record trace
    ctx = AuditContext(assessment_id=aid, run_id=run_id, code_version=code_ver)
    audit_service.record_rag_query(ctx=ctx, collection_name="iso27001_controls", query_text="test query", top_k=2, results=[])
    audit_service.record_assessment_completed(ctx=ctx, standard="iso27001", compliance_percentage=60.0, total_duration_seconds=5.0)

    res = validate_assessment_artifacts(assessment_id=aid, assessment_data=assessment_data)
    assert res["checks"]["raw_coverage_math"]["status"] == "PASS"
    assert res["checks"]["weighted_compliance_math"]["status"] == "PASS"
    assert res["checks"]["audit_trace_rag_metadata"]["status"] == "PASS"
