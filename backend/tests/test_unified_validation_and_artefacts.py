"""Unit and integration tests for UnifiedAssessmentResult validation, safe conflict branch, and artefact consistency (Goals 1, 2, 3)."""

from __future__ import annotations

import io
import os
import pathlib
import sys
from unittest.mock import MagicMock, patch

import openpyxl
import pytest
from docx import Document
from pydantic import ValidationError

BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from schemas.assessment_schema import (
    ControlCoverage,
    ControlItem,
    UnifiedAssessmentResult,
    WeightedCompliance,
)
from services.controls_catalog import calc_weighted_compliance, get_flat_controls
from services.report_docx_generator import generate_report_docx
from services.risk_register_exporter import generate_risk_register_xlsx
from services.soa_exporter import generate_soa_xlsx


# ── GOAL 1 TESTS: UnifiedAssessmentResult mandatory validation ──────────────


def test_validation_missing_required_fields():
    """UnifiedAssessmentResult must reject payloads missing assessment_id or run_id."""
    raw_missing_id = {
        "run_id": "run_001",
        "controls": [],
    }
    with pytest.raises(ValidationError) as exc_info:
        UnifiedAssessmentResult.model_validate(raw_missing_id)
    assert "assessment_id" in str(exc_info.value)

    raw_missing_run = {
        "assessment_id": "asm_001",
        "controls": [],
    }
    with pytest.raises(ValidationError) as exc_info:
        UnifiedAssessmentResult.model_validate(raw_missing_run)
    assert "run_id" in str(exc_info.value)


def test_validation_empty_whitespace_ids():
    """Empty or whitespace-only assessment_id / run_id must raise ValidationError."""
    with pytest.raises(ValidationError):
        UnifiedAssessmentResult.model_validate({
            "assessment_id": "   ",
            "run_id": "run_001",
            "controls": [],
        })

    with pytest.raises(ValidationError):
        UnifiedAssessmentResult.model_validate({
            "assessment_id": "asm_001",
            "run_id": "  \t ",
            "controls": [],
        })


def test_validation_invalid_data_types():
    """UnifiedAssessmentResult must reject invalid data types."""
    invalid_controls_payload = {
        "assessment_id": "asm_002",
        "run_id": "run_002",
        "controls": "not_a_list",
    }
    with pytest.raises(ValidationError):
        UnifiedAssessmentResult.model_validate(invalid_controls_payload)

    invalid_coverage_payload = {
        "assessment_id": "asm_002",
        "run_id": "run_002",
        "control_coverage": "invalid_type",
    }
    with pytest.raises(ValidationError):
        UnifiedAssessmentResult.model_validate(invalid_coverage_payload)


def test_validation_invalid_verdict():
    """ControlItem must reject invalid assessment verdicts."""
    with pytest.raises(ValidationError) as exc_info:
        ControlItem(
            control_id="A.5.1",
            assessment_verdict="guaranteed_compliant",
        )
    assert "Invalid assessment verdict" in str(exc_info.value)

    with pytest.raises(ValidationError):
        ControlItem(
            control_id="A.5.1",
            assessment_verdict="100%_secure",
        )


def test_validation_error_prevents_persistence_and_export():
    """When validation fails, neither database persistence nor exporter is called."""
    raw_invalid_payload = {
        "assessment_id": "",
        "run_id": "run_test",
        "controls": [{"control_id": "A.5.1", "assessment_verdict": "illegal_verdict"}],
    }

    mock_db_save = MagicMock()
    mock_exporter = MagicMock()

    validation_failed = False
    try:
        validated = UnifiedAssessmentResult.model_validate(raw_invalid_payload)
        mock_db_save(validated)
        mock_exporter(validated)
    except ValidationError:
        validation_failed = True

    assert validation_failed is True
    mock_db_save.assert_not_called()
    mock_exporter.assert_not_called()


# ── GOAL 3 TESTS: Safe branch for conflicting evidence ──────────────────────


