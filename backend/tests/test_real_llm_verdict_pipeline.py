"""Integration tests for real LLM verdict pipeline, schema enforcement, retry, and telemetry.

Tests:
1. LLM output conforming to {"control_verdicts": [...]}:
   A.5.1=satisfied (10pts), A.8.13=satisfied (10pts), A.8.20=satisfied (5pts), A.8.8=conflict->needs_expert_review (0pts).
   Weighted score = 25.0 / 495.0 = 5.1%, citations present, manifest summary not null,
   runtime_summary.total_duration_seconds == assessment_completed.total_duration_seconds.
2. Targeted single-control retry when candidate control with evidence is omitted in chunk output.
3. Fallback to needs_expert_review and audit event missing_control_verdict_from_llm if retry fails.
"""

import os
import json
import time
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from api.routes.iso27001 import load_assessment

client = TestClient(app, raise_server_exceptions=False)


def _extract_messages(args, kwargs):
    messages = kwargs.get("messages")
    if not messages:
        for a in args:
            if isinstance(a, list):
                messages = a
                break
    return messages or []


def test_real_llm_verdict_pipeline_schema_and_scoring(tmp_path):
    """Integration test simulating LLM returning {"control_verdicts": [...]} for:
    - A.5.1: satisfied (Critical, 10.0 pts)
    - A.8.13: satisfied (Critical, 10.0 pts)
    - A.8.20: satisfied (High, 5.0 pts)
    - A.8.8: conflict_detected -> needs_expert_review (High, 0.0 pts)
    Total points = 25.0 / 495.0 = 5.1%.
    Verify citations, raw verdicts, manifest summary, and duration alignment.
    """
    ev_map = {
        "A.5.1": ["chinh_sach_attt.pdf"],
        "A.8.13": ["backup_log.txt"],
        "A.8.20": ["network_diagram.png"],
        "A.8.8": ["patch_report.docx"],
    }
    implemented = ["A.5.1", "A.8.13", "A.8.20", "A.8.8"]

    chunk_verdicts_payload = json.dumps({
        "control_verdicts": [
            {
                "control_id": "A.5.1",
                "verdict": "satisfied",
                "rationale": "Chính sách an toàn thông tin được phê duyệt và ban hành định kỳ.",
                "citations": [
                    {
                        "evidence_id": "ev_a51",
                        "file_name": "chinh_sach_attt.pdf",
                        "excerpt": "Điều 1. Ban hành chính sách ATTT toàn công ty..."
                    }
                ],
                "severity": "critical",
                "likelihood": 1,
                "impact": 2,
                "risk": 2,
                "gap": "",
                "recommendation": "Duy trì rà soát hàng năm."
            },
            {
                "control_id": "A.8.13",
                "verdict": "satisfied",
                "rationale": "Quy trình sao lưu dự phòng tự động hoạt động hàng ngày và có biên bản diễn tập.",
                "citations": [
                    {
                        "evidence_id": "ev_a813",
                        "file_name": "backup_log.txt",
                        "excerpt": "Daily snapshot completed with status SUCCESS at 02:00."
                    }
                ],
                "severity": "critical",
                "likelihood": 1,
                "impact": 2,
                "risk": 2,
                "gap": "",
                "recommendation": "Duy trì giám sát sao lưu định kỳ."
            },
            {
                "control_id": "A.8.20",
                "verdict": "satisfied",
                "rationale": "Mạng được phân vùng hợp lý giữa khu vực DMZ và mạng người dùng nội bộ.",
                "citations": [
                    {
                        "evidence_id": "ev_a820",
                        "file_name": "network_diagram.png",
                        "excerpt": "Segmentation boundary configured between DMZ and LAN."
                    }
                ],
                "severity": "high",
                "likelihood": 1,
                "impact": 1,
                "risk": 1,
                "gap": "",
                "recommendation": "Kiểm tra luật firewall định kỳ."
            },
            {
                "control_id": "A.8.8",
                "verdict": "missing",
                "conflict_detected": True,
                "conflict_reason": "Tự kê khai là implemented nhưng bằng chứng kỹ thuật không có bản vá cho CVE trọng yếu.",
                "rationale": "Báo cáo cho thấy hệ thống còn tồn tại 3 lỗ hổng Critical chưa vá.",
                "citations": [
                    {
                        "evidence_id": "ev_a88",
                        "file_name": "patch_report.docx",
                        "excerpt": "3 Critical CVEs remain unpatched on production database."
                    }
                ],
                "severity": "high",
                "likelihood": 3,
                "impact": 3,
                "risk": 9,
                "gap": "Chưa hoàn tất vá lỗ hổng nghiêm trọng.",
                "recommendation": "Khẩn trương cập nhật bản vá trong vòng 7 ngày."
            }
        ]
    })

    def mock_ollama_call(*args, **kwargs):
        messages = _extract_messages(args, kwargs)
        content_str = messages[-1].get("content", "") if messages else ""
        if "FORMATTING ENGINE" in content_str or "EXECUTIVE SUMMARY" in content_str:
            return {
                "content": "## 1. TỔNG QUAN\nBáo cáo IT Audit.\n## 5. EXECUTIVE SUMMARY\nTổng quan tuân thủ.",
                "model": "gemma:latest",
                "provider": "ollama",
                "tokens": 200,
            }
        return {
            "content": chunk_verdicts_payload,
            "model": "qwen2.5-coder:7b",
            "provider": "ollama",
            "tokens": 400,
        }

    assess_payload = {
        "assessment_standard": "iso27001",
        "org_name": "Công ty TNHH Thẩm định An toàn Số",
        "implemented_controls": implemented,
        "evidence_map": ev_map,
        "model_mode": "local",
    }

    with patch("services.chat_service.CloudLLMService._call_ollama", side_effect=mock_ollama_call), \
         patch("services.cloud_llm_service.CloudLLMService._call_ollama", side_effect=mock_ollama_call), \
         patch("repositories.vector_store.VectorStore.search", return_value=[]):
        resp = client.post("/api/iso27001/assess", json=assess_payload)

    assert resp.status_code == 200, resp.text
    aid = resp.json()["id"]

    record = load_assessment(aid)
    assert record is not None
    assert record["status"] == "completed"

    json_data = record["json_data"]
    controls = json_data["controls"]
    c_map = {c["control_id"]: c for c in controls}

    # 1. Per-control verdicts check
    assert c_map["A.5.1"]["assessment_verdict"] == "satisfied"
    assert c_map["A.5.1"]["ai_verdict_raw"] == "satisfied"
    assert c_map["A.5.1"]["normalized_ai_verdict"] == "satisfied"
    assert len(c_map["A.5.1"]["evidence_citations"]) >= 1
    assert c_map["A.5.1"]["evidence_citations"][0]["file_name"] == "chinh_sach_attt.pdf"

    assert c_map["A.8.13"]["assessment_verdict"] == "satisfied"
    assert c_map["A.8.13"]["ai_verdict_raw"] == "satisfied"
    assert c_map["A.8.13"]["normalized_ai_verdict"] == "satisfied"
    assert c_map["A.8.13"]["evidence_citations"][0]["file_name"] == "backup_log.txt"

    assert c_map["A.8.20"]["assessment_verdict"] == "satisfied"
    assert c_map["A.8.20"]["ai_verdict_raw"] == "satisfied"
    assert c_map["A.8.20"]["normalized_ai_verdict"] == "satisfied"

    # A.8.8 conflict branch check: conflict_detected -> needs_expert_review
    assert c_map["A.8.8"]["assessment_verdict"] == "needs_expert_review"
    assert c_map["A.8.8"]["verdict_source"] == "safe_fallback_conflict"

    # 2. Weighted score verification
    # A.5.1 (Critical=10 * 1.0 = 10.0)
    # A.8.13 (Critical=10 * 1.0 = 10.0)
    # A.8.20 (Critical=10 * 1.0 = 10.0)
    # A.8.8 (High=5 * 0.0 = 0.0)
    # Total score = 30.0, Max = 495.0, Percentage = 6.1%
    w_comp = json_data["weighted_compliance"]
    assert w_comp["weighted_score"] == 30.0
    assert w_comp["weighted_max_score"] == 495.0
    assert w_comp["percentage"] == 6.1

    # 3. Telemetry and Manifest verification
    manifest_id = json_data.get("evidence_manifest_id")
    assert manifest_id is not None and len(manifest_id) > 0
    assert record.get("evidence_manifest_id") == manifest_id

    manifest = json_data.get("evidence_manifest")
    assert manifest is not None
    assert isinstance(manifest, dict)
    assert manifest.get("manifest_id") == manifest_id
    assert manifest.get("total_files") >= 4
    assert "control_mapping" in manifest

    # Total duration consistency
    rt_summary = json_data.get("runtime_summary") or {}
    assert "total_duration_seconds" in rt_summary
    assert "phase1_candidate_duration_seconds" in rt_summary
    assert "candidate_llm_calls" in rt_summary
    assert "number_of_llm_calls" in rt_summary

    # Audit trace check: read trace from file
    trace_path = os.path.join(os.getenv("DATA_PATH", "./data"), "audit_traces", f"{aid}.json")
    assert os.path.exists(trace_path), f"Audit trace missing at {trace_path}"
    with open(trace_path, "r", encoding="utf-8") as tf:
        trace_data = json.load(tf)

    completed_events = [e for e in trace_data.get("events", []) if e.get("event_type") == "assessment_completed"]
    assert len(completed_events) == 1
    completed_dur = completed_events[0]["payload"]["total_duration_seconds"]
    assert completed_dur == rt_summary["total_duration_seconds"], (
        f"runtime_summary.total_duration_seconds ({rt_summary['total_duration_seconds']}) != "
        f"assessment_completed.total_duration_seconds ({completed_dur})"
    )


