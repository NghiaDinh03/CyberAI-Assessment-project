"""Pydantic schemas for the document ingest pipeline (Phase 0).

The shape mirrors the on-disk ``extracted.json`` artifact written by
``services.document_ingest.storage`` so the API and storage layers share a
single source of truth.

Schema is intentionally minimal (Section 9.A of context.md): no
``toolkit_type`` classifier, no ``uploaded_by``, no OCR fields. These can be
added later without breaking clients because every new field will be
optional.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class Section(BaseModel):
    """A logical heading + body block extracted from a document."""

    heading: str = ""
    body: str = ""
    level: int = 0


class Table(BaseModel):
    """A tabular block. ``name`` is the sheet name for .xlsx, table index for .docx."""

    name: str = ""
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)


class ExtractedDocument(BaseModel):
    """Result of parsing one uploaded evidence file.

    Fields (9):
      1. doc_id          — uuid4, primary key
      2. filename        — original upload filename (sanitized)
      3. mime_type       — detected MIME (best-effort from extension)
      4. size_bytes      — raw byte count of the upload
      5. uploaded_at     — server-side timestamp (UTC, ISO 8601)
      6. checksum        — SHA-256 of the raw bytes (hex), used for dedupe
      7. extracted_text  — concatenated plain-text rendering
      8. sections        — list of {heading, body, level}
      9. tables          — list of {name, headers, rows}

    ``chunk_ids`` is reserved for the ChromaDB indexing step (PR (b)) and
    defaults to an empty list so clients can rely on its presence today.
    """

    doc_id: str
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime
    checksum: str
    extracted_text: str = ""
    sections: List[Section] = Field(default_factory=list)
    tables: List[Table] = Field(default_factory=list)
    chunk_ids: List[str] = Field(default_factory=list)


class DocumentUploadResponse(BaseModel):
    """Slim response returned from POST /api/documents/upload.

    Contains the metadata clients need immediately (id, size, dedupe info)
    plus a short text preview so the UI can show feedback without a second
    round-trip. Full extraction is fetched via GET /api/documents/{doc_id}/text.
    """

    doc_id: str
    filename: str
    mime_type: str
    size_bytes: int
    checksum: str
    deduplicated: bool = False
    section_count: int = 0
    table_count: int = 0
    preview: str = ""
