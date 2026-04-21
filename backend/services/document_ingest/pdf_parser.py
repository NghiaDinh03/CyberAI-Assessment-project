"""PDF parser — text-layer only via ``pypdf``.

Scanned/image-only PDFs return very little text; per Section 9.A of
context.md we explicitly defer OCR to a later phase. When the extracted
text is below :data:`_MIN_USEFUL_CHARS` we surface a single Section with a
warning so the UI can prompt the user to re-upload a text-based PDF.
"""

from __future__ import annotations

import io
from typing import List

from api.schemas.document import Section, Table

from .base import ParserResult, register

_MIN_USEFUL_CHARS = 50


@register("pdf")
def parse_pdf(data: bytes) -> ParserResult:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "pypdf is required to parse .pdf files. "
            "Install it with: pip install pypdf"
        ) from exc

    reader = PdfReader(io.BytesIO(data))

    if reader.is_encrypted:
        # Try empty-password first (common for "view-only" PDFs); fall back
        # to a clear error so the route can return a useful 4xx.
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError("PDF is password-protected") from exc

    sections: List[Section] = []
    text_lines: list[str] = []

    for idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            # pypdf can raise on malformed content streams; treat as empty.
            page_text = ""
        page_text = page_text.strip()
        sections.append(
            Section(heading=f"Page {idx}", body=page_text, level=1)
        )
        if page_text:
            text_lines.append(page_text)

    full_text = "\n\n".join(text_lines).strip()

    if len(full_text) < _MIN_USEFUL_CHARS:
        sections.insert(
            0,
            Section(
                heading="warning",
                body=(
                    "PDF appears to contain no extractable text "
                    "(likely a scanned image). OCR is not enabled."
                ),
                level=0,
            ),
        )

    return full_text, sections, []
