"""On-disk persistence for ingested evidence documents.

Layout per document, rooted at ``DATA_PATH/evidence/{doc_id}/``::

    raw/{filename}     — original upload bytes
    extracted.json     — full ExtractedDocument as JSON
    preview.md         — first ~2KB of extracted text for quick UI rendering

Functions are deliberately small and synchronous; the route layer wraps
them in ``run_in_threadpool`` if it needs to keep the event loop free.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from api.schemas.document import ExtractedDocument

# 2 KB of extracted text is enough for the upload toast / drawer preview
# without bloating the API response.
_PREVIEW_BYTES = 2048


def _evidence_root() -> Path:
    """Resolve the evidence root directory from the env-driven DATA_PATH.

    Reads at call time (not import time) so tests can monkeypatch
    ``DATA_PATH`` between cases.
    """
    base = os.getenv("DATA_PATH", "./data")
    root = Path(base) / "evidence"
    root.mkdir(parents=True, exist_ok=True)
    return root


def doc_dir(doc_id: str) -> Path:
    return _evidence_root() / doc_id


def find_by_checksum(checksum: str) -> Optional[ExtractedDocument]:
    """Return the existing document with this checksum, or None.

    Used to deduplicate uploads: the same bytes under any filename map to
    the same ``doc_id``. Scan is O(N) over evidence/; acceptable for the
    expected single-tenant scale (hundreds of docs, not millions).
    """
    root = _evidence_root()
    if not root.exists():
        return None
    for child in root.iterdir():
        meta = child / "extracted.json"
        if not meta.is_file():
            continue
        try:
            payload = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("checksum") == checksum:
            try:
                return ExtractedDocument.model_validate(payload)
            except Exception:
                return None
    return None


def save(doc: ExtractedDocument, raw_bytes: bytes) -> Path:
    """Persist *doc* and the original *raw_bytes* under DATA_PATH/evidence."""
    target = doc_dir(doc.doc_id)
    (target / "raw").mkdir(parents=True, exist_ok=True)

    raw_path = target / "raw" / doc.filename
    raw_path.write_bytes(raw_bytes)

    meta_path = target / "extracted.json"
    meta_path.write_text(
        doc.model_dump_json(indent=2),
        encoding="utf-8",
    )

    preview_path = target / "preview.md"
    preview_path.write_text(
        (doc.extracted_text or "")[:_PREVIEW_BYTES],
        encoding="utf-8",
    )
    return target


def load(doc_id: str) -> Optional[ExtractedDocument]:
    meta = doc_dir(doc_id) / "extracted.json"
    if not meta.is_file():
        return None
    try:
        return ExtractedDocument.model_validate_json(meta.read_text(encoding="utf-8"))
    except Exception:
        return None


def raw_path(doc_id: str) -> Optional[Path]:
    """Return the path of the original uploaded file, or None if missing."""
    raw_dir = doc_dir(doc_id) / "raw"
    if not raw_dir.is_dir():
        return None
    files = [p for p in raw_dir.iterdir() if p.is_file()]
    return files[0] if files else None


def utc_now() -> datetime:
    """Timestamp helper kept here so tests can monkeypatch one location."""
    return datetime.now(timezone.utc)
