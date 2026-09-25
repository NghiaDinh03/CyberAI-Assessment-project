"""Run a live assessment against the running backend with actual evidence files and live Ollama models.
Outputs detailed audit evidence, checks per-control verdicts, citations, telemetry, and manifest summary.
"""

import sys
import json
import time
import requests

BACKEND_URL = "http://127.0.0.1:8000"

payload = {
    "assessment_standard": "iso27001",
    "evidence_manifest_id": f"manifest_live_{int(time.time())}",
    "evidence_files": [
        {
            "filename": "20260922_180520_asset_inventory_redacted.csv",
            "size_bytes": 897,
            "sha256": "70e63f2298449d25e6547022fe331df4398903190908152ec13df0e6dc1abbdc",
            "ocr_applied": False,
            "mapped_controls": ["A.5.9", "A.5.10"]
        }
    ],
    "organization": {
        "name": "Live Assessment Corp",
        "size": "small",
        "industry": "Công nghệ",
        "employees": 50,
        "it_staff": 1
    },
    "infrastructure": {
        "servers": 11,
        "firewalls": "Sophos",
        "vpn": "Có",
        "cloud": "Không sử dụng",
        "antivirus": "Trellix",
        "backup": "Không có",
        "siem": "Elastic",
        "network_diagram": "Không cung cấp"
    },
    "compliance": {
        "iso_status": "Đang triển khai",
        "implemented_controls": [
            "A.5.1",
            "A.8.4",
            "A.8.8",
            "A.8.13",
            "A.8.15",
            "A.8.20",
            "A.5.9",
            "A.5.10"
        ],
        "evidence_map": {
            "A.5.1": ["20260922_180346_A.5.1_Information_Security_Policy.docx"],
            "A.8.4": ["20260922_180404_A.8.4_Soa_Justification_Not_Applicable.pdf"],
            "A.8.8": ["20260922_180418_A.8.8_Vulnerability_Management_Conflict.log"],
            "A.8.13": ["20260922_180430_A.8.13_Backup_Recovery_Review.txt"],
            "A.8.15": ["20260922_180444_A.8.15_No_Evidence_Case.md"],
            "A.8.20": ["20260922_180509_A.8.20_Firewall_Status_Screenshot.png"],
            "A.5.9": ["20260922_180520_asset_inventory_redacted.csv"],
            "A.5.10": ["20260922_180520_asset_inventory_redacted.csv"]
        }
    },
    "implemented_controls": [
        "A.5.1",
        "A.8.4",
        "A.8.8",
        "A.8.13",
        "A.8.15",
        "A.8.20",
        "A.5.9",
        "A.5.10"
    ],
    "evidence_map": {
        "A.5.1": ["20260922_180346_A.5.1_Information_Security_Policy.docx"],
        "A.8.4": ["20260922_180404_A.8.4_Soa_Justification_Not_Applicable.pdf"],
        "A.8.8": ["20260922_180418_A.8.8_Vulnerability_Management_Conflict.log"],
        "A.8.13": ["20260922_180430_A.8.13_Backup_Recovery_Review.txt"],
        "A.8.15": ["20260922_180444_A.8.15_No_Evidence_Case.md"],
        "A.8.20": ["20260922_180509_A.8.20_Firewall_Status_Screenshot.png"],
        "A.5.9": ["20260922_180520_asset_inventory_redacted.csv"],
        "A.5.10": ["20260922_180520_asset_inventory_redacted.csv"]
    },
    "notes": (
        "BẰNG CHỨNG ĐÃ CUNG CẤP CHO CÁC CONTROLS:\n"
        "  A.5.1: [1 file] — 20260922_180346_A.5.1_Information_Security_Policy.docx\n"
        "  A.8.4: [1 file] — 20260922_180404_A.8.4_Soa_Justification_Not_Applicable.pdf\n"
        "  A.8.8: [1 file] — 20260922_180418_A.8.8_Vulnerability_Management_Conflict.log\n"
        "  A.8.13: [1 file] — 20260922_180430_A.8.13_Backup_Recovery_Review.txt\n"
        "  A.8.15: [1 file] — 20260922_180444_A.8.15_No_Evidence_Case.md\n"
        "  A.8.20: [1 file] — 20260922_180509_A.8.20_Firewall_Status_Screenshot.png\n"
        "  A.5.9: [1 file] — 20260922_180520_asset_inventory_redacted.csv\n"
        "  A.5.10: [1 file] — 20260922_180520_asset_inventory_redacted.csv"
    ),
    "model_mode": "local",
    "selected_model": "gemma4:latest"
}

