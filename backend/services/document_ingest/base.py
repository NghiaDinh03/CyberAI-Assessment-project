"""Parser registry and dispatch for the document ingest pipeline.

Each parser is a pure function ``(data: bytes) -> (text, sections, tables)``
registered against one or more lowercase file-extension suffixes (without
the dot). The dispatcher in :func:`parse_bytes` selects the parser by the
filename's suffix; unknown suffixes raise :class:`UnsupportedFormatError`.

Parsers MUST NOT perform I/O or network calls — they receive raw bytes and
return python objects only. Storage and HTTP concerns live elsewhere.
"""

from __future__ import annotations

import os
from typing import Callable, List, Tuple

from api.schemas.document import Section, Table

ParserResult = Tuple[str, List[Section], List[Table]]
ParserFn = Callable[[bytes], ParserResult]


class UnsupportedFormatError(ValueError):
    """Raised when no parser is registered for the given file extension."""


# Lowercase extension (no leading dot) -> parser callable.
# Populated below after parser modules are imported.
_REGISTRY: dict[str, ParserFn] = {}


def register(*extensions: str) -> Callable[[ParserFn], ParserFn]:
    """Decorator: bind a parser function to one or more file extensions."""

    def _wrap(fn: ParserFn) -> ParserFn:
        for ext in extensions:
            _REGISTRY[ext.lower().lstrip(".")] = fn
        return fn

    return _wrap


def _file_extension(filename: str) -> str:
    """Return the lowercase extension of *filename* without the dot."""
    _, ext = os.path.splitext(filename or "")
    return ext.lower().lstrip(".")


# MIME map kept tiny on purpose — only formats we actually parse. Anything
# else falls through to ``application/octet-stream`` so we never lie about
# content type for an unsupported file.
_MIME_BY_EXT: dict[str, str] = {
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def guess_mime_type(filename: str) -> str:
    """Best-effort MIME lookup driven by the file extension."""
    return _MIME_BY_EXT.get(_file_extension(filename), "application/octet-stream")


def parse_bytes(data: bytes, filename: str) -> ParserResult:
    """Dispatch *data* to the parser registered for *filename*'s extension.

    Raises:
        UnsupportedFormatError: when no parser handles the extension.
        ValueError: when the parser itself rejects malformed input.
    """
    ext = _file_extension(filename)
    parser = _REGISTRY.get(ext)
    if parser is None:
        raise UnsupportedFormatError(
            f"Unsupported file extension '.{ext}'. "
            f"Allowed: {sorted(_REGISTRY)}"
        )
    return parser(data)


# Import parser modules so their @register decorators populate the registry.
# Imports are placed after register() is defined to avoid a circular import.
from . import docx_parser  # noqa: E402,F401
from . import pdf_parser  # noqa: E402,F401
from . import text_parser  # noqa: E402,F401
from . import xlsx_parser  # noqa: E402,F401

SUPPORTED_EXTENSIONS = frozenset(_REGISTRY)
