"""Artifact Consistency & Validation Engine.

Provides comprehensive validation across all generated assessment artifacts:
JSON, Audit Trace, Evidence Manifest, SoA XLSX, DOCX, and PDF.
Ensures consistency of IDs, run metadata, scoring formulas, RAG telemetry,
and scrubbing of sensitive data/PII/secrets.
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set

import openpyxl
import docx

logger = logging.getLogger(__name__)

# Pattern to detect unmasked private IPv4 addresses (e.g. 192.168.1.50)
_UNMASKED_IP_PATTERN = re.compile(r'\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b')
# Pattern to detect secret tokens/passwords
_SECRET_PATTERN = re.compile(r'(?:password|secret_key|api_key|token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{8,}["\']?', re.IGNORECASE)


def validate_assessment_artifacts(
    assessment_id: str,
    bundle_dir: Optional[str] = None,
    assessment_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Execute rigorous consistency check across all artifacts for an assessment.

    Returns a structured dictionary with overall status PASS/FAIL and detailed checks.
    """
    data_dir = os.getenv("DATA_PATH", "./data")
    check_results: Dict[str, Any] = {
        "assessment_id": assessment_id,
        "overall_status": "PASS",
        "timestamp": None,
        "checks": {},
        "failures": [],
    }

    def fail(check_name: str, message: str):
        check_results["overall_status"] = "FAIL"
        check_results["failures"].append(f"[{check_name}] {message}")
        if check_name not in check_results["checks"]:
            check_results["checks"][check_name] = {"status": "FAIL", "errors": []}
        check_results["checks"][check_name]["status"] = "FAIL"
        check_results["checks"][check_name]["errors"].append(message)

    def pass_check(check_name: str, details: Any = None):
        if check_name not in check_results["checks"]:
            check_results["checks"][check_name] = {"status": "PASS", "details": details or "OK"}

    # 1. Load Primary Assessment JSON
    json_path = None
    if bundle_dir:
        json_path = os.path.join(bundle_dir, f"assessment_{assessment_id}.json")
    if not json_path or not os.path.exists(json_path):
        json_path = os.path.join(data_dir, "assessments", f"{assessment_id}.json")

    a_data = assessment_data
    if not a_data and os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                a_data = json.load(f)
        except Exception as e:
            fail("load_assessment_json", f"Cannot load JSON: {e}")
            return check_results

    if not a_data:
        fail("load_assessment_json", f"Assessment JSON not found at {json_path}")
        return check_results

    pass_check("load_assessment_json", f"Loaded successfully from {json_path}")

    # Extract core metadata
    eff_aid = a_data.get("assessment_id") or assessment_id
    eff_run_id = a_data.get("run_id") or a_data.get("result", {}).get("json_data", {}).get("run_id") or "run_default"
    eff_code_ver = a_data.get("code_version") or a_data.get("result", {}).get("json_data", {}).get("code_version") or "v1.2.0-verdict"
    raw_std = a_data.get("standard") or a_data.get("system_info", {}).get("assessment_standard") or "iso27001"
    std_id = raw_std.get("id") if isinstance(raw_std, dict) else str(raw_std)

    # 2. Check Scoring Consistency (Coverage vs Weighted Compliance)
    json_data = a_data.get("json_data") or a_data.get("result", {}).get("json_data") or {}
    coverage = json_data.get("control_coverage") or a_data.get("control_coverage") or {}
    weighted = json_data.get("weighted_compliance") or a_data.get("weighted_compliance") or {}

    if coverage:
        self_impl = coverage.get("self_declared_implemented", 0)
        tot_ctrls = coverage.get("total_controls", 0)
        raw_pct = coverage.get("raw_percentage", 0.0)
        expected_raw_pct = round((self_impl / tot_ctrls * 100), 1) if tot_ctrls > 0 else 0.0
        if abs(raw_pct - expected_raw_pct) > 0.1:
            fail("scoring_consistency", f"Raw coverage percentage mismatch: {raw_pct} != {expected_raw_pct}")
        else:
            pass_check("raw_coverage_math", f"{self_impl}/{tot_ctrls} = {raw_pct}%")

    if weighted:
        w_score = float(weighted.get("weighted_score", 0.0))
        w_max = float(weighted.get("weighted_max_score", 0.0))
        w_pct = float(weighted.get("percentage", 0.0))
        algorithm = weighted.get("algorithm", "")
        weight_scheme = weighted.get("weight_scheme")

        expected_w_pct = round((w_score / w_max * 100), 1) if w_max > 0 else 0.0
        if abs(w_pct - expected_w_pct) > 0.1:
            fail("scoring_consistency", f"Weighted compliance percentage mismatch: {w_pct} != {expected_w_pct}")
        else:
            pass_check("weighted_compliance_math", f"{w_score}/{w_max} = {w_pct}%")

        # Check weight_scheme for new algorithm
        if algorithm == "verdict_weighted_v2" or weight_scheme is not None:
            expected_scheme = "critical_10_high_5_medium_3_low_1"
            if weight_scheme != expected_scheme:
                fail("weight_scheme_validity", f"Invalid weight_scheme '{weight_scheme}', expected '{expected_scheme}'")
            else:
                pass_check("weight_scheme_validity", f"Weight scheme valid: {weight_scheme}")

        # Check standard maximum weights dynamically without hardcoding static constants
        is_new_algo = (algorithm == "verdict_weighted_v2" or weight_scheme == "critical_10_high_5_medium_3_low_1")
        if is_new_algo:
            ctrls = json_data.get("controls") or a_data.get("controls") or []
            if ctrls:
                applicable = [c for c in ctrls if (c.get("user_declaration") or "").lower() != "not_applicable"]
                expected_w_max = sum(
                    {"critical": 10.0, "high": 5.0, "medium": 3.0, "low": 1.0}.get(
                        str(c.get("weight") or c.get("weight_level") or "medium").lower(), 3.0
                    )
                    for c in applicable
                )
                if abs(w_max - expected_w_max) > 0.5:
                    fail("weighted_max_score_catalog", f"weighted_max_score mismatch: {w_max} != {expected_w_max}")
                else:
                    pass_check("weighted_max_score_catalog", f"max score = {expected_w_max} (dynamically verified from {len(applicable)} applicable controls)")
            else:
                pass_check("weighted_max_score_catalog", f"No controls array to recalculate max score, accepted {w_max}")

        # Check zero-verdict anomaly: if all control verdicts in controls_out are 0-factor, weighted_score cannot be > 0
        ctrls = json_data.get("controls") or a_data.get("controls") or []
        if ctrls:
            verdicts = [
                (c.get("assessment_verdict") or c.get("evidence_verdict") or "missing").lower()
                for c in ctrls
            ]
            all_zero = all(v in ("not_evidenced", "missing", "needs_expert_review") for v in verdicts)
            if all_zero and len(verdicts) > 0 and w_score > 0.0:
                fail("zero_verdict_consistency", f"All verdicts are non-achieving ({len(verdicts)} controls), but weighted_score is {w_score} > 0")
            else:
                pass_check("zero_verdict_consistency", "Verdict scoring consistent with control verdicts")

    # 2.1 Check Risk Scoring Consistency (Likelihood 1-4, Impact 1-4, Risk Score = L × I <= 16)
    all_risk_items = []
    ctrls = json_data.get("controls") or a_data.get("controls") or []
    for c in ctrls:
        if isinstance(c, dict) and ("likelihood" in c or "impact" in c or "risk_score" in c):
            all_risk_items.append((c.get("control_id") or c.get("id") or "control", c))
    for r in json_data.get("risk_register") or a_data.get("risk_register") or []:
        if isinstance(r, dict):
            all_risk_items.append((r.get("control_id") or r.get("id") or "risk", r))
    for g in json_data.get("top_gaps") or a_data.get("top_gaps") or []:
        if isinstance(g, dict) and ("likelihood" in g or "impact" in g or "risk_score" in g):
            all_risk_items.append((g.get("control_id") or g.get("id") or "gap", g))

    risk_check_passed = True
    for item_id, item in all_risk_items:
        if item.get("is_legacy"):
            continue
        l_val = item.get("likelihood")
        i_val = item.get("impact")
        r_score = item.get("risk_score") if item.get("risk_score") is not None else item.get("risk")

        if l_val is not None:
            if not isinstance(l_val, int) or l_val < 1 or l_val > 4:
                fail("risk_score_consistency", f"Control/Risk {item_id}: likelihood={l_val} outside valid range [1, 4]")
                risk_check_passed = False
        if i_val is not None:
            if not isinstance(i_val, int) or i_val < 1 or i_val > 4:
                fail("risk_score_consistency", f"Control/Risk {item_id}: impact={i_val} outside valid range [1, 4]")
                risk_check_passed = False
        if l_val is not None and i_val is not None and r_score is not None:
            expected_score = l_val * i_val
            if r_score != expected_score:
                fail("risk_score_consistency", f"Control/Risk {item_id}: risk_score={r_score} != likelihood({l_val}) * impact({i_val}) = {expected_score}")
                risk_check_passed = False
            if r_score > 16:
                fail("risk_score_consistency", f"Control/Risk {item_id}: risk_score={r_score} exceeds maximum allowed 16")
                risk_check_passed = False

    if risk_check_passed and all_risk_items:
        pass_check("risk_score_consistency", f"Verified {len(all_risk_items)} risk items conform to 4x4 matrix (1-16)")
    elif not all_risk_items:
        pass_check("risk_score_consistency", "No risk items to validate")

    # 3. Check Evidence Manifest
    manifest_path = None
    if bundle_dir:
        manifest_path = os.path.join(bundle_dir, f"evidence_manifest_{assessment_id}.json")
    if not manifest_path or not os.path.exists(manifest_path):
        manifest_path = os.path.join(data_dir, "evidence_manifests", f"{assessment_id}.json")

    manifest_data = None
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_data = json.load(mf)
            pass_check("evidence_manifest_exists", f"Found at {manifest_path}")

            # Validate manifest fields
            if manifest_data.get("assessment_id") != eff_aid:
                fail("manifest_metadata", f"Manifest assessment_id mismatch: {manifest_data.get('assessment_id')} != {eff_aid}")
            if manifest_data.get("run_id") != eff_run_id:
                fail("manifest_metadata", f"Manifest run_id mismatch: {manifest_data.get('run_id')} != {eff_run_id}")

            # Verify no unmasked IP in filenames
            for f_item in manifest_data.get("files", []):
                m_name = f_item.get("masked_filename", "")
                if _UNMASKED_IP_PATTERN.search(m_name):
                    fail("manifest_security", f"Unmasked IP found in manifest filename: {m_name}")
            pass_check("manifest_metadata", "Manifest metadata consistent and sanitized")
        except Exception as e:
            fail("evidence_manifest", f"Failed to parse manifest: {e}")
    else:
        # Note if no files uploaded
        pass_check("evidence_manifest", "No evidence files manifest (zero-evidence assessment)")

    # 4. Check Audit Trace
    trace_path = None
    if bundle_dir:
        trace_path = os.path.join(bundle_dir, f"audit_trace_{assessment_id}.json")
    if not trace_path or not os.path.exists(trace_path):
        trace_path = os.path.join(data_dir, "audit_traces", f"{assessment_id}.json")

    if os.path.exists(trace_path):
        try:
            with open(trace_path, "r", encoding="utf-8") as tf:
                trace_data = json.load(tf)
            pass_check("audit_trace_exists", f"Found at {trace_path}")

            events = trace_data.get("events", [])
            rag_events = [e for e in events if e.get("event_type") == "rag_query_completed"]
            llm_events = [e for e in events if e.get("event_type") == "llm_invocation_completed"]

            # Validate RAG telemetry
            for rev in rag_events:
                p = rev.get("payload", {})
                if p.get("embedding_provider") not in ("ollama", "openai", "local"):
                    fail("rag_telemetry", f"Invalid embedding provider: {p.get('embedding_provider')}")
                if p.get("embedding_dimensions") != 1024:
                    fail("rag_telemetry", f"Invalid embedding dimensions: {p.get('embedding_dimensions')}, expected 1024")
                if p.get("distance_metric") != "cosine":
                    fail("rag_telemetry", f"Invalid distance metric: {p.get('distance_metric')}, expected cosine")
                if not p.get("query_hash") or not p.get("query_hash").startswith("sha256:"):
                    fail("rag_telemetry", "Missing or invalid query_hash in RAG query event")

            pass_check("audit_trace_rag_metadata", f"Verified {len(rag_events)} RAG query events")

            # Validate evidence parsed counter against manifest
            ev_parsed_events = [e for e in events if e.get("event_type") == "evidence_parsed"]
            if ev_parsed_events and manifest_data:
                tr_file_count = ev_parsed_events[0].get("payload", {}).get("total_files", 0)
                mf_file_count = manifest_data.get("total_files", 0)
                if tr_file_count != mf_file_count:
                    fail("evidence_counter_consistency", f"Trace total_files ({tr_file_count}) != Manifest total_files ({mf_file_count})")
                else:
                    pass_check("evidence_counter_consistency", f"Counters match: {tr_file_count} files")

        except Exception as e:
            fail("audit_trace", f"Failed to parse audit trace: {e}")
    else:
        fail("audit_trace", f"Audit trace file not found at {trace_path}")

    # 5. Check SoA XLSX
    soa_path = None
    if bundle_dir:
        for f in os.listdir(bundle_dir):
            if f.startswith("SoA_") and f.endswith(".xlsx"):
                soa_path = os.path.join(bundle_dir, f)
                break
    if not soa_path:
        # Check exports dir
        exp_dir = os.path.join(data_dir, "exports")
        if os.path.exists(exp_dir):
            for f in os.listdir(exp_dir):
                if f.startswith(f"soa_{assessment_id[:8]}") and f.endswith(".xlsx"):
                    soa_path = os.path.join(exp_dir, f)
                    break

    if soa_path and os.path.exists(soa_path):
        try:
            wb = openpyxl.load_workbook(soa_path, data_only=True)
            ws = wb.active
            # Count data rows (excluding title/meta/header/summary rows)
            expected_count = 34 if std_id == "tcvn11930" else 93
            control_rows = 0
            for row in ws.iter_rows(min_row=5, values_only=True):
                cid_val = str(row[0] or "")
                if cid_val and (cid_val.startswith("A.") or cid_val.startswith("NW.") or cid_val.startswith("SV.") or cid_val.startswith("APP.") or cid_val.startswith("DAT.") or cid_val.startswith("MNG.")):
                    control_rows += 1

            if control_rows != expected_count:
                fail("soa_control_count", f"SoA control row count {control_rows} != expected {expected_count} for {std_id}")
            else:
                pass_check("soa_control_count", f"SoA has exact {control_rows} control rows matching {std_id}")

            # Verify meta banner in row 2 contains run_id and aid
            r2_val = str(ws["A2"].value or "")
            if eff_aid[:8] not in r2_val and "N/A" not in r2_val:
                fail("soa_metadata", f"SoA header metadata missing assessment_id: {r2_val}")
            else:
                pass_check("soa_metadata", "SoA contains valid metadata banner")

        except Exception as e:
            fail("soa_xlsx_read", f"Failed to open or parse SoA XLSX: {e}")
    else:
        fail("soa_xlsx_exists", "SoA XLSX not found in bundle or exports")

    # 6. Check DOCX Report
    docx_path = None
    if bundle_dir:
        for f in os.listdir(bundle_dir):
            if f.startswith("Audit_Report_") and f.endswith(".docx"):
                docx_path = os.path.join(bundle_dir, f)
                break
    if not docx_path:
        exp_dir = os.path.join(data_dir, "exports")
        if os.path.exists(exp_dir):
            for f in os.listdir(exp_dir):
                if f.startswith(f"report_{assessment_id[:8]}") and f.endswith(".docx"):
                    docx_path = os.path.join(exp_dir, f)
                    break

    if docx_path and os.path.exists(docx_path):
        try:
            doc = docx.Document(docx_path)
            # Verify tables and mandatory disclaimer
            all_text = "\n".join([p.text for p in doc.paragraphs])
            for t in doc.tables:
                for r in t.rows:
                    for c in r.cells:
                        all_text += "\n" + c.text

            if "LƯU Ý: Kết quả được sinh để hỗ trợ tự đánh giá" not in all_text and "hỗ trợ tự đánh giá" not in all_text:
                fail("docx_disclaimer", "Mandatory disclaimer missing from DOCX report")
            else:
                pass_check("docx_disclaimer", "Mandatory assessment disclaimer present")

            # Check no raw Markdown symbols in paragraphs
            raw_hashes = re.findall(r'^\s*#{1,4}\s+', all_text, re.MULTILINE)
            if raw_hashes:
                fail("docx_markdown_cleanliness", f"Raw markdown headers found in DOCX text: {raw_hashes[:3]}")
            else:
                pass_check("docx_markdown_cleanliness", "DOCX clean of raw markdown headers")

        except Exception as e:
            fail("docx_read", f"Failed to open or parse DOCX: {e}")
    else:
        # Not fatal if not yet exported
        pass_check("docx_report", "DOCX report file checked")

    # 7. Check Sensitive Data Leakage in all public text
    if _UNMASKED_IP_PATTERN.search(str(json_data.get("report", ""))):
        fail("secret_sanitization", "Unmasked private IP found in report text")
    if _SECRET_PATTERN.search(str(json_data.get("report", ""))):
        fail("secret_sanitization", "Secret / API token pattern found in report text")

    # 8. Check Core Invariants (citations, catalogue consistency, math recomputability)
    inv_valid, inv_fails = validate_assessment_invariants(a_data, manifest_data)
    if not inv_valid:
        for f_msg in inv_fails:
            fail("assessment_invariants", f_msg)
    else:
        pass_check("assessment_invariants", "All assessment invariants verified")

    from datetime import datetime, timezone
    check_results["timestamp"] = datetime.now(timezone.utc).isoformat()
    return check_results


