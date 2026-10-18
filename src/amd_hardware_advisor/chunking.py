"""Recursive text chunking with stable IDs and provenance carrying.

Splits SourceDocs into overlapping chunks suitable for embedding and retrieval.
Each Chunk carries provenance metadata (source url/file, page, section, chunk_id)
so citations can be traced back precisely.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Iterator

from amd_hardware_advisor.ingestion import SourceDoc

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A text chunk with provenance metadata for vector storage and citation tracing."""

    chunk_id: str
    text: str
    source_id: str
    source_url_or_file: str
    page: int | None
    section: str | None
    char_offset: int
    char_len: int


def _compute_chunk_id(source_id: str, offset: int, text: str) -> str:
    """Stable chunk ID hash derived from source id, offset, and text prefix."""
    raw = f"{source_id}:{offset}:{text[:64]}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def split_text(text: str, chunk_size: int = 700, overlap: int = 100) -> Iterator[tuple[int, int, str]]:
    """Simple recursive/sliding window text splitter.

    Yields (offset, length, chunk_text). Splits on paragraph boundaries (\n\n) or
    sentences/spaces where possible, falling back to hard character slices.
    """
    if not text:
        return

    text_len = len(text)
    start = 0

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # If we aren't at the end of the text, try to find a natural break (newline or space)
        if end < text_len:
            # Look for paragraph break first
            break_pos = text.rfind("\n\n", start + chunk_size // 2, end)
            if break_pos != -1:
                end = break_pos + 2
            else:
                # Look for single newline or space
                break_pos = text.rfind("\n", start + chunk_size // 2, end)
                if break_pos != -1:
                    end = break_pos + 1
                else:
                    break_pos = text.rfind(" ", start + chunk_size // 2, end)
                    if break_pos != -1:
                        end = break_pos + 1

        chunk_str = text[start:end].strip()
        if chunk_str:
            yield (start, len(chunk_str), chunk_str)

        if end >= text_len:
            break
        # Advance by chunk_size - overlap
        start = max(start + 1, end - overlap)


def chunk_document(
    doc: SourceDoc, chunk_size: int = 700, overlap: int = 100
) -> list[Chunk]:
    """Split a SourceDoc into multiple Chunks carrying full provenance metadata."""
    chunks: list[Chunk] = []
    for offset, length, text in split_text(doc.text, chunk_size=chunk_size, overlap=overlap):
        cid = _compute_chunk_id(doc.id, offset, text)
        chunks.append(
            Chunk(
                chunk_id=cid,
                text=text,
                source_id=doc.id,
                source_url_or_file=doc.source_url_or_file,
                page=doc.page,
                section=None,  # Section extraction can be added if needed
                char_offset=offset,
                char_len=length,
            )
        )
    logger.debug("chunked doc %s into %d chunks", doc.id, len(chunks))
    return chunks


def chunk_documents(
    docs: list[SourceDoc], chunk_size: int = 700, overlap: int = 100
) -> list[Chunk]:
    """Chunk a list of SourceDocs."""
    all_chunks: list[Chunk] = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc, chunk_size=chunk_size, overlap=overlap))
    logger.info("chunked %d SourceDoc(s) into %d total Chunk(s)", len(docs), len(all_chunks))
    return all_chunks


__all__ = ["Chunk", "chunk_document", "chunk_documents", "split_text"]
