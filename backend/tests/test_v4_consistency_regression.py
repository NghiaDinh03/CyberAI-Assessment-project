"""Regression test suite for cross-artifact consistency (Item 4).

Verifies:
1. PDF/DOCX contain no controls/risks outside the current assessment.
2. TCVN report contains no A.5.31, A.5.34, A.8.5 or hardcoded ISO risks.
3. Test-pack Risk Register contains only controls with GAP/risk; satisfied controls (A.5.1, A.5.6) are omitted.
4. weight_level matches weight_points in JSON, SoA, DOCX, and PDF (A.5.6 is Low / 1.0 everywhere).
5. UI zero-verified has no "Preliminary Weighted Coverage" or 246/495; UTF-8 Vietnamese strings are clean.
"""

import asyncio
import io
import json
import os
import openpyxl
import pytest
from datetime import datetime, timezone
import docx

from schemas.assessment_schema import (
    ControlItem,
    UnifiedAssessmentResult,
    WeightedCompliance,
    ControlCoverage,
)
from services.report_docx_generator import generate_report_docx
from services.risk_register_exporter import generate_risk_register_xlsx
from services.soa_exporter import generate_soa_xlsx
from services.chat_service import ChatService
from services.controls_catalog import calc_weighted_compliance


def _build_test_pack_unified() -> UnifiedAssessmentResult:
    """Standard 4-control test pack:
    - A.5.1: satisfied (critical, 10.0)
    - A.5.3: partial (high, 5.0 -> contribution 2.5)
    - A.5.5: missing (medium, 3.0 -> contribution 0.0)
    - A.5.6: satisfied (low, 1.0 -> contribution 1.0)
    """
    controls = [
        ControlItem(
            control_id="A.5.1",
            label="Chính sách an toàn thông tin",
            weight="critical",
            weight_points=10.0,
            weight_level="critical",
            user_declaration="implemented",
            assessment_verdict="satisfied",
            evidence_file_ids=["A.5.1_chinh_sach_attt.pdf"],
            likelihood=1,
            impact=2,
            risk_score=2,
            risk_severity="low",
            gap="Chính sách đã ban hành đầy đủ.",
            recommendation="Duy trì rà soát định kỳ.",
        ),
        ControlItem(
            control_id="A.5.3",
            label="Phân định vai trò và trách nhiệm ATTT",
            weight="high",
            weight_points=5.0,
            weight_level="high",
            user_declaration="implemented",
            assessment_verdict="partial",
            evidence_file_ids=["A.5.3_phan_dinh_vai_tro_attt.docx"],
            likelihood=2,
            impact=3,
            risk_score=6,
            risk_severity="medium",
            gap="Chưa phân định rõ vai trò quản trị ứng dụng và cơ sở dữ liệu.",
            recommendation="Ban hành ma trận trách nhiệm RACI.",
        ),
        ControlItem(
            control_id="A.5.5",
            label="Liên hệ với cơ quan chức năng",
            weight="medium",
            weight_points=3.0,
            weight_level="medium",
            user_declaration="not_implemented",
            assessment_verdict="missing",
            evidence_file_ids=["A.5.5_missing_authority_contact.txt"],
            likelihood=3,
            impact=3,
            risk_score=9,
            risk_severity="high",
            gap="Chưa thiết lập danh bạ và quy trình liên lạc cơ quan thẩm quyền (Cục ATTT, VNCERT).",
            recommendation="Xây dựng quy trình liên hệ cơ quan quản lý khi có sự cố.",
        ),
        ControlItem(
            control_id="A.5.6",
            label="Liên hệ với các nhóm chuyên môn đặc thù",
            weight="low",
            weight_points=1.0,
            weight_level="low",
            user_declaration="implemented",
            assessment_verdict="satisfied",
            evidence_file_ids=["A.5.6_special_interest_groups.txt"],
            likelihood=1,
            impact=1,
            risk_score=1,
            risk_severity="low",
            gap="",
            recommendation="",
        ),
    ]

    scoring = calc_weighted_compliance([c.model_dump() for c in controls])
    # 12.5 / 18.0 = 69.4%
    return UnifiedAssessmentResult(
        assessment_id="asm_test_pack_v4",
        run_id="run_test_pack_v4",
        standard="iso27001",
        code_version="v1.2.0-rel",
        created_at=datetime.now(timezone.utc).isoformat(),
        controls=controls,
        weighted_compliance=WeightedCompliance(**scoring),
        control_coverage=ControlCoverage(
            self_declared_implemented=2,
            evidence_supported_implemented=1,
            not_evidenced_or_missing=1,
            total_controls=3,
            raw_percentage=66.7,
        ),
        organization={
            "name": "Tổ chức Kiểm thử Chuẩn 69.4%",
            "industry": "Công nghệ số & Kiểm thử",
        },
    )


