"""Assessment pipeline helpers — chunked prompt building, JSON validation, markdown conversion."""

import json
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

WEIGHT_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1}
SEV_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def build_chunk_prompt(cat_name: str, cat_controls: list, implemented: list,
                       pct: float, sc: int, mx: int,
                       sys_summary: str, std_name: str, rag_ctx: str = "") -> str:
    missing = [c for c in cat_controls if c["id"] not in implemented]
    present = [c for c in cat_controls if c["id"] in implemented]
    missing_str = "\n".join(
        f"  ❌ {c['id']} [{c.get('weight','medium').upper()}] {c.get('label','')}"
        for c in missing[:20]
    )
    present_str = ", ".join(c["id"] for c in present[:15])
    rag_section = f"\nTÀI LIỆU THAM CHIẾU {std_name}:\n{rag_ctx[:600]}\n" if rag_ctx else ""
    return (
        f"Auditor {std_name} — Category: {cat_name}\n"
        f"Tuân thủ tổng: {pct}% ({sc}/{mx})\n"
        f"{rag_section}\n"
        f"CONTROLS ĐÃ ĐẠT: {present_str or 'Không có'}\n"
        f"CONTROLS CHƯA ĐẠT:\n{missing_str or 'Tất cả đã đạt'}\n\n"
        f"THÔNG TIN HỆ THỐNG:\n{sys_summary[:700]}\n\n"
        f"NHIỆM VỤ: Với mỗi control CHƯA ĐẠT trong nhóm '{cat_name}', "
        f"trả về JSON array (chỉ JSON, không text thêm):\n"
        f'[{{"id":"CTL.XX","severity":"critical|high|medium|low",'
        f'"likelihood":1-5,"impact":1-5,"risk":1-25,'
        f'"gap":"mô tả GAP ngắn","recommendation":"1 câu khuyến nghị"}}]\n'
        f"Nếu tất cả đã đạt, trả về: []"
    )


