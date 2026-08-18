"""Thin orchestration layer over :mod:`services.document_ingest`.

The service keeps the HTTP route simple by owning:
- upload size limits (50MB — mirrors the doc in context.md §7.6)
- deduplication by SHA-256 checksum
- mapping parser errors to HTTP-friendly responses
- persisting the ExtractedDocument + raw bytes on disk

ChromaDB indexing and chunking are intentionally deferred (PR (b)).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from typing import Tuple

from fastapi import HTTPException, UploadFile

from api.schemas.document import ExtractedDocument
from services.document_ingest import (
    SUPPORTED_EXTENSIONS,
    EvidenceIndexer,
    UnsupportedFormatError,
    chunk_text,
    guess_mime_type,
    parse_bytes,
)
from services.document_ingest import storage

logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def _safe_filename(name: str) -> str:
    """Strip path components and unsafe characters from an upload filename.

    The original basename is preserved for readability; only characters
    outside ``[A-Za-z0-9._ -]`` are replaced with an underscore.
    """
    base = os.path.basename(name or "") or "upload.bin"
    return _FILENAME_SAFE_RE.sub("_", base)


class DocumentService:
    """Parses an upload into an :class:`ExtractedDocument` and persists it."""

    def __init__(self, indexer: EvidenceIndexer | None = None) -> None:
        # Default to a real indexer; tests inject a fake collection so they
        # never hit ChromaDB on disk.
        self._indexer = indexer or EvidenceIndexer()

    async def process_upload(self, file: UploadFile) -> Tuple[ExtractedDocument, bool]:
        """Parse and store *file*.

        Returns:
            (document, deduplicated) — ``deduplicated`` is True when an
            identical checksum already exists on disk and we reuse the
            stored ``doc_id`` instead of writing a new one.
        """
        filename = _safe_filename(file.filename or "upload.bin")
        raw_bytes = await file.read()

        size = len(raw_bytes)
        if size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        if size > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {_MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.",
            )

        checksum = hashlib.sha256(raw_bytes).hexdigest()

        existing = storage.find_by_checksum(checksum)
        if existing is not None:
            logger.info(
                "document dedupe hit doc_id=%s filename=%s sha256=%s",
                existing.doc_id, filename, checksum[:12],
            )
            return existing, True

        try:
            text, sections, tables = parse_bytes(raw_bytes, filename)
        except UnsupportedFormatError as exc:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"{exc}. Supported extensions: "
                    f"{sorted(SUPPORTED_EXTENSIONS)}"
                ),
            ) from exc
        except ValueError as exc:
            # Parser rejected the payload (e.g. encrypted PDF, corrupt xlsx).
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ImportError as exc:
            # A parser dependency is missing at runtime — signal 503 so the
            # client knows this is a server-side config issue, not a bad file.
            logger.error("parser dependency missing: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Server is missing a required document parser dependency.",
            ) from exc

        doc_id = str(uuid.uuid4())
        mime_type = guess_mime_type(filename)

        # Chunk + index for RAG. Indexing failures degrade gracefully —
        # the document is still saved so the user does not lose work.
        chunks = chunk_text(text)
        chunk_ids = self._indexer.upsert(
            doc_id, chunks, filename=filename, mime_type=mime_type
        )

        doc = ExtractedDocument(
            doc_id=doc_id,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size,
            uploaded_at=storage.utc_now(),
            checksum=checksum,
            extracted_text=text,
            sections=sections,
            tables=tables,
            chunk_ids=chunk_ids,
        )
        storage.save(doc, raw_bytes)
        logger.info(
            "document ingested doc_id=%s filename=%s size=%dB sections=%d tables=%d chunks=%d",
            doc.doc_id, filename, size, len(sections), len(tables), len(chunk_ids),
        )
        return doc, False
