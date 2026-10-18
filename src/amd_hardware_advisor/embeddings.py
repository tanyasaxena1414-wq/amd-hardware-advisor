"""Local embeddings wrapper using sentence-transformers (all-MiniLM-L6-v2).

Runs CPU-only on Windows; zero external API dependency. Conforms to the embedding
provider pattern so it can be swapped if needed.
"""

from __future__ import annotations

import logging
from typing import Protocol

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
    @property
    def dim(self) -> int: ...
    @property
    def name(self) -> str: ...


class LocalEmbeddingProvider:
    """Sentence-transformers embedding provider running locally on CPU."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        logger.info("loading embedding model %s (local CPU)...", model_name)
        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dim = int(self._model.get_sentence_embedding_dimension())
        logger.info("embedding model loaded successfully (dim=%d)", self._dim)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self._dim
        vector = self._model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        return vector.tolist()

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return f"sentence-transformers/{self._model_name}"


__all__ = ["EmbeddingProvider", "LocalEmbeddingProvider"]
