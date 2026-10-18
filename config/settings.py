"""Typed application configuration loaded from environment / .env.

P0 scope: only provider selection and shared settings. No provider clients, no AMD
endpoint assumptions. AMD Token Factory / Dev Cloud fields are accepted from env but are
UNVERIFIED at planning time; they must be confirmed by a real test in P6 before use.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve paths relative to the project root (this file lives in config/).
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class LLMProvider(str, Enum):
    """Selectable inference backends. All are OpenAI-compatible except local Ollama,
    which exposes an OpenAI-compatible endpoint at OLLAMA_BASE_URL."""

    token_factory = "token_factory"
    dev_cloud = "dev_cloud"
    ollama = "ollama"


class Settings(BaseSettings):
    """Application settings. Secrets come only from the environment / .env — never
    hardcoded. A selected AMD provider with missing required fields falls back to
    Ollama and logs a clear message (enforced by the provider factory in later phases)."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Provider selection ----
    llm_provider: LLMProvider = LLMProvider.ollama

    # ---- Embeddings (always local for MVP) ----
    embedding_model: str = "all-MiniLM-L6-v2"

    # ---- AMD Token Factory (PRIMARY, UNVERIFIED) ----
    amd_token_factory_base_url: str | None = None
    amd_token_factory_api_key: str | None = None
    amd_token_factory_model: str | None = None

    # ---- AMD Developer Cloud vLLM (alternate AMD path) ----
    amd_dev_cloud_base_url: str | None = None
    amd_dev_cloud_api_key: str | None = None
    amd_dev_cloud_model: str | None = None

    # ---- Local Ollama fallback (default MVP provider) ----
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str | None = None

    # ---- Retrieval / chunking ----
    top_k: int = 5
    chunk_size: int = 700
    chunk_overlap: int = 100

    # ---- Logging ----
    log_level: str = "INFO"

    @field_validator("llm_provider", mode="before")
    @classmethod
    def _coerce_provider(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def _coerce_log_level(cls, v: object) -> object:
        if isinstance(v, str):
            return v.upper()
        return v

    @property
    def is_amd_provider(self) -> bool:
        """True only when an AMD-hosted provider is selected. Does NOT mean AMD execution
        is verified — that requires a passing scripts/verify_amd.py run (P6)."""
        return self.llm_provider in (LLMProvider.token_factory, LLMProvider.dev_cloud)


def get_settings() -> Settings:
    """Build and return Settings from the environment / .env."""
    return Settings()


__all__ = ["LLMProvider", "Settings", "get_settings", "PROJECT_ROOT"]
