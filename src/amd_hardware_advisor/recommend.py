"""Workload recommendation engine.

Per ARCHITECTURE.md §3 & §7: recommendation matches user workload profiles against
catalogue specs (memory, architecture, TDP, compute units) and retrieves grounded RAG
documentation context to build justification and citations. Never invents specs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from amd_hardware_advisor.answer import answer_query
from amd_hardware_advisor.catalogue import Product
from amd_hardware_advisor.citations import Citation
from amd_hardware_advisor.retrieval import retrieve

logger = logging.getLogger(__name__)


@dataclass
class WorkloadProfile:
    """User workload criteria for hardware recommendation."""

    task_type: str  # e.g. "llm_training", "llm_inference", "hpc_simulation", "edge_ai"
    min_memory_gb: float | None = None
    framework: str | None = None  # e.g. "ROCm", "PyTorch"
    prefer_apu: bool | None = None  # e.g. MI300A vs MI300X


@dataclass
class Recommendation:
    """A scored recommendation for an AMD hardware product with rationale and citations."""

    rank: int
    product: Product
    score: float
    rationale: str
    citations: list[Citation] = field(default_factory=list)


def recommend_hardware(
    profile: WorkloadProfile,
    catalogue: list[Product],
    top_n: int = 3,
) -> list[Recommendation]:
    """Score and rank catalogue products against a workload profile, grounding rationale

    in retrieved official documentation.
    """
    if not catalogue:
        return []

    scored_candidates: list[tuple[float, Product]] = []

    for p in catalogue:
        score = 0.0
        # Basic heuristic scoring based on available catalogue specs
        if profile.min_memory_gb is not None:
            if p.memory_gb is not None:
                if p.memory_gb >= profile.min_memory_gb:
                    score += 2.0
                else:
                    score -= 1.0  # insufficient memory penalty
            else:
                score += 0.5  # unverified specs get neutral score

        if profile.task_type in ("llm_training", "llm_inference"):
            # Favor Instinct accelerators for AI workloads
            if p.family.lower() == "instinct":
                score += 3.0
                if p.model in ("MI300X", "MI325X", "MI350X", "MI355X"):
                    score += 2.0  # high memory/compute AI flagship
            if profile.prefer_apu and p.model == "MI300A":
                score += 3.0

        if profile.framework and p.supported_frameworks:
            if any(profile.framework.lower() in fw.lower() for fw in p.supported_frameworks):
                score += 1.0

        scored_candidates.append((score, p))

    # Sort by score descending
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    recommendations: list[Recommendation] = []
    query_text = f"AMD hardware recommendation for {profile.task_type} requiring memory {profile.min_memory_gb or 'any'} GB"

    # Retrieve grounded doc chunks for rationale enrichment
    try:
        retrieved_chunks = retrieve(query_text, top_k=3)
    except Exception as exc:
        logger.warning("retrieval failed during recommendation rationale generation: %s", exc)
        retrieved_chunks = []

    # Generate an overall grounded answer context or use retrieved citations
    answer_res = answer_query(query_text, retrieved_chunks) if retrieved_chunks else None
    citations = answer_res.citations if answer_res else []

    for rank, (score, product) in enumerate(scored_candidates[:top_n], start=1):
        spec_notes = []
        if product.memory_gb:
            spec_notes.append(f"{product.memory_gb} GB memory")
        if product.architecture:
            spec_notes.append(f"architecture {product.architecture}")
        if product.tdp_w:
            spec_notes.append(f"{product.tdp_w}W TDP")

        specs_str = ", ".join(spec_notes) if spec_notes else "catalogue spec match"
        rationale = (
            f"Recommended {product.family} {product.model} (score: {score:.1f}) "
            f"based on official specs ({specs_str}). "
            f"Sourced from official AMD documentation ({product.source_url})."
        )

        recommendations.append(
            Recommendation(
                rank=rank,
                product=product,
                score=score,
                rationale=rationale,
                citations=citations,
            )
        )

    logger.info("generated %d recommendations for workload profile %s", len(recommendations), profile.task_type)
    return recommendations


__all__ = ["WorkloadProfile", "Recommendation", "recommend_hardware"]
