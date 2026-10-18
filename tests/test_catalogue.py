"""P1 gate tests: catalogue loading and validation.

These must pass before P2 starts. They exercise only P1 code (catalogue.py) and the
real seed catalogue at data/catalogue/catalogue.yaml. Offline.
"""

from pathlib import Path

import pytest

from amd_hardware_advisor.catalogue import (
    Product,
    get_by_model,
    load_catalogue,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = PROJECT_ROOT / "data" / "catalogue" / "catalogue.yaml"


# --- Real seed catalogue ---


def test_seed_catalogue_loads():
    """The committed seed catalogue must load and validate without error."""
    products = load_catalogue(CATALOGUE_PATH)
    assert len(products) >= 10, "expected at least 10 seeded Instinct products"


def test_every_record_has_source_url():
    """No catalogue record may exist without an official source_url."""
    products = load_catalogue(CATALOGUE_PATH)
    for p in products:
        assert p.source_url, f"{p.model} missing source_url"
        assert p.source_url.startswith("https://"), f"{p.model} source_url not https"


def test_seed_records_not_marked_verified():
    """Seed records carry arch/gfx from the release notes but numeric specs are unverified.
    source_verified must be False until specs are confirmed from product pages."""
    products = load_catalogue(CATALOGUE_PATH)
    for p in products:
        assert p.source_verified is False, (
            f"{p.model} must be source_verified=False until specs come from product pages"
        )


def test_seed_numeric_specs_are_null():
    """Numeric specs must NOT be invented in the seed. They stay null until ingested from
    official product pages."""
    products = load_catalogue(CATALOGUE_PATH)
    null_fields = ["memory_gb", "memory_type", "tdp_w", "compute_units", "peak_tflops_fp16"]
    for p in products:
        for f in null_fields:
            assert getattr(p, f) is None, f"{p.model}.{f} must be null in the seed"


def test_get_by_model_case_insensitive():
    products = load_catalogue(CATALOGUE_PATH)
    found = get_by_model("mi300x", products)
    assert found is not None
    assert found.model == "MI300X"
    assert get_by_model("nonexistent", products) is None


# --- Schema validation (reject bad records loudly) ---


def test_valid_product_with_specs():
    p = Product(
        family="Instinct",
        model="MI300X",
        architecture="CDNA 3",
        memory_gb=192,
        memory_type="HBM3",
        source_url="https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html",
        source_verified=True,
    )
    assert p.memory_gb == 192


def test_reject_missing_source_url():
    with pytest.raises(Exception):
        Product(family="Instinct", model="MI300X")


def test_reject_empty_model():
    with pytest.raises(Exception):
        Product(family="Instinct", model="  ", source_url="https://amd.com/x")


def test_reject_extra_fields(tmp_path):
    """extra='forbid' must reject unknown fields so typos can't slip into the catalogue."""
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(
        "- family: Instinct\n  model: MI300X\n  source_url: https://amd.com/x\n  bogus_field: 1\n",
        encoding="utf-8",
    )
    with pytest.raises(Exception):
        load_catalogue(bad_yaml)


def test_reject_non_list_yaml(tmp_path):
    bad = tmp_path / "notalist.yaml"
    bad.write_text("family: Instinct\nmodel: MI300X\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_catalogue(bad)
