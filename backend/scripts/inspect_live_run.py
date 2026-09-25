import json
import os

aid = "42678bba-13b1-4e9b-b869-de7638781e8e"
asm_path = f"/data/assessments/{aid}.json"
trace_path = f"/data/audit_traces/{aid}.json"

with open(asm_path, encoding="utf-8") as f:
    data = json.load(f)

print("=== LIVE ASSESSMENT AUDIT REPORT ===")
print("Assessment ID:", data.get("id"))
print("Run ID:", data.get("run_id"))
print("Code Version:", data.get("code_version"))
print("Status:", data.get("status"))

json_data = data.get("json_data", {})
raw_ctrls = json_data.get("controls", [])
if raw_ctrls:
    print("Sample control keys:", list(raw_ctrls[0].keys()))
controls = {(c.get("control_id") or c.get("id")): c for c in raw_ctrls if (c.get("control_id") or c.get("id"))}

print("\n--- TARGET CONTROLS AUDIT ---")
target_cids = ["A.5.1", "A.5.9", "A.5.10", "A.8.4", "A.8.8", "A.8.13", "A.8.15", "A.8.20"]
for cid in target_cids:
    c = controls.get(cid, {})
    v = c.get("assessment_verdict")
    raw_v = c.get("ai_verdict_raw")
    norm_v = c.get("normalized_ai_verdict")
    src = c.get("verdict_source")
    cits = c.get("evidence_citations", [])
    rat = c.get("verdict_rationale") or ""
    conf = c.get("conflict_detected", False)
    print(f"Control {cid:6s} | Verdict: {str(v):20s} | Raw: {str(raw_v):12s} | Norm: {str(norm_v):12s} | Src: {str(src):25s} | Cits: {len(cits)} | Conflict: {conf} | Rationale: {rat[:50]}")

print("\n--- TELEMETRY AUDIT ---")
rt = json_data.get("runtime_summary", {})
print("runtime_summary.total_duration_seconds:", rt.get("total_duration_seconds"))
print("runtime_summary.phase1_candidate_duration_seconds:", rt.get("phase1_candidate_duration_seconds"))
print("runtime_summary.candidate_llm_calls:", rt.get("candidate_llm_calls"))
print("runtime_summary.number_of_llm_calls:", rt.get("number_of_llm_calls"))
print("runtime_summary.average_seconds_per_control:", rt.get("average_seconds_per_control"))

print("\n--- MANIFEST AUDIT ---")
print("evidence_manifest_id:", json_data.get("evidence_manifest_id"))
manifest = json_data.get("evidence_manifest")
print("evidence_manifest is None?:", manifest is None)
if manifest:
    print("manifest_id:", manifest.get("manifest_id"))
    print("total_files:", manifest.get("total_files"))
    print("files count:", len(manifest.get("files", [])))
    print("control_mapping count:", len(manifest.get("control_mapping", {})))

print("\n--- SCORING AUDIT ---")
w_comp = json_data.get("weighted_compliance", {})
print("weighted_score:", w_comp.get("weighted_score"))
print("weighted_max_score:", w_comp.get("weighted_max_score"))
print("percentage:", w_comp.get("percentage"))

# Audit trace verification
with open(trace_path, encoding="utf-8") as tf:
    trace = json.load(tf)

events = trace.get("events", [])
print("\n--- AUDIT TRACE VERIFICATION ---")
print("Total audit events:", len(events))
comp_events = [e for e in events if e.get("event_type") == "assessment_completed"]
if comp_events:
    trace_dur = comp_events[0].get("payload", {}).get("total_duration_seconds")
    print("assessment_completed.total_duration_seconds in trace:", trace_dur)
    print("Duration equality check (trace == runtime_summary):", trace_dur == rt.get("total_duration_seconds"))

json_valid_events = [e for e in events if e.get("event_type") == "json_validation_checked"]
print(f"\nChunk JSON validation events ({len(json_valid_events)}):")
for jv in json_valid_events:
    p = jv.get("payload", {})
    print(f"  Phase {jv.get('phase')}: valid={p.get('output_schema_valid')}, items_count={p.get('items_count')}")

missing_events = [e for e in events if e.get("event_type") == "missing_control_verdict_from_llm"]
print(f"\nMissing control verdict events ({len(missing_events)}):")
for me in missing_events:
    p = me.get("payload", {})
    print(f"  Control {p.get('control_id')}: reason={p.get('parse_or_drop_reason')}, raw_hash={p.get('raw_response_hash')}")