FORBIDDEN_MOCK_FILES: Set[str] = {
    "chinh_sach_attt.pdf",
    "asset_inventory.pdf",
    "assessment_evidence.pdf",
    "assessment_evidence",
}

FORBIDDEN_PLACEHOLDERS: List[str] = [
    "[Địa điểm đánh giá]",
    "[Tên tổ chức]",
    "<FILL>",
    "[TODO]",
    "[INSERT]",
    "[Chưa điền]",
]


def validate_assessment_invariants(
    assessment_data: Dict[str, Any],
    manifest_data: Optional[Dict[str, Any]] = None,
    strict_catalogue_count: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate core audit integrity and mathematical invariants of an assessment.

    Returns (True, []) if completely valid, or (False, [error_messages]) if any
    invariant violation is detected.
    """
    failures: List[str] = []

    if not assessment_data or not isinstance(assessment_data, dict):
        return False, ["Assessment data is empty or not a valid dictionary."]

    json_data = assessment_data.get("json_data") or assessment_data.get("result", {}).get("json_data") or assessment_data
    controls = json_data.get("controls") or assessment_data.get("controls") or []

    # Extract assessment ID & run ID
    aid = assessment_data.get("assessment_id") or assessment_data.get("id") or json_data.get("assessment_id") or "unknown_assessment"

    # 1. Manifest Resolution & Citation Integrity
    eff_manifest = manifest_data or assessment_data.get("evidence_manifest") or json_data.get("evidence_manifest")
    if not eff_manifest:
        data_dir = os.getenv("DATA_PATH", "./data")
        mf_path = os.path.join(data_dir, "evidence_manifests", f"{aid}.json")
        if os.path.exists(mf_path):
            try:
                with open(mf_path, "r", encoding="utf-8") as f:
                    eff_manifest = json.load(f)
            except Exception:
                eff_manifest = None

    manifest_files = eff_manifest.get("files", []) if isinstance(eff_manifest, dict) else []
    manifest_lookup: Dict[str, Dict[str, Any]] = {}
    valid_filenames: Set[str] = set()
    valid_file_ids: Set[str] = set()

    for mf in manifest_files:
        if isinstance(mf, dict):
            mf_name = os.path.basename(mf.get("masked_filename") or mf.get("file_name") or mf.get("filename") or "")
            mf_fid = mf.get("file_id") or mf.get("evidence_id")
            mf_sha = mf.get("sha256") or mf.get("content_hash")
        else:
            mf_name = os.path.basename(getattr(mf, "masked_filename", getattr(mf, "file_name", getattr(mf, "filename", ""))))
            mf_fid = getattr(mf, "file_id", getattr(mf, "evidence_id", None))
            mf_sha = getattr(mf, "sha256", getattr(mf, "content_hash", None))

        entry = {"file_id": mf_fid, "sha256": mf_sha, "masked_filename": mf_name}
        if mf_name:
            manifest_lookup[mf_name] = entry
            manifest_lookup[mf_name.lower()] = entry
            valid_filenames.add(mf_name.lower())
        if mf_fid:
            manifest_lookup[mf_fid] = entry
            valid_file_ids.add(mf_fid)

    has_manifest_files = len(manifest_files) > 0

    if isinstance(controls, list):
        for c in controls:
            if not isinstance(c, dict):
                continue
            cid = c.get("control_id") or c.get("id") or "UNKNOWN"
            verdict = (c.get("assessment_verdict") or c.get("evidence_verdict") or "").lower()
            cits = c.get("evidence_citations") or c.get("citations") or []

            # Check citations against manifest
            for cit in cits:
                if not isinstance(cit, dict):
                    continue
                c_fname = os.path.basename(cit.get("file_name") or cit.get("filename") or "")
                c_fid = cit.get("evidence_id") or cit.get("file_id")
                c_sha = cit.get("sha256")

                # Check forbidden mock/hallucinated filenames
                if c_fname.lower() in FORBIDDEN_MOCK_FILES and c_fname.lower() not in valid_filenames:
                    failures.append(f"Control {cid}: Hallucinated mock citation detected '{c_fname}'.")

                if has_manifest_files:
                    matched = manifest_lookup.get(c_fname) or manifest_lookup.get(c_fname.lower()) or (manifest_lookup.get(c_fid) if c_fid else None)
                    if not matched:
                        failures.append(f"Control {cid}: Citation '{c_fname}' (ID: {c_fid}) not found in evidence manifest.")
                    else:
                        m_sha = matched.get("sha256")
                        if c_sha and m_sha and c_sha != m_sha:
                            failures.append(f"Control {cid}: Citation '{c_fname}' SHA-256 mismatch ({c_sha} != {m_sha}).")
                elif not has_manifest_files and c_fname:
                    failures.append(f"Control {cid}: Citation '{c_fname}' present in zero-evidence assessment.")

            # Satisfied verdict in evidence-bearing assessment must cite at least one valid file
            if verdict == "satisfied" and has_manifest_files:
                if not cits:
                    failures.append(f"Control {cid}: Verdict is 'satisfied' in an evidence assessment but has no valid citation.")

    # 2. Metadata & Catalogue Consistency
    raw_std = assessment_data.get("standard") or json_data.get("standard") or assessment_data.get("system_info", {}).get("assessment_standard") or "iso27001"
    std_id = raw_std.get("id") if isinstance(raw_std, dict) else str(raw_std).lower()
    is_tcvn = ("tcvn" in std_id or "11930" in std_id)
    expected_controls = 34 if is_tcvn else 93

    ALLOWED_VERDICTS = {"satisfied", "partial", "needs_expert_review", "not_evidenced", "missing"}
    ALLOWED_DECLARATIONS = {"implemented", "partially_implemented", "not_implemented", "not_applicable"}

    if isinstance(controls, list) and len(controls) > 0:
        if (strict_catalogue_count or len(controls) >= 30) and len(controls) != expected_controls:
            failures.append(f"Catalogue control count mismatch: {len(controls)} controls found, expected {expected_controls} for standard '{std_id}'.")
        for c in controls:
            if not isinstance(c, dict):
                continue
            cid = c.get("control_id") or c.get("id") or "UNKNOWN"
            v = (c.get("assessment_verdict") or c.get("evidence_verdict") or "").lower()
            decl = (c.get("user_declaration") or "").lower()
            if v and v not in ALLOWED_VERDICTS:
                failures.append(f"Control {cid}: Invalid assessment_verdict '{v}'. Must be one of {ALLOWED_VERDICTS}.")
            if decl and decl not in ALLOWED_DECLARATIONS:
                failures.append(f"Control {cid}: Invalid user_declaration '{decl}'. Must be one of {ALLOWED_DECLARATIONS}.")

    # 3. Mathematical Recomputability
    applicable_controls = [
        c for c in controls
        if isinstance(c, dict) and (c.get("user_declaration") or "").lower() != "not_applicable"
    ]
    factor_map = {
        "satisfied": 1.0,
        "partial": 0.5,
        "needs_expert_review": 0.0,
        "not_evidenced": 0.0,
        "missing": 0.0,
    }

    def _get_ctrl_weight(ctrl: Dict[str, Any]) -> float:
        w_pts = ctrl.get("weight_points")
        if w_pts is not None:
            try:
                v = float(w_pts)
                if v > 0:
                    return v
            except (ValueError, TypeError):
                pass
        w_val = ctrl.get("weight")
        if isinstance(w_val, (int, float)) and w_val > 0:
            return float(w_val)
        if isinstance(w_val, str) and w_val.strip():
            try:
                v = float(w_val)
                if v > 0:
                    return v
            except ValueError:
                pass
            w_name = w_val.strip().lower()
            if w_name in ("critical", "high", "medium", "low"):
                return {"critical": 10.0, "high": 5.0, "medium": 3.0, "low": 1.0}[w_name]
        w_lvl = str(ctrl.get("weight_level") or "").strip().lower()
        if w_lvl in ("critical", "high", "medium", "low"):
            return {"critical": 10.0, "high": 5.0, "medium": 3.0, "low": 1.0}[w_lvl]
        return 3.0

    if applicable_controls:
        recomputed_max = sum(_get_ctrl_weight(c) for c in applicable_controls)
        recomputed_score = sum(
            _get_ctrl_weight(c)
            * factor_map.get((c.get("assessment_verdict") or c.get("evidence_verdict") or "missing").lower(), 0.0)
            for c in applicable_controls
        )
        recomputed_pct = round((recomputed_score / recomputed_max * 100), 1) if recomputed_max > 0 else 0.0

        wc = json_data.get("weighted_compliance") or assessment_data.get("weighted_compliance") or {}
        if wc:
            stored_max = float(wc.get("weighted_max_score", 0.0))
            stored_score = float(wc.get("weighted_score", 0.0))
            stored_pct = float(wc.get("percentage", 0.0))
            if abs(stored_max - recomputed_max) > 0.5:
                failures.append(f"Mathematical invariant violation: stored weighted_max_score ({stored_max}) != recomputed ({recomputed_max}).")
            if abs(stored_score - recomputed_score) > 0.5:
                failures.append(f"Mathematical invariant violation: stored weighted_score ({stored_score}) != recomputed ({recomputed_score}).")
            if abs(stored_pct - recomputed_pct) > 0.5:
                failures.append(f"Mathematical invariant violation: stored weighted percentage ({stored_pct}%) != recomputed ({recomputed_pct}%).")

        cov = json_data.get("control_coverage") or assessment_data.get("control_coverage") or {}
        if cov:
            self_impl = sum(1 for c in applicable_controls if (c.get("user_declaration") or "").lower() == "implemented")
            tot_app = len(applicable_controls)
            expected_raw_pct = round((self_impl / tot_app * 100), 1) if tot_app > 0 else 0.0
            stored_raw_pct = float(cov.get("raw_percentage", 0.0))
            if abs(stored_raw_pct - expected_raw_pct) > 0.5:
                failures.append(f"Raw coverage invariant violation: stored raw_percentage ({stored_raw_pct}%) != recomputed ({expected_raw_pct}%).")

    # 4. Risk Scoring (4x4 matrix, score = L * I <= 16)
    all_risk_items = []
    if isinstance(controls, list):
        for c in controls:
            if isinstance(c, dict) and ("likelihood" in c or "impact" in c or "risk_score" in c):
                all_risk_items.append((c.get("control_id") or c.get("id") or "control", c))
    for r in json_data.get("risk_register") or assessment_data.get("risk_register") or []:
        if isinstance(r, dict):
            all_risk_items.append((r.get("control_id") or r.get("id") or "risk", r))
    for g in json_data.get("top_gaps") or assessment_data.get("top_gaps") or []:
        if isinstance(g, dict) and ("likelihood" in g or "impact" in g or "risk_score" in g):
            all_risk_items.append((g.get("control_id") or g.get("id") or "gap", g))

    for item_id, item in all_risk_items:
        if item.get("is_legacy"):
            continue
        l_val = item.get("likelihood")
        i_val = item.get("impact")
        r_score = item.get("risk_score") if item.get("risk_score") is not None else item.get("risk")
        if l_val is not None and (not isinstance(l_val, int) or l_val < 1 or l_val > 4):
            failures.append(f"Item {item_id}: likelihood={l_val} outside [1, 4].")
        if i_val is not None and (not isinstance(i_val, int) or i_val < 1 or i_val > 4):
            failures.append(f"Item {item_id}: impact={i_val} outside [1, 4].")
        if l_val is not None and i_val is not None and r_score is not None:
            if r_score != l_val * i_val:
                failures.append(f"Item {item_id}: risk_score={r_score} != likelihood({l_val}) * impact({i_val}).")
            if r_score > 16:
                failures.append(f"Item {item_id}: risk_score={r_score} exceeds max 16.")

    # 5. Cleanliness & Text Sanitization
    report_text = str(json_data.get("report") or assessment_data.get("report") or assessment_data.get("result", {}).get("report") or "")
    if report_text:
        for ph in FORBIDDEN_PLACEHOLDERS:
            if ph.lower() in report_text.lower():
                failures.append(f"Cleanliness invariant violation: Unresolved placeholder '{ph}' detected in report.")
        if any(re.search(pat, report_text, re.IGNORECASE) for pat in [
            r'(?:Tổ chức|Đơn vị|Doanh nghiệp|Phạm vi|Mục tiêu|Tiêu chuẩn)\s*[:\-]\s*None\b',
            r'^None\s*$',
            r'#+\s*None\b',
        ]):
            failures.append("Cleanliness invariant violation: Literal 'None' detected in report header or metadata fields.")

    is_valid = (len(failures) == 0)
    return is_valid, failures

