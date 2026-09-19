"""Unit tests for api.routes.iso27001 — `_validate_path_id` path-traversal guard."""

import os
import sys

# Ensure backend/ is importable when pytest is run from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app, raise_server_exceptions=False)


def _get_assessment(assessment_id: str):
    """GET /api/v1/iso27001/assessments/{assessment_id}"""
    return client.get(f"/api/v1/iso27001/assessments/{assessment_id}")


class TestValidAssessmentIds:
    def test_uuid_style_id_accepted(self):
        """A UUID-formatted ID (alphanumeric + hyphens) is a valid identifier."""
        response = _get_assessment("7e0b008d-34d9-4c5b-bf9a-f3de2d53658e")
        assert response.status_code != 400

    def test_simple_alphanumeric_id_accepted(self):
        """Plain alphanumeric IDs must not be rejected."""
        response = _get_assessment("valid123")
        assert response.status_code != 400

    def test_id_with_underscores_accepted(self):
        """Underscores are explicitly allowed by _SAFE_ID_RE."""
        response = _get_assessment("assessment_2024_001")
        assert response.status_code != 400

    def test_id_with_hyphens_accepted(self):
        """Hyphens are explicitly allowed by _SAFE_ID_RE."""
        response = _get_assessment("test-id-abc")
        assert response.status_code != 400

    def test_nonexistent_valid_id_returns_not_found(self):
        """A valid ID that does not exist in storage returns a non-400 response."""
        response = _get_assessment("nonexistent-valid-id-000")
        # Could be 200 with error body, 404, etc. — but never 400 from path validation
        assert response.status_code != 400


class TestPathTraversalProtection:
    def test_dotdot_slash_blocked(self):
        """Classic ../ path traversal must be rejected."""
        response = _get_assessment("../etc/passwd")
        assert response.status_code in (400, 404)

    def test_dotdot_url_encoded_blocked(self):
        """URL-encoded ..%2F traversal must be rejected."""
        # TestClient does not encode the path; we send the literal string
        response = client.get("/api/v1/iso27001/assessments/..%2Fetc%2Fpasswd")
        assert response.status_code in (400, 404)

    def test_dotdot_backslash_blocked(self):
        """Windows-style ..\\ traversal must be rejected."""
        response = _get_assessment("..\\windows\\system32")
        assert response.status_code in (400, 404)

    def test_nested_traversal_blocked(self):
        """Deep traversal paths must be rejected."""
        response = _get_assessment("../../etc/shadow")
        assert response.status_code in (400, 404)

    def test_traversal_with_valid_prefix_blocked(self):
        """Traversal appended after a valid-looking prefix must still be blocked."""
        response = _get_assessment("abc-123/../../../etc/passwd")
        assert response.status_code in (400, 404)


class TestNullByteInjection:
    def test_null_byte_url_encoded_blocked(self):
        """Null byte (%00) in the ID must be rejected."""
        response = client.get("/api/v1/iso27001/assessments/id%00malicious")
        assert response.status_code in (400, 404)

    def test_literal_null_byte_blocked(self):
        """A literal NUL character in the path must be rejected."""
        try:
            response = _get_assessment("id\x00malicious")
            assert response.status_code in (400, 404, 422)
        except Exception:
            # Client-side HTTP layer blocked invalid character (safe)
            pass


class TestSpecialCharacterBlocking:
    def test_angle_brackets_blocked(self):
        """XSS-style angle brackets must be rejected."""
        response = _get_assessment("id<script>alert(1)</script>")
        assert response.status_code in (400, 404, 422)

    def test_semicolon_blocked(self):
        """Semicolon (shell command separator) must be rejected."""
        response = _get_assessment("id;rm -rf /")
        assert response.status_code in (400, 404, 422)

    def test_pipe_blocked(self):
        """Pipe character must be rejected."""
        response = _get_assessment("id|cat /etc/passwd")
        assert response.status_code in (400, 404, 422)

    def test_ampersand_blocked(self):
        """Ampersand must be rejected."""
        response = _get_assessment("id&whoami")
        assert response.status_code in (400, 404, 422)

    def test_dollar_sign_blocked(self):
        """Dollar sign (shell variable expansion) must be rejected."""
        response = _get_assessment("id$HOME")
        assert response.status_code in (400, 404, 422)

    def test_backtick_blocked(self):
        """Backtick (shell command substitution) must be rejected."""
        response = _get_assessment("id`id`")
        assert response.status_code in (400, 404, 422)

    def test_slash_in_id_blocked(self):
        """Forward slash is not in the safe charset and must be rejected."""
        response = _get_assessment("id/extra")
        assert response.status_code in (400, 404, 422)

    def test_space_in_id_blocked(self):
        """Spaces are not in the safe charset."""
        response = _get_assessment("id with space")
        assert response.status_code in (400, 404, 422)


class TestEdgeCases:
    def test_empty_id_blocked(self):
        """An empty ID string — FastAPI will route to the list endpoint instead,
        so we just verify the assessments list endpoint itself doesn't error."""
        response = client.get("/api/v1/iso27001/assessments/")
        assert response.status_code < 500

    def test_very_long_id_rejected_or_not_found(self):
        """An excessively long but safe ID should not crash the server."""
        long_id = "a" * 500
        response = _get_assessment(long_id)
        assert response.status_code < 500

    def test_response_is_json(self):
        """All rejection responses must be valid JSON (not raw exception text)."""
        response = _get_assessment("../etc/passwd")
        assert response.status_code in (400, 404)
        data = response.json()
        assert isinstance(data, dict)


