"""Automated Test Suite for P0 Evidence Isolation and Cross-Assessment Scoping.

Verifies:
1. Multi-control mapping in Assessment A (F1 -> A.5.9, F2 -> A.5.10, F3 -> A.5.9 & A.5.10).
2. Clean isolation of Assessment B (starts with 0 files across all controls).
3. Independent uploads to Assessment B (F4 -> A.8.8 in B does not alter A).
4. Cross-assessment manifest submission rejection (HTTP 409 Conflict).
5. Scoped evidence deletion (deletion in B never affects files in A).
6. Strict zero-fallback enforcement when assessment_id is omitted.
"""

import os
import sys
import io
import json
import pytest

# Ensure backend/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def setup_assessments():
    """Initialize two distinct assessments A and B for testing."""
    # 1. Init Assessment A
    res_a = client.post("/api/iso27001/assessments/init")
    assert res_a.status_code == 200, f"Init A failed: {res_a.text}"
    data_a = res_a.json()
    aid_a = data_a["assessment_id"]
    manifest_a = data_a["manifest_id"]

    # 2. Init Assessment B
    res_b = client.post("/api/iso27001/assessments/init")
    assert res_b.status_code == 200, f"Init B failed: {res_b.text}"
    data_b = res_b.json()
    aid_b = data_b["assessment_id"]
    manifest_b = data_b["manifest_id"]

    assert aid_a != aid_b, "Assessment IDs must be globally unique UUIDs"

    return {
        "aid_a": aid_a,
        "manifest_a": manifest_a,
        "aid_b": aid_b,
        "manifest_b": manifest_b,
    }


