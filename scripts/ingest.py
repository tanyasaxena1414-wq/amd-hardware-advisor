"""CLI script to build or rebuild the RAG index from ingested documents.

P2 implementation: loads documents, chunks them, embeds them locally using sentence-transformers,
and upserts them into ChromaDB persistent storage at index/.

Usage:
    python scripts/ingest.py --build-index             # build vector index from curated sources (fetch URLs)
    python scripts/ingest.py --build-index --local-pdf   # build vector index from local PDFs only
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running as a script: put src/ and project root on the path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from amd_hardware_advisor.catalogue import load_catalogue  # noqa: E402
from amd_hardware_advisor.chunking import chunk_documents  # noqa: E402
from amd_hardware_advisor.embeddings import LocalEmbeddingProvider  # noqa: E402
from amd_hardware_advisor.ingestion import load_documents  # noqa: E402
from amd_hardware_advisor.vector_index import VectorIndex  # noqa: E402

DOC_SOURCES = [
    "https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/data-sheets/amd-instinct-mi300a-data-sheet.pdf",
    "https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/data-sheets/amd-instinct-mi300x-data-sheet.pdf",
    "https://rocm.docs.amd.com/en/latest/install/rocm.html",
    "https://rocm.docs.amd.com/en/latest/about/release-notes.html",
]

CATALOGUE_PATH = PROJECT_ROOT / "data" / "catalogue" / "catalogue.yaml"
LOCAL_DOCS_DIR = PROJECT_ROOT / "data" / "docs"
INDEX_DIR = PROJECT_ROOT / "index"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest AMD docs, validate catalogue, and build vector index.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List docs and validate the catalogue without building the index (P1 gate).",
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Build/rebuild the ChromaDB vector index from sources (P2 execution).",
    )
    parser.add_argument(
        "--fetch-urls",
        action="store_true",
        help="Fetch curated AMD doc URLs over the network during indexing.",
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        default=None,
        help="Override source list (PDF paths or URLs).",
    )
    parser.add_argument(
        "--catalogue",
        type=str,
        default=str(CATALOGUE_PATH),
        help="Path to the catalogue YAML.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (default INFO).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )

    if not args.dry_run and not args.build_index:
        parser.print_help()
        return 0

    sources = args.sources if args.sources is not None else DOC_SOURCES
    local_pdfs = [str(p) for p in sorted(LOCAL_DOCS_DIR.glob("*.pdf"))] if LOCAL_DOCS_DIR.exists() else []
    all_sources = local_pdfs + sources

    print(f"=== Ingestion & Indexing Pipeline ===")
    print(f"Sources ({len(all_sources)}):")
    for s in all_sources:
        print(f"  - {s}")

    # --- Validate catalogue ---
    print(f"\n--- Validating catalogue: {args.catalogue} ---")
    try:
        products = load_catalogue(args.catalogue)
        print(f"Catalogue valid: {len(products)} product(s).")
    except Exception as exc:
        print(f"CATALOGUE INVALID: {exc}")
        return 2

    if args.dry_run:
        print("\n[Dry-run mode] Skipping document fetch and index build.")
        return 0

    if args.build_index:
        print(f"\n--- Loading documents (fetch_urls={args.fetch_urls}) ---")
        docs = load_documents(all_sources, fetch_urls=args.fetch_urls)
        print(f"Loaded {len(docs)} SourceDoc(s).")
        if not docs:
            print("WARN: No documents loaded. Did you forget --fetch-urls or local PDFs?")
            return 1

        print("\n--- Chunking documents ---")
        chunks = chunk_documents(docs)
        print(f"Created {len(chunks)} chunk(s).")

        print("\n--- Initializing embedding provider (all-MiniLM-L6-v2) ---")
        embedder = LocalEmbeddingProvider("all-MiniLM-L6-v2")

        print("\n--- Generating embeddings ---")
        texts = [c.text for c in chunks]
        embeddings = embedder.embed_texts(texts)
        print(f"Generated {len(embeddings)} embedding vectors (dim={embedder.dim}).")

        print(f"\n--- Upserting into vector index at {INDEX_DIR} ---")
        index = VectorIndex(persist_dir=INDEX_DIR)
        index.upsert(chunks, embeddings)
        print(f"Index successfully built! Total items in collection: {index.count()}")

    print("\n=== P2 Pipeline Complete ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
