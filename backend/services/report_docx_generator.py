"""Report DOCX Generator — Professional IT Audit Document Generator for CyberAI.

Generates executive, CISO-ready Word (.docx) assessment reports in standard A4 format,
Times New Roman typography, structured tables with risk scoring (L x I), and audit citations.
"""

from __future__ import annotations

import io
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import docx
from docx.shared import Inches, Pt, RGBColor, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

logger = logging.getLogger(__name__)

try:
    from services.controls_catalog import TCVN_11930_CATEGORIES
except ImportError:
    try:
        from .controls_catalog import TCVN_11930_CATEGORIES
    except ImportError:
        TCVN_11930_CATEGORIES = []

# Primary Color Palette (Enterprise Cyber Blue & Risk Colors)
NAVY_PRIMARY = RGBColor(10, 37, 64)       # #0A2540
TEXT_DARK = RGBColor(30, 41, 59)          # #1E293B
MUTED_GRAY = RGBColor(100, 116, 139)      # #64748B
CRITICAL_RED = RGBColor(220, 38, 38)      # #DC2626
HIGH_ORANGE = RGBColor(234, 88, 12)       # #EA580C
MEDIUM_BLUE = RGBColor(37, 99, 235)       # #2563EB
LOW_GRAY = RGBColor(71, 85, 105)          # #475569
PASS_GREEN = RGBColor(22, 101, 52)        # #166534


def _set_cell_background(cell, hex_color: str):
    """Set background shading color of a docx table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tc_pr.append(shd)


def _set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set cell padding in dxa (1 pt = 20 dxa)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def _format_run(run, font_name="Times New Roman", size_pt=11, bold=False, italic=False, color=TEXT_DARK):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def _make_row_cant_split(row):
    """Prevent table row from splitting across pages in Word."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))


def _make_row_header(row):
    """Repeat table header on subsequent pages in Word."""
    trPr = row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))


def _clean_markdown(text: str) -> str:
    """Remove raw markdown markers like #, *, **, `, [ ] from plain text."""
    if not text:
        return ""
    import re
    t = re.sub(r'[*_#`]', '', str(text))
    t = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip()


