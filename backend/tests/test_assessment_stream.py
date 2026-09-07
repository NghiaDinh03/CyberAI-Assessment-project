import json
import os
import pytest
from fastapi.testclient import TestClient
from main import app
from api.routes.iso27001 import save_assessment, ASSESSMENTS_DIR

client = TestClient(app)


def test_stream_assessment_completed():
    test_id = "test_stream_completed_001"
    save_assessment(test_id, {
        "id": test_id,
        "status": "completed",
        "compliance_percent": 88.5,
        "created_at": "2026-09-05T08:00:00Z",
        "result": {
            "report": "Test report for stream completed",
            "json_data": {"test": True}
        }
    })

    try:
        response = client.get(f"/api/iso27001/assessments/{test_id}/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        assert "event: complete" in content
        assert '"status": "completed"' in content
    finally:
        fpath = os.path.join(ASSESSMENTS_DIR, f"{test_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)


def test_stream_assessment_failed():
    test_id = "test_stream_failed_001"
    save_assessment(test_id, {
        "id": test_id,
        "status": "failed",
        "created_at": "2026-09-05T08:00:00Z",
        "error": "Simulated pipeline failure",
        "error_code": "TEST_ERROR"
    })

    try:
        response = client.get(f"/api/iso27001/assessments/{test_id}/stream")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        content = response.text
        assert "event: error" in content
        assert '"status": "failed"' in content
    finally:
        fpath = os.path.join(ASSESSMENTS_DIR, f"{test_id}.json")
        if os.path.exists(fpath):
            os.remove(fpath)

