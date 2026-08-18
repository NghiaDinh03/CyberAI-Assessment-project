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
        assert response.status_code == 400

    def test_dotdot_url_encoded_blocked(self):
        """URL-encoded ..%2F traversal must be rejected."""
        # TestClient does not encode the path; we send the literal string
        response = client.get("/api/v1/iso27001/assessments/..%2Fetc%2Fpasswd")
        assert response.status_code == 400

    def test_dotdot_backslash_blocked(self):
        """Windows-style ..\\ traversal must be rejected."""
        response = _get_assessment("..\\windows\\system32")
        assert response.status_code == 400

    def test_nested_traversal_blocked(self):
        """Deep traversal paths must be rejected."""
        response = _get_assessment("../../etc/shadow")
        assert response.status_code == 400

    def test_traversal_with_valid_prefix_blocked(self):
        """Traversal appended after a valid-looking prefix must still be blocked."""
        response = _get_assessment("abc-123/../../../etc/passwd")
        assert response.status_code == 400


class TestNullByteInjection:
    def test_null_byte_url_encoded_blocked(self):
        """Null byte (%00) in the ID must be rejected."""
        response = client.get("/api/v1/iso27001/assessments/id%00malicious")
        assert response.status_code == 400

    def test_literal_null_byte_blocked(self):
        """A literal NUL character in the path must be rejected."""
        response = _get_assessment("id\x00malicious")
        assert response.status_code == 400


class TestSpecialCharacterBlocking:
    def test_angle_brackets_blocked(self):
        """XSS-style angle brackets must be rejected."""
        response = _get_assessment("id<script>alert(1)</script>")
        assert response.status_code in (400, 422)

    def test_semicolon_blocked(self):
        """Semicolon (shell command separator) must be rejected."""
        response = _get_assessment("id;rm -rf /")
        assert response.status_code in (400, 422)

    def test_pipe_blocked(self):
        """Pipe character must be rejected."""
        response = _get_assessment("id|cat /etc/passwd")
        assert response.status_code in (400, 422)

    def test_ampersand_blocked(self):
        """Ampersand must be rejected."""
        response = _get_assessment("id&whoami")
        assert response.status_code in (400, 422)

    def test_dollar_sign_blocked(self):
        """Dollar sign (shell variable expansion) must be rejected."""
        response = _get_assessment("id$HOME")
        assert response.status_code in (400, 422)

    def test_backtick_blocked(self):
        """Backtick (shell command substitution) must be rejected."""
        response = _get_assessment("id`id`")
        assert response.status_code in (400, 422)

    def test_slash_in_id_blocked(self):
        """Forward slash is not in the safe charset and must be rejected."""
        # Note: a bare slash becomes a path segment separator in HTTP;
        # FastAPI may route this as a different endpoint (404) rather than 400.
        # Either rejection code is acceptable.
        response = _get_assessment("id/extra")
        assert response.status_code in (400, 404, 422)

    def test_space_in_id_blocked(self):
        """Spaces are not in the safe charset."""
        response = _get_assessment("id with space")
        assert response.status_code in (400, 422)


class TestEdgeCases:
    def test_empty_id_blocked(self):
        """An empty ID string — FastAPI will route to the list endpoint instead,
        so we just verify the assessments list endpoint itself doesn't error."""
        response = client.get("/api/v1/iso27001/assessments/")
        # Should return list (200) or at worst an empty response — not a 500
        assert response.status_code < 500

    def test_very_long_id_rejected_or_not_found(self):
        """An excessively long but safe ID should not crash the server."""
        long_id = "a" * 500
        response = _get_assessment(long_id)
        # Either rejected (400) or not found (404/200 with error body) — not 500
        assert response.status_code < 500

    def test_response_is_json(self):
        """All rejection responses must be valid JSON (not raw exception text)."""
        response = _get_assessment("../etc/passwd")
        assert response.status_code == 400
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
        payload = {
            "assessment_standard": "iso27001",
            "org_name": "Test Org",
            "implemented_controls": ["A.5.1"],
            "evidence_map": {},  # intentionally empty — no evidence uploaded
            "model_mode": "local",
        }
        response = client.post("/api/v1/iso27001/assess", json=payload)
        # We only care that it is NOT rejected as a validation error.
        # 200/202 (accepted) is the happy case; 500 would also indicate
        # acceptance up to the background-task layer (still "no frontend gate
        # contract violation"). 4xx other than 422 is acceptable for unrelated
        # reasons (rate limit, etc.).
        assert response.status_code != 422, (
            f"Backend rejected implemented-without-evidence payload "
            f"(status={response.status_code}, body={response.text[:200]}). "
            "The mandatory-evidence gate must remain frontend-only."
        )
