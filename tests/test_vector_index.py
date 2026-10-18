"""P2 unit and integration tests: chunking, local embeddings, and vector indexing.

Tests verify:
- Chunking creates stable IDs and preserves provenance (url/file, page).
- Local embedding provider produces correct vector dimensions (384 for MiniLM).
- Vector index upserts chunks and retrieves the expected chunk for a known query.
"""

from pathlib import Path

import pytest

from amd_hardware_advisor.chunking import chunk_document, chunk_documents, split_text
from amd_hardware_advisor.embeddings import LocalEmbeddingProvider
from amd_hardware_advisor.ingestion import SourceDoc
from amd_hardware_advisor.vector_index import VectorIndex


# --- Chunking tests ---


def test_split_text_sliding_window():
    text = "Paragraph one is here.\n\nParagraph two has more text to split across windows."
    chunks = list(split_text(text, chunk_size=30, overlap=5))
    assert len(chunks) > 1
    for start, length, chunk_str in chunks:
        assert len(chunk_str) <= 45  # roughly chunk_size with break tolerance


def test_chunk_document_preserves_provenance():
    doc = SourceDoc(
        id="test_id_123",
        text="AMD Instinct MI300X features 192 GB HBM3 memory.",
        source_type="pdf",
        source_url_or_file="dummy.pdf",
        title="Dummy PDF",
        page=3,
        pages=5,
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_id
    assert c.source_id == "test_id_123"
    assert c.source_url_or_file == "dummy.pdf"
    assert c.page == 3
    assert "MI300X" in c.text


def test_chunk_documents_batch():
    docs = [
        SourceDoc(id="d1", text="Doc one text here.", source_type="pdf", source_url_or_file="a.pdf", title="A"),
        SourceDoc(id="d2", text="Doc two text here.", source_type="pdf", source_url_or_file="b.pdf", title="B"),
    ]
    chunks = chunk_documents(docs)
    assert len(chunks) >= 2
    assert {chunk.source_id for chunk in chunks} == {"d1", "d2"}


# --- Embeddings tests (offline CPU) ---


def test_local_embedding_provider_dim():
    embedder = LocalEmbeddingProvider("all-MiniLM-L6-v2")
    assert embedder.dim == 384
    assert "sentence-transformers" in embedder.name


def test_local_embedding_generation():
    embedder = LocalEmbeddingProvider("all-MiniLM-L6-v2")
    vec = embedder.embed_query("What is AMD MI300X?")
    assert isinstance(vec, list)
    assert len(vec) == 384
    assert isinstance(vec[0], float)

    vecs = embedder.embed_texts(["Hello AMD", "ROCm computing"])
    assert len(vecs) == 2
    assert len(vecs[0]) == 384


# --- Vector Index & Retrieval integration test ---


def test_vector_index_upsert_and_query(tmp_path):
    """End-to-end P2 test: chunk a test doc, embed it, upsert into Chroma, and query it.
    Verify that a known query retrieves the expected chunk."""
    # 1. Create test doc
    doc = SourceDoc(
        id="doc_mi300",
        text="AMD Instinct MI300X is an accelerator with 192 GB of HBM3 memory designed for large language models.",
        source_type="html",
        source_url_or_file="https://www.amd.com/mi300x",
        title="MI300X Page",
        page=None,
    )

    # 2. Chunk
    chunks = chunk_document(doc)
    assert len(chunks) == 1

    # 3. Embed
    embedder = LocalEmbeddingProvider("all-MiniLM-L6-v2")
    embeddings = embedder.embed_texts([c.text for c in chunks])

    # 4. Index (ephemeral temp path for testing)
    index_path = tmp_path / "chroma_test_index"
    index = VectorIndex(persist_dir=index_path, collection_name="test_collection")
    index.upsert(chunks, embeddings)
    assert index.count() == 1

    # 5. Query
    query_text = "How much memory does MI300X have?"
    query_vec = embedder.embed_query(query_text)
    results = index.query(query_vec, top_k=1)

    assert len(results) == 1
    top = results[0]
    assert top.chunk_id == chunks[0].chunk_id
    assert "192 GB" in top.text
    assert top.source_url_or_file == "https://www.amd.com/mi300x"
    assert top.score > 0.5  # high cosine similarity for exact match