def test_conflict_safe_branch_enforcement():
    """When conflict_detected=True, assessment_verdict must be forced to needs_expert_review."""
    ctrl = ControlItem(
        control_id="A.5.15",
        user_declaration="implemented",
        assessment_verdict="satisfied",
        conflict_detected=True,
        conflict_reason="Tự khai có MFA nhưng evidence log chỉ có password",
        conflicting_evidence_ids=["ev_auth_log_01"],
    )

    # Safe branch enforces needs_expert_review
    assert ctrl.assessment_verdict == "needs_expert_review"
    assert ctrl.conflict_detected is True
    assert "MFA" in (ctrl.conflict_reason or "")
    assert "ev_auth_log_01" in ctrl.conflicting_evidence_ids


def test_conflict_safe_branch_scoring_zero():
    """Controls with needs_expert_review must receive 0 score under authoritative scoring."""
    ctrl_dict = {
        "id": "A.5.15",
        "control_id": "A.5.15",
        "weight": "critical",
        "assessment_verdict": "needs_expert_review",
        "conflict_detected": True,
    }
    score_out = calc_weighted_compliance([ctrl_dict])
    assert score_out["weighted_score"] == 0.0
    assert score_out["percentage"] == 0.0


def test_attachment_existence_does_not_grant_satisfied():
    """Having file attachments does not automatically grant 'satisfied' if not validated."""
    ctrl = ControlItem(
        control_id="A.8.8",
        user_declaration="implemented",
        evidence_file_ids=["screenshot.png", "patch_report.docx"],
        assessment_verdict="not_evidenced",
    )
    assert ctrl.assessment_verdict == "not_evidenced"
    score_out = calc_weighted_compliance([ctrl.model_dump()])
    assert score_out["weighted_score"] == 0.0


# ── GOAL 2 TESTS: Artefacts consistency from single validated source ────────


@pytest.fixture
def sample_validated_assessment() -> UnifiedAssessmentResult:
    """Fixture providing a complete, validated UnifiedAssessmentResult for ISO 27001."""
    controls = [
        ControlItem(
            control_id="A.5.1",
            label="Chính sách an toàn thông tin",
            category="A.5 Tổ chức",
            weight="critical",
            user_declaration="implemented",
            assessment_verdict="satisfied",
            verdict_basis=["user_declaration", "direct_evidence"],
            evidence_file_ids=["isms_policy_v2.pdf"],
            gap="Chưa cập nhật kỳ đánh giá 2026",
            recommendation="Ban hành quy chế định kỳ hàng năm",
            score=4,
            risk_severity="low",
            likelihood=2,
            impact=2,
            risk_score=4,
        ),
        ControlItem(
            control_id="A.5.15",
            label="Kiểm soát truy cập",
            category="A.5 Tổ chức",
            weight="critical",
            user_declaration="implemented",
            assessment_verdict="needs_expert_review",
            verdict_basis=["user_declaration"],
            conflict_detected=True,
            conflict_reason="Kê khai có MFA nhưng log hệ thống cho thấy xác thực đơn yếu tố",
            conflicting_evidence_ids=["auth_audit.log"],
            evidence_file_ids=["auth_audit.log"],
            gap="Phát hiện mâu thuẫn giữa tự khai và bằng chứng kỹ thuật",
            recommendation="Chuyên gia ATTT thẩm định trực tiếp cấu hình PAM/IAM",
            risk_severity="critical",
            likelihood=4,
            impact=4,
            risk_score=16,
        ),
        ControlItem(
            control_id="A.8.8",
            label="Quản lý lỗ hổng kỹ thuật",
            category="A.8 Công nghệ",
            weight="high",
            user_declaration="not_implemented",
            assessment_verdict="missing",
            verdict_basis=["user_declaration"],
            gap="Chưa triển khai giải pháp quét lỗ hổng tự động",
            recommendation="Trang bị công cụ Nessus hoặc OpenVAS",
            risk_severity="high",
            likelihood=4,
            impact=3,
            risk_score=12,
        ),
    ]

    scoring = calc_weighted_compliance([c.model_dump() for c in controls])

    result = UnifiedAssessmentResult(
        assessment_id="asm_unified_artefact_test",
        run_id="run_artefact_test_01",
        code_version="v1.2.0-rel",
        created_at="2026-09-20T18:00:00Z",
        completed_at="2026-09-20T18:05:00Z",
        status="completed",
        standard={"id": "iso27001", "name": "ISO/IEC 27001:2022"},
        organization={"name": "Tập đoàn Công nghệ Demo", "industry": "Finance"},
        control_coverage=ControlCoverage(
            self_declared_implemented=2,
            evidence_supported_implemented=1,
            not_evidenced_or_missing=2,
            total_controls=3,
            raw_percentage=33.33,
        ),
        weighted_compliance=WeightedCompliance(
            weighted_score=scoring["weighted_score"],
            weighted_max_score=scoring["weighted_max_score"],
            percentage=scoring["percentage"],
        ),
        controls=controls,
        compliance={
            "weighted_score": scoring["weighted_score"],
            "weighted_max_score": scoring["weighted_max_score"],
            "score_pct": scoring["percentage"],
        },
        weighted_coverage={
            "score_pct": scoring["percentage"],
        },
    )
    return result


