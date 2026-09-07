"""Tests for assessment runtime resilience, error categorization, and background worker."""

import pytest
from unittest.mock import patch, MagicMock
from api.routes.iso27001 import SystemInfo, process_assessment_bg, load_assessment, save_assessment
from services.audit_service import AuditContext


def test_system_info_schema_flexibility():
    """SystemInfo schema accepts all frontend payload keys, numeric values for strings, and ignores extraneous metadata."""
    payload = {
        "assessment_standard": "tcvn11930",
        "org_name": "EVN Testing Corp",
        "org_size": "medium",
        "industry": "Năng lượng",
        "servers": 5,
        "firewalls": 2,  # Numeric firewall count from UI input
        "vpn": True,
        "cloud_provider": None,
        "antivirus": 1,
        "backup_solution": "Veeam",
        "siem": "Wazuh",
        "implemented_controls": ["A.5.1", "A.5.2"],
        "notes": "Testing notes",
        "model_mode": "local",
        "selected_model": "gemma4:latest",
        "assessment_scope": "full",
        "scope_description": "",
        "evidence_map": {"A.5.1": ["scan.log"]},
        "unknown_extra_field_from_future_ui": 12345,
    }
    info = SystemInfo(**payload)
    assert info.org_name == "EVN Testing Corp"
    assert info.firewalls == 2
    assert info.selected_model == "gemma4:latest"
    assert info.evidence_map == {"A.5.1": ["scan.log"]}


def test_process_assessment_bg_ollama_unavailable_categorization(tmp_path):
    """When Ollama connection fails, assessment transitions to 'failed' with error_code 'OLLAMA_UNAVAILABLE'."""
    aid = "test-fail-ollama-001"
    save_assessment(aid, {
        "id": aid,
        "status": "pending",
        "created_at": "2026-08-26T00:00:00Z"
    })

    with patch("services.chat_service.ChatService.assess_system", side_effect=Exception("[Ollama] Connection error: Connection refused")):
        process_assessment_bg(
            assessment_id=aid,
            system_data={"assessment_standard": "iso27001", "organization": {"name": "Test"}},
            model_mode="local",
            run_id="run_test001"
        )

    data = load_assessment(aid)
    assert data["status"] == "failed"
    assert data["error_code"] == "OLLAMA_UNAVAILABLE"
    assert "Connection refused" in data["error_summary"]


def test_process_assessment_bg_model_timeout_categorization(tmp_path):
    """When model inference times out, error_code is 'MODEL_TIMEOUT'."""
    aid = "test-fail-timeout-002"
    save_assessment(aid, {
        "id": aid,
        "status": "pending",
        "created_at": "2026-08-26T00:00:00Z"
    })

    with patch("services.chat_service.ChatService.assess_system", side_effect=Exception("Request timed out after 120s")):
        process_assessment_bg(
            assessment_id=aid,
            system_data={"assessment_standard": "iso27001", "organization": {"name": "Test"}},
            model_mode="local",
            run_id="run_test002"
        )

    data = load_assessment(aid)
    assert data["status"] == "failed"
    assert data["error_code"] == "MODEL_TIMEOUT"
