"""Retrieval module: embeds queries and fetches top-k chunks from ChromaDB."""

from __future__ import annotations

import logging
from pathlib import Path

from amd_hardware_advisor.embeddings import LocalEmbeddingProvider
from amd_hardware_advisor.vector_index import RetrievedChunk, VectorIndex
from config.settings import get_settings

logger = logging.getLogger(__name__)

# Global instances for reuse across queries
_EMBEDDER: LocalEmbeddingProvider | None = None
_INDEX: VectorIndex | None = None


def get_embedder() -> LocalEmbeddingProvider:
    global _EMBEDDER
    if _EMBEDDER is None:
        settings = get_settings()
        _EMBEDDER = LocalEmbeddingProvider(settings.embedding_model)
    return _EMBEDDER


def get_vector_index() -> VectorIndex:
    global _INDEX
    if _INDEX is None:
        settings = get_settings()
        index_dir = Path("index")
        _INDEX = VectorIndex(persist_dir=index_dir, collection_name="amd_docs")
    return _INDEX


def retrieve(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    """Retrieve top-k relevant chunks for a user query."""
    if not query or not query.strip():
        return []

    settings = get_settings()
    k = top_k if top_k is not None else settings.top_k

    embedder = get_embedder()
    index = get_vector_index()

    query_vector = embedder.embed_query(query.strip())
    results = index.query(query_vector, top_k=k)
    logger.info("retrieved %d chunks for query %r (top score=%.3f)", len(results), query, results[0].score if results else 0.0)
    return results


__all__ = ["retrieve", "get_embedder", "get_vector_index"]
