"""Token-aware chunker for ingested evidence documents.

Tokenization is approximated by character count (≈4 chars per token for
English / Vietnamese mixed text) so we don't add a tiktoken / transformers
dependency just for chunk sizing. The defaults map to:

    chunk_tokens = 700  → ~2800 chars
    overlap_tokens = 80 → ~320 chars

These match the ranges given in :file:`context.md` §7.2 / §9.A while
keeping chunks well below typical embedding-model context windows.

Splitting is greedy on paragraph boundaries first, then on sentence-ish
boundaries (``. `` / ``\n``) so chunks stay semantically coherent without
needing a heavyweight NLP library.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

# Average bytes of UTF-8 per LLM token, empirically ~4 for mixed Latin/
# Vietnamese corpora. Off-by-a-bit is fine: the chunker only needs a
# stable upper bound on chunk length.
_CHARS_PER_TOKEN = 4


def _to_chars(tokens: int) -> int:
    return max(1, tokens * _CHARS_PER_TOKEN)


@dataclass(frozen=True)
class Chunk:
    """One chunk ready for embedding/upsert.

    ``index`` is monotonically increasing within a document so callers
    can reconstruct ordering after retrieval.
    """

    index: int
    text: str


def chunk_text(
    text: str,
    *,
    chunk_tokens: int = 700,
    overlap_tokens: int = 80,
) -> List[Chunk]:
    """Split *text* into overlapping chunks.

    The result is empty when *text* is empty / whitespace-only — callers
    must treat zero chunks as a valid (no-op) outcome.
    """
    if not text or not text.strip():
        return []
    if chunk_tokens <= 0:
        raise ValueError("chunk_tokens must be positive")
    if overlap_tokens < 0 or overlap_tokens >= chunk_tokens:
        raise ValueError("overlap_tokens must be in [0, chunk_tokens)")

    max_chars = _to_chars(chunk_tokens)
    overlap_chars = _to_chars(overlap_tokens)

    # First pass: greedy paragraph packing keeps semantic units intact.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    buf = ""
    for para in paragraphs:
        if len(para) > max_chars:
            # A monster paragraph: flush current buffer, then hard-split.
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(_hard_split(para, max_chars))
            continue

        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            chunks.append(buf)
            buf = para
    if buf:
        chunks.append(buf)

    # Second pass: prepend an overlap tail from the previous chunk so the
    # boundary preserves context for retrieval.
    if overlap_chars and len(chunks) > 1:
        with_overlap: List[str] = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap_chars:]
            with_overlap.append(f"{tail}\n{chunks[i]}".strip())
        chunks = with_overlap

    return [Chunk(index=i, text=c) for i, c in enumerate(chunks)]


def _hard_split(paragraph: str, max_chars: int) -> Iterable[str]:
    """Split an oversized paragraph on sentence-ish boundaries.

    Falls back to a fixed-window slice when no boundary is found inside
    the next ``max_chars`` window.
    """
    remainder = paragraph
    while len(remainder) > max_chars:
        window = remainder[:max_chars]
        # Prefer breaking at the last full stop / newline / Vietnamese
        # period within the window so chunks end on a sentence.
        for sep in (". ", "\n", "。", "! ", "? "):
            idx = window.rfind(sep)
            if idx >= max_chars // 2:
                cut = idx + len(sep)
                yield remainder[:cut].strip()
                remainder = remainder[cut:].strip()
                break
        else:
            yield window.strip()
            remainder = remainder[max_chars:].strip()
    if remainder:
        yield remainder
