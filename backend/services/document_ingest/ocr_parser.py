"""OCR parser — extracts text from scanned PDFs and images via Tesseract.

Requires ``pytesseract``, ``pdf2image``, and ``Pillow``.  The Tesseract
binary and language data (vie + eng) must be installed at the OS level.

When the dependencies are missing the parser raises ``ImportError`` with
an actionable install message — same pattern as the other parsers.
"""

from __future__ import annotations

import io
import logging
from typing import List

from api.schemas.document import Section, Table

from .base import ParserResult, register

logger = logging.getLogger(__name__)

# Minimum character count to consider OCR output useful.
_MIN_USEFUL_OCR_CHARS = 30


def _ensure_tesseract():
    """Lazy-import and return (pytesseract, PIL.Image). Raises ImportError if missing."""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
        return pytesseract, Image
    except ImportError as exc:
        raise ImportError(
            "pytesseract and Pillow are required for OCR. "
            "Install with: pip install pytesseract Pillow"
        ) from exc


def _ensure_pdf2image():
    """Lazy-import pdf2image. Raises ImportError if missing."""
    try:
        from pdf2image import convert_from_bytes  # type: ignore
        return convert_from_bytes
    except ImportError as exc:
        raise ImportError(
            "pdf2image is required for PDF OCR. "
            "Install with: pip install pdf2image"
        ) from exc


def _ocr_image(image) -> str:
    """Run Tesseract OCR on a PIL Image object. Returns extracted text."""
    pytesseract, _ = _ensure_tesseract()
    try:
        text = pytesseract.image_to_string(image, lang="vie+eng")
        return (text or "").strip()
    except Exception as exc:
        logger.warning("OCR failed on image: %s", exc)
        return ""


@register("png", "jpg", "jpeg", "bmp", "tiff", "tif")
def parse_image(data: bytes) -> ParserResult:
    """Extract text from image files using Tesseract OCR."""
    pytesseract, Image = _ensure_tesseract()

    try:
        image = Image.open(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"Cannot open image: {exc}") from exc

    text = _ocr_image(image)

    if len(text) < _MIN_USEFUL_OCR_CHARS:
        sections = [
            Section(
                heading="warning",
                body="OCR extracted very little text from this image. "
                     "The image may be low quality or contain no readable text.",
                level=0,
            )
        ]
    else:
        sections = [Section(heading="OCR Result", body=text, level=1)]

    return text, sections, []


def ocr_pdf(data: bytes) -> ParserResult:
    """Extract text from a scanned PDF by converting pages to images and running OCR.

    This is called as a fallback from ``pdf_parser.parse_pdf`` when pypdf
    extracts insufficient text.  It is NOT registered as a direct parser
    for the ``pdf`` extension — that would conflict with the primary parser.
    """
    convert_from_bytes = _ensure_pdf2image()

    try:
        images = convert_from_bytes(data, dpi=200)
    except Exception as exc:
        logger.warning("pdf2image conversion failed: %s", exc)
        return "", [
            Section(
                heading="warning",
                body=f"PDF-to-image conversion failed: {exc}",
                level=0,
            )
        ], []

    sections: List[Section] = []
    text_parts: list[str] = []

    for idx, image in enumerate(images, start=1):
        page_text = _ocr_image(image)
        sections.append(
            Section(heading=f"Page {idx} (OCR)", body=page_text, level=1)
        )
        if page_text:
            text_parts.append(page_text)

    full_text = "\n\n".join(text_parts).strip()

    if len(full_text) < _MIN_USEFUL_OCR_CHARS:
        sections.insert(
            0,
            Section(
                heading="warning",
                body="OCR could not extract meaningful text from this scanned PDF.",
                level=0,
            ),
        )

    return full_text, sections, []
