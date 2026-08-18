"""Document ingest pipeline — parses uploaded evidence files into a
normalized ``ExtractedDocument`` (text + sections + tables) and persists
the result under ``DATA_PATH/evidence/{doc_id}/``.

Public API:
    parse_bytes(data, filename) -> tuple[str, list[Section], list[Table]]
    SUPPORTED_EXTENSIONS                 — set of accepted file suffixes
    UnsupportedFormatError               — raised for rejected formats

ChromaDB indexing and chunking are intentionally out of scope for this
module (deferred to PR (b)). Keeping the boundary explicit makes the unit
tests fast and side-effect free.
"""

from .base import (
    SUPPORTED_EXTENSIONS,
    UnsupportedFormatError,
    guess_mime_type,
    parse_bytes,
)
from .chunker import Chunk, chunk_text
from .indexer import EVIDENCE_COLLECTION, EvidenceIndexer

__all__ = [
    "SUPPORTED_EXTENSIONS",
    "UnsupportedFormatError",
    "guess_mime_type",
    "parse_bytes",
    "Chunk",
    "chunk_text",
    "EvidenceIndexer",
    "EVIDENCE_COLLECTION",
]
