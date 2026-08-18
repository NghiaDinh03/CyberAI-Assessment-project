"""Assessment pipeline helpers — chunked prompt building, JSON validation, markdown conversion."""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from prompts import get_prompt
from prompts import defaults as prompt_defaults
from utils.json_repair import repair_json_string

logger = logging.getLogger(__name__)

WEIGHT_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1}
SEV_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

EVIDENCE_VERDICTS: Tuple[str, ...] = ("satisfied", "partial", "missing", "not_applicable")


class ControlVerdict(TypedDict):
    """Per-control evidence verdict produced by SecurityLM / mid-tier local model.

    Stable shape shared between chunk outputs (Step 3) and the final report
    consumer in the frontend (Step 5).
    """

    control_id: str
    evidence_verdict: str  # one of EVIDENCE_VERDICTS
    missing_items: List[str]
    confidence: float


def normalize_verdict(raw: dict) -> ControlVerdict:
    """Coerce a raw dict into the canonical ControlVerdict shape.

    - Unknown / missing verdict → "missing".
    - confidence clamped to [0.0, 1.0]; non-numeric → 0.0.
    - missing_items defaults to []; non-list values are wrapped/dropped.
    - All strings are stripped; non-string entries in missing_items become str().
    """
    if not isinstance(raw, dict):
        raw = {}
    control_id = str(raw.get("control_id", "")).strip()
    verdict_raw = str(raw.get("evidence_verdict", "")).strip().lower()
    verdict = verdict_raw if verdict_raw in EVIDENCE_VERDICTS else "missing"
    items_raw = raw.get("missing_items", [])
    if not isinstance(items_raw, list):
        items_raw = [items_raw] if items_raw else []
    missing_items: List[str] = []
    for it in items_raw:
        if it is None:
            continue
        s = str(it).strip()
        if s:
            missing_items.append(s)
    try:
        conf = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    if conf < 0.0:
        conf = 0.0
    elif conf > 1.0:
        conf = 1.0
    return ControlVerdict(
        control_id=control_id,
        evidence_verdict=verdict,
        missing_items=missing_items,
        confidence=conf,
    )


def _load_prompt(key: str, fallback: str) -> str:
    """Safe wrapper so unit tests without DATA_PATH still work."""
    try:
        return get_prompt(key)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("assessment prompt lookup failed for %s: %s", key, exc)
        return fallback


