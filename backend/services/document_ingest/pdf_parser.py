"""PDF parser — text-layer via ``pypdf`` with OCR fallback for scanned PDFs.

When pypdf extracts fewer than :data:`_MIN_USEFUL_CHARS` characters the
parser automatically falls back to Tesseract OCR (via ``ocr_parser.ocr_pdf``).
If OCR dependencies are unavailable, a warning section is returned so the
UI can prompt the user.
"""

from __future__ import annotations

import io
import logging
from typing import List

from api.schemas.document import Section, Table

from .base import ParserResult, register

logger = logging.getLogger(__name__)

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
            page_text = ""
        page_text = page_text.strip()
        sections.append(
            Section(heading=f"Page {idx}", body=page_text, level=1)
        )
        if page_text:
            text_lines.append(page_text)

    full_text = "\n\n".join(text_lines).strip()

    # OCR fallback for scanned/image-only PDFs
    if len(full_text) < _MIN_USEFUL_CHARS:
        logger.info(
            "[PDF] Extracted only %d chars — attempting OCR fallback",
            len(full_text),
        )
        try:
            from .ocr_parser import ocr_pdf  # noqa: WPS433

            ocr_text, ocr_sections, ocr_tables = ocr_pdf(data)
            if ocr_text and len(ocr_text) >= _MIN_USEFUL_CHARS:
                logger.info("[PDF] OCR fallback succeeded (%d chars)", len(ocr_text))
                return ocr_text, ocr_sections, ocr_tables
            else:
                logger.info("[PDF] OCR fallback produced insufficient text")
        except ImportError:
            logger.info("[PDF] OCR dependencies not available — skipping fallback")
        except Exception as exc:
            logger.warning("[PDF] OCR fallback failed: %s", exc)

        # Final fallback: warning section
        sections.insert(
            0,
            Section(
                heading="warning",
                body=(
                    "PDF appears to contain no extractable text "
                    "(likely a scanned image). Install pytesseract + pdf2image "
                    "to enable OCR for scanned documents."
                ),
                level=0,
            ),
        )

    return full_text, sections, []
