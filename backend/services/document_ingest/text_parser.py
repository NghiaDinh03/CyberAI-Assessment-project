"""Plain-text parsers (.txt, .md, .csv).

These rely only on the standard library; they are the safety net used by
unit tests that must run even when ``python-docx`` / ``openpyxl`` /
``pypdf`` are not installed.
"""

from __future__ import annotations

import csv
import io
from typing import List

from api.schemas.document import Section, Table

from .base import ParserResult, register


def _decode(data: bytes) -> str:
    """Decode bytes as UTF-8, falling back to latin-1 to avoid hard failures
    on legacy/Windows-encoded evidence files.
    """
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1", errors="replace")


@register("txt")
def parse_txt(data: bytes) -> ParserResult:
    text = _decode(data)
    return text, [], []


@register("md")
def parse_md(data: bytes) -> ParserResult:
    """Markdown: keep raw text and split sections at ATX headings (``#``)."""
    text = _decode(data)
    sections: List[Section] = []

    current_heading = ""
    current_level = 0
    current_body: list[str] = []

    def _flush() -> None:
        if current_heading or current_body:
            sections.append(
                Section(
                    heading=current_heading,
                    body="\n".join(current_body).strip(),
                    level=current_level,
                )
            )

    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # Count leading '#' (cap at 6 per CommonMark) for the level.
            hashes = len(stripped) - len(stripped.lstrip("#"))
            if 1 <= hashes <= 6 and (len(stripped) == hashes or stripped[hashes] == " "):
                _flush()
                current_heading = stripped[hashes:].strip()
                current_level = hashes
                current_body = []
                continue
        current_body.append(line)
    _flush()

    return text, sections, []


@register("csv")
def parse_csv(data: bytes) -> ParserResult:
    """CSV: surface as a single Table; ``extracted_text`` keeps the raw view."""
    text = _decode(data)
    reader = csv.reader(io.StringIO(text))
    rows = [list(row) for row in reader]

    if not rows:
        return text, [], []

    headers, body = rows[0], rows[1:]
    table = Table(name="csv", headers=headers, rows=body)
    return text, [], [table]