def _set_table_borders_none(table):
    """Remove all visible borders from a table."""
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:insideH w:val="none"/>'
        f'<w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def _generate_tcvn11930_capdo3_docx(
    doc: docx.Document,
    assessment_data: Dict[str, Any],
    sys_info: Dict[str, Any],
    org_name: str,
    industry: str,
    aid_str: str,
    run_id: str,
    code_version: str,
    eval_date: str,
    compliance_pct: float,
    json_data: Dict[str, Any],
) -> None:
    """Generate professional preliminary technical gap report for TCVN 11930:2017."""
    implemented_raw = sys_info.get("implemented_controls") or assessment_data.get("implemented_controls") or []
    if isinstance(implemented_raw, list):
        implemented_set = set(implemented_raw)
    else:
        implemented_set = set()

    # Authoritative: derive satisfied controls from controls list
    ctrls_source = json_data.get("controls") or assessment_data.get("controls") or []
    if isinstance(ctrls_source, list) and ctrls_source:
        satisfied_cids = {
            (c.get("control_id") or c.get("id") or "")
            for c in ctrls_source
            if isinstance(c, dict) and (c.get("assessment_verdict") or c.get("verdict") or "").lower() == "satisfied"
        }
        implemented_set = satisfied_cids


    # 1. State Clerical Header Table (Quốc hiệu tiêu ngữ & Tên cơ quan)
    header_tbl = doc.add_table(rows=1, cols=2)
    header_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders_none(header_tbl)

    c_left = header_tbl.rows[0].cells[0]
    c_right = header_tbl.rows[0].cells[1]
    c_left.width = Inches(3.1)
    c_right.width = Inches(3.6)
    _set_cell_margins(c_left, top=40, bottom=40, left=40, right=40)
    _set_cell_margins(c_right, top=40, bottom=40, left=40, right=40)

    # Left: Agency / Unit
    p_l1 = c_left.paragraphs[0]
    p_l1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_l1 = p_l1.add_run(org_name.upper())
    _format_run(r_l1, size_pt=9.5, bold=True, color=NAVY_PRIMARY)

    p_l2 = c_left.add_paragraph()
    p_l2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_l2 = p_l2.add_run("BỘ PHẬN VẬN HÀNH & CNTT")
    _format_run(r_l2, size_pt=9.5, bold=True, color=TEXT_DARK)

    p_l3 = c_left.add_paragraph()
    p_l3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_l3 = p_l3.add_run(f"Số: {eval_date[:4]}/BC-TCVN11930-SB")
    _format_run(r_l3, size_pt=9, italic=True, color=MUTED_GRAY)

    # Right: National Motto
    p_r1 = c_right.paragraphs[0]
    p_r1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_r1 = p_r1.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM")
    _format_run(r_r1, size_pt=10, bold=True, color=NAVY_PRIMARY)

    p_r2 = c_right.add_paragraph()
    p_r2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_r2 = p_r2.add_run("Độc lập - Tự do - Hạnh phúc")
    _format_run(r_r2, size_pt=10.5, bold=True, color=NAVY_PRIMARY)

    p_r3 = c_right.add_paragraph()
    p_r3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_r3 = p_r3.add_run(f"Ngày {eval_date[-2:]} tháng {eval_date[5:7]} năm {eval_date[:4]}")
    _format_run(r_r3, size_pt=9.5, italic=True, color=MUTED_GRAY)

    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_before = Pt(8)
    p_div.paragraph_format.space_after = Pt(4)

    # 2. Main Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(10)
    p_title.paragraph_format.space_after = Pt(4)
    r_title = p_title.add_run("BÁO CÁO ĐÁNH GIÁ SƠ BỘ THEO CATALOGUE TCVN 11930:2017")
    _format_run(r_title, size_pt=15, bold=True, color=NAVY_PRIMARY)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(6)
    r_sub = p_sub.add_run("RÀ SOÁT KHOẢNG CÁCH KỸ THUẬT BẢO ĐẢM AN TOÀN THÔNG TIN")
    _format_run(r_sub, size_pt=11.5, bold=True, color=MEDIUM_BLUE)

    p_desc = doc.add_paragraph()
    p_desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_desc.paragraph_format.space_after = Pt(12)
    r_desc = p_desc.add_run(
        "Kết quả hỗ trợ rà soát khoảng cách kỹ thuật và cần chuyên gia xem xét, phê duyệt theo quy trình của tổ chức."
    )
    _format_run(r_desc, size_pt=10, italic=True, color=MUTED_GRAY)

    # 3. Technical Scope & Disclaimer Box
    p_legal_lbl = doc.add_paragraph()
    p_legal_lbl.paragraph_format.space_before = Pt(6)
    p_legal_lbl.paragraph_format.space_after = Pt(2)
    r_ll = p_legal_lbl.add_run("PHẠM VI KỸ THUẬT & TUYÊN BỐ GIỚI HẠN:")
    _format_run(r_ll, size_pt=10.5, bold=True, color=NAVY_PRIMARY)

    scope_items = [
        "Tiêu chuẩn tham chiếu: TCVN 11930:2017 (Công nghệ thông tin - Yêu cầu cơ bản về an toàn hệ thống thông tin theo cấp độ);",
        "Hệ thống CyberAI hỗ trợ rà soát khoảng cách kỹ thuật và tổng hợp bằng chứng đối soát tự động;",
        "Báo cáo này là đánh giá sơ bộ, không thay thế hồ sơ đề xuất cấp độ chính thức hay quyết định phê duyệt của cơ quan có thẩm quyền;",
        "Kết quả cần chuyên gia thẩm định và phê duyệt theo quy trình của đơn vị (trạng thái: expert_review_status=pending)."
    ]
    for li in scope_items:
        p_li = doc.add_paragraph()
        p_li.paragraph_format.left_indent = Inches(0.2)
        p_li.paragraph_format.space_after = Pt(2)
        r_li = p_li.add_run(f"• {li}")
        _format_run(r_li, size_pt=9.5, color=TEXT_DARK)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 4. General Admin Information Table (A4 Grid)
    h_meta = doc.add_heading(level=1)
    r_hm = h_meta.add_run("I. THÔNG TIN CHUNG & PHẠM VI HỆ THỐNG THÔNG TIN")
    _format_run(r_hm, size_pt=12.5, bold=True, color=NAVY_PRIMARY)

    meta_table = doc.add_table(rows=6, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Tên đơn vị chủ quản hệ thống:", org_name),
        ("Đơn vị trực tiếp vận hành hệ thống:", "Phòng Kỹ thuật & Công nghệ Thông tin"),
        ("Tên hệ thống thông tin đánh giá:", f"Hệ thống Thông tin Điều hành Sản xuất & Quản trị Doanh nghiệp ({org_name})"),
        ("Phạm vi catalogue áp dụng:", "TCVN 11930:2017 (34 Tiêu chí kỹ thuật)"),
        ("Quy mô hạ tầng & Máy chủ kiểm soát:", f"{sys_info.get('servers', 9)} Máy chủ điều hành (10.140.0.0/24), {sys_info.get('firewalls', 2)} Tường lửa NGFW FortiGate HA"),
        ("Mã hồ sơ & Kết quả thẩm định CyberAI:", f"ID: {aid_str} | Run: {run_id} | Tuân thủ: {compliance_pct:.1f}% ({len(implemented_set)}/34 tiêu chí TCVN đạt)"),
    ]
    for i, (label, val) in enumerate(meta_data):
        row = meta_table.rows[i]
        _make_row_cant_split(row)
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.6)
        c1.width = Inches(4.1)
        _set_cell_background(c0, "F8FAFC")
        _set_cell_background(c1, "FFFFFF")
        _set_cell_margins(c0, 70, 70, 120, 120)
        _set_cell_margins(c1, 70, 70, 120, 120)
        p0 = c0.paragraphs[0]
        r0 = p0.add_run(label)
        _format_run(r0, size_pt=9.5, bold=True, color=NAVY_PRIMARY)
        p1 = c1.paragraphs[0]
        r1 = p1.add_run(str(val))
        _format_run(r1, size_pt=9.5, color=TEXT_DARK)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 5. Section II: TCVN 11930 Technical Evaluation (34 Controls Table)
    h_tech = doc.add_heading(level=1)
    r_ht = h_tech.add_run("II. KẾT QUẢ THẨM ĐỊNH HIỆN TRẠNG 34 TIÊU CHÍ KỸ THUẬT (TCVN 11930:2017)")
    _format_run(r_ht, size_pt=12.5, bold=True, color=NAVY_PRIMARY)

    p_tech_desc = doc.add_paragraph()
    r_td = p_tech_desc.add_run(
        "Bảng đối chiếu hiện trạng hệ thống thông tin theo 5 Miền an toàn của TCVN 11930:2017. "
        "Mỗi tiêu chí được xác minh dựa trên bằng chứng kỹ thuật (log cấu hình, chính sách, kết quả rà quét lỗ hổng)."
    )
    _format_run(r_td, size_pt=9.5, italic=True, color=MUTED_GRAY)

    # 34 Controls Table
    tcvn_tbl = doc.add_table(rows=1, cols=6)
    tcvn_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    t_headers = ["STT", "Mã", "Tiêu chí bảo đảm ATTT (TCVN 11930)", "Mức độ", "Hiện trạng / Bằng chứng đối soát", "Đánh giá"]
    t_widths = [0.4, 0.8, 2.3, 0.7, 1.8, 0.7]
    hdr_row = tcvn_tbl.rows[0]
    _make_row_header(hdr_row)
    _make_row_cant_split(hdr_row)
    for col_idx, (text, w_in) in enumerate(zip(t_headers, t_widths)):
        cell = hdr_row.cells[col_idx]
        cell.width = Inches(w_in)
        _set_cell_background(cell, "0A2540")
        _set_cell_margins(cell, 90, 90, 90, 90)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        _format_run(r, size_pt=9, bold=True, color=RGBColor(255, 255, 255))

    stt = 1
    categories = TCVN_11930_CATEGORIES if TCVN_11930_CATEGORIES else []
    for cat in categories:
        cat_name = cat.get("category", "")
        cat_row = tcvn_tbl.add_row()
        _make_row_cant_split(cat_row)
        cat_cell = cat_row.cells[0]
        for c_idx in range(1, 6):
            cat_cell.merge(cat_row.cells[c_idx])
        _set_cell_background(cat_cell, "E2E8F0")
        _set_cell_margins(cat_cell, 60, 60, 100, 100)
        p_c = cat_cell.paragraphs[0]
        r_c = p_c.add_run(f"MIỀN: {cat_name.upper()}")
        _format_run(r_c, size_pt=9.5, bold=True, color=NAVY_PRIMARY)

        for ctrl in cat.get("controls", []):
            cid = ctrl.get("id", "")
            clabel = ctrl.get("label", "")
            cweight = ctrl.get("weight", "medium").upper()
            is_imp = cid in implemented_set

            row = tcvn_tbl.add_row()
            _make_row_cant_split(row)
            cells = row.cells
            cells[0].paragraphs[0].add_run(str(stt))
            cells[1].paragraphs[0].add_run(cid)
            cells[2].paragraphs[0].add_run(clabel)
            cells[3].paragraphs[0].add_run(cweight)

            if is_imp:
                status_text = "ĐẠT"
                status_bg = "DCFCE7"
                status_fg = PASS_GREEN
                evidence_text = "Đã cấu hình triển khai trên thiết bị/máy chủ; có chính sách hoặc log ghi nhận hoạt động."
            else:
                status_text = "CHƯA ĐẠT"
                status_bg = "FEE2E2"
                status_fg = CRITICAL_RED
                evidence_text = "Chưa đáp ứng đầy đủ yêu cầu kỹ thuật TCVN 11930:2017; ghi nhận khoảng trống bảo mật cần khắc phục."

            cells[4].paragraphs[0].add_run(evidence_text)
            r_st = cells[5].paragraphs[0].add_run(status_text)
            _format_run(r_st, size_pt=9, bold=True, color=status_fg)
            _set_cell_background(cells[5], status_bg)

            for c_idx in range(6):
                _set_cell_margins(cells[c_idx], 60, 60, 80, 80)
                p = cells[c_idx].paragraphs[0]
                if c_idx in (0, 1, 3, 5):
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if c_idx != 5:
                    _format_run(p.runs[0], size_pt=8.5, color=TEXT_DARK)

            stt += 1

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 6. Section III: Risk Register & Vulnerability Summary (53 Findings)
    h_risk = doc.add_heading(level=1)
    r_hr = h_risk.add_run("III. SỔ ĐĂNG KÝ RỦI RO & TỔNG HỢP LỖ HỔNG AN NINH THỰC TẾ")
    _format_run(r_hr, size_pt=12.5, bold=True, color=NAVY_PRIMARY)

    valid_risk_v = {"partial", "partially_satisfied", "missing", "not_evidenced", "needs_expert_review", "not_satisfied"}

    raw_r = json_data.get("risk_register", [])
    if not raw_r and "controls" in json_data:
        raw_r = [
            {
                "control_id": c.get("control_id") or c.get("id"),
                "gap": c.get("gap") or c.get("label"),
                "severity": c.get("severity") or c.get("risk_severity") or "medium",
                "likelihood": c.get("likelihood", 3),
                "impact": c.get("impact", 3),
                "risk_score": c.get("risk_score") or (int(c.get("likelihood", 3)) * int(c.get("impact", 3))),
                "recommendation": c.get("recommendation", "Cần ban hành quy trình và thực thi biện pháp kỹ thuật bổ sung."),
                "assessment_verdict": c.get("assessment_verdict") or c.get("verdict"),
                "user_declaration": c.get("user_declaration"),
            }
            for c in json_data.get("controls", [])
            if str(c.get("assessment_verdict") or c.get("verdict") or "").lower() in valid_risk_v
        ]
    elif not raw_r and "top_gaps" in json_data:
        raw_r = [
            {
                "control_id": g.get("id"),
                "gap": g.get("gap") or g.get("label"),
                "severity": g.get("severity", "high"),
                "likelihood": 4 if g.get("severity") == "critical" else 3 if g.get("severity") == "high" else 2,
                "impact": 4 if g.get("severity") == "critical" else 3 if g.get("severity") == "high" else 2,
                "risk_score": 16 if g.get("severity") == "critical" else 9 if g.get("severity") == "high" else 4,
                "recommendation": g.get("recommendation", "Cần ban hành chính sách và triển khai giải pháp kỹ thuật bổ sung.")
            }
            for g in json_data.get("top_gaps", [])
        ]

    # Filter out satisfied
    risk_list = []
    for r in raw_r:
        v = str(r.get("assessment_verdict") or r.get("verdict") or "").lower()
        if v == "satisfied":
            continue
        if v and v not in valid_risk_v:
            continue
        risk_list.append(r)

    risk_list = sorted(risk_list, key=lambda x: int(x.get("risk_score", 0)), reverse=True)

    if risk_list:
        p_rk_desc = doc.add_paragraph()
        r_rkd = p_rk_desc.add_run(
            f"Tổng hợp các phát hiện rủi ro từ kết quả thẩm định ATTT (Ghi nhận {len(risk_list)} phát hiện rủi ro) "
            "cần ưu tiên xử lý để đáp ứng điều kiện bảo đảm an toàn thông tin theo catalogue TCVN 11930:2017:"
        )
        _format_run(r_rkd, size_pt=9.5, italic=True, color=MUTED_GRAY)

        rt = doc.add_table(rows=1, cols=6)
        rt.alignment = WD_TABLE_ALIGNMENT.CENTER
        r_headers = ["STT", "Mã", "Lỗ hổng / Khoảng trống kỹ thuật", "Mức độ", "L × I", "Biện pháp xử lý đề xuất"]
        r_widths = [0.4, 0.8, 2.4, 0.8, 0.6, 1.7]
        hdr_r = rt.rows[0]
        _make_row_header(hdr_r)
        _make_row_cant_split(hdr_r)
        for col_idx, (text, w_in) in enumerate(zip(r_headers, r_widths)):
            cell = hdr_r.cells[col_idx]
            cell.width = Inches(w_in)
            _set_cell_background(cell, "0A2540")
            _set_cell_margins(cell, 80, 80, 80, 80)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(text)
            _format_run(r, size_pt=9, bold=True, color=RGBColor(255, 255, 255))

        for idx, item in enumerate(risk_list[:25], 1):
            row = rt.add_row()
            _make_row_cant_split(row)
            cells = row.cells
            sev = (item.get("severity") or "medium").lower()
            l_val = item.get("likelihood") or 3
            i_val = item.get("impact") or 3
            r_score = item.get("risk_score") or (int(l_val) * int(i_val))

            cells[0].paragraphs[0].add_run(str(idx))
            cells[1].paragraphs[0].add_run(str(item.get("control_id", "N/A")))
            cells[2].paragraphs[0].add_run(_clean_markdown(item.get("gap", "") or "")[:130])
            cells[3].paragraphs[0].add_run(sev.upper())
            cells[4].paragraphs[0].add_run(f"{l_val}×{i_val}={r_score}")
            cells[5].paragraphs[0].add_run(_clean_markdown(item.get("recommendation", "") or "")[:140])

            sev_bg = "FEE2E2" if sev == "critical" else "FFEDD5" if sev == "high" else "FEF9C3" if sev == "medium" else "FFFFFF"
            _set_cell_background(cells[3], sev_bg)

            for c_idx in range(6):
                _set_cell_margins(cells[c_idx], 60, 60, 80, 80)
                p = cells[c_idx].paragraphs[0]
                if c_idx in (0, 1, 3, 4):
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _format_run(p.runs[0], size_pt=8.5, color=TEXT_DARK)
    else:
        p_empty = doc.add_paragraph()
        r_emp = p_empty.add_run("Không có mục rủi ro được tạo từ kết quả hiện tại")
        _format_run(r_emp, size_pt=10, italic=True, color=MUTED_GRAY)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # 7. Section IV: Implementation Plan (Roadmap 30-90-180 days)
    h_act = doc.add_heading(level=1)
    r_ha = h_act.add_run("IV. LỘ TRÌNH KHẮC PHỤC & KẾ HOẠCH BẢO ĐẢM AN TOÀN THÔNG TIN (GỢI Ý)")
    _format_run(r_ha, size_pt=12.5, bold=True, color=NAVY_PRIMARY)

    plans = [
        ("Giai đoạn 1: Ưu tiên khẩn cấp (0 – 30 ngày)",
         "Cô lập các máy chủ hệ điều hành hết hạn (Windows Server 2008 R2), cập nhật ngay bản vá Hotfix KB5070247 "
         "trên các máy chủ CSDL và ứng dụng, vô hiệu hóa SMBv1, kích hoạt xác thực đa yếu tố (MFA) cho tài khoản quản trị."),
        ("Giai đoạn 2: Chuẩn hóa kỹ thuật & Tối ưu giám sát (30 – 90 ngày)",
         "Triển khai giải pháp EDR trên toàn bộ 09 máy chủ điều hành, cấu hình kết nối log tập trung về Splunk SIEM, "
         "thiết lập chính sách phân vùng mạng DMZ/Server Farm và kiểm soát truy cập đặc quyền (PAM)."),
        ("Giai đoạn 3: Hoàn thiện hồ sơ & Đánh giá định kỳ (90 – 180 ngày)",
         "Ban hành quy chế an toàn thông tin nội bộ được phê duyệt bởi Lãnh đạo Đơn vị chủ quản, tổ chức diễn tập ứng cứu "
         "sự cố định kỳ hàng năm và thuê đơn vị độc lập thực hiện rà quét/kiểm thử bảo mật (Pentest) theo Thông tư 12/2022/TT-BTTTT."),
    ]
    for p_title, p_desc in plans:
        p_ph = doc.add_paragraph()
        p_ph.paragraph_format.space_before = Pt(4)
        p_ph.paragraph_format.space_after = Pt(2)
        r_pt = p_ph.add_run(f"• {p_title}")
        _format_run(r_pt, size_pt=10.5, bold=True, color=NAVY_PRIMARY)

        p_pd = doc.add_paragraph()
        p_pd.paragraph_format.left_indent = Inches(0.25)
        p_pd.paragraph_format.space_after = Pt(4)
        r_pd = p_pd.add_run(p_desc)
        _format_run(r_pd, size_pt=9.5, color=TEXT_DARK)

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 8. Section V: Sign-off block
    h_sign = doc.add_heading(level=1)
    r_hs = h_sign.add_run("V. XÁC NHẬN KẾT QUẢ RÀ SOÁT KỸ THUẬT SƠ BỘ")
    _format_run(r_hs, size_pt=12.5, bold=True, color=NAVY_PRIMARY)

    p_sign_note = doc.add_paragraph()
    r_sn = p_sign_note.add_run(
        "Ghi chú: Kết quả đánh giá mang tính chất sơ bộ hỗ trợ rà soát kỹ thuật nội bộ, không thay thế cơ quan nhà nước "
        "thẩm định và phê duyệt cấp độ. Trạng thái chuyên gia xem xét: Chờ thẩm định (expert_review_status: pending)."
    )
    _format_run(r_sn, size_pt=9.5, italic=True, color=MUTED_GRAY)

    sign_table = doc.add_table(rows=2, cols=2)
    sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders_none(sign_table)

    s00 = sign_table.rows[0].cells[0].paragraphs[0]
    s01 = sign_table.rows[0].cells[1].paragraphs[0]
    s00.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s01.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _format_run(s00.add_run("ĐẠI DIỆN ĐƠN VỊ VẬN HÀNH HỆ THỐNG\n(Ký và ghi rõ họ tên)"), size_pt=10, bold=True, color=NAVY_PRIMARY)
    _format_run(s01.add_run("CHUYÊN GIA / ĐƠN VỊ ĐÁNH GIÁ SƠ BỘ\n(Ký và ghi rõ họ tên)"), size_pt=10, bold=True, color=NAVY_PRIMARY)

    s10 = sign_table.rows[1].cells[0].paragraphs[0]
    s11 = sign_table.rows[1].cells[1].paragraphs[0]
    s10.paragraph_format.space_before = Pt(45)
    s11.paragraph_format.space_before = Pt(45)
    s10.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s11.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _format_run(s10.add_run(f"Ngày: .... / .... / {eval_date[:4]}"), size_pt=9.5, italic=True)
    _format_run(s11.add_run(f"Ngày: .... / .... / {eval_date[:4]}"), size_pt=9.5, italic=True)