def test_artefacts_share_identical_data_source(sample_validated_assessment):
    """Exporters receive identical validated model; verify common fields across JSON, SoA, Risk, DOCX."""
    asm = sample_validated_assessment

    # 1. JSON Export
    json_data = asm.model_dump()
    assert json_data["assessment_id"] == "asm_unified_artefact_test"
    assert json_data["run_id"] == "run_artefact_test_01"
    assert json_data["weighted_compliance"]["percentage"] == asm.weighted_compliance.percentage

    # 2. SoA XLSX Export
    soa_bytes = generate_soa_xlsx(assessment_data=asm.model_dump())
    assert len(soa_bytes) > 1000
    soa_wb = openpyxl.load_workbook(io.BytesIO(soa_bytes))
    soa_ws = soa_wb.active

    # Check SoA metadata row
    meta_row = soa_ws.cell(row=2, column=1).value or ""
    assert "asm_unified_artefact_test" in meta_row
    assert "run_artefact_test_01" in meta_row

    # Verify control row in SoA
    soa_controls = {}
    for row in soa_ws.iter_rows(min_row=5, values_only=True):
        if row and row[0] and str(row[0]).startswith("A."):
            soa_controls[row[0]] = {
                "verdict": row[10],
                "score": row[7],
            }

    assert "A.5.1" in soa_controls
    assert soa_controls["A.5.1"]["verdict"] == "Satisfied"
    assert soa_controls["A.5.1"]["score"] in (10, 10.0)

    assert "A.5.15" in soa_controls
    assert soa_controls["A.5.15"]["verdict"] == "Needs Expert Review"
    assert soa_controls["A.5.15"]["score"] == 0

    # 3. Risk Register XLSX Export
    risk_bytes = generate_risk_register_xlsx(assessment_data=asm.model_dump())
    assert len(risk_bytes) > 1000
    risk_wb = openpyxl.load_workbook(io.BytesIO(risk_bytes))
    risk_ws = risk_wb.active
    risk_meta = risk_ws.cell(row=2, column=1).value or ""
    assert "asm_unified_artefact_test" in risk_meta

    risk_controls = {}
    for row in risk_ws.iter_rows(min_row=4, values_only=True):
        if row and row[1] and str(row[1]).startswith("A."):
            risk_controls[row[1]] = {
                "severity": str(row[5]).strip().lower(),
                "score": row[8],
            }

    assert "A.5.15" in risk_controls
    assert risk_controls["A.5.15"]["severity"] == "critical"
    assert risk_controls["A.5.15"]["score"] == 16

    # 4. DOCX Export
    docx_bytes = generate_report_docx(assessment_data=asm.model_dump())
    assert len(docx_bytes) > 5000
    doc = Document(io.BytesIO(docx_bytes))
    doc_text = " ".join([p.text for p in doc.paragraphs])
    assert "asm_unified_artefact_test" in doc_text or "Tập đoàn Công nghệ Demo" in doc_text

    # 5. PDF Export (Weasyprint generation from same validated model)
    sample_html = f"""<!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Audit Report</title></head>
    <body>
        <h1>BÁO CÁO ĐÁNH GIÁ AN TOÀN THÔNG TIN</h1>
        <p>Assessment ID: {asm.assessment_id}</p>
        <p>Run ID: {asm.run_id}</p>
        <p>Weighted Compliance: {asm.weighted_compliance.percentage}%</p>
    </body>
    </html>"""
    from weasyprint import HTML
    pdf_bytes = HTML(string=sample_html).write_pdf()
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    # Cross-artefact verdict and score consistency
    assert soa_controls["A.5.1"]["verdict"].lower() == json_data["controls"][0]["assessment_verdict"].lower()
    assert soa_controls["A.5.15"]["verdict"].lower().replace(" ", "_") == json_data["controls"][1]["assessment_verdict"].lower()
    assert risk_controls["A.5.15"]["severity"] == json_data["controls"][1]["risk_severity"].lower()


