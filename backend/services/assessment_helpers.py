"""Assessment pipeline helpers — chunked prompt building, JSON validation, markdown conversion."""

import json
import re
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from prompts import get_prompt
from prompts import defaults as prompt_defaults
from utils.json_repair import repair_json_string

logger = logging.getLogger(__name__)

from services.controls_catalog import WEIGHT_SCORE
SEV_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "⚪"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

ALLOWED_VERDICTS: Tuple[str, ...] = (
    "satisfied",
    "partial",
    "missing",
    "not_evidenced",
    "needs_expert_review",
)
EVIDENCE_VERDICTS: Tuple[str, ...] = ALLOWED_VERDICTS


class ControlVerdict(TypedDict):
    """Per-control evidence verdict produced by SecurityLM / mid-tier local model.

    Stable shape shared between chunk outputs (Step 3) and the final report
    consumer in the frontend (Step 5).
    """

    control_id: str
    evidence_verdict: str  # one of ALLOWED_VERDICTS
    missing_items: List[str]
    confidence: float
    ai_verdict_raw: Optional[str]
    normalized_ai_verdict: Optional[str]
    verdict_rationale: Optional[str]
    evidence_citations: List[Dict[str, Any]]


def normalize_verdict(raw: dict) -> ControlVerdict:
    """Coerce a raw dict into the canonical ControlVerdict shape.

    - Preserves ai_verdict_raw and computes normalized_ai_verdict against ALLOWED_VERDICTS.
    - Extracts verdict_rationale / rationale.
    - Normalizes evidence_citations.
    - confidence clamped to [0.0, 1.0]; non-numeric → 0.0.
    - missing_items defaults to []; non-list values are wrapped/dropped.
    """
    if not isinstance(raw, dict):
        raw = {}
    control_id = str(raw.get("control_id", "")).strip()
    raw_v = raw.get("evidence_verdict") if "evidence_verdict" in raw else raw.get("verdict")
    ai_verdict_raw = str(raw_v).strip() if raw_v is not None else None
    verdict_lower = ai_verdict_raw.lower() if ai_verdict_raw else ""

    # Normalization aliases
    if verdict_lower in ("compliant", "satisfied", "pass", "implemented"):
        normalized = "satisfied"
    elif verdict_lower in ("partial", "partially_satisfied", "partially_compliant"):
        normalized = "partial"
    elif verdict_lower in ("needs_expert_review", "review", "expert_review", "ambiguous", "conflict"):
        normalized = "needs_expert_review"
    elif verdict_lower in ("not_evidenced", "unverified"):
        normalized = "not_evidenced"
    elif verdict_lower in ("missing", "non_compliant", "fail", "not_satisfied"):
        normalized = "missing"
    elif verdict_lower in ALLOWED_VERDICTS:
        normalized = verdict_lower
    else:
        normalized = None

    effective_evidence_verdict = normalized if normalized in ALLOWED_VERDICTS else "missing"

    items_raw = raw.get("missing_items", [])
    if not isinstance(items_raw, list):
        items_raw = [items_raw] if items_raw else []
    missing_items: List[str] = []
    for it in items_raw:
        if it is not None:
            s = str(it).strip()
            if s:
                missing_items.append(s)

    try:
        conf = float(raw.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    rationale = raw.get("verdict_rationale") or raw.get("rationale") or raw.get("reason") or raw.get("ai_reasoning")
    verdict_rationale = str(rationale).strip() if rationale else None

    raw_cits = raw.get("evidence_citations") or raw.get("citations") or []
    if not isinstance(raw_cits, list):
        raw_cits = [raw_cits] if raw_cits else []
    citations: List[Dict[str, Any]] = []
    for cit in raw_cits:
        if isinstance(cit, dict):
            citations.append({
                "evidence_id": cit.get("evidence_id") or cit.get("file_id"),
                "file_name": cit.get("file_name") or cit.get("filename"),
                "sha256": cit.get("sha256"),
                "excerpt": cit.get("excerpt") or cit.get("section") or cit.get("quote"),
            })
        elif isinstance(cit, str) and cit.strip():
            citations.append({"file_name": cit.strip()})

    return ControlVerdict(
        control_id=control_id,
        evidence_verdict=effective_evidence_verdict,
        missing_items=missing_items,
        confidence=conf,
        ai_verdict_raw=ai_verdict_raw,
        normalized_ai_verdict=normalized,
        verdict_rationale=verdict_rationale,
        evidence_citations=citations,
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
                       evidence_text: Optional[str] = None,
                       fact_cards_text: Optional[str] = None,
                       feedback_exemplars_text: Optional[str] = None) -> str:
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
        fact_cards_text: Structured Security Fact Cards from Agent 1 (optional).
        feedback_exemplars_text: Few-shot historical auditor feedback (optional).
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
    # Inject structured fact cards from Agent 1
    if fact_cards_text and fact_cards_text.strip():
        rag_section += f"\n{fact_cards_text.strip()}\n"
    # Inject raw evidence for this control group if available
    if evidence_text and evidence_text.strip():
        rag_section += f"\nEVIDENCE TEXT:\n{evidence_text.strip()[:3000]}\n"
        
    # Inject historical auditor few-shot corrections from Feedback Store
    if feedback_exemplars_text and feedback_exemplars_text.strip():
        rag_section += f"\n{feedback_exemplars_text.strip()}\n"

    few_shot = _load_prompt(
        "assessment.chunk_fewshot", prompt_defaults.ASSESSMENT_CHUNK_FEWSHOT,
    )
    template = _load_prompt(
        "assessment.chunk_template", prompt_defaults.ASSESSMENT_CHUNK_TEMPLATE,
    )
    candidates_list = []
    for c in cat_controls:
        cid = c.get("id") or c.get("control_id", "")
        if not cid:
            continue
        c_wt = c.get("weight", "medium").upper()
        c_lbl = c.get("label", "")[:60]
        status = "Tự khai: ĐÃ TRIỂN KHAI" if cid in implemented else "Tự khai: CHƯA TRIỂN KHAI"
        candidates_list.append(f"- Control {cid} [{c_wt}]: {c_lbl} ({status})")
    candidates_str = "\n".join(candidates_list) if candidates_list else "None"

    format_kwargs = {
        "std_name": std_name,
        "cat_name": cat_name,
        "pct": pct,
        "sc": sc,
        "mx": mx,
        "sys_summary": sys_summary[:400],
        "rag_section": rag_section,
        "present_str": present_str,
        "missing_str": missing_str,
        "candidates_str": candidates_str,
        "few_shot": few_shot,
    }
    try:
        return template.format_map(format_kwargs)
    except (KeyError, ValueError) as exc:
        logger.error("chunk template format failed (%s) — using hard-coded default", exc)
        return prompt_defaults.ASSESSMENT_CHUNK_TEMPLATE.format_map(format_kwargs)


def extract_group_evidence_and_cards(
    raw_evidence_text: str,
    target_control_ids: set,
    implemented_control_ids: set,
    ev_map: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Extract evidence text and structured Security Fact Cards scoped specifically to target control IDs.

    Prevents context truncation (>16k chars) from starving later controls (like A.5.9, A.8.8)
    and avoids synthesizing dummy 'assessment_evidence' filenames.
    """
    if not raw_evidence_text or not raw_evidence_text.strip():
        return None, None

    import os
    import re
    from services.evidence_fact_extractor import EvidenceFactExtractor

    # 1. Look for [Control <ID>] sections created by build_evidence_context_for_ai
    pattern = re.compile(r'(\[Control\s+([A-Za-z0-9_\.\-]+)\][^\n]*)')
    matches = list(pattern.finditer(raw_evidence_text))

    group_sections = []
    group_fact_cards = []

    if matches:
        first_pos = matches[0].start()
        prefix = raw_evidence_text[:first_pos].strip()
        prefix_clean = "\n".join(line for line in prefix.splitlines() if not line.startswith("--- BẰNG CHỨNG")).strip()
        if prefix_clean and len(prefix_clean) > 20:
            group_sections.append(prefix_clean[:800])

        for i, match in enumerate(matches):
            cid = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_evidence_text)
            block = raw_evidence_text[start:end].strip()

            if cid in target_control_ids:
                group_sections.append(block)
                file_blocks = re.split(r'[•\*\-]\s*File:\s*', block)
                for fb in file_blocks[1:]:
                    lines = fb.splitlines()
                    fname = os.path.basename(lines[0].strip()) if lines else "evidence_file"
                    content = "\n".join(lines[1:]).strip()
                    content = re.sub(r'^\s*Nội dung thực tế trích xuất:\s*', '', content, flags=re.IGNORECASE).strip()
                    if content:
                        fc = EvidenceFactExtractor.extract_facts(content, filename=fname, use_llm=False)
                        group_fact_cards.append(fc)
    else:
        sample_fname = "system_evidence.log"
        if ev_map:
            for cid in target_control_ids:
                files = ev_map.get(cid, [])
                if isinstance(files, str) and files:
                    sample_fname = os.path.basename(files)
                    break
                elif isinstance(files, list) and files:
                    sample_fname = os.path.basename(files[0])
                    break
        fc = EvidenceFactExtractor.extract_facts(raw_evidence_text, filename=sample_fname, use_llm=False)
        rel_set = set(fc.relevant_controls)
        for d in fc.security_deficiencies:
            rel_set.update(d.get("control_ids", []))
        for s in fc.compliance_readiness.get("satisfied_controls", []):
            cid_s = s.get("control_id") if isinstance(s, dict) else str(s)
            if cid_s:
                rel_set.add(cid_s)

        if rel_set.intersection(target_control_ids) or not rel_set:
            group_fact_cards.append(fc)
            group_sections.append(raw_evidence_text[:4000])

    scoped_evidence_text = "\n\n".join(group_sections).strip() if group_sections else None
    fact_cards_text = None
    if group_fact_cards:
        attested = [cid for cid in target_control_ids if cid in implemented_control_ids]
        fact_cards_text = EvidenceFactExtractor.format_for_auditor(group_fact_cards, self_attested_controls=attested)

    return scoped_evidence_text, fact_cards_text


def infer_gap_from_control(ctrl: dict, cat_name: str) -> dict:
    """Fallback: infer a gap item from control metadata when SecurityLM fails."""
    from services.risk_scoring import calculate_risk_score
    sev_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
    w = ctrl.get("weight", "medium")
    sev = sev_map.get(w, "medium")
    l_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    i_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    likelihood = l_map.get(w, 2)
    impact = i_map.get(w, 2)
    cid = ctrl.get("id") or ctrl.get("control_id", "")
    return {
        "id": cid,
        "control_id": cid,
        "category": cat_name,
        "severity": sev,
        "likelihood": likelihood,
        "impact": impact,
        "risk": calculate_risk_score(likelihood, impact),
        "gap": f"{ctrl.get('label', cid)} chưa được triển khai",
        "recommendation": "Triển khai và tài liệu hóa biện pháp kiểm soát này",
    }


def extract_json_payload(content: str) -> Any:
    """Safely extract JSON array or object from LLM response."""
    if not content or not content.strip():
        return None
    cleaned = content.strip()

    # Strip thinking blocks <think>...</think> or <thought>...</thought>
    cleaned = re.sub(r'<think(?:ing)?>.*?</think(?:ing)?>', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'<thought>.*?</thought>', '', cleaned, flags=re.DOTALL)

    # Strategy 1: Code fences ```json ... ``` or ``` ... ```
    fence_matches = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned, re.IGNORECASE)
    for block in fence_matches:
        block_str = block.strip()
        try:
            return json.loads(block_str)
        except Exception:
            try:
                return json.loads(repair_json_string(block_str))
            except Exception:
                continue

    # Strategy 2: Direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Strategy 3: Find first JSON object { ... } or array [ ... ]
    # Prioritize object if { appears first
    first_brace = cleaned.find('{')
    first_bracket = cleaned.find('[')
    
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        last_brace = cleaned.rfind('}')
        if last_brace > first_brace:
            cand = cleaned[first_brace:last_brace + 1]
            try:
                return json.loads(cand)
            except Exception:
                try:
                    return json.loads(repair_json_string(cand))
                except Exception:
                    pass

    if first_bracket != -1:
        last_bracket = cleaned.rfind(']')
        if last_bracket > first_bracket:
            cand = cleaned[first_bracket:last_bracket + 1]
            try:
                return json.loads(cand)
            except Exception:
                try:
                    return json.loads(repair_json_string(cand))
                except Exception:
                    pass

    return None


def validate_chunk_output(content: str, cat_name: str,
                          valid_ids: Optional[List[str]] = None) -> Optional[List[Dict]]:
    """Parse and validate JSON output from SecurityLM.
    Supports both {"control_verdicts": [...]} and raw array [...].
    valid_ids: if provided, reject items with IDs not in this set (anti-hallucination).
    """
    try:
        data = extract_json_payload(content)
        if data is None:
            logger.warning(f"[Validate] Could not extract valid JSON from chunk '{cat_name}'")
            return None

        if isinstance(data, dict):
            for k in ("control_verdicts", "gaps", "items", "controls", "data"):
                if isinstance(data.get(k), list):
                    data = data[k]
                    break
            else:
                # If dict represents a single control item
                if "control_id" in data or "id" in data:
                    data = [data]

        if not isinstance(data, list):
            return None
        # Empty list is valid (all controls implemented)
        if len(data) == 0:
            return []
            
        validated = []
        for item in data:
            if not isinstance(item, dict):
                continue
            ctrl_id = str(item.get("control_id") or item.get("id", "")).strip()
            if not ctrl_id:
                continue
            # Anti-hallucination: skip if ID not in valid set
            if valid_ids and ctrl_id not in valid_ids:
                logger.debug(f"[Validate] Rejected hallucinated control ID: {ctrl_id}")
                continue
            sev = item.get("severity", "medium")
            if sev not in ("critical", "high", "medium", "low"):
                sev = "medium"

            raw_l = item.get("likelihood")
            raw_i = item.get("impact")
            try:
                l_val = int(raw_l) if raw_l is not None else 3
                i_val = int(raw_i) if raw_i is not None else 3
            except (ValueError, TypeError):
                l_val, i_val = -1, -1

            from services.risk_scoring import calculate_risk_score
            # If LLM returns out-of-range risk values (e.g. 5, 0), reject and use deterministic fallback with trace
            if not (1 <= l_val <= 4 and 1 <= i_val <= 4):
                logger.warning(
                    "[Validate] Invalid risk metric from LLM for control '%s' (Likelihood=%s, Impact=%s outside 1-4). Fallback triggered with trace.",
                    ctrl_id, raw_l, raw_i
                )
                fb = infer_gap_from_control({"id": ctrl_id, "weight": sev}, cat_name)
                l_val, i_val = fb["likelihood"], fb["impact"]

            r_score = calculate_risk_score(l_val, i_val)

            entry = {
                "id": ctrl_id,
                "control_id": ctrl_id,
                "category": cat_name,
                "severity": sev,
                "likelihood": l_val,
                "impact": i_val,
                "risk": r_score,
                "gap": str(item.get("gap", ""))[:200],
                "recommendation": str(item.get("recommendation", ""))[:200],
            }
            # Step 2: optionally normalize per-control verdict fields if present.
            # Backward compatible — absence of these fields is not an error.
            verdict_keys = ("control_id", "evidence_verdict", "verdict", "missing_items", "confidence", "rationale", "citations", "verdict_rationale", "ai_verdict_raw")
            if any(k in item for k in verdict_keys):
                raw_verdict = {
                    "control_id": ctrl_id,
                    "evidence_verdict": item.get("verdict") if "verdict" in item else item.get("evidence_verdict"),
                    "missing_items": item.get("missing_items", []),
                    "confidence": item.get("confidence", 0.0),
                    "rationale": item.get("rationale") or item.get("verdict_rationale") or item.get("reason") or item.get("ai_reasoning"),
                    "citations": item.get("citations") or item.get("evidence_citations", []),
                }
                normalized_v = normalize_verdict(raw_verdict)
                if hasattr(normalized_v, "model_dump"):
                    entry.update(normalized_v.model_dump())
                else:
                    entry.update(normalized_v)
                entry["control_id"] = ctrl_id
                entry["id"] = ctrl_id
                entry["verdict"] = entry.get("evidence_verdict")
                entry["citations"] = entry.get("evidence_citations") or item.get("citations", [])
                entry["rationale"] = entry.get("verdict_rationale") or item.get("rationale", "")
            else:
                logger.debug(
                    "[Validate] No verdict fields on item %s — skipping normalize", ctrl_id
                )
            validated.append(entry)
        return validated
    except Exception as e:
        logger.warning(f"[Validate] Exception validating chunk output: {e}")
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


def get_control_weight_level(ctrl: Any) -> str:
    """Normalize control weight into one of 'critical', 'high', 'medium', or 'low'.
    Checks weight_level, weight_points, and weight across dict or pydantic models.
    """
    if isinstance(ctrl, dict):
        w_lvl = ctrl.get("weight_level")
        w_pts = ctrl.get("weight_points")
        w_raw = ctrl.get("weight")
    else:
        w_lvl = getattr(ctrl, "weight_level", None)
        w_pts = getattr(ctrl, "weight_points", None)
        w_raw = getattr(ctrl, "weight", None)

    if w_lvl and str(w_lvl).strip().lower() in ("critical", "high", "medium", "low"):
        return str(w_lvl).strip().lower()

    if isinstance(w_raw, str) and w_raw.strip().lower() in ("critical", "high", "medium", "low"):
        return w_raw.strip().lower()

    pts = w_pts if w_pts is not None else w_raw
    try:
        f_pts = float(pts)
        if f_pts >= 9.0:
            return "critical"
        elif f_pts >= 4.5:
            return "high"
        elif f_pts >= 2.5:
            return "medium"
        else:
            return "low"
    except (TypeError, ValueError):
        return "medium"


def aggregate_priority_breakdown(
    controls: List[Any],
    weighted_compliance: Optional[Any] = None,
    enforce_invariants: bool = True,
) -> Dict[str, Any]:
    """Aggregate priority / weight category breakdown strictly matching verdict_weighted_v2.
    Produces counts, gaps, and weighted scores for each tier (critical, high, medium, low)
    and validates invariants against weighted_compliance and total applicable controls.
    """
    from schemas.assessment_schema import VERDICT_FACTOR, WEIGHT_NAME_TO_POINTS

    tier_order = ["critical", "high", "medium", "low"]
    tier_labels = {
        "critical": "Critical (Trọng yếu)",
        "high": "High (Cao)",
        "medium": "Medium (Trung bình)",
        "low": "Low (Thấp)",
    }

    tiers = {
        tier: {
            "tier": tier,
            "name": tier_labels[tier],
            "weight_per_control": WEIGHT_NAME_TO_POINTS[tier],
            "total_controls": 0,
            "satisfied_verified": 0,
            "partial_controls": 0,
            "gap_controls": 0,
            "weighted_score": 0.0,
            "weighted_max_score": 0.0,
            "percentage": 0.0,
        }
        for tier in tier_order
    }

    total_applicable = 0
    total_satisfied = 0
    total_partial = 0
    total_gaps = 0
    total_weighted_score = 0.0
    total_weighted_max_score = 0.0

    for c in (controls or []):
        if isinstance(c, dict):
            verdict = str(c.get("assessment_verdict") or c.get("evidence_verdict") or c.get("verdict") or "missing").lower()
            conflict = bool(c.get("conflict_detected", False))
            contrib = c.get("weighted_score_contribution")
            pts = c.get("weight_points")
        else:
            verdict = str(getattr(c, "assessment_verdict", None) or getattr(c, "evidence_verdict", None) or getattr(c, "verdict", None) or "missing").lower()
            conflict = bool(getattr(c, "conflict_detected", False))
            contrib = getattr(c, "weighted_score_contribution", None)
            pts = getattr(c, "weight_points", None)

        tier = get_control_weight_level(c)
        t_data = tiers[tier]

        t_data["total_controls"] += 1
        total_applicable += 1

        unit_w = float(pts) if pts is not None else WEIGHT_NAME_TO_POINTS.get(tier, 3.0)
        t_data["weighted_max_score"] += unit_w
        total_weighted_max_score += unit_w

        factor = VERDICT_FACTOR.get(verdict, 0.0)
        if contrib is not None and not conflict:
            score_contrib = float(contrib)
        else:
            score_contrib = (unit_w * factor) if not conflict else 0.0

        t_data["weighted_score"] += score_contrib
        total_weighted_score += score_contrib

        if verdict == "satisfied" and not conflict:
            t_data["satisfied_verified"] += 1
            total_satisfied += 1
        elif verdict in ("partial", "partially_satisfied") and not conflict:
            t_data["partial_controls"] += 1
            total_partial += 1
            t_data["gap_controls"] += 1
            total_gaps += 1
        else:
            t_data["gap_controls"] += 1
            total_gaps += 1

    # Round scores and compute percentages
    for tier, t_data in tiers.items():
        t_data["weighted_score"] = round(t_data["weighted_score"], 1)
        t_data["weighted_max_score"] = round(t_data["weighted_max_score"], 1)
        if t_data["weighted_max_score"] > 0:
            t_data["percentage"] = round((t_data["weighted_score"] / t_data["weighted_max_score"]) * 100, 1)
        else:
            t_data["percentage"] = 0.0

    total_weighted_score = round(total_weighted_score, 1)
    total_weighted_max_score = round(total_weighted_max_score, 1)
    total_pct = round((total_weighted_score / total_weighted_max_score) * 100, 1) if total_weighted_max_score > 0 else 0.0

    summary = {
        "tiers": tiers,
        "total_applicable": total_applicable,
        "total_satisfied": total_satisfied,
        "total_partial": total_partial,
        "total_gaps": total_gaps,
        "total_weighted_score": total_weighted_score,
        "total_weighted_max_score": total_weighted_max_score,
        "percentage": total_pct,
    }

    if enforce_invariants and weighted_compliance:
        wc_score = weighted_compliance.get("weighted_score") if isinstance(weighted_compliance, dict) else getattr(weighted_compliance, "weighted_score", None)
        wc_max = weighted_compliance.get("weighted_max_score") if isinstance(weighted_compliance, dict) else getattr(weighted_compliance, "weighted_max_score", None)
        if wc_score is not None and abs(total_weighted_score - float(wc_score)) > 0.15:
            raise ValueError(
                f"Priority Breakdown invariant violation: sum of tier weighted scores ({total_weighted_score}) does not match weighted_compliance.weighted_score ({wc_score})"
            )
        if wc_max is not None and abs(total_weighted_max_score - float(wc_max)) > 0.15:
            raise ValueError(
                f"Priority Breakdown invariant violation: sum of tier weighted max scores ({total_weighted_max_score}) does not match weighted_compliance.weighted_max_score ({wc_max})"
            )

    return summary

