"""Statement of Applicability (SoA) .xlsx exporter.

Reads the controls catalog (ISO 27001 or TCVN 11930) and assessment state from
``data/assessments/{assessment_id}.json`` to produce a standards-compliant
SoA spreadsheet matching the unified assessment schema contract.
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

from services.evidence_parser import mask_evidence_filename

logger = logging.getLogger(__name__)

# ── Style constants ──────────────────────────────────────────────────

_HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
_CATEGORY_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
_CATEGORY_FONT = Font(name="Calibri", size=11, bold=True)
_BODY_FONT = Font(name="Calibri", size=10)
_WRAP = Alignment(wrap_text=True, vertical="top")
_CENTER = Alignment(horizontal="center", vertical="top", wrap_text=True)
_THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)

# Verdict color badges
_VERDICT_FILLS = {
    "satisfied": PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid"),
    "not_evidenced": PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid"),
    "missing": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid"),
    "needs_expert_review": PatternFill(start_color="FFEDD5", end_color="FFEDD5", fill_type="solid"),
}
_VERDICT_FONTS = {
    "satisfied": Font(name="Calibri", size=10, bold=True, color="166534"),
    "not_evidenced": Font(name="Calibri", size=10, bold=True, color="854D0E"),
    "missing": Font(name="Calibri", size=10, bold=True, color="991B1B"),
    "needs_expert_review": Font(name="Calibri", size=10, bold=True, color="9A3412"),
}

# Column layout for ISO 27001 (English)
_COLUMNS_ISO = [
    ("Control ID", 14),
    ("Control Name", 38),
    ("Category", 20),
    ("Weight", 12),
    ("Applicable", 12),
    ("Justification for Inclusion/Exclusion", 36),
    ("Implementation Status", 22),
    ("Score (0-5)", 12),
    ("Evidence (Masked)", 32),
    ("Notes / Recommendation", 36),
    ("Verdict", 18),
    ("Expert Review", 16),
]

# Column layout for TCVN 11930 (Vietnamese)
_COLUMNS_TCVN = [
    ("Mã Kiểm soát", 14),
    ("Tên Biện pháp Kiểm soát", 38),
    ("Phân nhóm", 22),
    ("Trọng số", 12),
    ("Áp dụng", 12),
    ("Lý do Áp dụng / Căn cứ", 36),
    ("Trạng thái Triển khai", 22),
    ("Điểm số (0-5)", 12),
    ("Minh chứng (Đã che)", 32),
    ("Ghi chú / Khuyến nghị", 36),
    ("Kết luận Đánh giá", 18),
    ("Trạng thái Chuyên gia", 16),
]


def _flatten_controls(standard: str) -> List[dict]:
    """Flatten the nested category structure into a flat list with category info."""
    flat: List[dict] = []
    from services.controls_catalog import get_categories
    categories = get_categories(standard)
    for cat in categories:
        category_name = cat["category"]
        for ctrl in cat["controls"]:
            flat.append({
                "id": ctrl["id"],
                "label": ctrl["label"],
                "category": category_name,
                "weight": ctrl.get("weight", "medium"),
            })
    return flat


def _load_assessment(assessment_id: str) -> Optional[dict]:
    """Load assessment data from disk."""
    base = os.getenv("DATA_PATH", "./data")
    path = Path(base) / "assessments" / f"{assessment_id}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _extract_control_scores(assessment: dict) -> Dict[str, dict]:
    """Extract per-control scoring data from an assessment record according to unified schema.

    Returns a dict keyed by control ID with verdict, basis, evidence files, and notes.
    """
    scores: Dict[str, dict] = {}

    json_data = assessment.get("json_data") or assessment.get("result", {}).get("json_data") or {}
    controls_data = json_data.get("controls") or []

    for ctrl in controls_data:
        cid = ctrl.get("control_id") or ctrl.get("id")
        if not cid:
            continue

        raw_ev = ctrl.get("evidence_file_ids", [])
        if not raw_ev and ctrl.get("evidence"):
            raw_ev = ctrl["evidence"] if isinstance(ctrl["evidence"], list) else [ctrl["evidence"]]

        masked_ev = [mask_evidence_filename(os.path.basename(f)) for f in raw_ev if f]

        verdict = ctrl.get("assessment_verdict") or ctrl.get("evidence_verdict")
        decl = ctrl.get("user_declaration")
        if not verdict:
            verdict = "satisfied" if decl == "implemented" and masked_ev else "not_evidenced" if decl == "implemented" else "missing"

        v_basis = ctrl.get("verdict_basis", [])
        basis_str = ", ".join(v_basis) if isinstance(v_basis, list) else str(v_basis)
        score_val = ctrl.get("score")
        if score_val is None:
            score_val = 4 if verdict == "satisfied" else 3 if (decl == "implemented" or verdict == "not_evidenced") else 0

        scores[cid] = {
            "user_declaration": decl or ("implemented" if verdict in ("satisfied", "not_evidenced") else "not_implemented"),
            "assessment_verdict": verdict,
            "verdict_basis": basis_str or "user_declaration",
            "score": score_val,
            "evidence": masked_ev,
            "expert_review_status": ctrl.get("expert_review_status", "pending"),
            "notes": ctrl.get("recommendation", ctrl.get("notes", "")),
        }

    # Fallback to implemented_controls list if json_data was not populated
    sys_info = assessment.get("system_info") or {}
    compliance = sys_info.get("compliance") or {}
    implemented = compliance.get("implemented_controls") or []
    for cid in implemented:
        if cid not in scores:
            scores[cid] = {
                "user_declaration": "implemented",
                "assessment_verdict": "not_evidenced",
                "verdict_basis": "user_declaration",
                "score": 3,
                "evidence": [],
                "expert_review_status": "pending",
                "notes": "",
            }

    # Fallback evidence_map
    evidence_map = sys_info.get("evidence_map") or assessment.get("evidence_map") or {}
    for cid, files in evidence_map.items():
        flist = files if isinstance(files, list) else [files]
        masked = [mask_evidence_filename(os.path.basename(f)) for f in flist if f]
        if cid in scores:
            scores[cid]["evidence"] = masked
            if scores[cid]["user_declaration"] == "implemented":
                scores[cid]["assessment_verdict"] = "satisfied"
                scores[cid]["verdict_basis"] = "user_declaration, direct_evidence"
        else:
            scores[cid] = {
                "user_declaration": "not_implemented",
                "assessment_verdict": "not_evidenced",
                "verdict_basis": "direct_evidence",
                "evidence": masked,
                "expert_review_status": "pending",
                "notes": "",
            }

    return scores


def generate_soa_xlsx(
    assessment_id: Optional[str] = None,
    implemented_controls: Optional[List[str]] = None,
    org_name: str = "",
    assessment_data: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generate a Statement of Applicability .xlsx file supporting dynamic standards.

    Args:
        assessment_id: If provided, loads scoring data and standard from the assessment.
        implemented_controls: Fallback list of implemented control IDs.
        org_name: Organization name for the header.
        assessment_data: Optional direct assessment dictionary.

    Returns:
        Raw .xlsx bytes ready for HTTP streaming.
    """
    standard = "iso27001"
    control_scores: Dict[str, dict] = {}
    run_id = "N/A"
    code_version = "v1.2.0-rel"
    created_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    assessment = assessment_data
    if not assessment and assessment_id:
        assessment = _load_assessment(assessment_id)

    if assessment:
        raw_std = assessment.get("standard") or assessment.get("system_info", {}).get("assessment_standard") or "iso27001"
        standard = raw_std.get("id") if isinstance(raw_std, dict) else str(raw_std)
        run_id = assessment.get("run_id") or "run_default"
        code_version = assessment.get("code_version") or "v1.2.0-rel"
        created_time = assessment.get("created_at") or created_time
        control_scores = _extract_control_scores(assessment)
        if not org_name:
            sys_info = assessment.get("system_info") or {}
            org_info = sys_info.get("organization") or {}
            org_name = org_info.get("name") or sys_info.get("org_name", "")

    elif implemented_controls:
        if any(c.split(".")[0] in ("NW", "SV", "APP", "DAT", "MNG") for c in implemented_controls):
            standard = "tcvn11930"
        for cid in implemented_controls:
            control_scores[cid] = {
                "user_declaration": "implemented",
                "assessment_verdict": "not_evidenced",
                "verdict_basis": "user_declaration",
                "evidence": [],
                "expert_review_status": "pending",
                "notes": "",
            }

    is_tcvn = standard == "tcvn11930"
    columns = _COLUMNS_TCVN if is_tcvn else _COLUMNS_ISO

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Statement of Applicability"

    # ── Title rows ───────────────────────────────────────────────────
    ws.merge_cells(f"A1:{get_column_letter(len(columns))}1")
    title_cell = ws["A1"]
    if is_tcvn:
        title_cell.value = f"BẢN TUYÊN BỐ ÁP DỤNG (SoA) — TCVN 11930:2017 (5 CẤP ĐỘ ATTT) — {org_name.upper() or 'DOANH NGHIỆP'}"
    else:
        title_cell.value = f"STATEMENT OF APPLICABILITY (SoA) — ISO/IEC 27001:2022 ANNEX A — {org_name.upper() or 'ORGANIZATION'}"
    title_cell.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill(start_color="0A2540", end_color="0A2540", fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34

    ws.merge_cells(f"A2:{get_column_letter(len(columns))}2")
    meta_cell = ws["A2"]
    aid_str = assessment_id or (assessment.get("assessment_id") if assessment else "N/A")
    org_label = "Tổ chức" if is_tcvn else "Organization"
    meta_text = (
        f"{org_label}: {org_name or '—'}   |   Assessment ID: {aid_str}   |   Run ID: {run_id}   |   Code Version: {code_version}   |   "
        f"Standard: {'TCVN 11930:2017' if is_tcvn else 'ISO/IEC 27001:2022'}   |   Exported: {created_time[:19]}"
    )
    meta_cell.value = meta_text
    meta_cell.font = Font(name="Calibri", size=10, italic=True, color="334155")
    meta_cell.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    meta_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    # ── Header row ───────────────────────────────────────────────────
    header_row = 4
    for col_idx, (name, width) in enumerate(columns, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=name)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _THIN_BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[header_row].height = 28

    # ── Data rows ────────────────────────────────────────────────────
    controls = _flatten_controls(standard)
    current_row = header_row + 1
    last_category = ""

    satisfied_count = 0
    self_decl_count = 0

    for ctrl in controls:
        if ctrl["category"] != last_category:
            last_category = ctrl["category"]
            ws.merge_cells(
                start_row=current_row, start_column=1,
                end_row=current_row, end_column=len(columns),
            )
            cat_cell = ws.cell(row=current_row, column=1, value=f"Phân nhóm: {last_category}" if is_tcvn else f"Category: {last_category}")
            cat_cell.fill = _CATEGORY_FILL
            cat_cell.font = _CATEGORY_FONT
            cat_cell.border = _THIN_BORDER
            ws.row_dimensions[current_row].height = 24
            current_row += 1

        cid = ctrl["id"]
        score_data = control_scores.get(cid, {})
        u_decl = score_data.get("user_declaration", "not_implemented")
        verdict = score_data.get("assessment_verdict", "missing")
        v_basis = score_data.get("verdict_basis", "rule_based")
        ev_list = score_data.get("evidence", [])
        exp_rev = score_data.get("expert_review_status", "pending")
        notes = score_data.get("notes", "")

        if verdict == "satisfied":
            satisfied_count += 1
        if u_decl == "implemented":
            self_decl_count += 1

        weight = ctrl["weight"]
        if is_tcvn:
            w_lbl = "Chủ chốt" if weight == "critical" else "Cao" if weight == "high" else "Trung bình" if weight == "medium" else "Thấp"
            decl_lbl = "Đã triển khai" if u_decl == "implemented" else "Chưa triển khai"
            v_lbl = "Đạt (Có minh chứng)" if verdict == "satisfied" else "Tự khai báo (Chưa đủ minh chứng)" if verdict == "not_evidenced" else "Khoảng trống (Missing)"
            app_lbl = "Có"
            rev_lbl = "Chờ duyệt" if exp_rev == "pending" else "Đã duyệt"
        else:
            w_lbl = weight.capitalize()
            decl_lbl = "Implemented" if u_decl == "implemented" else "Not Implemented"
            v_lbl = "Satisfied" if verdict == "satisfied" else "Not Evidenced" if verdict == "not_evidenced" else "Missing"
            app_lbl = "Yes"
            rev_lbl = exp_rev.capitalize()

        score_num = score_data.get("score")
        if score_num is None:
            score_num = 4 if verdict == "satisfied" else 3 if u_decl == "implemented" else 0

        just_lbl = "Bắt buộc theo TCVN" if is_tcvn else "Required per Annex A"

        row_vals = [
            (cid, _CENTER, Font(name="Calibri", size=10, bold=True), None),
            (ctrl["label"], _WRAP, _BODY_FONT, None),
            (ctrl["category"], _WRAP, _BODY_FONT, None),
            (w_lbl, _CENTER, _BODY_FONT, None),
            (app_lbl, _CENTER, _BODY_FONT, None),
            (just_lbl, _WRAP, _BODY_FONT, None),
            (decl_lbl, _CENTER, _BODY_FONT, None),
            (score_num, _CENTER, _BODY_FONT, None),
            (", ".join(ev_list) if ev_list else ("Không có" if is_tcvn else "None"), _WRAP, _BODY_FONT, None),
            (notes, _WRAP, _BODY_FONT, None),
            (v_lbl, _CENTER, _VERDICT_FONTS.get(verdict, _BODY_FONT), _VERDICT_FILLS.get(verdict)),
            (rev_lbl, _CENTER, _BODY_FONT, None),
        ]

        for col_idx, (val, align, font_style, fill_style) in enumerate(row_vals, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font_style
            cell.alignment = align
            cell.border = _THIN_BORDER
            if fill_style:
                cell.fill = fill_style

        ws.row_dimensions[current_row].height = 22
        current_row += 1

    # ── Summary row ──────────────────────────────────────────────────
    current_row += 1
    ws.merge_cells(
        start_row=current_row, start_column=1,
        end_row=current_row, end_column=3,
    )
    sum_title = "Tổng kết SoA" if is_tcvn else "SoA Summary"
    summary_cell = ws.cell(row=current_row, column=1, value=sum_title)
    summary_cell.font = Font(name="Calibri", size=11, bold=True)
    summary_cell.alignment = Alignment(horizontal="center", vertical="center")

    total = len(controls)
    t_label = f"Tổng số: {total}" if is_tcvn else f"Total Controls: {total}"
    decl_label = f"Khai báo đạt: {self_decl_count}/{total}" if is_tcvn else f"Self-declared: {self_decl_count}/{total}"
    ev_label = f"Có minh chứng: {satisfied_count}/{total}" if is_tcvn else f"Evidenced: {satisfied_count}/{total}"
    cov_pct = round((self_decl_count / total * 100), 1) if total > 0 else 0

    ws.cell(row=current_row, column=4, value=t_label).font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=current_row, column=6, value=decl_label).font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=current_row, column=7, value=ev_label).font = Font(name="Calibri", size=10, bold=True)
    ws.cell(row=current_row, column=8, value=f"{cov_pct}% (Raw Coverage)").font = Font(name="Calibri", size=10, bold=True)

    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(columns))}{current_row - 2}"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
