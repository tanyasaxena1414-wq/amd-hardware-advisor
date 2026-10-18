"""Citation assembly and mapping module.

Maps referenced chunk IDs back to source metadata (URL or file, page, section)
and formats verifiable citations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from amd_hardware_advisor.vector_index import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """A verifiable citation pointing to an official AMD source document."""

    index: int
    chunk_id: str
    source_url_or_file: str
    page: int | None
    section: str | None


def assemble_citations(retrieved_chunks: list[RetrievedChunk], used_chunk_ids: list[str]) -> list[Citation]:
    """Map used chunk IDs back to source metadata, deduplicating while preserving order."""
    seen_ids = set()
    citations: list[Citation] = []
    index = 1

    # Map chunk_id to RetrievedChunk for quick lookup
    chunk_map = {c.chunk_id: c for c in retrieved_chunks}

    # Also keep any chunks referenced by the model
    for cid in used_chunk_ids:
        if cid in chunk_map and cid not in seen_ids:
            seen_ids.add(cid)
            c = chunk_map[cid]
            citations.append(
                Citation(
                    index=index,
                    chunk_id=c.chunk_id,
                    source_url_or_file=c.source_url_or_file,
                    page=c.page,
                    section=c.section,
                )
            )
            index += 1

    # If the model didn't explicitly reference chunk IDs but we retrieved chunks,
    # include top retrieved chunks as grounded citations so answers are never uncited.
    if not citations and retrieved_chunks:
        for c in retrieved_chunks[:3]:
            if c.chunk_id not in seen_ids:
                seen_ids.add(c.chunk_id)
                citations.append(
                    Citation(
                        index=index,
                        chunk_id=c.chunk_id,
                        source_url_or_file=c.source_url_or_file,
                        page=c.page,
                        section=c.section,
                    )
                )
                index += 1

    return citations


__all__ = ["Citation", "assemble_citations"]
