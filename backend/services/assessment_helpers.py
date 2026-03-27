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
        f"❌{c['id']}[{c.get('weight','m').upper()[0]}]{c.get('label','')[:40]}"
        for c in missing[:15]
    )
    present_str = ", ".join(c["id"] for c in present[:12])
    rag_section = f"\nREF:{rag_ctx[:350]}\n" if rag_ctx else ""
    # Few-shot examples embedded directly so SecurityLM 7B understands exact format
    few_shot = (
        'VÍ DỤ OUTPUT (chỉ trả về JSON, không text thêm):\n'
        '[{"id":"A.5.1","severity":"critical","likelihood":4,"impact":5,"risk":20,'
        '"gap":"Chính sách ATTT chưa được ban hành","recommendation":"Ban hành chính sách ATTT ngay trong 30 ngày"},\n'
        ' {"id":"A.5.9","severity":"high","likelihood":3,"impact":3,"risk":9,'
        '"gap":"Chưa có danh mục tài sản thông tin","recommendation":"Lập asset inventory cho phần cứng và dữ liệu"}]\n\n'
    )
    return (
        f"ISO Auditor — {std_name} | {cat_name} | Tuân thủ:{pct}%({sc}/{mx})\n"
        f"HỆ THỐNG:{sys_summary[:400]}\n"
        f"{rag_section}"
        f"ĐÃ ĐẠT:{present_str or 'none'}\n"
        f"CHƯA ĐẠT:\n{missing_str or 'all done'}\n\n"
        f"{few_shot}"
        f"Trả về JSON array cho mỗi control CHƯA ĐẠT ở trên (CHÍNH XÁC format như ví dụ, chỉ JSON):\n"
        f"[]\n nếu tất cả đạt."
    )


def infer_gap_from_control(ctrl: dict, cat_name: str) -> dict:
    """Fallback: infer a gap item from control metadata when SecurityLM fails."""
    sev_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
    w = ctrl.get("weight", "medium")
    sev = sev_map.get(w, "medium")
    l_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    i_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    likelihood = l_map.get(w, 2)
    impact = i_map.get(w, 2)
    return {
        "id": ctrl["id"],
        "category": cat_name,
        "severity": sev,
        "likelihood": likelihood,
        "impact": impact,
        "risk": likelihood * impact,
        "gap": f"{ctrl.get('label', ctrl['id'])} chưa được triển khai",
        "recommendation": "Triển khai và tài liệu hóa biện pháp kiểm soát này",
    }


def validate_chunk_output(content: str, cat_name: str,
                          valid_ids: Optional[List[str]] = None) -> Optional[List[Dict]]:
    """Parse and validate JSON output from SecurityLM.
    valid_ids: if provided, reject items with IDs not in this set (anti-hallucination).
    """
    content = content.strip()
    # Handle model wrapping in ```json ... ``` or just ```...```
    match = re.search(r'\[.*?\]', content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        if not isinstance(data, list):
            return None
        # Empty list is valid (all controls implemented)
        if len(data) == 0:
            return []
        validated = []
        for item in data:
            if not isinstance(item, dict):
                continue
            ctrl_id = str(item.get("id", "")).strip()
            if not ctrl_id:
                continue
            # Anti-hallucination: skip if ID not in valid set
            if valid_ids and ctrl_id not in valid_ids:
                logger.debug(f"[Validate] Rejected hallucinated control ID: {ctrl_id}")
                continue
            sev = item.get("severity", "medium")
            if sev not in ("critical", "high", "medium", "low"):
                sev = "medium"
            validated.append({
                "id": ctrl_id,
                "category": cat_name,
                "severity": sev,
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


def normalize_severity_distribution(gap_items: list) -> list:
    """Prevent all-critical output from 7B model — redistribute if > 70% critical.
    
    Real-world ISO assessments: ~20% critical, 35% high, 30% medium, 15% low.
    If SecurityLM marks > 70% as critical, scale down proportionally using risk scores.
    """
    if not gap_items or len(gap_items) < 3:
        return gap_items
    critical_count = sum(1 for g in gap_items if g["severity"] == "critical")
    if critical_count / len(gap_items) <= 0.7:
        return gap_items
    logger.debug(f"[SeverityNorm] {critical_count}/{len(gap_items)} critical — normalizing")
    sorted_items = sorted(gap_items, key=lambda x: -x["risk"])
    n = len(sorted_items)
    critical_cutoff = max(1, int(n * 0.25))
    high_cutoff = max(1, int(n * 0.50))
    normalized = []
    for i, item in enumerate(sorted_items):
        new_item = dict(item)
        if i < critical_cutoff:
            new_item["severity"] = "critical"
        elif i < high_cutoff:
            new_item["severity"] = "high"
        elif i < int(n * 0.80):
            new_item["severity"] = "medium"
        else:
            new_item["severity"] = "low"
        normalized.append(new_item)
    return normalized


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
