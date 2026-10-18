"""P3 unit and integration tests: retrieval, citations, answer generation, and LLM provider abstraction."""

from unittest.mock import MagicMock

import pytest

from amd_hardware_advisor.answer import answer_query
from amd_hardware_advisor.citations import assemble_citations
from amd_hardware_advisor.llm.provider import OpenAICompatibleLLMProvider, get_llm_provider
from amd_hardware_advisor.vector_index import RetrievedChunk
from config.settings import LLMProvider as ProviderEnum, Settings


# --- Provider abstraction tests ---


def test_provider_factory_defaults_to_ollama():
    settings = Settings(llm_provider=ProviderEnum.ollama)
    provider = get_llm_provider(settings)
    assert provider.provider_name == "ollama"
    assert provider.is_amd_hosted is False


def test_provider_factory_token_factory():
    settings = Settings(
        llm_provider=ProviderEnum.token_factory,
        amd_token_factory_base_url="https://example.com/v1",
        amd_token_factory_api_key="fake-key",
        amd_token_factory_model="test-model",
    )
    provider = get_llm_provider(settings)
    assert provider.provider_name == "token_factory"
    assert provider.model_id == "test-model"
    assert provider.is_amd_hosted is True


# --- Citation assembly tests ---


def test_assemble_citations_maps_correctly():
    chunks = [
        RetrievedChunk(
            chunk_id="1234567890abcdef",
            text="MI300X has 192GB memory.",
            score=0.95,
            source_url_or_file="https://amd.com/mi300x",
            page=None,
            section=None,
            source_id="s1",
        )
    ]
    citations = assemble_citations(chunks, used_chunk_ids=["1234567890abcdef"])
    assert len(citations) == 1
    assert citations[0].index == 1
    assert citations[0].chunk_id == "1234567890abcdef"
    assert citations[0].source_url_or_file == "https://amd.com/mi300x"


# --- Answer generation & unanswerable query tests ---


class MockLLMProvider:
    """Mock LLM provider for deterministic test assertions."""

    def __init__(self, response_text: str) -> None:
        self._response = response_text

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        return self._response

    @property
    def model_id(self) -> str:
        return "mock-model"

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def is_amd_hosted(self) -> bool:
        return True


def test_answer_query_grounded_success():
    chunk = RetrievedChunk(
        chunk_id="1234567890abcdef",
        text="AMD Instinct MI300X features 192 GB of HBM3 memory.",
        score=0.98,
        source_url_or_file="https://www.amd.com/mi300x",
        page=None,
        section=None,
        source_id="s1",
    )
    mock_provider = MockLLMProvider(
        response_text="The MI300X has 192 GB of HBM3 memory [chunk_id: 1234567890abcdef]."
    )

    result = answer_query("How much memory does MI300X have?", [chunk], provider=mock_provider)
    assert result.is_answerable is True
    assert "192 GB" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == "1234567890abcdef"


def test_answer_query_unanswerable():
    chunk = RetrievedChunk(
        chunk_id="1234567890abcdef",
        text="ROCm 10.1 supports Ubuntu and RHEL.",
        score=0.40,
        source_url_or_file="https://rocm.docs.amd.com",
        page=1,
        section=None,
        source_id="s2",
    )
    mock_provider = MockLLMProvider(
        response_text="I cannot answer this question from the provided official AMD documentation."
    )

    result = answer_query("What is the stock price of AMD?", [chunk], provider=mock_provider)
    assert result.is_answerable is False
    assert "cannot answer" in result.answer.lower()