def test_targeted_retry_on_missing_candidate_control():
    """Test targeted single-control retry:
    Chunk output yields A.5.1 but omits candidate A.5.9 (which has evidence).
    The pipeline must launch a targeted retry for A.5.9 with mapped evidence.
    If retry yields A.5.9 verdict, it must be successfully merged.
    """
    ev_map = {
        "A.5.1": ["policy.pdf"],
        "A.5.9": ["asset_inventory.xlsx"],
    }
    implemented = ["A.5.1", "A.5.9"]

    retry_called = []

    def mock_ollama_call(*args, **kwargs):
        messages = _extract_messages(args, kwargs)
        content_str = messages[-1].get("content", "") if messages else ""

        if "A.5.9" in content_str and ("BẮT BUỘC" in content_str or "Control ID: A.5.9" in content_str):
            retry_called.append("retry_A.5.9")
            return {
                "content": json.dumps({
                    "control_verdicts": [
                        {
                            "control_id": "A.5.9",
                            "verdict": "satisfied",
                            "rationale": "Danh mục tài sản thông tin đã được kiểm kê đầy đủ qua file Excel.",
                            "citations": [{"file_name": "asset_inventory.xlsx", "excerpt": "Sheet Assets: 150 servers listed."}]
                        }
                    ]
                }),
                "model": "qwen2.5-coder:7b",
                "provider": "ollama",
                "tokens": 200,
            }
        if "FORMATTING ENGINE" in content_str:
            return {"content": "## Report", "model": "gemma", "provider": "ollama", "tokens": 100}

        # Initial chunk response: returns A.5.1 but OMITS A.5.9
        return {
            "content": json.dumps({
                "control_verdicts": [
                    {
                        "control_id": "A.5.1",
                        "verdict": "satisfied",
                        "rationale": "Chính sách đầy đủ.",
                        "citations": [{"file_name": "policy.pdf"}]
                    }
                ]
            }),
            "model": "qwen2.5-coder:7b",
            "provider": "ollama",
            "tokens": 250,
        }

    assess_payload = {
        "assessment_standard": "iso27001",
        "org_name": "Retry Verification Org",
        "implemented_controls": implemented,
        "evidence_map": ev_map,
        "model_mode": "local",
    }

    with patch("services.chat_service.CloudLLMService._call_ollama", side_effect=mock_ollama_call), \
         patch("services.cloud_llm_service.CloudLLMService._call_ollama", side_effect=mock_ollama_call), \
         patch("repositories.vector_store.VectorStore.search", return_value=[]):
        resp = client.post("/api/iso27001/assess", json=assess_payload)

    assert resp.status_code == 200
    aid = resp.json()["id"]

    assert len(retry_called) >= 1, "Targeted retry was NOT invoked for missing control A.5.9"

    record = load_assessment(aid)
    controls = {c["control_id"]: c for c in record["json_data"]["controls"]}

    # A.5.9 should be recovered as satisfied via retry
    assert controls["A.5.9"]["assessment_verdict"] == "satisfied"
    assert controls["A.5.9"]["ai_verdict_raw"] == "satisfied"


