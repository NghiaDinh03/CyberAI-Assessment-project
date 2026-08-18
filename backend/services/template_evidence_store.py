"""JSON-based mapping of evidence documents to assessment templates.

Each template gets a JSON file at ``DATA_PATH/template_evidence/{template_id}.json``
containing an array of evidence metadata entries. Actual document bytes and
extracted text live in the existing ``data/evidence/{doc_id}/`` tree managed by
:mod:`services.document_ingest.storage`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class TemplateEvidenceItem(BaseModel):
    """Metadata for one evidence document linked to a template."""

    doc_id: str
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: str
    preview: str = ""


class TemplateEvidenceManifest(BaseModel):
    """On-disk manifest for a single template's evidence list."""

    template_id: str
    evidence: List[TemplateEvidenceItem] = Field(default_factory=list)


def _store_root() -> Path:
    base = os.getenv("DATA_PATH", "./data")
    root = Path(base) / "template_evidence"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _manifest_path(template_id: str) -> Path:
    return _store_root() / f"{template_id}.json"


def load_manifest(template_id: str) -> TemplateEvidenceManifest:
    """Load the evidence manifest for *template_id*, creating if absent."""
    path = _manifest_path(template_id)
    if path.is_file():
        try:
            return TemplateEvidenceManifest.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            pass
    return TemplateEvidenceManifest(template_id=template_id)


def save_manifest(manifest: TemplateEvidenceManifest) -> None:
    path = _manifest_path(manifest.template_id)
    path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def add_evidence(
    template_id: str,
    doc_id: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    uploaded_at: datetime,
    preview: str = "",
) -> TemplateEvidenceItem:
    """Append an evidence entry to the template manifest and persist."""
    manifest = load_manifest(template_id)
    item = TemplateEvidenceItem(
        doc_id=doc_id,
        filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        uploaded_at=uploaded_at.isoformat(),
        preview=preview,
    )
    manifest.evidence.append(item)
    save_manifest(manifest)
    return item


def list_evidence(template_id: str) -> List[TemplateEvidenceItem]:
    """Return all evidence items for *template_id*."""
    return load_manifest(template_id).evidence


def find_evidence(template_id: str, doc_id: str) -> Optional[TemplateEvidenceItem]:
    """Find a specific evidence item by doc_id within a template."""
    for item in load_manifest(template_id).evidence:
        if item.doc_id == doc_id:
            return item
    return None