def build_chunk_prompt(cat_name: str, cat_controls: list, implemented: list,
                       pct: float, sc: int, mx: int,
                       sys_summary: str, std_name: str, rag_ctx: str = "",
                       evidence_summary: Optional[str] = None,
                       evidence_text: Optional[str] = None) -> str:
    """Build a per-control-group assessment prompt.

    Args:
        cat_name: Category/group name (e.g. "A.5 Tổ chức (1/7)").
        cat_controls: List of control dicts in this group (5-8 controls).
        implemented: List of implemented control IDs.
        pct: Current compliance percentage.
        sc: Current score (implemented count).
        mx: Max score (total controls).
        sys_summary: System summary text.
        std_name: Standard name (e.g. "ISO 27001:2022").
        rag_ctx: RAG context from ChromaDB.
        evidence_summary: Pre-computed evidence summary from SecurityLM.
        evidence_text: Raw evidence text for this control group (optional).
    """
    missing = [c for c in cat_controls if c["id"] not in implemented]
    present = [c for c in cat_controls if c["id"] in implemented]
    missing_str = "\n".join(
        f"❌{c['id']}[{c.get('weight','m').upper()[0]}]{c.get('label','')[:40]}"
        for c in missing[:15]
    ) or "all done"
    present_str = ", ".join(c["id"] for c in present[:12]) or "none"
    rag_section = f"\nREF:{rag_ctx[:350]}\n" if rag_ctx else ""
    if evidence_summary and evidence_summary.strip():
        rag_section = (
            f"\nEVIDENCE SUMMARY:\n{evidence_summary.strip()[:600]}\n"
            + rag_section
        )
    # Inject raw evidence for this control group if available
    if evidence_text and evidence_text.strip():
        rag_section += f"\nEVIDENCE TEXT:\n{evidence_text.strip()[:2000]}\n"
    few_shot = _load_prompt(
        "assessment.chunk_fewshot", prompt_defaults.ASSESSMENT_CHUNK_FEWSHOT,
    )
    template = _load_prompt(
        "assessment.chunk_template", prompt_defaults.ASSESSMENT_CHUNK_TEMPLATE,
    )
    try:
        return template.format_map({
            "std_name": std_name,
            "cat_name": cat_name,
            "pct": pct,
            "sc": sc,
            "mx": mx,
            "sys_summary": sys_summary[:400],
            "rag_section": rag_section,
            "present_str": present_str,
            "missing_str": missing_str,
            "few_shot": few_shot,
        })
    except (KeyError, ValueError) as exc:
        logger.error("chunk template format failed (%s) — using hard-coded default", exc)
        return prompt_defaults.ASSESSMENT_CHUNK_TEMPLATE.format_map({
            "std_name": std_name, "cat_name": cat_name, "pct": pct, "sc": sc, "mx": mx,
            "sys_summary": sys_summary[:400], "rag_section": rag_section,
            "present_str": present_str, "missing_str": missing_str, "few_shot": few_shot,
        })


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
    try:
        content = content.strip()
        
        # 1. Thử parse JSON chuẩn trước
        data = None
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                pass
                
        # 2. Nếu thất bại, chạy json_repair để sửa lỗi
        if data is None:
            try:
                repaired = repair_json_string(content)
                data = json.loads(repaired)
                logger.info(f"[Validate] JSON repaired successfully for chunk '{cat_name}'")
            except Exception as repair_exc:
                logger.warning(f"[Validate] JSON repair failed for chunk '{cat_name}': {repair_exc}")
                return None
                
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
            entry = {
                "id": ctrl_id,
                "category": cat_name,
                "severity": sev,
                "likelihood": max(1, min(5, int(item.get("likelihood", 3)))),
                "impact": max(1, min(5, int(item.get("impact", 3)))),
                "risk": max(1, min(25, int(item.get("risk", 9)))),
                "gap": str(item.get("gap", ""))[:200],
                "recommendation": str(item.get("recommendation", ""))[:200],
            }
            # Step 2: optionally normalize per-control verdict fields if present.
            # Backward compatible — absence of these fields is not an error.
            verdict_keys = ("control_id", "evidence_verdict", "missing_items", "confidence")
            if any(k in item for k in verdict_keys):
                raw_verdict = {
                    "control_id": item.get("control_id", ctrl_id),
                    "evidence_verdict": item.get("evidence_verdict"),
                    "missing_items": item.get("missing_items", []),
                    "confidence": item.get("confidence", 0.0),
                }
                entry.update(normalize_verdict(raw_verdict))
            else:
                logger.debug(
                    "[Validate] No verdict fields on item %s — skipping normalize", ctrl_id
                )
            validated.append(entry)
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
    template = _load_prompt(
        "assessment.report_system", prompt_defaults.ASSESSMENT_REPORT_SYSTEM,
    )
    try:
        sp = template.format_map({
            "std_name": std_name, "pct": pct, "sc": sc, "mx": mx,
        })
    except (KeyError, ValueError) as exc:
        logger.error("report template format failed (%s) — using default", exc)
        sp = prompt_defaults.ASSESSMENT_REPORT_SYSTEM.format_map({
            "std_name": std_name, "pct": pct, "sc": sc, "mx": mx,
        })
    um = f"Tài liệu {std_name}:\n{ctx}\n\nBiên bản khảo sát:\n{sys_info}"
    return sp, um


def build_evidence_block(
    evidence_text: str,
    evidence_summary: Optional[str] = None,
) -> str:
    """Return the evidence instruction block (empty if no evidence).

    The caller is responsible for trimming very large evidence bodies before
    passing them here; this function only injects it into the configured
    instruction template.

    Args:
        evidence_text: raw concatenated evidence body (already trimmed).
        evidence_summary: optional pre-computed summary produced by
            ``summarize_evidence`` (Step 2/3 hybrid pipeline). When provided
            and non-empty it is prepended as a clearly delimited
            "EVIDENCE SUMMARY" section ahead of the raw evidence block.
            Default ``None`` preserves the previous behaviour exactly.
    """
    if not evidence_text and not evidence_summary:
        return ""
    base = ""
    if evidence_text:
        template = _load_prompt(
            "assessment.evidence_instruction",
            prompt_defaults.ASSESSMENT_EVIDENCE_INSTRUCTION,
        )
        try:
            base = template.format_map({"evidence": evidence_text})
        except (KeyError, ValueError):
            base = prompt_defaults.ASSESSMENT_EVIDENCE_INSTRUCTION.format_map(
                {"evidence": evidence_text}
            )
    if evidence_summary and evidence_summary.strip():
        summary_block = (
            "=== EVIDENCE SUMMARY (pre-computed by SecurityLM) ===\n"
            f"{evidence_summary.strip()}\n"
            "=== END EVIDENCE SUMMARY ===\n\n"
        )
        return summary_block + base
    return base


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


