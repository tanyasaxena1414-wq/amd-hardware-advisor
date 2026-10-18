"""P4 unit and integration tests: hardware comparison and workload recommendations.

Tests verify:
- Comparison table correctly diffs products across shared spec fields.
- Comparison handles missing/null fields gracefully without inventing specs.
- Workload recommendations correctly rank products and ground rationales.
- Source provenance is preserved on both comparison results and recommendations.
"""

from pathlib import Path

import pytest

from amd_hardware_advisor.catalogue import Product, load_catalogue
from amd_hardware_advisor.compare import compare_models
from amd_hardware_advisor.recommend import WorkloadProfile, recommend_hardware

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = PROJECT_ROOT / "data" / "catalogue" / "catalogue.yaml"


@pytest.fixture
def sample_catalogue() -> list[Product]:
    return [
        Product(
            family="Instinct",
            model="MI300X",
            architecture="CDNA 3",
            gfx_id="gfx942",
            memory_gb=192,
            memory_type="HBM3",
            tdp_w=750,
            compute_units=304,
            source_url="https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html",
            source_verified=True,
        ),
        Product(
            family="Instinct",
            model="MI300A",
            architecture="CDNA 3",
            gfx_id="gfx942",
            memory_gb=128,
            memory_type="HBM3",
            tdp_w=650,
            compute_units=228,
            source_url="https://www.amd.com/en/products/accelerators/instinct/mi300/mi300a.html",
            source_verified=True,
        ),
        Product(
            family="Instinct",
            model="MI210",
            architecture="CDNA 2",
            gfx_id="gfx90a",
            memory_gb=64,
            memory_type="HBM2e",
            tdp_w=300,
            compute_units=104,
            source_url="https://rocm.docs.amd.com/en/latest/about/release-notes.html",
            source_verified=False,
        ),
    ]


# --- Comparison Engine Tests ---


def test_compare_models_success(sample_catalogue):
    table = compare_models(["MI300X", "MI300A"], sample_catalogue)
    assert "MI300X" in table.models
    assert "MI300A" in table.models
    assert "memory_gb" in table.fields
    assert table.rows["MI300X"]["memory_gb"] == 192
    assert table.rows["MI300A"]["memory_gb"] == 128
    assert table.source_urls["MI300X"].startswith("https://")


def test_compare_models_missing_model_raises(sample_catalogue):
    with pytest.raises(ValueError, match="not found in the catalogue"):
        compare_models(["MI300X", "NONEXISTENT"], sample_catalogue)


def test_compare_models_too_few_raises(sample_catalogue):
    with pytest.raises(ValueError, match="at least 2 models"):
        compare_models(["MI300X"], sample_catalogue)


def test_compare_handles_unverified_null_specs(sample_catalogue):
    """Seed catalogue items have null numeric specs; comparison must handle them without inventing."""
    real_catalogue = load_catalogue(CATALOGUE_PATH)
    # MI355X and MI300X are in the seed catalogue
    table = compare_models(["MI355X", "MI300X"], real_catalogue)
    assert "MI355X" in table.models
    assert "MI300X" in table.models
    # Unverified seed items have null memory_gb, which is omitted or null in rows
    assert table.rows["MI355X"].get("memory_gb") is None


# --- Recommendation Engine Tests ---


def test_recommend_hardware_llm_workload(sample_catalogue):
    profile = WorkloadProfile(
        task_type="llm_inference",
        min_memory_gb=150.0,
    )
    recs = recommend_hardware(profile, sample_catalogue, top_n=2)
    assert len(recs) > 0
    # MI300X has 192 GB (> 150 GB), so it should rank #1
    assert recs[0].product.model == "MI300X"
    assert "192.0 GB" in recs[0].rationale
    assert recs[0].product.source_url.startswith("https://")


def test_recommend_hardware_empty_catalogue():
    recs = recommend_hardware(WorkloadProfile(task_type="llm_training"), [], top_n=3)
    assert recs == []
