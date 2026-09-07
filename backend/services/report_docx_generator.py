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

    sys_info = assessment_data.get("system_info", {})
    org_name = sys_info.get("organization", {}).get("name") or sys_info.get("org_name") or "Tổ chức / Doanh nghiệp"
    industry = sys_info.get("organization", {}).get("industry") or sys_info.get("industry") or "Công nghệ & Dịch vụ"
    raw_std = assessment_data.get("standard") or sys_info.get("assessment_standard") or "iso27001"
    std_code = raw_std.get("id") if isinstance(raw_std, dict) else str(raw_std)
    std_name = "ISO/IEC 27001:2022" if "27001" in std_code else "TCVN 11930:2017" if "11930" in std_code else std_code.upper()
    compliance_pct = assessment_data.get("compliance_percent") or assessment_data.get("result", {}).get("json_data", {}).get("compliance", {}).get("percentage", 0.0)
    eval_date = assessment_data.get("created_at", "")[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    json_data = assessment_data.get("json_data") or assessment_data.get("result", {}).get("json_data") or {}

    aid_str = assessment_data.get("assessment_id") or json_data.get("assessment_id") or "N/A"
    run_id = assessment_data.get("run_id") or json_data.get("run_id") or "run_default"
    code_version = assessment_data.get("code_version") or json_data.get("code_version") or "v1.2.0-rel"

    # ── COVER / TITLE SECTION ──────────────────────────────────────────
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
    tier_label = "Tuân thủ một phần" if 25 <= compliance_pct < 80 else "Tuân thủ mức cao" if compliance_pct >= 80 else "Không tuân thủ"
    r_sum = p_summary.add_run(
        f"Qua quá trình thu thập tài liệu quy trình, bằng chứng thực tế từ máy chủ/hạ tầng mạng và đối soát qua pipeline "
        f"Multi-Agent (Agent 1 Fact Extraction & Agent 2 Compliance Auditor), hệ thống xác định mức độ tuân thủ có trọng số của "
        f"{org_name} đạt: {compliance_pct:.1f}% ({tier_label})."
    )
    _format_run(r_sum, size_pt=10.5, color=TEXT_DARK)

    # Weight Breakdown Table
    wb = json_data.get("weight_breakdown", {})
    if wb:
        wb_p = doc.add_paragraph()
        r_wb = wb_p.add_run("Bảng phân bổ mức độ đạt theo trọng số an ninh:")
        _format_run(r_wb, size_pt=10.5, bold=True, color=NAVY_PRIMARY)

        wb_table = doc.add_table(rows=1, cols=4)
        wb_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        headers = ["Mức độ trọng số", "Số controls đạt", "Tổng số controls", "Tỷ lệ tuân thủ (%)"]
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

        for w_key, w_name, w_col in [
            ("critical", "Nghiêm trọng (Critical)", "FEE2E2"),
            ("high", "Cao (High)", "FFEDD5"),
            ("medium", "Trung bình (Medium)", "FEF9C3"),
            ("low", "Thấp (Low)", "F1F5F9"),
        ]:
            data_w = wb.get(w_key, {})
            if not data_w:
                continue
            row = wb_table.add_row()
            _make_row_cant_split(row)
            cells = row.cells
            cells[0].paragraphs[0].add_run(w_name)
            cells[1].paragraphs[0].add_run(str(data_w.get("implemented", 0)))
            cells[2].paragraphs[0].add_run(str(data_w.get("total", 0)))
            cells[3].paragraphs[0].add_run(f"{data_w.get('percent', 0.0):.1f}%")

            _set_cell_background(cells[0], w_col)
            for c_idx in range(4):
                _set_cell_margins(cells[c_idx], 70, 70, 100, 100)
                cells[c_idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
                _format_run(cells[c_idx].paragraphs[0].runs[0], size_pt=9.5, color=TEXT_DARK)

    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # ── SECTION 2: RISK REGISTER ──────────────────────────────────────
    h2 = doc.add_heading(level=1)
    r_h2 = h2.add_run("2. Sổ đăng ký rủi ro (Risk Register)")
    _format_run(r_h2, size_pt=13, bold=True, color=NAVY_PRIMARY)

    p_risk_desc = doc.add_paragraph()
    r_rd = p_risk_desc.add_run(
        "Danh mục các khoảng trống an ninh (GAP) được định lượng theo công thức rủi ro: "
        "Điểm rủi ro (Risk Score) = Khả năng xảy ra (Likelihood: 1-5) × Mức độ tác động (Impact: 1-5)."
    )
    _format_run(r_rd, size_pt=10, italic=True, color=MUTED_GRAY)
    _format_run(r_rd, size_pt=10.5, italic=True, color=MUTED_GRAY)

    risk_list = json_data.get("risk_register", [])
    if not risk_list and "top_gaps" in json_data:
        # Fallback from top_gaps
        risk_list = [
            {
                "control_id": g.get("id"),
                "gap": g.get("gap") or g.get("label"),
                "severity": g.get("severity", "high"),
                "likelihood": 4 if g.get("severity") in ("critical", "high") else 3,
                "impact": 5 if g.get("severity") == "critical" else 3,
                "risk_score": 20 if g.get("severity") == "critical" else 12,
                "recommendation": g.get("recommendation", "Cần ban hành chính sách và triển khai giải pháp kỹ thuật bổ sung.")
            }
            for g in json_data.get("top_gaps", [])
        ]

    # Sort risk by risk_score desc
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

        for idx, item in enumerate(risk_list[:30], 1):  # top 30 gaps
            row = rt.add_row()
            _make_row_cant_split(row)
            cells = row.cells
            sev = (item.get("severity") or "medium").lower()
            l_val = item.get("likelihood", 3)
            i_val = item.get("impact", 3)
            r_score = item.get("risk_score") or (int(l_val) * int(i_val))

            cells[0].paragraphs[0].add_run(str(idx))
            cells[1].paragraphs[0].add_run(str(item.get("control_id", "N/A")))
            cells[2].paragraphs[0].add_run(_clean_markdown(item.get("gap", ""))[:120])
            cells[3].paragraphs[0].add_run(sev.upper())
            cells[4].paragraphs[0].add_run(f"{l_val}×{i_val}={r_score}")
            cells[5].paragraphs[0].add_run(_clean_markdown(item.get("recommendation", ""))[:150])

            # Color highlight for severity
            sev_bg = "FEE2E2" if sev == "critical" else "FFEDD5" if sev == "high" else "FEF9C3" if sev == "medium" else "FFFFFF"
            _set_cell_background(cells[3], sev_bg)

            for c_idx in range(6):
                _set_cell_margins(cells[c_idx], 80, 80, 100, 100)
                p = cells[c_idx].paragraphs[0]
                if c_idx in (0, 1, 3, 4):
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                _format_run(p.runs[0], size_pt=9, color=TEXT_DARK)

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
