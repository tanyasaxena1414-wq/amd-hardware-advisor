"""Hardware catalogue: structured, curated AMD product specs (kept separate from the RAG index).

Per ARCHITECTURE.md §7: the catalogue is a distinct data store from the RAG document index.
It holds typed product records used for comparison and recommendation. Every field must
trace to an official AMD source recorded in source_url; fields that could not be confirmed
from official docs are left null with source_verified=False. We never invent specs.

Catalogue source of truth for this MVP seed: ROCm 10.1.0 release notes
(https://rocm.docs.amd.com/en/latest/about/release-notes.html, verified live 2026-10-17),
which lists each Instinct/Radeon/Ryzen AI model with its GPU architecture. Numeric specs
(memory, TDP, compute units, TFLOPS) are left null here because they are NOT present in the
release notes — they will be populated in P1+ only from product pages we successfully
ingest, never invented.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Architectures confirmed in the ROCm 10.1.0 release notes (verified 2026-10-17).
KNOWN_ARCHITECTURES = {
    "CDNA 4",
    "CDNA 3",
    "CDNA 2",
    "CDNA 1",
    "RDNA 4",
    "RDNA 3",
    "RDNA 3.5",
    "RDNA 2",
    "Zen 5",
    "Zen 4",
}


class Product(BaseModel):
    """A curated AMD hardware product record. Only fields sourced from official AMD
    documentation are populated; everything else stays null with source_verified=False."""

    family: str = Field(..., description="e.g. Instinct, EPYC, Radeon PRO, Ryzen AI")
    model: str = Field(..., description="e.g. MI300X, MI355X, 9655")
    architecture: str | None = Field(
        None, description="GPU/CPU arch e.g. CDNA 3, RDNA 4, Zen 5"
    )
    gfx_id: str | None = Field(None, description="e.g. gfx942, gfx950 (GPU ISA id)")

    # Numeric specs — left null unless confirmed from an official AMD product page.
    memory_gb: float | None = None
    memory_type: str | None = None
    tdp_w: float | None = None
    compute_units: int | None = None
    peak_tflops_fp16: float | None = None
    cores: int | None = None  # CPU core count for EPYC/Ryzen

    supported_frameworks: list[str] = Field(default_factory=list)

    # Provenance: required. Every record must cite an official AMD source.
    source_url: str = Field(..., description="Official AMD source for this record")
    source_verified: bool = Field(
        default=False,
        description="True only if fields were confirmed from the cited official source",
    )

    model_config = {"extra": "forbid"}

    @field_validator("family", "model")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("family/model must be non-empty")
        return v.strip()


def load_catalogue(path: str | Path) -> list[Product]:
    """Load and validate the catalogue YAML. Invalid records raise loudly — we never
    silently coerce or drop data, since bad specs would poison comparison/recommendation."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Catalogue file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Catalogue {path} must be a YAML list of product records")

    products: list[Product] = []
    for i, record in enumerate(raw):
        try:
            products.append(Product.model_validate(record))
        except Exception as exc:
            raise ValueError(f"Invalid catalogue record #{i} in {path}: {exc}") from exc

    logger.info("loaded catalogue %s: %d products", path, len(products))
    return products


def get_by_model(model: str, products: list[Product]) -> Product | None:
    """Look up a product by model name (case-insensitive)."""
    needle = model.strip().lower()
    for p in products:
        if p.model.lower() == needle:
            return p
    return None


__all__ = ["Product", "load_catalogue", "get_by_model", "KNOWN_ARCHITECTURES"]
