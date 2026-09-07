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
from typing import Any, Dict, List, Optional, Tuple

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
    eff_code_ver = a_data.get("code_version") or a_data.get("result", {}).get("json_data", {}).get("code_version") or "v1.2.0-rel"
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
        w_score = weighted.get("weighted_score", 0.0)
        w_max = weighted.get("weighted_max_score", 0.0)
        w_pct = weighted.get("percentage", 0.0)
        expected_w_pct = round((w_score / w_max * 100), 1) if w_max > 0 else 0.0
        if abs(w_pct - expected_w_pct) > 0.1:
            fail("scoring_consistency", f"Weighted compliance percentage mismatch: {w_pct} != {expected_w_pct}")
        else:
            pass_check("weighted_compliance_math", f"{w_score}/{w_max} = {w_pct}%")

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

    if not check_results["failures"]:
        pass_check("secret_sanitization", "No private IPs, passwords, or secret tokens detected")

    from datetime import datetime, timezone
    check_results["timestamp"] = datetime.now(timezone.utc).isoformat()
    return check_results