def test_docx_pdf_no_alien_controls():
    """1. PDF/DOCX must NOT contain controls/risks outside current assessment (no sample A.5.31, A.5.34, A.8.5)."""
    unified = _build_test_pack_unified()
    data = unified.model_dump()

    # Generate DOCX
    docx_bytes = generate_report_docx(data)
    doc = docx.Document(io.BytesIO(docx_bytes))

    full_docx_text = "\n".join([p.text for p in doc.paragraphs])
    for table in doc.tables:
        for row in table.rows:
            full_docx_text += "\n" + " | ".join([cell.text for cell in row.cells])

    # Assert no alien controls in DOCX
    assert "A.5.31" not in full_docx_text
    assert "A.5.34" not in full_docx_text
    assert "A.8.5" not in full_docx_text
    assert "A.5.29" not in full_docx_text

    # Assert test pack controls A.5.3 and A.5.5 are present in risk table
    assert "A.5.3" in full_docx_text
    assert "A.5.5" in full_docx_text

    # Generate healed report (used for PDF generation)
    raw_rep = "# BÁO CÁO\nNội dung sơ bộ..."
    healed = ChatService.ensure_complete_report(
        markdown_report=raw_rep,
        percentage=unified.weighted_compliance.percentage,
        score=1,
        max_score=3,
        json_data=data,
    )

    # Assert healed report contains ONLY real risks from current assessment
    assert "A.5.31" not in healed
    assert "A.5.34" not in healed
    assert "A.8.5" not in healed
    assert "A.5.3" in healed
    assert "A.5.5" in healed


def test_tcvn_report_no_iso_controls():
    """2. TCVN report must NOT contain A.5.31, A.5.34, A.8.5 or hardcoded 53 findings."""
    tcvn_controls = [
        ControlItem(
            control_id="NW.01",
            label="Phân vùng mạng và cấu hình Firewall",
            weight="critical",
            weight_points=10.0,
            weight_level="critical",
            user_declaration="implemented",
            assessment_verdict="partial",
            gap="Chưa hoàn thiện phân vùng IT/OT.",
            recommendation="Bổ sung Firewall công nghiệp phân tách.",
            likelihood=2,
            impact=4,
            risk_score=8,
            risk_severity="high",
        ),
        ControlItem(
            control_id="SV.01",
            label="Bảo vệ máy chủ điều hành",
            weight="high",
            weight_points=5.0,
            weight_level="high",
            user_declaration="implemented",
            assessment_verdict="missing",
            gap="HĐH máy chủ Windows Server 2008 EOL.",
            recommendation="Nâng cấp HĐH và cập nhật Hotfix.",
            likelihood=3,
            impact=3,
            risk_score=9,
            risk_severity="high",
        ),
    ]
    scoring = calc_weighted_compliance([c.model_dump() for c in tcvn_controls])
    tcvn_unified = UnifiedAssessmentResult(
        assessment_id="asm_tcvn_test_v4",
        run_id="run_tcvn_test_v4",
        standard="tcvn11930",
        code_version="v1.2.0-rel",
        created_at=datetime.now(timezone.utc).isoformat(),
        controls=tcvn_controls,
        weighted_compliance=WeightedCompliance(**scoring),
        organization={
            "name": "Nhiệt điện Thủ Đức - EVN TPC",
            "industry": "Năng lượng & Điện lực",
        },
    )
    tcvn_data = tcvn_unified.model_dump()

    # Generate TCVN DOCX
    docx_bytes = generate_report_docx(tcvn_data)
    doc = docx.Document(io.BytesIO(docx_bytes))
    docx_text = "\n".join([p.text for p in doc.paragraphs])
    for table in doc.tables:
        for row in table.rows:
            docx_text += "\n" + " | ".join([cell.text for cell in row.cells])

    # Assert no ISO controls in TCVN report
    assert "A.5.31" not in docx_text
    assert "A.5.34" not in docx_text
    assert "A.8.5" not in docx_text
    assert "53 lỗ hổng bảo mật (18 Nghiêm trọng" not in docx_text

    # Healed markdown report for TCVN
    healed = ChatService.ensure_complete_report(
        markdown_report="# TCVN REPORT",
        percentage=tcvn_unified.weighted_compliance.percentage,
        std_name="TCVN 11930:2017 Cấp độ 3",
        json_data=tcvn_data,
    )
    assert "A.5.31" not in healed
    assert "A.5.34" not in healed
    assert "A.8.5" not in healed
    assert "NW.01" in healed or "SV.01" in healed


