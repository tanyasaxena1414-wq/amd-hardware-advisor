# AMD Hardware Advisor — Architecture

## 1. Tech stack

Lightweight, Windows-compatible, minimal dependencies. No heavy RAG framework.

| Concern | Choice | Pinned intent | Rationale |
|---|---|---|---|
| Language / runtime | Python 3.11 | 3.11.x | Mature, broad lib support, good typing |
| Env / deps | `uv` + `pyproject.toml` | latest stable | Fast, reproducible, lockfile |
| Doc loaders | `pypdf` (PDF) + `httpx` + `selectolax` (HTML) | pinned in lockfile | Minimal, no heavy parser deps |
| Chunking | Custom recursive text splitter | n/a | Tiny, dependency-free |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | pinned | Local, CPU-capable, no external API |
| Vector store | `chromadb` (persistent local) | pinned | Local, no server, good enough for MVP |
| LLM client | `openai` SDK (OpenAI-compatible) | pinned | Works for Token Factory, Dev Cloud vLLM, Ollama, OpenAI |
| UI | `streamlit` | pinned | Fastest path to a usable demo UI |
| Config | `pydantic-settings` | pinned | Typed env/config, validation |
| Testing | `pytest` | pinned | Standard |
| Logging | `structlog` | pinned | Structured logs for verification records |

Default provider for MVP: **local Ollama** (LLM) + local embeddings, until AMD Token
Factory access is confirmed by a real test. Embeddings stay local regardless of LLM
provider (no dependency on an AMD embedding endpoint).

## 2. Directory structure

```
amd-hardware-advisor/
├── PRD.md
├── ARCHITECTURE.md
├── AGENTS.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   └── settings.py              # pydantic-settings, provider selection
├── data/
│   ├── docs/                    # ingested source docs (PDFs, cached HTML)
│   └── catalogue/               # hardware catalogue YAML/JSON (structured)
├── index/                       # persisted vector store (gitignored)
├── src/amd_hardware_advisor/
│   ├── __init__.py
│   ├── ingestion.py             # load PDF + HTML -> normalized docs
│   ├── chunking.py              # recursive text splitter
│   ├── embeddings.py            # sentence-transformers wrapper
│   ├── vector_index.py          # chromadb create/query
│   ├── retrieval.py             # top-k retrieval + (optional) rerank stub
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── provider.py          # Provider abstraction interface
│   │   ├── token_factory.py     # AMD Token Factory (OpenAI-compatible, UNVERIFIED)
│   │   ├── dev_cloud.py         # AMD Dev Cloud vLLM (OpenAI-compatible)
│   │   ├── ollama.py            # local fallback
│   │   └── factory.py           # select provider from config
│   ├── answer.py                # grounded prompt + citation assembly
│   ├── catalogue.py             # load/validate structured catalogue
│   ├── compare.py               # comparison engine over catalogue
│   ├── recommend.py             # workload -> recommendation over catalogue + docs
│   ├── citations.py             # map chunks -> verifiable source refs
│   └── ui/
│       └── app.py               # Streamlit UI
├── scripts/
│   ├── ingest.py                # build/rebuild index + cache docs
│   └── verify_amd.py            # AMD execution verification test (real test)
└── tests/
    ├── test_chunking.py
    ├── test_retrieval.py
    ├── test_citations.py
    ├── test_catalogue.py
    ├── test_compare.py
    ├── test_recommend.py
    └── test_verify_amd.py
```

## 3. Module responsibilities

- **ingestion.py** — load PDFs and HTML from `data/docs/` (and curated URLs), return
  normalized documents with source metadata (url/file, page, title, fetched_at).
- **chunking.py** — split documents into chunks with stable ids and carried metadata.
- **embeddings.py** — wrap sentence-transformers; embed texts and queries locally.
- **vector_index.py** — create/persist/query a chromadb collection; store chunk metadata.
- **retrieval.py** — top-k vector retrieval; rerank is a stub interface (no-op default).
- **llm/provider.py** — define the provider interface (chat completion + listing).
- **llm/token_factory.py / dev_cloud.py / ollama.py** — provider implementations.
- **llm/factory.py** — select provider from config; fail loudly with a clear message if
  configured provider is unavailable.
