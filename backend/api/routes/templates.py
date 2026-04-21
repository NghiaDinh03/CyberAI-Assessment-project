"""HTTP routes for template-specific evidence management.

Endpoints (mounted under both ``/api`` and ``/api/v1``):
    POST   /templates/{template_id}/evidence/upload    — upload evidence for a template
    GET    /templates/{template_id}/evidence            — list evidence for a template
    GET    /templates/{template_id}/evidence/{doc_id}/raw  — download original file
    GET    /templates/{template_id}/evidence/{doc_id}/text — extracted text preview
"""

from __future__ import annotations

import mimetypes
import re

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from services.document_ingest import storage as doc_storage
from services.document_service import DocumentService
from services import template_evidence_store as te_store

router = APIRouter()
doc_service = DocumentService()

_PREVIEW_CHARS = 500
_TEMPLATE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_template_id(template_id: str) -> None:
    if not _TEMPLATE_ID_RE.match(template_id) or len(template_id) > 64:
        raise HTTPException(status_code=400, detail="Invalid template_id format.")


@router.post("/templates/{template_id}/evidence/upload")
async def upload_template_evidence(template_id: str, file: UploadFile = File(...)):
    """Upload an evidence file and link it to *template_id*."""
    _validate_template_id(template_id)

    doc, deduplicated = await doc_service.process_upload(file)
    preview = (doc.extracted_text or "")[:_PREVIEW_CHARS]

    item = te_store.add_evidence(
        template_id=template_id,
        doc_id=doc.doc_id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        uploaded_at=doc.uploaded_at,
        preview=preview,
    )

    return {
        "doc_id": item.doc_id,
        "filename": item.filename,
        "mime_type": item.mime_type,
        "size_bytes": item.size_bytes,
        "uploaded_at": item.uploaded_at,
        "preview": item.preview,
        "deduplicated": deduplicated,
    }


@router.get("/templates/{template_id}/evidence")
async def list_template_evidence(template_id: str):
    """List all evidence files linked to *template_id*."""
    _validate_template_id(template_id)
    items = te_store.list_evidence(template_id)
    return {"template_id": template_id, "evidence": [i.model_dump() for i in items]}


@router.get("/templates/{template_id}/evidence/{doc_id}/raw")
async def download_template_evidence_raw(template_id: str, doc_id: str):
    """Download the original uploaded file for a template evidence doc."""
    _validate_template_id(template_id)

    item = te_store.find_evidence(template_id, doc_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence not found for this template.")

    path = doc_storage.raw_path(doc_id)
    if path is None or not path.is_file():
        raise HTTPException(status_code=404, detail="Raw file not found on disk.")

    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(
        path=str(path),
        media_type=media_type or "application/octet-stream",
        filename=path.name,
    )


@router.get("/templates/{template_id}/evidence/{doc_id}/text", response_class=PlainTextResponse)
async def get_template_evidence_text(template_id: str, doc_id: str) -> str:
    """Return extracted text content for a template evidence doc."""
    _validate_template_id(template_id)

    item = te_store.find_evidence(template_id, doc_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence not found for this template.")

    doc = doc_storage.load(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    return doc.extracted_text or ""
