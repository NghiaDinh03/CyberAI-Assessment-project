"""Unit tests for the document ingest pipeline (Phase 0 PR (a)).

Fixtures are generated at runtime so no binary blobs are committed to the
repository. Tests that require optional parser deps skip gracefully when
those libraries are not installed.
"""

from __future__ import annotations

import io
import os
import pathlib

import pytest
from fastapi.testclient import TestClient

# Add backend/ to sys.path when running from repo root.
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.fixture
def data_path(tmp_path, monkeypatch):
    """Point DATA_PATH at an isolated temp dir for each test."""
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(data_path):
    """Build a minimal FastAPI app that mounts only the document router.

    Using a focused app keeps these tests hermetic — they don't require
    chromadb, slowapi, or any other optional dependency of the full
    backend; only the ingest pipeline is exercised.
    """
    from fastapi import FastAPI

    from api.routes.document import router

    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


# ---------- parser-level tests (no FastAPI) ------------------------------


def test_txt_parser_roundtrip():
    from services.document_ingest import parse_bytes

    text, sections, tables = parse_bytes(b"hello\nworld", "note.txt")
    assert text == "hello\nworld"
    assert sections == []
    assert tables == []


def test_md_parser_splits_sections():
    from services.document_ingest import parse_bytes

    md = b"# Intro\nalpha\n\n## Body\nbeta\n"
    text, sections, tables = parse_bytes(md, "policy.md")
    assert "Intro" in text
    headings = [s.heading for s in sections]
    assert "Intro" in headings and "Body" in headings
    assert tables == []


def test_csv_parser_extracts_table():
    from services.document_ingest import parse_bytes

    csv_bytes = b"name,score\nalice,5\nbob,4\n"
    _text, _sections, tables = parse_bytes(csv_bytes, "risks.csv")
    assert len(tables) == 1
    assert tables[0].headers == ["name", "score"]
    assert tables[0].rows == [["alice", "5"], ["bob", "4"]]


def test_unsupported_extension_rejected():
    from services.document_ingest import UnsupportedFormatError, parse_bytes

    with pytest.raises(UnsupportedFormatError):
        parse_bytes(b"...", "image.png")


def test_docx_parser_extracts_heading_and_table():
    docx = pytest.importorskip("docx")

    # Build a minimal .docx in memory so we don't commit a binary fixture.
    document = docx.Document()
    document.add_heading("Access Control Policy", level=1)
    document.add_paragraph("MFA is required for all admin accounts.")
    table = document.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Control"
    table.rows[0].cells[1].text = "Status"
    table.rows[1].cells[0].text = "A.5.1"
    table.rows[1].cells[1].text = "Implemented"

    buf = io.BytesIO()
    document.save(buf)

    from services.document_ingest import parse_bytes

    text, sections, tables = parse_bytes(buf.getvalue(), "policy.docx")
    assert "Access Control Policy" in text
    assert "MFA" in text
    assert any(s.heading == "Access Control Policy" and s.level == 1 for s in sections)
    assert len(tables) == 1
    assert tables[0].headers == ["Control", "Status"]
    assert tables[0].rows == [["A.5.1", "Implemented"]]


def test_xlsx_parser_extracts_sheet():
    openpyxl = pytest.importorskip("openpyxl")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "RiskRegister"
    ws.append(["ID", "Asset", "Likelihood", "Impact"])
    ws.append(["R1", "Web App", 3, 4])
    ws.append(["R2", "Database", 2, 5])

    buf = io.BytesIO()
    wb.save(buf)

    from services.document_ingest import parse_bytes

    _text, _sections, tables = parse_bytes(buf.getvalue(), "risks.xlsx")
    assert len(tables) == 1
    assert tables[0].name == "RiskRegister"
    assert tables[0].headers == ["ID", "Asset", "Likelihood", "Impact"]
    assert tables[0].rows[0] == ["R1", "Web App", "3", "4"]


def test_pdf_parser_scanned_warning():
    """An empty / non-text PDF must return a low-text warning, not crash."""
    pypdf = pytest.importorskip("pypdf")

    # Build a minimal valid empty PDF in memory.
    try:
        from pypdf import PdfWriter
    except ImportError:
        pytest.skip("pypdf writer unavailable")

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)

    from services.document_ingest import parse_bytes

    text, sections, _tables = parse_bytes(buf.getvalue(), "scan.pdf")
    # Blank page → no extractable text → warning section inserted first.
    assert any(s.heading == "warning" for s in sections)
    assert len(text) < 50


# ---------- route-level tests --------------------------------------------


def test_upload_and_fetch_txt(client, data_path):
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("evidence.txt", b"hello evidence", "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filename"] == "evidence.txt"
    assert body["size_bytes"] == len(b"hello evidence")
    assert body["deduplicated"] is False
    assert body["preview"].startswith("hello evidence")

    doc_id = body["doc_id"]

    meta = client.get(f"/api/documents/{doc_id}").json()
    assert meta["checksum"] == body["checksum"]
    assert meta["extracted_text"] == "hello evidence"

    text_resp = client.get(f"/api/documents/{doc_id}/text")
    assert text_resp.status_code == 200
    assert text_resp.text == "hello evidence"

    raw_resp = client.get(f"/api/documents/{doc_id}/raw")
    assert raw_resp.status_code == 200
    assert raw_resp.content == b"hello evidence"


def test_upload_dedupes_by_checksum(client):
    payload = {"file": ("a.txt", b"same-bytes", "text/plain")}
    first = client.post("/api/documents/upload", files=payload).json()
    # Second upload with a different filename but same bytes → same doc_id.
    second = client.post(
        "/api/documents/upload",
        files={"file": ("b.txt", b"same-bytes", "text/plain")},
    ).json()
    assert first["doc_id"] == second["doc_id"]
    assert second["deduplicated"] is True


def test_upload_rejects_empty_file(client):
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_rejects_unsupported_extension(client):
    resp = client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"MZ\x00\x00", "application/octet-stream")},
    )
    assert resp.status_code == 415


def test_get_missing_document_returns_404(client):
    assert client.get("/api/documents/does-not-exist").status_code == 404
    assert client.get("/api/documents/does-not-exist/text").status_code == 404
    assert client.get("/api/documents/does-not-exist/raw").status_code == 404


def test_filename_is_sanitized(client):
    # Traversal attempt — service must strip the path component before
    # the parser even runs. The basename still resolves to a supported .txt.
    resp = client.post(
        "/api/documents/upload",
        files={
            "file": (
                "../../etc/passwd.txt",
                b"not really passwd",
                "text/plain",
            )
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "/" not in body["filename"] and "\\" not in body["filename"]
    assert body["filename"].endswith("passwd.txt")
