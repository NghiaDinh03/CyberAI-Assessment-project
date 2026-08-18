"""HTTP routes for the evidence document ingest pipeline.

Endpoints (mounted under both ``/api`` and ``/api/v1`` in :mod:`main`):
    POST   /documents/upload             — parse + persist an uploaded file
    GET    /documents/{doc_id}           — full ExtractedDocument metadata
    GET    /documents/{doc_id}/raw       — download the original upload
    GET    /documents/{doc_id}/text      — plain-text extraction only

All endpoints are read-side idempotent; upload deduplicates on SHA-256.
"""

from __future__ import annotations

import mimetypes

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from api.schemas.document import DocumentUploadResponse, ExtractedDocument
from services.document_ingest import storage
from services.document_service import DocumentService

router = APIRouter()
doc_service = DocumentService()

_PREVIEW_CHARS = 500


def _build_upload_response(
    doc: ExtractedDocument, deduplicated: bool
) -> DocumentUploadResponse:
    return DocumentUploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        checksum=doc.checksum,
        deduplicated=deduplicated,
        section_count=len(doc.sections),
        table_count=len(doc.tables),
        preview=(doc.extracted_text or "")[:_PREVIEW_CHARS],
    )


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    """Parse an uploaded evidence file and persist the extraction result."""
    doc, deduplicated = await doc_service.process_upload(file)
    return _build_upload_response(doc, deduplicated)


@router.get("/documents/{doc_id}", response_model=ExtractedDocument)
async def get_document(doc_id: str) -> ExtractedDocument:
    doc = storage.load(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.get("/documents/{doc_id}/text", response_class=PlainTextResponse)
async def get_document_text(doc_id: str) -> str:
    doc = storage.load(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc.extracted_text or ""


@router.get("/documents/{doc_id}/raw")
async def get_document_raw(doc_id: str) -> FileResponse:
    """Stream back the original uploaded file bytes."""
    path = storage.raw_path(doc_id)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Document not found.")

    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(
        path=str(path),
        media_type=media_type or "application/octet-stream",
        filename=path.name,
    )


@router.get("/documents/{doc_id}/chunks")
async def get_document_chunks(doc_id: str, q: str = "", top_k: int = 5) -> dict:
    """Return chunks of *doc_id* — either listed (no ``q``) or RAG-ranked.

    - ``q=""``       → list all chunk_ids stored on disk (no embedding cost).
    - ``q="..."``    → cosine-similarity search restricted to this document.
    """
    doc = storage.load(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not q:
        return {
            "doc_id": doc_id,
            "chunk_ids": doc.chunk_ids,
            "count": len(doc.chunk_ids),
        }

    from services.document_ingest import EvidenceIndexer

    results = EvidenceIndexer().query(q, top_k=top_k, doc_id=doc_id)
    return {"doc_id": doc_id, "query": q, "results": results}