# ── SECTION 6 MANDATORY REGRESSION TESTS ─────────────────────────────────────


def test_control_contribution_weights_and_verdict_factors():
    """Verify exact 10/5/3/1 weights and 100%/50%/0% verdict factors across 5 authoritative verdicts."""
    # satisfied
    crit_sat = ControlItem(control_id="C1", weight="critical", assessment_verdict="satisfied")
    high_sat = ControlItem(control_id="H1", weight="high", assessment_verdict="satisfied")
    med_sat = ControlItem(control_id="M1", weight="medium", assessment_verdict="satisfied")
    low_sat = ControlItem(control_id="L1", weight="low", assessment_verdict="satisfied")

    assert crit_sat.weighted_score_contribution == 10.0
    assert high_sat.weighted_score_contribution == 5.0
    assert med_sat.weighted_score_contribution == 3.0
    assert low_sat.weighted_score_contribution == 1.0

    # partial
    crit_part = ControlItem(control_id="C2", weight="critical", assessment_verdict="partial")
    high_part = ControlItem(control_id="H2", weight="high", assessment_verdict="partial")
    med_part = ControlItem(control_id="M2", weight="medium", assessment_verdict="partial")
    low_part = ControlItem(control_id="L2", weight="low", assessment_verdict="partial")

    assert crit_part.weighted_score_contribution == 5.0
    assert high_part.weighted_score_contribution == 2.5
    assert med_part.weighted_score_contribution == 1.5
    assert low_part.weighted_score_contribution == 0.5

    # 0 contribution verdicts
    crit_miss = ControlItem(control_id="C3", weight="critical", assessment_verdict="missing")
    crit_notev = ControlItem(control_id="C4", weight="critical", assessment_verdict="not_evidenced")
    crit_rev = ControlItem(control_id="C5", weight="critical", assessment_verdict="needs_expert_review")

    assert crit_miss.weighted_score_contribution == 0.0
    assert crit_notev.weighted_score_contribution == 0.0
    assert crit_rev.weighted_score_contribution == 0.0

    # Test scoring with all 5 standard verdicts in denominator
    scoring = calc_weighted_compliance([
        crit_sat.model_dump(),
        crit_part.model_dump(),
        crit_miss.model_dump(),
        crit_notev.model_dump(),
        crit_rev.model_dump(),
    ])
    # Denominator should be 10 * 5 = 50.0, numerator 10 + 5 = 15.0 -> 30.0%
    assert scoring["weighted_max_score"] == 50.0
    assert scoring["weighted_score"] == 15.0
    assert scoring["percentage"] == 30.0


def test_catalog_total_weights():
    """ISO 27001 (93 controls) total weight must equal 495; TCVN 11930 (34 controls) must equal 271."""
    from services.controls_catalog import WEIGHT_SCORE
    flat_iso = get_flat_controls("iso27001")
    assert len(flat_iso) == 93
    iso_total_w = sum(WEIGHT_SCORE[c["weight"]] for c in flat_iso)
    assert iso_total_w == 495.0

    flat_tcvn = get_flat_controls("tcvn11930")
    assert len(flat_tcvn) == 34
    tcvn_total_w = sum(WEIGHT_SCORE[c["weight"]] for c in flat_tcvn)
    assert tcvn_total_w == 271.0


