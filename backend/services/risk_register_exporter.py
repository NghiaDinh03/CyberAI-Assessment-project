"""Risk Register .xlsx Exporter for CyberAI Assessment Platform.

Generates an IT Audit Risk Register spreadsheet with L x I quantitative risk scoring,
SOC severity badges, treatment plans, and ownership assignments.
"""

from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# ── Color Palettes & Styles ──────────────────────────────────────────
_HEADER_FILL = PatternFill(start_color="0A2540", end_color="0A2540", fill_type="solid")
_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
_META_FILL = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
_META_FONT = Font(name="Calibri", size=11, bold=True, color="0A2540")
_BODY_FONT = Font(name="Calibri", size=10)
_BOLD_FONT = Font(name="Calibri", size=10, bold=True)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)

_SEV_FILLS = {
    "critical": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
    "high": PatternFill(start_color="FFEDD5", end_color="FFEDD5", fill_type="solid"),
    "medium": PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid"),
    "low": PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid"),
}

_SEV_FONTS = {
    "critical": Font(name="Calibri", size=10, bold=True, color="991B1B"),
    "high": Font(name="Calibri", size=10, bold=True, color="9A3412"),
    "medium": Font(name="Calibri", size=10, bold=True, color="854D0E"),
    "low": Font(name="Calibri", size=10, bold=True, color="334155"),
}


