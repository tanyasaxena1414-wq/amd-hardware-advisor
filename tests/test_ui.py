"""UI smoke tests for Streamlit app functions and settings reflection."""

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from amd_hardware_advisor.catalogue import load_catalogue
from amd_hardware_advisor.compare import compare_models
from amd_hardware_advisor.recommend import WorkloadProfile, recommend_hardware
from config.settings import get_settings, LLMProvider


def test_catalogue_loads_for_ui():
    cat_path = PROJECT_ROOT / "data" / "catalogue" / "catalogue.yaml"
    products = load_catalogue(cat_path)
    assert len(products) >= 10


def test_compare_models_for_ui():
    cat_path = PROJECT_ROOT / "data" / "catalogue" / "catalogue.yaml"
    products = load_catalogue(cat_path)
    table = compare_models(["MI355X", "MI300X"], products)
    assert len(table.models) == 2
    assert "MI355X" in table.models


def test_recommend_for_ui():
    cat_path = PROJECT_ROOT / "data" / "catalogue" / "catalogue.yaml"
    products = load_catalogue(cat_path)
    profile = WorkloadProfile(task_type="llm_inference", min_memory_gb=100.0)
    recs = recommend_hardware(profile, products, top_n=2)
    assert isinstance(recs, list)


def test_settings_reflects_token_factory_when_configured(monkeypatch):
    """Regression test: verify settings load token_factory correctly when configured."""
    monkeypatch.setenv("LLM_PROVIDER", "token_factory")
    settings = get_settings()
    assert settings.llm_provider == LLMProvider.token_factory
    assert settings.is_amd_provider is True
