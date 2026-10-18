"""Persistent vector index wrapper using ChromaDB.

Stores chunks, embeddings, and provenance metadata in an embedded Chroma client
persisted to index/ (or a configured directory). Supports upserting batches and
querying by vector with top-k retrieval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from amd_hardware_advisor.chunking import Chunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved chunk with similarity score and provenance metadata."""

    chunk_id: str
    text: str
    score: float
    source_url_or_file: str
    page: int | None
    section: str | None
    source_id: str


class VectorIndex:
    """ChromaDB-backed vector store for RAG chunks."""

    def __init__(self, persist_dir: str | Path = "index", collection_name: str = "amd_docs") -> None:
        self.persist_dir = Path(persist_dir)
        self.collection_name = collection_name

        # Ensure persist directory exists
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        logger.info("initializing ChromaDB PersistentClient at %s", self.persist_dir)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("vector collection %r ready (count=%d)", self.collection_name, self._collection.count())

    def count(self) -> int:
        return self._collection.count()

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upsert chunks and their precomputed embeddings into Chroma."""
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError(f"mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings")

        ids = [c.chunk_id for c in chunks]
        texts = [c.text for c in chunks]
        metadatas: list[dict[str, Any]] = []

        for c in chunks:
            metadatas.append({
                "source_id": c.source_id,
                "source_url_or_file": c.source_url_or_file,
                "page": c.page if c.page is not None else -1,
                "section": c.section or "",
                "char_offset": c.char_offset,
                "char_len": c.char_len,
            })

        # Chroma upsert in batches of 500
        batch_size = 500
        for i in range(0, len(chunks), batch_size):
            end = i + batch_size
            self._collection.upsert(
                ids=ids[i:end],
                documents=texts[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
            )
        logger.info("upserted %d chunks into collection %r", len(chunks), self.collection_name)

    def query(self, query_vector: list[float], top_k: int = 5) -> list[RetrievedChunk]:
        """Query the vector index by embedding vector and return top-k results."""
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=min(top_k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        retrieved: list[RetrievedChunk] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return retrieved

        ids = results["ids"][0]
        docs = results["documents"][0] if results["documents"] else ["" * len(ids)]
        metas = results["metadatas"][0] if results["metadatas"] else [{}] * len(ids)
        distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)

        for cid, doc, meta, dist in zip(ids, docs, metas, distances):
            # Chroma cosine distance -> similarity score (1 - distance)
            score = float(1.0 - dist)
            page_val = meta.get("page")
            page = int(page_val) if page_val is not None and page_val != -1 else None

            retrieved.append(
                RetrievedChunk(
                    chunk_id=cid,
                    text=doc,
                    score=score,
                    source_url_or_file=str(meta.get("source_url_or_file", "")),
                    page=page,
                    section=str(meta.get("section", "")) or None,
                    source_id=str(meta.get("source_id", "")),
                )
            )

        return retrieved

    def clear(self) -> None:
        """Delete and recreate the collection (useful for testing/re-indexing)."""
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("cleared collection %r", self.collection_name)


__all__ = ["VectorIndex", "RetrievedChunk"]