def generate_risk_register_xlsx(
    assessment_id: Optional[str] = None,
    assessment_data: Optional[Dict[str, Any]] = None,
    org_name: str = "",
) -> bytes:
    """Produce Risk Register Excel workbook as bytes."""
    data = assessment_data or {}
    if assessment_id and not data:
        data_path = os.getenv("DATA_PATH", "./data")
        fpath = os.path.join(data_path, "assessments", f"{assessment_id}.json")
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load assessment {assessment_id}: {e}")

    sys_info = data.get("system_info", {})
    display_org = org_name or sys_info.get("organization", {}).get("name") or sys_info.get("org_name") or "Doanh nghiệp"
    raw_std = data.get("standard") or sys_info.get("assessment_standard") or "ISO 27001:2022"
    std_display = raw_std.get("name") if isinstance(raw_std, dict) else str(raw_std)
    eval_date = data.get("created_at", "")[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_data = data.get("json_data") or data.get("result", {}).get("json_data") or {}
    aid_str = assessment_id or data.get("assessment_id") or "N/A"
    run_id = data.get("run_id") or json_data.get("run_id") or "run_default"
    code_version = data.get("code_version") or json_data.get("code_version") or "v1.2.0-rel"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Risk Register"
    ws.views.sheetView[0].showGridLines = True

    # 1. Title & Meta Banner
    ws.merge_cells("A1:O1")
    t_cell = ws["A1"]
    t_cell.value = f"SỔ ĐĂNG KÝ RỦI RO AN TOÀN THÔNG TIN (RISK REGISTER) — {display_org.upper()}"
    t_cell.font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    t_cell.fill = PatternFill(start_color="0A2540", end_color="0A2540", fill_type="solid")
    t_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Row 2: Metadata Info
    ws.merge_cells("A2:O2")
    m_cell = ws["A2"]
    m_cell.value = (
        f"Assessment ID: {aid_str}   |   Run ID: {run_id}   |   Code Version: {code_version}   |   "
        f"Tiêu chuẩn: {std_display}   |   Ngày lập: {eval_date}   |   Nền tảng: CyberAI Platform"
    )
    m_cell.font = Font(name="Calibri", size=10, italic=True, color="334155")
    m_cell.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    m_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 24

    # Row 3: Headers
    headers = [
        ("STT", 6),
        ("Mã Control", 13),
        ("Tên Control / Tiêu Chuẩn", 26),
        ("Nhóm Kiểm Soát", 20),
        ("Khoảng Trống An Ninh (GAP)", 36),
        ("Mức Độ", 13),
        ("Khả Năng (L: 1-5)", 15),
        ("Tác Động (I: 1-5)", 15),
        ("Điểm Rủi Ro (L×I)", 16),
        ("Cơ sở Đánh giá", 18),
        ("Khuyến Nghị Khắc Phục", 36),
        ("Phương Án Xử Lý", 18),
        ("Thời Hạn", 14),
        ("Chủ Sở Hữu", 18),
        ("Trạng Thái", 14),
    ]

    for col_idx, (h_title, col_width) in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col_idx, value=h_title)
        cell.font = _HEADER_FONT
        cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        cell.alignment = _CENTER
        cell.border = _THIN_BORDER
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = col_width

    ws.row_dimensions[3].height = 28

    # Extract risk rows
    raw_risks = json_data.get("risk_register", [])
    if not raw_risks and "top_gaps" in json_data:
        raw_risks = json_data.get("top_gaps", [])

    # Sort by risk_score desc
    def _score(r):
        return int(r.get("risk_score") or (int(r.get("likelihood", 3)) * int(r.get("impact", 3))))

    sorted_risks = sorted(raw_risks, key=_score, reverse=True)

    current_row = 4
    for idx, r_item in enumerate(sorted_risks, 1):
        ctrl_id = str(r_item.get("control_id") or r_item.get("id") or "N/A")
        ctrl_label = str(r_item.get("label") or ctrl_id)
        cat = str(r_item.get("category") or "General")
        gap = str(r_item.get("gap") or "Khoảng trống kiểm soát cần bổ sung bằng chứng hoặc chính sách.")
        sev = str(r_item.get("severity") or "medium").lower()
        l_val = int(r_item.get("likelihood") or (4 if sev in ("critical", "high") else 3))
        i_val = int(r_item.get("impact") or (5 if sev == "critical" else 3))
        r_score = int(r_item.get("risk_score") or (l_val * i_val))
        basis = str(r_item.get("risk_assessment_basis") or "rule_based")
        rec = str(r_item.get("recommendation") or "Ban hành quy trình và thực thi biện pháp kỹ thuật.")
        treatment = "Giảm thiểu (Mitigate)" if r_score >= 10 else "Chấp nhận có điều kiện" if r_score < 5 else "Kiểm soát bổ sung"
        timeline = str(r_item.get("timeline") or ("0-30 ngày" if sev in ("critical", "high") else "1-3 tháng"))
        owner = "CISO / IT Security" if sev in ("critical", "high") else "Hạ tầng / SysAdmin"
        status = "Đang mở (Open)"

        row_vals = [
            (idx, _CENTER, _BODY_FONT, None),
            (ctrl_id, _CENTER, _BOLD_FONT, None),
            (ctrl_label, _LEFT, _BODY_FONT, None),
            (cat, _LEFT, _BODY_FONT, None),
            (gap, _LEFT, _BODY_FONT, None),
            (sev.upper(), _CENTER, _SEV_FONTS.get(sev, _BOLD_FONT), _SEV_FILLS.get(sev)),
            (l_val, _CENTER, _BODY_FONT, None),
            (i_val, _CENTER, _BODY_FONT, None),
            (r_score, _CENTER, _SEV_FONTS.get(sev, _BOLD_FONT), _SEV_FILLS.get(sev)),
            (basis, _CENTER, _BODY_FONT, None),
            (rec, _LEFT, _BODY_FONT, None),
            (treatment, _CENTER, _BODY_FONT, None),
            (timeline, _CENTER, _BODY_FONT, None),
            (owner, _CENTER, _BODY_FONT, None),
            (status, _CENTER, _BODY_FONT, None),
        ]

        for col_idx, (val, align, font_style, fill_style) in enumerate(row_vals, 1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.alignment = align
            cell.font = font_style
            cell.border = _THIN_BORDER
            if fill_style:
                cell.fill = fill_style

        ws.row_dimensions[current_row].height = 24
        current_row += 1

    # Freeze panes below header
    ws.freeze_panes = "A4"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