- **answer.py** — build a grounded prompt from retrieved chunks, call the LLM, assemble
  the final answer with citation markers.
- **citations.py** — map answer citation markers back to source chunks → verifiable refs.
- **catalogue.py** — load and validate the structured hardware catalogue (schema-enforced).
- **compare.py** — produce comparison tables from catalogue spec fields.
- **recommend.py** — match a workload description to catalogue products, using retrieved
  docs for rationale where available.
- **ui/app.py** — Streamlit: Q&A with citations, compare, recommend, provider status badge.
- **config/settings.py** — typed config from env; provider selection and credentials.
- **scripts/ingest.py** — CLI to build/rebuild the index.
- **scripts/verify_amd.py** — the real AMD verification test (see §7).

## 4. Data flow

```
ingestion -> chunking -> embeddings -> vector_index (persisted in index/)
                                                    |
user query -> embeddings(query) -> retrieval(top-k) -> [rerank stub]
        |
        +-> answer.py: grounded prompt(retrieved chunks) -> LLM provider
        |        |
        |        +-> citations.py: markers -> source refs (url/file, page, chunk id)
        |
        +-> (compare/recommend path uses catalogue.py, joined with retrieved docs at answer time)
        |
UI <- answer + citations / comparison table / recommendation
```

Citations are traced by carrying metadata through the whole pipeline: each chunk keeps
`{source_url_or_file, page, section, chunk_id}`. The prompt instructs the model to cite by
`chunk_id`; `citations.py` resolves `chunk_id` → the full verifiable reference. The UI
renders each citation as a link to the official source where possible.

## 5. Interfaces

Kept minimal; dataclasses / typed signatures. (Final signatures fixed at implementation.)

```python
# ingestion.py
@dataclass
class SourceDoc:
    id: str
    text: str
    source_url_or_file: str
    page: int | None
    section: str | None
    title: str
    fetched_at: str

def load_documents(sources: list[str]) -> list[SourceDoc]: ...

# chunking.py
@dataclass
class Chunk:
    chunk_id: str
    text: str
    source_url_or_file: str
    page: int | None
    section: str | None

def split(doc: SourceDoc, chunk_size: int, overlap: int) -> list[Chunk]: ...

# embeddings.py
def embed_texts(texts: list[str]) -> list[list[float]]: ...
def embed_query(text: str) -> list[float]: ...

# vector_index.py
def upsert(chunks: list[Chunk], vectors: list[list[float]]) -> None: ...
def query(vector: list[float], k: int) -> list[Chunk]: ...

# retrieval.py
def retrieve(query: str, k: int = 5) -> list[Chunk]: ...

# llm/provider.py
class LLMProvider(Protocol):
    name: str
    is_amd_hosted: bool        # True only for Token Factory / Dev Cloud, set by impl
    def chat(self, messages: list[dict], temperature: float) -> str: ...
    def list_models(self) -> list[str]: ...

def get_provider(config) -> LLMProvider: ...   # factory.py

# answer.py
@dataclass
class AnswerResult:
    answer: str
    citations: list[dict]      # [{chunk_id, source_url_or_file, page, section}]

def answer(query: str, retrieved: list[Chunk], provider: LLMProvider) -> AnswerResult: ...

# catalogue.py
@dataclass
class Product:
    family: str
    model: str
    memory_gb: float | None
    tdp_w: float | None
    compute_units: int | None
    supported_frameworks: list[str]
    source_url: str           # required: official AMD source for every field

def load_catalogue(path: str) -> list[Product]: ...

# compare.py
def compare(models: list[str], catalogue: list[Product]) -> dict: ...

# recommend.py
@dataclass
class Recommendation:
    model: str
    rationale: str
    source_chunks: list[dict]
def recommend(workload: str, catalogue, retrieved_docs) -> list[Recommendation]: ...
```

## 6. Provider abstraction (AMD Token Factory primary)