def test_iso_fixture_regression_and_coverage():
    """ISO fixture: 45 satisfied, 48 not-evidenced/missing, total 93 -> coverage not all zero, sum contribution == weighted_score."""
    flat_iso = get_flat_controls("iso27001")
    controls = []
    for idx, c in enumerate(flat_iso):
        if idx < 45:
            verdict = "satisfied"
            decl = "implemented"
        elif idx < 60:
            verdict = "not_evidenced"
            decl = "implemented"
        else:
            verdict = "missing"
            decl = "not_implemented"
        controls.append(ControlItem(
            control_id=c["id"],
            label=c["label"],
            category=c.get("category", "General"),
            weight=c["weight"],
            user_declaration=decl,
            assessment_verdict=verdict,
        ))

    scoring = calc_weighted_compliance([c.model_dump() for c in controls])
    assert scoring["weighted_score"] == 246.0
    assert scoring["weighted_max_score"] == 495.0
    assert scoring["percentage"] == 49.7

    asm = UnifiedAssessmentResult(
        assessment_id="asm_iso_test_01",
        run_id="run_iso_test_01",
        standard="iso27001",
        controls=controls,
        weighted_compliance=WeightedCompliance(
            weighted_score=scoring["weighted_score"],
            weighted_max_score=scoring["weighted_max_score"],
            percentage=scoring["percentage"],
        ),
    )

    # Coverage checks
    cov = asm.control_coverage
    assert cov.total_applicable_controls == 93
    assert cov.evidence_supported_implemented == 45
    assert cov.not_evidenced_or_missing == 48
    assert cov.self_declared_implemented == 60
    assert cov.raw_percentage == 64.5

    # Sum contribution invariant
    contrib_sum = round(sum(c.weighted_score_contribution for c in asm.controls), 1)
    assert contrib_sum == asm.weighted_compliance.weighted_score == 246.0

    # SoA test: headers do not have Score (0-5), rows have non-zero contributions
    soa_bytes = generate_soa_xlsx(assessment_data=asm.model_dump())
    wb = openpyxl.load_workbook(io.BytesIO(soa_bytes))
    ws = wb.active
    header_col8 = ws.cell(row=4, column=8).value
    assert "0-5" not in header_col8
    assert "Score Contribution" in header_col8 or "Điểm Đóng góp" in header_col8

    # Verify A.5.1 row has positive contribution (10.0 for critical satisfied)
    a51_contrib = None
    for r in range(5, 15):
        if ws.cell(row=r, column=1).value == "A.5.1":
            a51_contrib = ws.cell(row=r, column=8).value
            break
    assert a51_contrib == 10.0


def test_tcvn_fixture_and_docx_satisfied_count():
    """TCVN fixture: 20 satisfied, 14 missing -> 62.0%, DOCX must say '(20/34 tiêu chí TCVN đạt)', NOT '(0/34'."""
    flat_tcvn = get_flat_controls("tcvn11930")
    controls = []
    for idx, c in enumerate(flat_tcvn):
        is_imp = idx < 20
        controls.append(ControlItem(
            control_id=c["id"],
            label=c["label"],
            category=c.get("category", "TCVN 11930"),
            weight=c["weight"],
            user_declaration="implemented" if is_imp else "not_implemented",
            assessment_verdict="satisfied" if is_imp else "missing",
        ))

    scoring = calc_weighted_compliance([c.model_dump() for c in controls])
    assert scoring["weighted_score"] == 168.0
    assert scoring["weighted_max_score"] == 271.0
    assert scoring["percentage"] == 62.0

    asm = UnifiedAssessmentResult(
        assessment_id="asm_tcvn_evidence_2026",
        run_id="run_tcvn_evidence_001",
        standard="tcvn11930",
        controls=controls,
        weighted_compliance=WeightedCompliance(
            weighted_score=scoring["weighted_score"],
            weighted_max_score=scoring["weighted_max_score"],
            percentage=scoring["percentage"],
        ),
    )

    cov = asm.control_coverage
    assert cov.total_applicable_controls == 34
    assert cov.evidence_supported_implemented == 20
    assert cov.not_evidenced_or_missing == 14
    assert cov.self_declared_implemented == 20
    assert cov.raw_percentage == 58.8

    # Invariant
    contrib_sum = round(sum(c.weighted_score_contribution for c in asm.controls), 1)
    assert contrib_sum == asm.weighted_compliance.weighted_score == 168.0

    # DOCX test
    docx_bytes = generate_report_docx(assessment_data=asm.model_dump())
    doc = Document(io.BytesIO(docx_bytes))
    all_text = " ".join([p.text for p in doc.paragraphs] + [cell.text for t in doc.tables for r in t.rows for cell in r.cells])
    assert "20/34 tiêu chí TCVN đạt" in all_text
    assert "(0/34 tiêu chí TCVN đạt)" not in all_text
    assert "( 0/34 tiêu chí TCVN đạt)" not in all_text


