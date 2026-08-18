"""Tests for template-specific evidence storage endpoints.

Covers:
- POST   /api/templates/{template_id}/evidence/upload
- GET    /api/templates/{template_id}/evidence
- GET    /api/templates/{template_id}/evidence/{doc_id}/raw
- GET    /api/templates/{template_id}/evidence/{doc_id}/text
- Storage-layer unit tests for template_evidence_store
"""

from __future__ import annotations

import pathlib
import sys

import pytest
from fastapi.testclient import TestClient

BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def data_path(tmp_path, monkeypatch):
    """Point DATA_PATH at an isolated temp dir for each test."""
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(data_path):
    """Minimal FastAPI app mounting only the templates router."""
    from fastapi import FastAPI
    from api.routes.templates import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def _upload(client: TestClient, template_id: str, filename: str = "policy.txt", content: bytes = b"Hello world"):
    return client.post(
        f"/api/templates/{template_id}/evidence/upload",
        files={"file": (filename, content, "text/plain")},
    )


# ---------------------------------------------------------------------------
# Storage-layer unit tests
# ---------------------------------------------------------------------------

class TestTemplateEvidenceStore:
    def test_load_manifest_empty(self, data_path):
        from services.template_evidence_store import load_manifest

        m = load_manifest("vietcombank")
        assert m.template_id == "vietcombank"
        assert m.evidence == []

    def test_add_and_list(self, data_path):
        from datetime import datetime, timezone
        from services.template_evidence_store import add_evidence, list_evidence

        add_evidence(
            template_id="fpt",
            doc_id="abc-123",
            filename="report.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            uploaded_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            preview="First page...",
        )
        items = list_evidence("fpt")
        assert len(items) == 1
        assert items[0].doc_id == "abc-123"
        assert items[0].filename == "report.pdf"

    def test_find_evidence(self, data_path):
        from datetime import datetime, timezone
        from services.template_evidence_store import add_evidence, find_evidence

        add_evidence(
            template_id="vcb",
            doc_id="doc-1",
            filename="a.txt",
            mime_type="text/plain",
            size_bytes=10,
            uploaded_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        assert find_evidence("vcb", "doc-1") is not None
        assert find_evidence("vcb", "nonexistent") is None

    def test_manifest_persisted_on_disk(self, data_path):
        from datetime import datetime, timezone
        from services.template_evidence_store import add_evidence, load_manifest

        add_evidence(
            template_id="test-tpl",
            doc_id="d1",
            filename="f.txt",
            mime_type="text/plain",
            size_bytes=5,
            uploaded_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        manifest_file = data_path / "template_evidence" / "test-tpl.json"
        assert manifest_file.is_file()

        reloaded = load_manifest("test-tpl")
        assert len(reloaded.evidence) == 1
        assert reloaded.evidence[0].doc_id == "d1"


# ---------------------------------------------------------------------------
# Route-level integration tests
# ---------------------------------------------------------------------------

class TestUploadEndpoint:
    def test_upload_txt_success(self, client):
        resp = _upload(client, "vietcombank", "policy.txt", b"Security policy content")
        assert resp.status_code == 200
        body = resp.json()
        assert body["filename"] == "policy.txt"
        assert body["doc_id"]
        assert "Security policy" in body["preview"]

    def test_upload_empty_file_rejected(self, client):
        resp = _upload(client, "vietcombank", "empty.txt", b"")
        assert resp.status_code == 400

    def test_upload_invalid_template_id(self, client):
        resp = _upload(client, "bad!id@here", "policy.txt", b"data")
        assert resp.status_code == 400

    def test_upload_unsupported_format(self, client):
        resp = client.post(
            "/api/templates/fpt/evidence/upload",
            files={"file": ("image.png", b"\x89PNG\r\n", "image/png")},
        )
        assert resp.status_code == 415


class TestListEndpoint:
    def test_list_empty(self, client):
        resp = client.get("/api/templates/vietcombank/evidence")
        assert resp.status_code == 200
        body = resp.json()
        assert body["template_id"] == "vietcombank"
        assert body["evidence"] == []

    def test_list_after_upload(self, client):
        _upload(client, "fpt", "doc.txt", b"content here")
        resp = client.get("/api/templates/fpt/evidence")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["evidence"]) == 1
        assert body["evidence"][0]["filename"] == "doc.txt"


class TestRawDownloadEndpoint:
    def test_download_raw_success(self, client):
        upload_resp = _upload(client, "vcb", "report.txt", b"raw bytes here")
        doc_id = upload_resp.json()["doc_id"]

        resp = client.get(f"/api/templates/vcb/evidence/{doc_id}/raw")
        assert resp.status_code == 200
        assert resp.content == b"raw bytes here"

    def test_download_raw_not_found(self, client):
        resp = client.get("/api/templates/vcb/evidence/nonexistent-id/raw")
        assert resp.status_code == 404


class TestTextEndpoint:
    def test_get_text_success(self, client):
        upload_resp = _upload(client, "fpt", "notes.txt", b"Extracted text content")
        doc_id = upload_resp.json()["doc_id"]

        resp = client.get(f"/api/templates/fpt/evidence/{doc_id}/text")
        assert resp.status_code == 200
        assert "Extracted text content" in resp.text

    def test_get_text_not_found(self, client):
        resp = client.get("/api/templates/fpt/evidence/bad-id/text")
        assert resp.status_code == 404


class TestDeduplication:
    def test_same_file_deduplicates(self, client):
        content = b"identical content for dedup test"
        r1 = _upload(client, "vcb", "v1.txt", content)
        r2 = _upload(client, "vcb", "v2.txt", content)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r2.json()["deduplicated"] is True
        assert r1.json()["doc_id"] == r2.json()["doc_id"]