def validate_chunk_output(content: str, cat_name: str) -> Optional[List[Dict]]:
    content = content.strip()
    match = re.search(r'\[.*?\]', content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        if not isinstance(data, list):
            return None
        validated = []
        for item in data:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            validated.append({
                "id": item["id"],
                "category": cat_name,
                "severity": item.get("severity", "medium"),
                "likelihood": max(1, min(5, int(item.get("likelihood", 3)))),
                "impact": max(1, min(5, int(item.get("impact", 3)))),
                "risk": max(1, min(25, int(item.get("risk", 9)))),
                "gap": str(item.get("gap", ""))[:200],
                "recommendation": str(item.get("recommendation", ""))[:200],
            })
        return validated
    except Exception:
        return None


def gap_items_to_markdown(all_gap_items: list) -> str:
    if not all_gap_items:
        return "✅ Không phát hiện GAP đáng kể nào.\n"
    sorted_items = sorted(all_gap_items, key=lambda x: (SEV_ORDER.get(x["severity"], 2), -x["risk"]))
    lines = [
        "## RISK REGISTER\n",
        "| # | Control | Category | GAP | Severity | L | I | Risk | Khuyến nghị |",
        "|---|---------|----------|-----|----------|---|---|------|-------------|",
    ]
    for i, item in enumerate(sorted_items, 1):
        sev = item["severity"]
        lines.append(
            f"| {i} | {item['id']} | {item['category'][:20]} | {item['gap'][:60]} "
            f"| {SEV_EMOJI.get(sev,'')} {sev} | {item['likelihood']} | {item['impact']} "
            f"| {item['risk']} | {item['recommendation'][:60]} |"
        )
    counts = {s: sum(1 for x in all_gap_items if x["severity"] == s) for s in SEV_ORDER}
    lines.append(
        f"\n## TÓM TẮT: 🔴 Critical={counts['critical']} 🟠 High={counts['high']} "
        f"🟡 Medium={counts['medium']} ⚪ Low={counts['low']}"
    )
    return "\n".join(lines)


def build_full_prompt(std_name: str, pct: float, sc: int, mx: int,
                      sys_info: str, ctx: str) -> tuple:
    sp = (
        f"Bạn là chuyên gia Auditor về {std_name}. Tuân thủ: {pct}% ({sc}/{mx} Controls).\n\n"
        f"NHIỆM VỤ:\n"
        f"1. Phân loại GAP theo rủi ro: 🔴 Critical, 🟠 High, 🟡 Medium, ⚪ Low\n"
        f"2. Đánh giá Likelihood + Impact cho mỗi GAP\n"
        f"3. Risk Score = L × I; sắp xếp giảm dần\n"
        f"4. RISK REGISTER dạng bảng: Control | GAP | Severity | L | I | Risk | Khuyến nghị\n\n"
        f"## DANH SÁCH PHÁT HIỆN\n[GAP với severity]\n\n"
        f"## RISK REGISTER\n"
        f"| Control | GAP | Severity | L | I | Risk | Khuyến nghị |\n"
        f"|---------|-----|----------|---|---|------|-------------|\n[data]\n\n"
        f"## TÓM TẮT RỦI RO\n[Tổng: Critical/High/Medium/Low]"
    )
    um = f"Tài liệu {std_name}:\n{ctx}\n\nBiên bản khảo sát:\n{sys_info}"
    return sp, um


def build_weight_breakdown_txt(breakdown: dict, missing_by_weight: dict) -> str:
    if not any(v["total"] > 0 for v in breakdown.values()):
        return ""
    weight_labels = {"critical": "Tối quan trọng", "high": "Quan trọng", "medium": "Trung bình", "low": "Thấp"}
    lines = ["\n\nPHÂN BỔ TRỌNG SỐ CONTROLS:"]
    for w in ["critical", "high", "medium", "low"]:
        bd = breakdown[w]
        if bd["total"] > 0:
            pct = round(bd["implemented"] / bd["total"] * 100, 1)
            lines.append(f"- {weight_labels[w]}: {bd['implemented']}/{bd['total']} đạt ({pct}%)")
    critical_missing = missing_by_weight.get("critical", [])
    high_missing = missing_by_weight.get("high", [])
    if critical_missing:
        lines.append(f"\n⚠️ CONTROLS TỐI QUAN TRỌNG CHƯA ĐẠT ({len(critical_missing)}):")
        lines.extend(f"  🔴 {m}" for m in critical_missing[:15])
    if high_missing:
        lines.append(f"\n⚠️ CONTROLS QUAN TRỌNG CHƯA ĐẠT ({len(high_missing)}):")
        lines.extend(f"  🟠 {m}" for m in high_missing[:15])
    return "\n".join(lines)


def compress_for_phase2(raw_analysis: str, max_chars: int = 2500) -> str:
    if len(raw_analysis) <= max_chars:
        return raw_analysis
    lines = raw_analysis.split("\n")
    table_lines = [l for l in lines if l.startswith("|") or l.startswith("##") or "Critical" in l or "High" in l or "TÓM TẮT" in l]
    compressed = "\n".join(table_lines)
    if len(compressed) < 200:
        compressed = raw_analysis[:max_chars] + "\n...[truncated]"
    return compressed[:max_chars]


def build_sys_summary(system_data: dict) -> str:
    org = system_data.get("organization", {})
    inf = system_data.get("infrastructure", {})
    comp = system_data.get("compliance", {})
    return (
        f"Tổ chức: {org.get('name','')} | Ngành: {org.get('industry','')} | "
        f"Nhân sự: {org.get('employees',0)} | IT: {org.get('it_staff',0)}\n"
        f"Firewall: {inf.get('firewalls','')[:80]}\n"
        f"AV/EDR: {inf.get('antivirus','')[:60]}\n"
        f"SIEM: {inf.get('siem','')[:60]}\n"
        f"Cloud: {inf.get('cloud','')[:60]}\n"
        f"Backup: {inf.get('backup','')[:60]}\n"
        f"VPN: {inf.get('vpn','')}\n"
        f"Sự cố 12T: {comp.get('incidents_12m', 0)}\n"
        f"Ghi chú: {(system_data.get('notes') or '')[:300]}"
    )