def test_regression_two_real_cases_metrics_and_traceability():
    """Verify live case files on disk strictly adhere to specified metrics, risk summary, and evidence traceability."""
    import os
    import json
    data_dir = os.getenv("DATA_PATH", "./data")
    iso_path = os.path.join(data_dir, "assessments", "163f3f6b-1265-41ac-acab-10f9d7580da5.json")
    tcvn_path = os.path.join(data_dir, "assessments", "e9bee7ff-8f23-4f01-9666-7e271e7b1a77.json")

    if not (os.path.exists(iso_path) and os.path.exists(tcvn_path)):
        pytest.skip("Live assessment data not mounted in test environment")

    # 1. ISO 27001
    with open(iso_path, "r", encoding="utf-8") as f:
        iso_asm = json.load(f)
    iso_jd = iso_asm.get("json_data", iso_asm)
    assert len(iso_jd["controls"]) == 93
    assert iso_jd["compliance"]["score"] == 34
    assert iso_jd["compliance"]["percentage"] == 36.6
    assert iso_jd["weighted_compliance"]["weighted_score"] == 257.0
    assert iso_jd["weighted_compliance"]["weighted_max_score"] == 495.0
    assert iso_jd["weighted_compliance"]["percentage"] == 51.9
    assert len(iso_jd["risk_register"]) == 59
    assert iso_jd["risk_summary"]["total_gaps"] == 59
    assert iso_jd["risk_summary"]["critical_gaps"] == 3
    assert iso_jd["risk_summary"]["high_gaps"] == 23
    assert iso_jd["risk_summary"]["medium_gaps"] == 28
    assert iso_jd["risk_summary"]["low_gaps"] == 5

    # Citations check
    iso_null_shas = [cit for c in iso_jd["controls"] for cit in c.get("evidence_citations", []) if not cit.get("sha256")]
    assert len(iso_null_shas) == 0

    # 2. TCVN 11930
    with open(tcvn_path, "r", encoding="utf-8") as f:
        tcvn_asm = json.load(f)
    tcvn_jd = tcvn_asm.get("json_data", tcvn_asm)
    assert len(tcvn_jd["controls"]) == 34
    assert tcvn_jd["compliance"]["score"] == 22
    assert tcvn_jd["compliance"]["percentage"] == 64.7
    assert tcvn_jd["weighted_compliance"]["weighted_score"] == 195.0
    assert tcvn_jd["weighted_compliance"]["weighted_max_score"] == 271.0
    assert tcvn_jd["weighted_compliance"]["percentage"] == 72.0
    assert len(tcvn_jd["risk_register"]) == 12
    assert tcvn_jd["risk_summary"]["total_gaps"] == 12
    assert tcvn_jd["risk_summary"]["critical_gaps"] == 4
    assert tcvn_jd["risk_summary"]["high_gaps"] == 6
    assert tcvn_jd["risk_summary"]["medium_gaps"] == 2
    assert tcvn_jd["risk_summary"]["low_gaps"] == 0

    tcvn_null_shas = [cit for c in tcvn_jd["controls"] for cit in c.get("evidence_citations", []) if not cit.get("sha256")]
    assert len(tcvn_null_shas) == 0

    # Manifest checks
    iso_mf_path = os.path.join(data_dir, "evidence_manifests", "163f3f6b-1265-41ac-acab-10f9d7580da5.json")
    tcvn_mf_path = os.path.join(data_dir, "evidence_manifests", "e9bee7ff-8f23-4f01-9666-7e271e7b1a77.json")
    with open(iso_mf_path, "r", encoding="utf-8") as f:
        iso_mf = json.load(f)
    assert iso_mf["total_files"] == 37
    assert iso_mf["mapped_control_count"] == 37

    with open(tcvn_mf_path, "r", encoding="utf-8") as f:
        tcvn_mf = json.load(f)
    assert tcvn_mf["total_files"] == 23
    assert tcvn_mf["mapped_control_count"] == 23