A single OpenAI-compatible interface so AMD Token Factory, AMD Dev Cloud vLLM, and local
Ollama are swappable via config. All three are OpenAI-compatible (vLLM by design; Ollama
via its OpenAI-compatible endpoint). Token Factory is *assumed* OpenAI-compatible —
**unverified**.

Config selects the provider:
```env
LLM_PROVIDER=token_factory | dev_cloud | ollama
# token_factory
AMD_TOKEN_FACTORY_BASE_URL=...
AMD_TOKEN_FACTORY_API_KEY=...
AMD_TOKEN_FACTORY_MODEL=...
# dev_cloud (vLLM)
AMD_DEV_CLOUD_BASE_URL=...
AMD_DEV_CLOUD_API_KEY=...
AMD_DEV_CLOUD_MODEL=...
# ollama (local fallback)
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=...
```

Embeddings are always local (sentence-transformers) and do not depend on any AMD
embedding endpoint.

What must be VERIFIED before using an AMD provider (gate, not assumption):
1. A real HTTP request to the configured base URL returns a model list / chat completion.
2. Auth scheme and request/response shape are confirmed against a live response.
3. The response includes a marker proving the host is AMD-provided (see §7).
Until all three pass, the app uses the local fallback and the UI clearly shows
"AMD execution: not verified".

## 7. Catalogue vs RAG index (kept separate)

Hard boundary required by the brief.

- **RAG document index** = unstructured official AMD docs (PDFs, HTML pages), chunked and
  embedded in chromadb. Used for grounded Q&A and citation. Lives in `index/`.
- **Hardware catalogue** = structured, human-curated product records with typed fields,
  in `data/catalogue/` (YAML recommended for human editability; validated by
  `catalogue.py` against the `Product` schema). Used for comparison and recommendation.
  Every field carries a `source_url` to an official AMD page.

Boundary rules:
- Comparison and recommendation read **only** the catalogue for spec values — never the
  free-text index, never invented.
- Q&A reads **only** the RAG index for prose answers and citations.
- At answer time the two may be **joined**: a recommendation can retrieve relevant docs
  from the index to add rationale/citations, but the spec numbers in the comparison table
  always come from the catalogue, and the prose always cites the index. The catalogue never
  emits prose; the index never emits structured specs.

## 8. AMD infrastructure verification (real test)

"AMD execution is verified" only when `scripts/verify_amd.py` passes and logs:

```
AMD_VERIFICATION=PASS
endpoint=<base_url>
model=<model_id>
host_marker=<evidence the host is AMD-provided, e.g. response header, server field,
            or documented AMD-provided endpoint URL>
latency_ms=<measured>
sample_prompt="..."
sample_completion="<first 200 chars>"
timestamp=<ISO8601>
```

Verification steps:
1. Configure an AMD provider (Token Factory or Dev Cloud) in `.env`.
2. Run `python scripts/verify_amd.py`. It issues a real chat completion, captures the
   response, measures latency, and records the host marker.
3. If host marker cannot be confirmed as AMD-provided, the test FAILS and the app falls
   back to the local provider with "AMD execution: not verified" shown in the UI and logs.
4. The PASS record is written to `index/amd_verification.json` and surfaced in the UI
   status badge. No PASS record = no AMD claim, anywhere.

Fallback behavior (if Token Factory unavailable / Dev Cloud not provisioned):
- `LLM_PROVIDER` auto-falls to `ollama`; UI badge shows
  "Inference: local (AMD execution NOT verified)".
- The full RAG + catalogue + compare + recommend pipeline still runs on local inference.

## 9. Config & security

- Secrets only in `.env` (gitignored); `.env.example` documents keys without values.
- No hardcoded API keys. `config/settings.py` loads via pydantic-settings; missing
  required secrets for a provider → clear error, fall back to local.
- `.gitignore`: `.env`, `index/`, `data/docs/_cache/`, `__pycache__/`, `.venv/`.
- User queries are sanitized before logging; no prompt injection passthrough — retrieved
  chunks are fenced in the prompt and the model is instructed to cite only by `chunk_id`.
- Catalogue YAML validated against schema on load; invalid records rejected loudly.
- All AMD verification records treat endpoint URLs/keys as secrets — logs redact keys.