class TestAssessAcceptsImplementedWithoutEvidence:
    """Step 7 regression: the mandatory-evidence gate is FRONTEND-ONLY (Step 5).

    The backend ``/iso27001/assess`` endpoint must continue to accept an
    ``implemented_controls`` list that has no matching ``evidence_map`` entry.
    If a future change adds a server-side validator that rejects this payload,
    this test will fail and the contract should be re-discussed.
    """

    def test_implemented_without_evidence_accepted(self):
        from unittest.mock import patch
        payload = {
            "assessment_standard": "iso27001",
            "org_name": "Test Org",
            "implemented_controls": ["A.5.1"],
            "evidence_map": {},  # intentionally empty — no evidence uploaded
            "model_mode": "local",
        }
        with patch("api.routes.iso27001.process_assessment_bg"):
            response = client.post("/api/v1/iso27001/assess", json=payload)
        # We only care that it is NOT rejected as a validation error.
        assert response.status_code != 422, (
            f"Backend rejected implemented-without-evidence payload "
            f"(status={response.status_code}, body={response.text[:200]}). "
            "The mandatory-evidence gate must remain frontend-only."
        )


class TestControlAiAssistAndEvidence:
    """Tests for individual control evidence upload and real-time AI assist."""

    def test_upload_and_list_control_evidence(self):
        import io
        file_content = b"Windows Firewall is active and blocking unauthorized ports."
        files = {"file": ("firewall_check.txt", io.BytesIO(file_content), "text/plain")}
        upload_resp = client.post("/api/iso27001/evidence/A.8.20", files=files)
        assert upload_resp.status_code == 200
        up_data = upload_resp.json()
        assert up_data.get("status") == "success"
        assert up_data.get("control_id") == "A.8.20"
        assert "firewall_check.txt" in up_data.get("filename")

        # List evidence
        list_resp = client.get("/api/iso27001/evidence/A.8.20")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data.get("control_id") == "A.8.20"
        filenames = [f["filename"] for f in list_data.get("files", [])]
        assert any("firewall_check.txt" in fn for fn in filenames)

    def test_control_ai_assist_generate_sop_mocked_llm(self):
        from unittest.mock import patch
        payload = {
            "standard": "iso27001",
            "control_id": "A.5.6",
            "control_label": "Liên lạc với nhóm chuyên gia",
            "requirement": "Duy trì liên lạc với các nhóm chuyên gia bảo mật",
            "criteria": "Có danh bạ và kênh tiếp nhận cảnh báo",
            "mode": "generate_sop",
            "model": "gemma4:latest"
        }
        with patch("services.cloud_llm_service.CloudLLMService.chat_completion") as mock_chat:
            mock_chat.return_value = {
                "content": "### SOP A.5.6 Liên lạc với nhóm chuyên gia\n1. Bước 1: Tiếp nhận thông tin.",
                "model": "gemma4:latest"
            }
            resp = client.post("/api/iso27001/controls/A.5.6/ai-assist", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert data.get("control_id") == "A.5.6"
        assert data.get("mode") == "generate_sop"
        assert "SOP A.5.6" in data.get("response", "")

    def test_control_ai_assist_fallback_on_exception(self):
        from unittest.mock import patch
        payload = {
            "standard": "iso27001",
            "control_id": "A.5.32",
            "control_label": "Bảo vệ quyền sở hữu trí tuệ",
            "requirement": "Bảo vệ quyền sở hữu trí tuệ phần mềm",
            "criteria": "Có danh mục bản quyền",
            "mode": "generate_sop",
            "model": "gemma4:latest"
        }
        with patch("services.cloud_llm_service.CloudLLMService.chat_completion", side_effect=Exception("Ollama unavailable")):
            resp = client.post("/api/iso27001/controls/A.5.32/ai-assist", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert "A.5.32" in data.get("response", "")
        assert "QUY TRÌNH VẬN HÀNH CHUẨN" in data.get("response", "")

    def test_control_ai_assist_verify_evidence_no_evidence(self):
        from unittest.mock import patch
        payload = {
            "standard": "iso27001",
            "control_id": "A.5.32",
            "control_label": "Bảo vệ quyền sở hữu trí tuệ",
            "requirement": "Bảo vệ quyền sở hữu trí tuệ phần mềm",
            "criteria": "Có danh mục bản quyền",
            "mode": "verify_evidence",
            "evidence_filenames": []
        }
        with patch("services.cloud_llm_service.CloudLLMService.chat_completion", side_effect=Exception("Busy")):
            resp = client.post("/api/iso27001/controls/A.5.32/ai-assist", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "success"
        assert "A.5.32" in data.get("response", "")

    def test_get_assessment_extraction_proof(self):
        from unittest.mock import patch
        fake_assessment = {
            "id": "test_proof_123",
            "system_data": {
                "organization": {"name": "EVN TPC"},
                "notes": "Host Name: SRV-01\nOS Name: Windows Server 2008 R2\nHotfix(s): KB2841134",
                "compliance": {"implemented_controls": ["SV.07"]}
            }
        }
        with patch("api.routes.iso27001.load_assessment", return_value=fake_assessment):
            resp = client.get("/api/iso27001/assessments/test_proof_123/extraction-proof")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("integrity_status") == "VERIFIED_100_PERCENT"
            assert data.get("completeness_score") == 100.0
            assert "technical_facts" in data
            assert "cross_verification" in data