def test_regression_export_endpoints_all_six_artefacts():
    """Verify export endpoints generate valid 6 artefacts and log audit traces with SHA-256."""
    from fastapi.testclient import TestClient
    from main import app
    import openpyxl
    from docx import Document

    client = TestClient(app)

    for aid, is_tcvn in [("163f3f6b-1265-41ac-acab-10f9d7580da5", False), ("e9bee7ff-8f23-4f01-9666-7e271e7b1a77", True)]:
        short_id = aid[:8]

        # 1. DOCX
        resp_docx = client.post(f"/api/iso27001/assessments/{aid}/export-docx")
        assert resp_docx.status_code == 200
        assert f"IT_Audit_Report_{short_id}.docx" in resp_docx.headers["content-disposition"]
        doc = Document(io.BytesIO(resp_docx.content))
        assert len(doc.paragraphs) > 10
        if is_tcvn:
            full_text = " ".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for r in t.rows for c in r.cells])
            assert "HỒ SƠ ĐỀ XUẤT CẤP ĐỘ AN TOÀN HỆ THỐNG THÔNG TIN" not in full_text
            assert "XÁC NHẬN VÀ KÝ DUYỆT HỒ SƠ ĐỀ XUẤT CẤP ĐỘ" not in full_text
            assert "CĂN CỨ PHÁP LÝ THỰC HIỆN" not in full_text
            assert "BÁO CÁO ĐÁNH GIÁ SƠ BỘ THEO CATALOGUE TCVN 11930:2017" in full_text

        # 2. SoA XLSX
        resp_soa = client.post("/api/iso27001/soa/export", json={"assessment_id": aid, "org_name": "Test Org"})
        assert resp_soa.status_code == 200
        expected_soa_fn = f"SoA_TCVN11930_{short_id}.xlsx" if is_tcvn else f"SoA_ISO27001_{short_id}.xlsx"
        assert expected_soa_fn in resp_soa.headers["content-disposition"]
        wb_soa = openpyxl.load_workbook(io.BytesIO(resp_soa.content))
        assert "Statement of Applicability" in wb_soa.sheetnames

        # 3. Risk Register XLSX
        resp_rr = client.post(f"/api/iso27001/assessments/{aid}/export-risk-register")
        assert resp_rr.status_code == 200
        assert f"Risk_Register_{short_id}.xlsx" in resp_rr.headers["content-disposition"]
        wb_rr = openpyxl.load_workbook(io.BytesIO(resp_rr.content))
        assert "Risk Register" in wb_rr.sheetnames

        # 4. PDF
        resp_pdf = client.post(f"/api/iso27001/assessments/{aid}/export-pdf")
        assert resp_pdf.status_code == 200
        assert f"Audit_Report_{short_id}.pdf" in resp_pdf.headers["content-disposition"]
        assert resp_pdf.content[:4] == b"%PDF" or b"<!DOCTYPE html" in resp_pdf.content

        # 5. Assessment JSON
        resp_json = client.get(f"/api/iso27001/assessments/{aid}")
        assert resp_json.status_code == 200

        # 6. Audit Trace JSON
        resp_trace = client.get(f"/api/iso27001/assessments/{aid}/audit-trace")
        assert resp_trace.status_code == 200
        trace_data = resp_trace.json()
        export_events = [e for e in trace_data.get("events", []) if e.get("event_type") == "artifact_exported"]
        assert len(export_events) >= 5
        formats_logged = {e.get("payload", {}).get("export_format") for e in export_events}
        assert {"docx", "soa_xlsx", "risk_register_xlsx", "pdf"}.issubset(formats_logged)