_EVIDENCE_SUMMARY_SYSTEM_PROMPT = (
    "You are SecurityLM, a compliance analyst. Read the raw evidence text and "
    "produce a concise plain-text bullet list (no JSON, no markdown headers) "
    "covering THREE sections in this order:\n"
    "1) Controls referenced — ISO/NIST/TCVN control IDs or clauses explicitly or "
    "implicitly mentioned.\n"
    "2) Concrete artifacts — policies, procedures, logs, screenshots, tool names, "
    "config files, dates, owners.\n"
    "3) Gaps / ambiguities — missing items, unclear scope, or evidence that does "
    "not demonstrate implementation.\n"
    "Be terse. Use '- ' bullets. Do NOT invent facts not present in the input."
)


def summarize_evidence(
    evidence_text: str,
    *,
    max_tokens: int = 256,
    model_router=None,
    logger=None,
) -> str:
    """Summarize raw evidence text using the smallest local model (SecurityLM).

    Safe helper for the Step 3 hybrid pipeline: SecurityLM compresses evidence
    before the mid-tier model drafts per-control verdicts. On any failure this
    returns an empty string — callers must treat a missing summary as a soft
    degradation and fall back to the raw evidence block.

    Args:
        evidence_text: raw concatenated evidence body. Truncated to the last
            ~8 KB if longer (tail bias: later evidence chunks tend to be the
            most specific).
        max_tokens: upper bound on the summary output length. Step 3 will pass
            ``settings.EVIDENCE_SUMMARY_TOKENS`` here.
        model_router: optional override (module or object exposing the routing
            helpers) — primarily to keep this function unit-test friendly.
            When ``None``, the real :mod:`services.model_router` is imported
            lazily to avoid import-time cycles.
        logger: optional logger override; falls back to the module logger.

    Returns:
        Plain-text bullet list summary, or ``""`` on any failure.
    """
    log = logger if logger is not None else globals()["logger"]
    if not evidence_text or not evidence_text.strip():
        return ""

    # Truncate safely — keep the tail (most recent / most specific evidence).
    _MAX_INPUT_BYTES = 8 * 1024
    text = evidence_text
    if len(text.encode("utf-8", errors="ignore")) > _MAX_INPUT_BYTES:
        text = text[-_MAX_INPUT_BYTES:]

    # Lazy import to avoid import cycles and keep tests lightweight.
    if model_router is None:
        try:
            from services import model_router as _mr  # noqa: WPS433
            model_router = _mr
        except Exception as exc:  # pragma: no cover — defensive
            log.warning("summarize_evidence: model_router import failed: %s", exc)
            return ""

    try:
        get_fn = getattr(model_router, "get_security_model", None)
        if callable(get_fn):
            security_model = get_fn()
        else:
            security_model = getattr(model_router, "SECURITY_MODEL", None)
    except Exception:
        security_model = None

    try:
        from services.cloud_llm_service import CloudLLMService  # noqa: WPS433
    except Exception as exc:  # pragma: no cover — defensive
        log.warning("summarize_evidence: CloudLLMService import failed: %s", exc)
        return ""

    messages = [
        {"role": "system", "content": _EVIDENCE_SUMMARY_SYSTEM_PROMPT},
        {"role": "user", "content": f"RAW EVIDENCE:\n{text}"},
    ]
    try:
        result = CloudLLMService.chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=max(32, int(max_tokens)),
            prefer_cloud=False,
            local_model=security_model,
            task_type="iso_local",
        )
        content = (result or {}).get("content", "") or ""
        return content.strip()
    except Exception as exc:
        log.warning("summarize_evidence: inference failed: %s", exc)
        return ""