def main():
    print("=== STARTING LIVE ASSESSMENT ===")
    start_resp = requests.post(f"{BACKEND_URL}/api/iso27001/assess", json=payload, timeout=30)
    if start_resp.status_code != 200:
        print(f"FAILED to start assessment: {start_resp.status_code} {start_resp.text}")
        sys.exit(1)

    init_data = start_resp.json()
    aid = init_data["id"]
    run_id = init_data.get("run_id")
    print(f"Assessment started: id={aid}, initial run_id={run_id}")

    # Poll until completed
    max_wait = 900
    t0 = time.time()
    completed_data = None
    while time.time() - t0 < max_wait:
        poll_resp = requests.get(f"{BACKEND_URL}/api/iso27001/assessments/{aid}", timeout=10)
        if poll_resp.status_code == 200:
            doc = poll_resp.json()
            status = doc.get("status")
            progress = doc.get("progress", {})
            pct = progress.get("percent", 0)
            msg = progress.get("message", "")
            print(f"[{int(time.time()-t0)}s] Status: {status} ({pct}%) - {msg[:60]}")
            if status in ("completed", "failed"):
                completed_data = doc
                break
        time.sleep(3)

    if not completed_data or completed_data.get("status") != "completed":
        print(f"ERROR: Assessment did not complete successfully. Status: {completed_data.get('status') if completed_data else 'timeout'}")
        if completed_data:
            print("Error details:", completed_data.get("error"))
        sys.exit(1)

    print("\n=== LIVE ASSESSMENT COMPLETED SUCCESSFULLY ===")
    final_run_id = completed_data.get("run_id")
    print(f"Assessment ID: {aid}")
    print(f"Run ID: {final_run_id}")

    json_data = completed_data.get("json_data", {})
    controls = {c["control_id"]: c for c in json_data.get("controls", [])}

    print("\n--- PER-CONTROL VERDICTS AUDIT ---")
    target_cids = ["A.5.1", "A.5.9", "A.5.10", "A.8.4", "A.8.8", "A.8.13", "A.8.15", "A.8.20"]
    for cid in target_cids:
        c = controls.get(cid, {})
        v = c.get("assessment_verdict")
        raw_v = c.get("ai_verdict_raw")
        norm_v = c.get("normalized_ai_verdict")
        src = c.get("verdict_source")
        cits = c.get("evidence_citations", [])
        rat = c.get("verdict_rationale") or ""
        print(f"Control {cid:6s} | Verdict: {str(v):18s} | Raw: {str(raw_v):10s} | Norm: {str(norm_v):10s} | Source: {str(src):25s} | Citations: {len(cits)} | Rationale: {rat[:40]}")

    print("\n--- TELEMETRY AUDIT ---")
    rt = json_data.get("runtime_summary", {})
    print("runtime_summary.total_duration_seconds:", rt.get("total_duration_seconds"))
    print("runtime_summary.phase1_candidate_duration_seconds:", rt.get("phase1_candidate_duration_seconds"))
    print("runtime_summary.candidate_llm_calls:", rt.get("candidate_llm_calls"))
    print("runtime_summary.number_of_llm_calls:", rt.get("number_of_llm_calls"))

    # Check evidence manifest summary
    man_id = json_data.get("evidence_manifest_id")
    man = json_data.get("evidence_manifest")
    print("\nevidence_manifest_id:", man_id)
    print("evidence_manifest is not None:", man is not None)
    if man:
        print("evidence_manifest keys:", list(man.keys()))
        print("evidence_manifest total_files:", man.get("total_files"))
        print("evidence_manifest mapped controls count:", len(man.get("control_mapping", {})))

    # Fetch audit trace
    trace_resp = requests.get(f"{BACKEND_URL}/api/iso27001/audit-trace/{aid}", timeout=10)
    if trace_resp.status_code == 200:
        trace_data = trace_resp.json()
        print("\n--- AUDIT TRACE EVENTS SUMMARY ---")
        events = trace_data.get("events", [])
        event_types = [e.get("event_type") for e in events]
        print(f"Total audit events: {len(events)}")
        print("Unique event types:", sorted(set(event_types)))

        comp_events = [e for e in events if e.get("event_type") == "assessment_completed"]
        if comp_events:
            dur_trace = comp_events[0].get("payload", {}).get("total_duration_seconds")
            print(f"assessment_completed.total_duration_seconds: {dur_trace}")
            print(f"Duration equality check: {dur_trace == rt.get('total_duration_seconds')}")

        json_valid_events = [e for e in events if e.get("event_type") == "json_validation_checked"]
        print(f"\nChunk JSON validation events: {len(json_valid_events)}")
        for jv in json_valid_events:
            p = jv.get("payload", {})
            print(f"  Phase {jv.get('phase', '')}: valid={p.get('output_schema_valid')}, items_count={p.get('items_count')}")

        missing_ctrl_events = [e for e in events if e.get("event_type") == "missing_control_verdict_from_llm"]
        print(f"\nMissing control verdict events: {len(missing_ctrl_events)}")
        for mce in missing_ctrl_events:
            p = mce.get("payload", {})
            print(f"  Control {p.get('control_id')}: reason={p.get('parse_or_drop_reason')}, raw_hash={p.get('raw_response_hash')}")

if __name__ == "__main__":
    main()
