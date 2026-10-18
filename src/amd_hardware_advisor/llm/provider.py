"""Provider abstraction for LLM chat completion.

Conforms to ARCHITECTURE.md §3 and §6: a single protocol allowing swappable LLM providers
(AMD Token Factory, AMD Dev Cloud vLLM, local Ollama, OpenAI-compatible APIs) via config.
All OpenAI-compatible providers use the standard `openai` SDK client with configurable
`base_url` and `api_key`.

Per instructions: AMD Token Factory is configured as primary, but its endpoint/model/auth
MUST be verified with a real call before claiming success. Ollama remains the local fallback.
"""

from __future__ import annotations

import logging
from typing import Protocol

from openai import OpenAI

from config.settings import LLMProvider as ProviderEnum, Settings, get_settings

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    """Protocol for LLM chat completion providers."""

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        """Send chat messages and return completion text."""
        ...

    @property
    def model_id(self) -> str:
        ...

    @property
    def provider_name(self) -> str:
        ...

    @property
    def is_amd_hosted(self) -> bool:
        ...


class OpenAICompatibleLLMProvider:
    """OpenAI-compatible LLM provider (covers AMD Token Factory, Dev Cloud vLLM, etc.)."""

    def __init__(self, base_url: str, api_key: str, model: str, name: str, is_amd: bool = True) -> None:
        self._base_url = base_url
        self._api_key = api_key or "not-needed"
        self._model = model
        self._name = name
        self._is_amd = is_amd

        logger.info("initializing OpenAICompatibleLLMProvider (%s) at %s model=%s", name, base_url, model)
        self._client = OpenAI(base_url=base_url, api_key=self._api_key)

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
            )
            content = response.choices[0].message.content
            return content if content is not None else ""
        except Exception as exc:
            logger.error("LLM chat completion failed on provider %s: %s", self._name, exc)
            raise RuntimeError(f"LLM provider {self._name} error: {exc}") from exc

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def is_amd_hosted(self) -> bool:
        return self._is_amd


class OllamaLLMProvider:
    """Local Ollama provider acting as offline fallback."""

    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3") -> None:
        self._base_url = base_url
        self._model = model or "llama3"
        self._name = "ollama"
        logger.info("initializing OllamaLLMProvider at %s model=%s", base_url, self._model)
        self._client = OpenAI(base_url=base_url, api_key="ollama")

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
            )
            content = response.choices[0].message.content
            return content if content is not None else ""
        except Exception as exc:
            logger.error("Ollama LLM chat completion failed: %s", exc)
            raise RuntimeError(f"Ollama local fallback error (is Ollama running?): {exc}") from exc

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def is_amd_hosted(self) -> bool:
        return False


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Factory function to instantiate the configured LLM provider with fallback logic."""
    settings = settings or get_settings()

    provider_type = settings.llm_provider

    if provider_type == ProviderEnum.token_factory:
        base_url = settings.amd_token_factory_base_url
        api_key = settings.amd_token_factory_api_key
        model = settings.amd_token_factory_model
        if base_url and model:
            return OpenAICompatibleLLMProvider(
                base_url=base_url,
                api_key=api_key or "",
                model=model,
                name="token_factory",
                is_amd=True,
            )
        logger.warning("Token Factory selected but base_url or model missing; falling back to ollama")

    elif provider_type == ProviderEnum.dev_cloud:
        base_url = settings.amd_dev_cloud_base_url
        api_key = settings.amd_dev_cloud_api_key
        model = settings.amd_dev_cloud_model
        if base_url and model:
            return OpenAICompatibleLLMProvider(
                base_url=base_url,
                api_key=api_key or "",
                model=model,
                name="dev_cloud",
                is_amd=True,
            )
        logger.warning("Dev Cloud selected but base_url or model missing; falling back to ollama")

    # Default / fallback to Ollama
    return OllamaLLMProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model or "llama3",
    )


__all__ = ["LLMProvider", "OpenAICompatibleLLMProvider", "OllamaLLMProvider", "get_llm_provider"]