def test_missing_control_audit_event_when_retry_fails():
    """Test fallback and audit logging when targeted retry also fails to return candidate verdict:
    - Control falls back to needs_expert_review
    - verdict_source is missing_control_verdict_from_llm
    - Audit trace logs missing_control_verdict_from_llm event with raw_response_hash and reason.
    """
    ev_map = {
        "A.5.10": ["unreadable_scan.bin"],
    }
    implemented = ["A.5.10"]

    def mock_ollama_call(*args, **kwargs):
        messages = _extract_messages(args, kwargs)
        content_str = messages[-1].get("content", "") if messages else ""
        if "FORMATTING ENGINE" in content_str:
            return {"content": "## Report", "model": "gemma", "provider": "ollama", "tokens": 100}
        # Returns empty list for both initial chunk and retry
        return {
            "content": "{\"control_verdicts\": []}",
            "model": "qwen2.5-coder:7b",
            "provider": "ollama",
            "tokens": 50,
        }

    assess_payload = {
        "assessment_standard": "iso27001",
        "org_name": "Audit Missing Org",
        "implemented_controls": implemented,
        "evidence_map": ev_map,
        "model_mode": "local",
    }

    with patch("services.chat_service.CloudLLMService._call_ollama", side_effect=mock_ollama_call), \
         patch("services.cloud_llm_service.CloudLLMService._call_ollama", side_effect=mock_ollama_call), \
         patch("repositories.vector_store.VectorStore.search", return_value=[]):
        resp = client.post("/api/iso27001/assess", json=assess_payload)

    assert resp.status_code == 200
    aid = resp.json()["id"]

    record = load_assessment(aid)
    controls = {c["control_id"]: c for c in record["json_data"]["controls"]}

    assert controls["A.5.10"]["assessment_verdict"] == "needs_expert_review"
    assert controls["A.5.10"]["verdict_source"] == "missing_control_verdict_from_llm"

    # Check Audit trace for missing_control_verdict_from_llm
    trace_path = os.path.join(os.getenv("DATA_PATH", "./data"), "audit_traces", f"{aid}.json")
    assert os.path.exists(trace_path)
    with open(trace_path, "r", encoding="utf-8") as tf:
        trace_data = json.load(tf)

    missing_events = [
        e for e in trace_data.get("events", [])
        if e.get("event_type") == "missing_control_verdict_from_llm"
    ]
    assert len(missing_events) >= 1
    ev_detail = missing_events[0]["payload"]
    assert ev_detail["control_id"] == "A.5.10"
    assert "raw_response_hash" in ev_detail
    assert "parse_or_drop_reason" in ev_detail
    assert ev_detail["fallback_verdict"] == "needs_expert_review"