class TestEvidenceIsolationAndScoping:

    def test_assessment_a_multi_control_upload(self, setup_assessments):
        """Test 1: Upload F1 to A.5.9, F2 to A.5.10, and F3 to both A.5.9 & A.5.10 in Assessment A."""
        aid_a = setup_assessments["aid_a"]

        # Upload F1 to A.5.9
        f1_content = b"Content of Policy F1 for ISO control A.5.9"
        res1 = client.post(
            f"/api/iso27001/evidence/A.5.9?assessment_id={aid_a}",
            files={"file": ("F1_policy.txt", io.BytesIO(f1_content), "text/plain")},
        )
        assert res1.status_code == 200, f"Upload F1 failed: {res1.text}"
        data1 = res1.json()
        assert data1["control_id"] == "A.5.9"
        assert "F1_policy" in data1["filename"]

        # Upload F2 to A.5.10
        f2_content = b"Content of Access Rights F2 for ISO control A.5.10"
        res2 = client.post(
            f"/api/iso27001/evidence/A.5.10?assessment_id={aid_a}",
            files={"file": ("F2_access.txt", io.BytesIO(f2_content), "text/plain")},
        )
        assert res2.status_code == 200, f"Upload F2 failed: {res2.text}"

        # Upload F3 to A.5.9 and A.5.10
        f3_content = b"Content of Dual Control Evidence F3 for A.5.9 and A.5.10"
        res3a = client.post(
            f"/api/iso27001/evidence/A.5.9?assessment_id={aid_a}",
            files={"file": ("F3_dual.txt", io.BytesIO(f3_content), "text/plain")},
        )
        assert res3a.status_code == 200

        res3b = client.post(
            f"/api/iso27001/evidence/A.5.10?assessment_id={aid_a}",
            files={"file": ("F3_dual.txt", io.BytesIO(f3_content), "text/plain")},
        )
        assert res3b.status_code == 200

        # Verification in Assessment A:
        # A.5.9 must have exactly 2 files (F1, F3)
        res_ctrl_a59 = client.get(f"/api/iso27001/evidence/A.5.9?assessment_id={aid_a}")
        assert res_ctrl_a59.status_code == 200
        files_a59 = res_ctrl_a59.json().get("files", [])
        assert len(files_a59) == 2, f"Expected 2 files in A.5.9, got {len(files_a59)}"
        names_a59 = [f["clean_name"] for f in files_a59]
        assert any("F1_policy.txt" in n for n in names_a59)
        assert any("F3_dual.txt" in n for n in names_a59)

        # A.5.10 must have exactly 2 files (F2, F3)
        res_ctrl_a510 = client.get(f"/api/iso27001/evidence/A.5.10?assessment_id={aid_a}")
        assert res_ctrl_a510.status_code == 200
        files_a510 = res_ctrl_a510.json().get("files", [])
        assert len(files_a510) == 2, f"Expected 2 files in A.5.10, got {len(files_a510)}"
        names_a510 = [f["clean_name"] for f in files_a510]
        assert any("F2_access.txt" in n for n in names_a510)
        assert any("F3_dual.txt" in n for n in names_a510)

        # Summary for Assessment A: exactly 2 controls mapped
        res_summary = client.get(f"/api/iso27001/evidence-summary?assessment_id={aid_a}")
        assert res_summary.status_code == 200
        summary_data = res_summary.json()
        assert "A.5.9" in summary_data["controls"]
        assert "A.5.10" in summary_data["controls"]
        assert len(summary_data["controls"]) == 2

    def test_assessment_b_clean_isolation(self, setup_assessments):
        """Test 2: Assessment B created after A must be completely clean with 0 files across all controls."""
        aid_b = setup_assessments["aid_b"]

        # Check A.5.9 for Assessment B -> must be 0 files
        res_b_59 = client.get(f"/api/iso27001/evidence/A.5.9?assessment_id={aid_b}")
        assert res_b_59.status_code == 200
        assert len(res_b_59.json().get("files", [])) == 0

        # Check A.5.10 for Assessment B -> must be 0 files
        res_b_510 = client.get(f"/api/iso27001/evidence/A.5.10?assessment_id={aid_b}")
        assert res_b_510.status_code == 200
        assert len(res_b_510.json().get("files", [])) == 0

        # Check evidence-summary for Assessment B -> must be 0
        res_b_sum = client.get(f"/api/iso27001/evidence-summary?assessment_id={aid_b}")
        assert res_b_sum.status_code == 200
        assert res_b_sum.json()["total_files"] == 0
        assert len(res_b_sum.json()["controls"]) == 0

    def test_upload_f4_to_assessment_b(self, setup_assessments):
        """Test 3: Upload F4 to A.8.8 in B; verify A remains untouched and B has 1 file."""
        aid_a = setup_assessments["aid_a"]
        aid_b = setup_assessments["aid_b"]

        f4_content = b"Get-Hotfix patch management log F4 for A.8.8"
        res_upload = client.post(
            f"/api/iso27001/evidence/A.8.8?assessment_id={aid_b}",
            files={"file": ("F4_patch.log", io.BytesIO(f4_content), "text/plain")},
        )
        assert res_upload.status_code == 200

        # B must have 1 file in A.8.8
        res_b_88 = client.get(f"/api/iso27001/evidence/A.8.8?assessment_id={aid_b}")
        assert res_b_88.status_code == 200
        files_b = res_b_88.json().get("files", [])
        assert len(files_b) == 1
        assert "F4_patch.log" in files_b[0]["clean_name"]

        # A must have 0 files in A.8.8
        res_a_88 = client.get(f"/api/iso27001/evidence/A.8.8?assessment_id={aid_a}")
        assert res_a_88.status_code == 200
        assert len(res_a_88.json().get("files", [])) == 0

        # A's A.5.9 and A.5.10 must still have their 2 files each
        res_a_59 = client.get(f"/api/iso27001/evidence/A.5.9?assessment_id={aid_a}")
        assert len(res_a_59.json().get("files", [])) == 2

    def test_cross_assessment_manifest_conflict_rejected(self, setup_assessments):
        """Test 4: Submitting Manifest of Assessment A into Assessment B must return HTTP 409 Conflict."""
        aid_a = setup_assessments["aid_a"]
        aid_b = setup_assessments["aid_b"]
        manifest_a = setup_assessments["manifest_a"]

        # Prepare payload with assessment_id B but evidence_manifest_id of A
        conflicting_payload = {
            "assessment_id": aid_b,
            "evidence_manifest_id": manifest_a,
            "org_name": "Test Conflict Org",
            "assessment_standard": "iso27001",
            "implemented_controls": ["A.5.9"],
            "model_mode": "local",
        }

        res = client.post(
            "/api/iso27001/assess",
            json=conflicting_payload,
            headers={"X-Assessment-ID": aid_b},
        )
        assert res.status_code == 409, f"Expected HTTP 409 Conflict, got {res.status_code}: {res.text}"
        detail = res.json().get("error") or res.json().get("detail") or ""
        assert "belongs to assessment" in detail or "manifest" in detail.lower()

    def test_scoped_file_content_and_deletion(self, setup_assessments):
        """Test 5 & 6: File content retrieval and deletion strictly scoped by assessment_id."""
        aid_a = setup_assessments["aid_a"]
        aid_b = setup_assessments["aid_b"]

        # Query content of F4 in Assessment B
        res_content = client.get(
            f"/api/iso27001/evidence/file-content?filename=F4_patch.log&assessment_id={aid_b}"
        )
        assert res_content.status_code == 200
        assert res_content.json()["status"] == "success"

        # Querying F4 in Assessment A must fail with 404 (F4 belongs to B)
        res_content_a = client.get(
            f"/api/iso27001/evidence/file-content?filename=F4_patch.log&assessment_id={aid_a}"
        )
        assert res_content_a.status_code == 404

        # Delete F4 in Assessment B globally across controls
        res_del = client.delete(
            f"/api/iso27001/evidence/file/F4_patch.log?assessment_id={aid_b}"
        )
        assert res_del.status_code == 200

        # Now B has 0 files in A.8.8
        res_b_empty = client.get(f"/api/iso27001/evidence/A.8.8?assessment_id={aid_b}")
        assert len(res_b_empty.json().get("files", [])) == 0

        # Assessment A files must remain 100% intact
        res_a_59 = client.get(f"/api/iso27001/evidence/A.5.9?assessment_id={aid_a}")
        assert len(res_a_59.json().get("files", [])) == 2

    def test_zero_global_fallback_enforcement(self):
        """Test 7: When assessment_id is missing, APIs must NOT fall back to global directories."""
        # list_evidence without assessment_id returns 0 files
        res_list = client.get("/api/iso27001/evidence/A.5.9")
        assert res_list.status_code == 200
        assert res_list.json().get("files") == []

        # evidence-summary without assessment_id returns 0 files
        res_sum = client.get("/api/iso27001/evidence-summary")
        assert res_sum.status_code == 200
        assert res_sum.json().get("total_files") == 0

        # upload without assessment_id gracefully handled or rejected
        res_upload = client.post(
            "/api/iso27001/evidence/A.5.9",
            files={"file": ("unscoped.txt", io.BytesIO(b"unscoped"), "text/plain")},
        )
        assert res_upload.status_code in (200, 400)

        # delete file without assessment_id gracefully handled or rejected
        res_del = client.delete("/api/iso27001/evidence/file/test.txt")
        assert res_del.status_code in (200, 400)