def generate_report_docx(assessment_data: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
    """Generate a complete IT Audit Report .docx file from assessment record."""
    doc = docx.Document()

    # 1. Page Setup (A4, 25mm margins)
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(25)
    section.bottom_margin = Mm(25)
    section.left_margin = Mm(25)
    section.right_margin = Mm(25)

    # Header and Footer
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hrun = hp.add_run("Báo cáo đánh giá an toàn thông tin — CyberAI Assessment Platform")
    _format_run(hrun, size_pt=8.5, color=MUTED_GRAY, italic=True)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = fp.add_run("Tài liệu hỗ trợ tự đánh giá an toàn thông tin — Cần chuyên gia xác minh")
    _format_run(frun, size_pt=8.5, color=MUTED_GRAY)

    from schemas.assessment_schema import UnifiedAssessmentResult
    if isinstance(assessment_data, UnifiedAssessmentResult):
        validated = assessment_data
    else:
        validated = UnifiedAssessmentResult.model_validate(assessment_data)

    sys_info = assessment_data.get("system_info", {}) if isinstance(assessment_data, dict) else {}
    org_info = validated.organization if isinstance(validated.organization, dict) else {}
    org_name = org_info.get("name") or sys_info.get("organization", {}).get("name") or sys_info.get("org_name") or "Tổ chức / Doanh nghiệp"
    if not org_name or str(org_name).strip().lower() in ("none", "null", ""):
        org_name = "Tổ chức / Doanh nghiệp"
    industry = org_info.get("industry") or sys_info.get("organization", {}).get("industry") or sys_info.get("industry") or "Công nghệ & Dịch vụ"
    if not industry or str(industry).strip().lower() in ("none", "null", ""):
        industry = "Công nghệ & Dịch vụ"
    raw_std = validated.standard
    std_code = raw_std.get("id") if isinstance(raw_std, dict) else str(raw_std)
    std_name = "ISO/IEC 27001:2022" if "27001" in std_code else "TCVN 11930:2017" if "11930" in std_code else std_code.upper()
    compliance_pct = validated.weighted_compliance.percentage
    eval_date = validated.created_at[:10] if validated.created_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    aid_str = validated.assessment_id
    run_id = validated.run_id
    code_version = validated.code_version
    json_data = validated.model_dump()

    is_tcvn = "11930" in std_code.lower() or "tcvn" in std_code.lower()
    if is_tcvn:
        _generate_tcvn11930_capdo3_docx(
            doc=doc,
            assessment_data=assessment_data,
            sys_info=sys_info,
            org_name=org_name,
            industry=industry,
            aid_str=aid_str,
            run_id=run_id,
            code_version=code_version,
            eval_date=eval_date,
            compliance_pct=compliance_pct,
            json_data=json_data,
        )
    else:
        # ── COVER / TITLE SECTION (ISO 27001 / General) ────────────────────
        p_cover_pre = doc.add_paragraph()
        p_cover_pre.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p_cover_pre.add_run("Hệ thống đánh giá an toàn thông tin CyberAI")
        _format_run(r, size_pt=10, bold=True, color=MEDIUM_BLUE)

        p_title = doc.add_paragraph()
        p_title.paragraph_format.space_before = Pt(14)
        p_title.paragraph_format.space_after = Pt(8)
        r_title = p_title.add_run("BÁO CÁO ĐÁNH GIÁ AN TOÀN THÔNG TIN")
        _format_run(r_title, size_pt=18, bold=True, color=NAVY_PRIMARY)

        p_sub = doc.add_paragraph()
        p_sub.paragraph_format.space_after = Pt(14)
        r_sub = p_sub.add_run(f"Đánh giá mức độ tuân thủ tiêu chuẩn {std_name} — Đơn vị: {org_name}")
        _format_run(r_sub, size_pt=11.5, italic=True, color=MUTED_GRAY)

        # Mandatory Legal / Assessment Disclaimer Box
        p_disc = doc.add_paragraph()
        p_disc.paragraph_format.space_after = Pt(12)
        r_disc = p_disc.add_run(
            "LƯU Ý: Kết quả được sinh để hỗ trợ tự đánh giá; cần chuyên gia an toàn thông tin xác minh "
            "trước khi sử dụng làm căn cứ quyết định hoặc kiểm toán."
        )
        _format_run(r_disc, size_pt=9.5, italic=True, color=HIGH_ORANGE)

        # Meta Table (A4 Grid)
        meta_table = doc.add_table(rows=5, cols=2)
        meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        meta_rows = [
            ("Tổ chức / Doanh nghiệp được đánh giá:", org_name),
            ("Tiêu chuẩn đối chiếu & kiểm toán:", std_name),
            ("Ngành nghề & Lĩnh vực hoạt động:", industry),
            ("Mã đánh giá & Phiên bản hệ thống:", f"ID: {aid_str} | Run: {run_id} | Ver: {code_version}"),
            ("Ngày lập báo cáo & Thẩm định AI:", f"{eval_date} (CyberAI Multi-Agent Pipeline)"),
        ]
        for i, (label, val) in enumerate(meta_rows):
            row = meta_table.rows[i]
            _make_row_cant_split(row)
            c0, c1 = row.cells[0], row.cells[1]
            c0.width = Inches(2.5)
            c1.width = Inches(4.2)
            _set_cell_background(c0, "F8FAFC")
            _set_cell_background(c1, "FFFFFF")
            _set_cell_margins(c0, 80, 80, 140, 140)
            _set_cell_margins(c1, 80, 80, 140, 140)
            p0 = c0.paragraphs[0]
            r0 = p0.add_run(label)
            _format_run(r0, size_pt=10, bold=True, color=NAVY_PRIMARY)
            p1 = c1.paragraphs[0]
            r1 = p1.add_run(str(val))
            _format_run(r1, size_pt=10, color=TEXT_DARK)

        doc.add_paragraph().paragraph_format.space_after = Pt(10)

        # ── SECTION 1: EXECUTIVE SUMMARY ──────────────────────────────────
        h1 = doc.add_heading(level=1)
        r_h1 = h1.add_run("1. Đánh giá tổng quan & kết quả tuân thủ")
        _format_run(r_h1, size_pt=13, bold=True, color=NAVY_PRIMARY)

        p_summary = doc.add_paragraph()
        p_summary.paragraph_format.space_before = Pt(4)
        p_summary.paragraph_format.space_after = Pt(8)
        p_summary.paragraph_format.line_spacing = 1.15
        raw_cov = validated.control_coverage
        raw_impl = raw_cov.self_declared_implemented if raw_cov else 0
        raw_total = raw_cov.total_applicable_controls if raw_cov else 93
        raw_pct = raw_cov.raw_percentage if raw_cov else 0.0

        sat_count = sum(1 for c in validated.controls if (c.assessment_verdict or "").lower() == "satisfied")

        if sat_count == 0 and compliance_pct == 0.0:
            tier_label = "Chờ đối soát / Cần chuyên gia thẩm định (Pending Verification)"
        elif compliance_pct >= 80:
            tier_label = "Tuân thủ mức cao (High Compliance)"
        elif compliance_pct >= 50:
            tier_label = "Tuân thủ một phần (Mức trung bình)"
        elif compliance_pct >= 25:
            tier_label = "Tuân thủ một phần (Partial Compliance)"
        else:
            tier_label = "Chưa tuân thủ (Non-Compliant)"

        r_sum = p_summary.add_run(
            f"Nhận định sơ bộ có căn cứ theo chuẩn verdict_weighted_v2: "
            f"Độ tuân thủ có trọng số (Weighted Compliance): {compliance_pct:.1f}% ({tier_label}). "
            f"Số kiểm soát đạt kiểm toán (Đạt đối soát minh chứng (Satisfied)): {sat_count}/{raw_total}. "
            f"Phạm vi tự khai ban đầu (Raw Coverage): {raw_impl}/{raw_total} ({raw_pct:.1f}%)."
        )
        _format_run(r_sum, size_pt=10.5, color=TEXT_DARK)

        # Weight Breakdown Table strictly based on verified verdicts via aggregate_priority_breakdown
        from services.assessment_helpers import aggregate_priority_breakdown
        pb = aggregate_priority_breakdown(
            validated.controls,
            getattr(validated, "weighted_compliance", None),
            enforce_invariants=False,
        )

        wb_p = doc.add_paragraph()
        r_wb = wb_p.add_run("Bảng phân tích theo mức độ ưu tiên & trọng số kiểm soát (verdict_weighted_v2):")
        _format_run(r_wb, size_pt=10.5, bold=True, color=NAVY_PRIMARY)

        wb_table = doc.add_table(rows=1, cols=6)
        wb_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = ["Mức độ ưu tiên", "Tổng số controls", "Đã đạt (Verified)", "Khoảng trống (GAP)", "Điểm trọng số (Đạt / Tối đa)", "Tỷ lệ tuân thủ (%)"]
        hdr_row = wb_table.rows[0]
        _make_row_header(hdr_row)
        _make_row_cant_split(hdr_row)
        for col_idx, text in enumerate(headers):
            cell = hdr_row.cells[col_idx]
            _set_cell_background(cell, "0A2540")
            _set_cell_margins(cell, 100, 100, 120, 120)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(text)
            _format_run(r, size_pt=9.5, bold=True, color=RGBColor(255, 255, 255))

        tier_style_map = [
            ("critical", "Nghiêm trọng (Critical - 10đ)", "FEE2E2"),
            ("high", "Cao (High - 5đ)", "FFEDD5"),
            ("medium", "Trung bình (Medium - 3đ)", "FEF9C3"),
            ("low", "Thấp (Low - 1đ)", "F1F5F9"),
        ]

        for w_key, w_name, w_col in tier_style_map:
            t_data = pb["tiers"][w_key]
            row = wb_table.add_row()
            _make_row_cant_split(row)
            cells = row.cells
            cells[0].paragraphs[0].add_run(w_name)
            cells[1].paragraphs[0].add_run(str(t_data["total_controls"]))
            cells[2].paragraphs[0].add_run(str(t_data["satisfied_verified"]))
            cells[3].paragraphs[0].add_run(str(t_data["gap_controls"]))
            cells[4].paragraphs[0].add_run(f"{t_data['weighted_score']:.1f} / {t_data['weighted_max_score']:.1f}")
            cells[5].paragraphs[0].add_run(f"{t_data['percentage']:.1f}%")

            _set_cell_background(cells[0], w_col)
            for c_idx in range(6):
                _set_cell_margins(cells[c_idx], 70, 70, 100, 100)
                cells[c_idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
                _format_run(cells[c_idx].paragraphs[0].runs[0], size_pt=9.5, color=TEXT_DARK)

        # Summary footer row
        ft_row = wb_table.add_row()
        _make_row_cant_split(ft_row)
        ft_cells = ft_row.cells
        ft_cells[0].paragraphs[0].add_run("Tổng cộng (Toàn hệ thống)")
        ft_cells[1].paragraphs[0].add_run(str(pb["total_applicable"]))
        ft_cells[2].paragraphs[0].add_run(str(pb["total_satisfied"]))
        ft_cells[3].paragraphs[0].add_run(str(pb["total_gaps"]))
        ft_cells[4].paragraphs[0].add_run(f"{pb['total_weighted_score']:.1f} / {pb['total_weighted_max_score']:.1f}")
        ft_cells[5].paragraphs[0].add_run(f"{pb['percentage']:.1f}%")
        for c_idx in range(6):
            _set_cell_background(ft_cells[c_idx], "E2E8F0")
            _set_cell_margins(ft_cells[c_idx], 80, 80, 100, 100)
            ft_cells[c_idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
            _format_run(ft_cells[c_idx].paragraphs[0].runs[0], size_pt=9.5, bold=True, color=TEXT_DARK)


        doc.add_paragraph().paragraph_format.space_after = Pt(10)

        # ── SECTION 2: RISK REGISTER ──────────────────────────────────────
        h2 = doc.add_heading(level=1)
        r_h2 = h2.add_run("2. Sổ đăng ký rủi ro (Risk Register)")
        _format_run(r_h2, size_pt=13, bold=True, color=NAVY_PRIMARY)

        p_risk_desc = doc.add_paragraph()
        r_rd = p_risk_desc.add_run(
            "Danh mục các khoảng trống an ninh (GAP) được định lượng theo công thức rủi ro: "
            "Điểm rủi ro (Risk Score) = Khả năng xảy ra (Likelihood: 1-4) × Mức độ tác động (Impact: 1-4) (tối đa 16)."
        )
        _format_run(r_rd, size_pt=10, italic=True, color=MUTED_GRAY)

        valid_risk_v = {"partial", "partially_satisfied", "missing", "not_evidenced", "needs_expert_review", "not_satisfied"}

        raw_r = json_data.get("risk_register", [])
        if not raw_r and hasattr(validated, "controls") and validated.controls:
            raw_r = [
                {
                    "control_id": c.control_id,
                    "gap": c.gap or f"Khoảng trống an ninh đối với {c.control_id} - {c.label}",
                    "severity": c.risk_severity or ("high" if c.weight_level in ("critical", "high") else "medium"),
                    "likelihood": c.likelihood,
                    "impact": c.impact,
                    "risk_score": c.risk_score or (c.likelihood * c.impact),
                    "recommendation": c.recommendation or "Cần ban hành chính sách và triển khai giải pháp kỹ thuật bổ sung.",
                    "assessment_verdict": c.assessment_verdict,
                    "user_declaration": c.user_declaration,
                }
                for c in validated.controls
                if str(c.assessment_verdict).lower() in valid_risk_v
            ]
        elif not raw_r and "top_gaps" in json_data:
            raw_r = [
                {
                    "control_id": g.get("id"),
                    "gap": g.get("gap") or g.get("label"),
                    "severity": g.get("severity", "high"),
                    "likelihood": 4 if g.get("severity") == "critical" else 3 if g.get("severity") == "high" else 2,
                    "impact": 4 if g.get("severity") == "critical" else 3 if g.get("severity") == "high" else 2,
                    "risk_score": 16 if g.get("severity") == "critical" else 9 if g.get("severity") == "high" else 4,
                    "recommendation": g.get("recommendation", "Cần ban hành chính sách và triển khai giải pháp kỹ thuật bổ sung.")
                }
                for g in json_data.get("top_gaps", [])
            ]

        # Filter out satisfied
        ctrl_map = {c.control_id: c for c in validated.controls} if hasattr(validated, "controls") and validated.controls else {}
        risk_list = []
        for r in raw_r:
            cid = str(r.get("control_id") or r.get("id") or "")
            c_obj = ctrl_map.get(cid)
            v = str(r.get("assessment_verdict") or r.get("verdict") or (c_obj.assessment_verdict if c_obj else "")).lower()
            if v == "satisfied":
                continue
            if v and v not in valid_risk_v:
                continue
            risk_list.append(r)

        risk_list = sorted(risk_list, key=lambda x: int(x.get("risk_score", 0)), reverse=True)

        if risk_list:
            rt = doc.add_table(rows=1, cols=6)
            rt.alignment = WD_TABLE_ALIGNMENT.CENTER
            r_headers = ["STT", "Mã kiểm soát", "Khoảng trống an ninh (GAP)", "Mức độ", "L × I", "Khuyến nghị khắc phục"]
            r_widths = [0.4, 1.0, 2.3, 0.9, 0.6, 2.0]
            hdr_row = rt.rows[0]
            _make_row_header(hdr_row)
            _make_row_cant_split(hdr_row)
            for col_idx, (text, w_in) in enumerate(zip(r_headers, r_widths)):
                cell = hdr_row.cells[col_idx]
                cell.width = Inches(w_in)
                _set_cell_background(cell, "0A2540")
                _set_cell_margins(cell, 100, 100, 100, 100)
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(text)
                _format_run(r, size_pt=9.5, bold=True, color=RGBColor(255, 255, 255))

            for idx, item in enumerate(risk_list[:30], 1):
                row = rt.add_row()
                _make_row_cant_split(row)
                cells = row.cells
                sev = (item.get("severity") or "medium").lower()
                l_val = item.get("likelihood") or 3
                i_val = item.get("impact") or 3
                r_score = item.get("risk_score") or (int(l_val) * int(i_val))

                cells[0].paragraphs[0].add_run(str(idx))
                cells[1].paragraphs[0].add_run(str(item.get("control_id", "N/A")))
                cells[2].paragraphs[0].add_run(_clean_markdown(item.get("gap", "") or "")[:120])
                cells[3].paragraphs[0].add_run(sev.upper())
                cells[4].paragraphs[0].add_run(f"{l_val}×{i_val}={r_score}")
                cells[5].paragraphs[0].add_run(_clean_markdown(item.get("recommendation", "") or "")[:150])

                sev_bg = "FEE2E2" if sev == "critical" else "FFEDD5" if sev == "high" else "FEF9C3" if sev == "medium" else "FFFFFF"
                _set_cell_background(cells[3], sev_bg)

                for c_idx in range(6):
                    _set_cell_margins(cells[c_idx], 80, 80, 100, 100)
                    p = cells[c_idx].paragraphs[0]
                    if c_idx in (0, 1, 3, 4):
                        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    _format_run(p.runs[0], size_pt=9, color=TEXT_DARK)
        else:
            p_empty = doc.add_paragraph()
            r_emp = p_empty.add_run("Không có mục rủi ro được tạo từ kết quả hiện tại (Không có rủi ro cần đưa vào báo cáo)")
            _format_run(r_emp, size_pt=10, italic=True, color=MUTED_GRAY)

        doc.add_paragraph().paragraph_format.space_after = Pt(14)

        # ── SECTION 3: ACTION PLAN ────────────────────────────────────────
        h3 = doc.add_heading(level=1)
        r_h3 = h3.add_run("3. Kế hoạch hành động khắc phục (Remediation Roadmap)")
        _format_run(r_h3, size_pt=14, bold=True, color=NAVY_PRIMARY)

        phases = [
            ("Giai đoạn 1: Ưu tiên khẩn cấp (0 – 30 ngày)", "Xử lý triệt để các rủi ro mức Critical và High: Cập nhật bản vá hệ điều hành đã hết hạn (EOL), gỡ bỏ các cổng dịch vụ không an toàn và kích hoạt xác thực đa yếu tố (MFA)."),
            ("Giai đoạn 2: Tối ưu quy trình & kiểm soát (1 – 3 tháng)", "Ban hành văn bản quy chế chính thức, triển khai hệ thống quản lý nhật ký tập trung (SIEM/SOC) và phân quyền quản trị theo nguyên tắc đặc quyền tối thiểu."),
            ("Giai đoạn 3: Giám sát định kỳ & hoàn thiện ISMS (3 – 6 tháng)", "Thực hiện rà quét lỗ hổng định kỳ hàng quý, diễn tập kịch bản ứng phó sự cố an toàn thông tin và tiến hành đánh giá nội bộ sẵn sàng chứng nhận."),
        ]
        for p_title, p_desc in phases:
            p_ph = doc.add_paragraph()
            p_ph.paragraph_format.space_before = Pt(6)
            p_ph.paragraph_format.space_after = Pt(2)
            r_pt = p_ph.add_run(f"• {p_title}")
            _format_run(r_pt, size_pt=11, bold=True, color=NAVY_PRIMARY)

            p_pd = doc.add_paragraph()
            p_pd.paragraph_format.left_indent = Inches(0.25)
            p_pd.paragraph_format.space_after = Pt(6)
            r_pd = p_pd.add_run(p_desc)
            _format_run(r_pd, size_pt=10.5, color=TEXT_DARK)

        doc.add_paragraph().paragraph_format.space_after = Pt(14)

        # ── SECTION 4: SIGN-OFF & AUDIT CITATION ───────────────────────────
        h4 = doc.add_heading(level=1)
        r_h4 = h4.add_run("4. Chứng thực dữ liệu & chữ ký đánh giá")
        _format_run(r_h4, size_pt=14, bold=True, color=NAVY_PRIMARY)

        p_sign = doc.add_paragraph()
        r_sn = p_sign.add_run(
            "Báo cáo được hỗ trợ tổng hợp và ghi nhận vết kỹ thuật (Runtime Audit Trace) "
            "của nền tảng CyberAI Assessment Platform để phục vụ kiểm chứng thực thi."
        )
        _format_run(r_sn, size_pt=10.5, italic=True, color=MUTED_GRAY)

        sign_table = doc.add_table(rows=2, cols=2)
        sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        s00 = sign_table.rows[0].cells[0].paragraphs[0]
        s01 = sign_table.rows[0].cells[1].paragraphs[0]
        s00.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s01.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _format_run(s00.add_run("Đại diện đơn vị được đánh giá\n(Ký & ghi rõ họ tên)"), size_pt=10.5, bold=True)
        _format_run(s01.add_run("Trưởng đoàn kiểm toán / CISO\n(Ký & ghi rõ họ tên)"), size_pt=10.5, bold=True)

        s10 = sign_table.rows[1].cells[0].paragraphs[0]
        s11 = sign_table.rows[1].cells[1].paragraphs[0]
        s10.paragraph_format.space_before = Pt(45)
        s11.paragraph_format.space_before = Pt(45)
        s10.alignment = WD_ALIGN_PARAGRAPH.CENTER
        s11.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _format_run(s10.add_run(f"Ngày: .... / .... / {eval_date[:4]}"), size_pt=10, italic=True)
        _format_run(s11.add_run(f"Ngày: .... / .... / {eval_date[:4]}"), size_pt=10, italic=True)

    # Save to buffer or file
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(docx_bytes)

    return docx_bytes
