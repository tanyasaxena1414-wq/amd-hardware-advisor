"""Hardware comparison engine.

Per ARCHITECTURE.md §3 & §7: comparison reads ONLY from the structured hardware catalogue
for specification values. It never reads the free-text RAG index for numbers and never
invents missing specs. Diffs two or more products across common spec fields.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from amd_hardware_advisor.catalogue import Product, get_by_model

logger = logging.getLogger(__name__)


@dataclass
class ComparisonTable:
    """Structured comparison result across selected hardware models."""

    fields: list[str]
    models: list[str]
    rows: dict[str, dict[str, str | int | float | None]]  # model -> field -> value
    source_urls: dict[str, str]  # model -> source_url


def compare_models(models: list[str], catalogue: list[Product]) -> ComparisonTable:
    """Compare two or more AMD hardware models using only catalogue spec fields.

    Raises ValueError if any model is not found in the catalogue.
    """
    if len(models) < 2:
        raise ValueError("Comparison requires at least 2 models")

    matched_products: list[Product] = []
    for m in models:
        p = get_by_model(m, catalogue)
        if p is None:
            raise ValueError(f"Model {m!r} not found in the catalogue")
        matched_products.append(p)

    # Standard specification fields to compare
    standard_fields = [
        "family",
        "architecture",
        "gfx_id",
        "memory_gb",
        "memory_type",
        "tdp_w",
        "compute_units",
        "peak_tflops_fp16",
        "cores",
    ]

    # Determine fields that have at least one non-null value across the selected models
    active_fields: list[str] = []
    for f in standard_fields:
        if any(getattr(p, f) is not None for p in matched_products):
            active_fields.append(f)

    rows: dict[str, dict[str, Any]] = {}
    source_urls: dict[str, str] = {}
    model_names: list[str] = []

    for p in matched_products:
        model_names.append(p.model)
        source_urls[p.model] = p.source_url
        rows[p.model] = {
            "family": p.family,
            "architecture": p.architecture,
            "gfx_id": p.gfx_id,
            "memory_gb": p.memory_gb,
            "memory_type": p.memory_type,
            "tdp_w": p.tdp_w,
            "compute_units": p.compute_units,
            "peak_tflops_fp16": p.peak_tflops_fp16,
            "cores": p.cores,
        }

    logger.info("compared models %s across fields %s", model_names, active_fields)
    return ComparisonTable(
        fields=active_fields,
        models=model_names,
        rows=rows,
        source_urls=source_urls,
    )


__all__ = ["ComparisonTable", "compare_models"]
