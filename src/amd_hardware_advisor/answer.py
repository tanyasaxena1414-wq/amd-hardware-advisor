"""Grounded answer generation with citations and fallback handling for unanswerable queries."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from amd_hardware_advisor.citations import Citation, assemble_citations
from amd_hardware_advisor.llm.provider import LLMProvider, get_llm_provider
from amd_hardware_advisor.vector_index import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class AnswerResult:
    """Result of grounded question answering."""

    answer: str
    citations: list[Citation] = field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    is_answerable: bool = True


SYSTEM_PROMPT = """You are the official AMD Hardware Advisor, an expert assistant that answers questions about AMD hardware (Instinct accelerators, EPYC CPUs, Radeon GPUs, ROCm software) strictly using the provided official AMD documentation chunks.

RULES:
1. Ground your answer ONLY in the provided context chunks. Never invent hardware specifications, part numbers, or citations.
2. Every factual claim or spec must include a citation marker referencing the chunk ID in brackets, e.g. [chunk_id:abcdef1234567890].
3. If the provided context chunks do not contain enough information to answer the question, you MUST state clearly: "I cannot answer this question from the provided official AMD documentation." Do not guess or extrapolate.
4. Keep answers professional, clear, and direct."""


def answer_query(
    query: str,
    retrieved_chunks: list[RetrievedChunk],
    provider: LLMProvider | None = None,
) -> AnswerResult:
    """Generate a grounded answer using retrieved documentation chunks and an LLM provider."""
    provider = provider or get_llm_provider()

    if not retrieved_chunks:
        return AnswerResult(
            answer="I cannot answer this question from the provided official AMD documentation (no relevant documents retrieved).",
            citations=[],
            retrieved_chunks=[],
            is_answerable=False,
        )

    # Build context string from retrieved chunks
    context_blocks = []
    for i, c in enumerate(retrieved_chunks, start=1):
        source_label = c.source_url_or_file
        if c.page:
            source_label += f" (page {c.page})"
        block = f"--- Source [{i}] (chunk_id: {c.chunk_id}) ---\nSource: {source_label}\n{c.text}\n"
        context_blocks.append(block)

    context_str = "\n".join(context_blocks)

    user_prompt = f"""Context documents:
{context_str}

User Question: {query}

Answer the question based strictly on the context above, cite chunk IDs, or state if it cannot be answered."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw_answer = provider.chat(messages, temperature=0.1)
    except Exception as exc:
        logger.error("LLM chat failed during answer generation: %s", exc)
        return AnswerResult(
            answer=f"Error generating answer via provider {provider.provider_name}: {exc}",
            citations=[],
            retrieved_chunks=retrieved_chunks,
            is_answerable=False,
        )

    # Check for unanswerable signals in the model output
    unanswerable_phrases = [
        "cannot answer this question",
        "do not contain enough information",
        "not provided in the context",
    ]
    is_answerable = not any(p in raw_answer.lower() for p in unanswerable_phrases)

    # Extract cited chunk IDs from model output using regex matching chunk ids
    cited_ids = re.findall(r"chunk_id:\s*([a-f0-9]{16})", raw_answer)
    if not cited_ids:
        # Also look for bracketed IDs
        cited_ids = re.findall(r"\[([a-f0-9]{16})\]", raw_answer)

    citations = assemble_citations(retrieved_chunks, cited_ids)

    return AnswerResult(
        answer=raw_answer,
        citations=citations,
        retrieved_chunks=retrieved_chunks,
        is_answerable=is_answerable,
    )


__all__ = ["AnswerResult", "answer_query"]
