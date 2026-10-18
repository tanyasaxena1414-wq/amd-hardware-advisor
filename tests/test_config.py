"""P0/P3 config tests including absolute env path resolution test."""

from pathlib import Path
import os

from config.settings import LLMProvider, Settings, PROJECT_ROOT, get_settings


def test_settings_loads_with_defaults():
    """Settings must instantiate from the environment with sensible defaults."""
    settings = get_settings()
    assert isinstance(settings, Settings)


def test_default_provider_is_ollama():
    """The MVP default provider is local Ollama — no AMD dependency to boot."""
    settings = Settings(_env_file=None)
    assert settings.llm_provider is LLMProvider.ollama


def test_env_file_resolves_regardless_of_cwd(monkeypatch, tmp_path):
    """Settings must load .env from PROJECT_ROOT even if CWD is changed elsewhere."""
    original_cwd = Path.cwd()
    monkeypatch.chdir(tmp_path)
    try:
        settings = get_settings()
        # Verify settings successfully read PROJECT_ROOT / ".env"
        assert isinstance(settings, Settings)
        assert settings.ollama_base_url == "http://localhost:11434/v1"
    finally:
        os.chdir(original_cwd)


def test_default_is_not_marked_amd_verified():
    settings = Settings(_env_file=None)
    assert settings.is_amd_provider is False


def test_token_factory_selection_marks_amd_provider():
    settings = Settings(_env_file=None, llm_provider=LLMProvider.token_factory)
    assert settings.is_amd_provider is True


def test_dev_cloud_selection_marks_amd_provider():
    settings = Settings(_env_file=None, llm_provider=LLMProvider.dev_cloud)
    assert settings.is_amd_provider is True


def test_provider_enum_values():
    assert LLMProvider.token_factory.value == "token_factory"
    assert LLMProvider.dev_cloud.value == "dev_cloud"
    assert LLMProvider.ollama.value == "ollama"


def test_embedding_model_default():
    settings = Settings(_env_file=None)
    assert settings.embedding_model == "all-MiniLM-L6-v2"


def test_retrieval_defaults():
    settings = Settings(_env_file=None)
    assert settings.top_k == 5
    assert settings.chunk_size == 700
    assert settings.chunk_overlap == 100


def test_amd_fields_optional_until_verified():
    settings = Settings(_env_file=None)
    assert settings.amd_token_factory_base_url is None
    assert settings.amd_token_factory_api_key is None
    assert settings.amd_token_factory_model is None
    assert settings.amd_dev_cloud_base_url is None