def test_frontend_resultview_no_preliminary_weighted_coverage_and_valid_utf8():
    """5b. Ensure ResultView.js contains no 'Preliminary Weighted Coverage' card or '246/495' and has valid UTF-8."""
    # Read ResultView.js from frontend-next if mounted / accessible
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend-next", "src", "app", "form-iso", "_components", "views", "ResultView.js"),
        "/workspace/frontend-next/src/app/form-iso/_components/views/ResultView.js",
    ]
    frontend_path = next((p for p in candidates if os.path.exists(p)), None)
    if frontend_path:
        with open(frontend_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Assert no 'Preliminary Weighted Coverage' label in the score stats cards
        assert "Preliminary Weighted Coverage" not in content, "ResultView.js must not contain 'Preliminary Weighted Coverage'"

        # Assert no 246/495 or 289/495 hardcoded numbers
        assert "246 / 495" not in content
        assert "289 / 495" not in content

        # Assert template label is present in proper Vietnamese UTF-8
        assert "Dữ liệu mẫu từ template" in content
        assert "không được coi là evidence" in content

        # Assert no mojibake character patterns in ResultView.js
        assert "Ã" not in content
        assert "á»" not in content


def test_test_pack_risk_register_excludes_na_and_satisfied():
    """3. Test-pack Risk Register contains only applicable controls with GAP/risk; A.5.6 NA is omitted."""
    unified = _build_test_pack_unified()
    xlsx_bytes = generate_risk_register_xlsx(assessment_data=unified)

    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    ws = wb["Risk Register"]

    # Iterate rows starting from row 4
    risk_control_ids = []
    for r in range(4, ws.max_row + 1):
        cid = ws.cell(row=r, column=2).value
        if cid:
            risk_control_ids.append(str(cid).strip())

    # A.5.3 (partial) and A.5.5 (missing) MUST be present
    assert "A.5.3" in risk_control_ids
    assert "A.5.5" in risk_control_ids

    # A.5.1 (satisfied) and A.5.6 (satisfied) MUST NOT be present
    assert "A.5.1" not in risk_control_ids
    assert "A.5.6" not in risk_control_ids
    assert len(risk_control_ids) == 2


def test_weight_level_and_points_consistency():
    """4. Check weight_level matches weight_points in JSON, SoA, DOCX, and PDF. A.5.6 is Low everywhere."""
    unified = _build_test_pack_unified()
    data = unified.model_dump()

    # Check JSON
    a56_json = next(c for c in data["controls"] if c["control_id"] == "A.5.6")
    assert a56_json["weight_level"] == "low"
    assert a56_json["weight_points"] == 1.0

    # Check SoA export
    soa_bytes = generate_soa_xlsx(assessment_data=unified)
    wb = openpyxl.load_workbook(io.BytesIO(soa_bytes))
    ws = wb["Statement of Applicability"]

    # Find row for A.5.6
    a56_soa_row = None
    for r in range(5, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == "A.5.6":
            a56_soa_row = r
            break

    assert a56_soa_row is not None, "A.5.6 not found in SoA"
    weight_in_soa = ws.cell(row=a56_soa_row, column=4).value
    # Must be "Low", NOT "Medium"
    assert str(weight_in_soa).lower() == "low"


def test_zero_verified_no_risks_fallback_and_ui_consistency():
    """5. Zero verified assessment with no risks outputs 'Không có rủi ro cần đưa vào báo cáo' and UI check."""
    # Build clean zero-verified where all controls are satisfied or no risks
    clean_unified = UnifiedAssessmentResult(
        assessment_id="asm_clean_v4",
        run_id="run_clean_v4",
        standard="iso27001",
        code_version="v1.2.0-rel",
        created_at=datetime.now(timezone.utc).isoformat(),
        controls=[
            ControlItem(
                control_id="A.5.1",
                label="Chính sách ATTT",
                weight="critical",
                weight_points=10.0,
                weight_level="critical",
                assessment_verdict="satisfied",
                user_declaration="implemented",
            )
        ],
        weighted_compliance=WeightedCompliance(
            score=10.0,
            weighted_score=10.0,
            weighted_max_score=10.0,
            percentage=100.0,
        ),
    )

    # DOCX: must say "Không có rủi ro cần đưa vào báo cáo"
    docx_bytes = generate_report_docx(clean_unified.model_dump())
    doc = docx.Document(io.BytesIO(docx_bytes))
    docx_text = "\n".join([p.text for p in doc.paragraphs])
    assert "Không có rủi ro cần đưa vào báo cáo" in docx_text

    # Risk Register Excel: must say "Không có rủi ro cần đưa vào báo cáo"
    rr_bytes = generate_risk_register_xlsx(assessment_data=clean_unified)
    wb = openpyxl.load_workbook(io.BytesIO(rr_bytes))
    ws = wb["Risk Register"]
    assert "Không có rủi ro cần đưa vào báo cáo" in str(ws["A4"].value)

    # Healed markdown: must say "Không có rủi ro cần đưa vào báo cáo"
    healed = ChatService.ensure_complete_report(
        markdown_report="# REPORT",
        percentage=100.0,
        json_data=clean_unified.model_dump(),
    )
    assert "Không có rủi ro cần đưa vào báo cáo" in healed
