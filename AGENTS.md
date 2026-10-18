# AMD Hardware Advisor — Agent & Implementation Guide

## 1. Operating constraints

- One laptop, one repository, one coding agent, one `main` branch.
- Work **sequentially**; pass each phase's test gate before moving on.
- Keep the stack lightweight and Windows-compatible. Avoid unnecessary abstractions or
  features. No code beyond what a phase requires.
- Never invent hardware specifications. Never fabricate citations. Every spec field and
  every citation must trace to an official AMD source.
- Never claim AMD execution is verified without a passing `scripts/verify_amd.py` run.

## 2. Coding rules

- Python 3.11, `pyproject.toml` with `uv`, pinned versions in the lockfile.
- Type hints on all public functions; dataclasses for data shapes (see ARCHITECTURE.md §5).
- Module boundaries from ARCHITECTURE.md §3 are authoritative: do not cross-couple the
  catalogue engines (compare/recommend) into the RAG path, and vice versa.
- Keep the provider abstraction in `src/amd_hardware_advisor/llm/`; never call `openai`
  directly outside `llm/*`.
- Config via `config/settings.py` (pydantic-settings) only; no secrets in code.
- Logging via `structlog`; log key steps (ingest counts, retrieval k, provider name,
  AMD verification status). Never log API keys.
- Match surrounding style. Comments only where non-obvious.

## 3. Implementation phases & test gates

Each phase has a runnable test that must pass before the next phase starts.

- **P0 — Scaffold.** `pyproject.toml`, `.env.example`, `.gitignore`, `config/settings.py`,
  package skeleton, `uv` install works.
  *Gate:* `uv run python -c "import amd_hardware_advisor"` and `uv run pytest -q` (no tests
  yet, exits 0) succeed.

- **P1 — Ingestion + catalogue.** `ingestion.py` loads curated PDFs + cached HTML into
  `SourceDoc`s; `catalogue.py` loads and validates the catalogue YAML against the `Product`
  schema.
  *Gate:* `uv run scripts/ingest.py --dry-run` lists loaded docs with source metadata;
  `pytest tests/test_catalogue.py` validates catalogue records (every field has
  `source_url`).

- **P2 — Embeddings + index.** `embeddings.py` (sentence-transformers) + `vector_index.py`
  (chromadb). `scripts/ingest.py` builds the persisted index.
  *Gate:* `pytest tests/test_chunking.py` and a manual check: index a 2-doc set, retrieve a
  known query, top-1 is the expected chunk.

- **P3 — Retrieval + grounded answers + citations.** `retrieval.py`, `answer.py`,
  `citations.py`, and the provider abstraction (`llm/`) with the Ollama fallback wired.
  *Gate:* `pytest tests/test_retrieval.py`, `tests/test_citations.py` pass; an end-to-end
  Q&A over a 3-doc set returns an answer with a correct citation. An unanswerable query
  returns an explicit "cannot answer from provided docs" message.

- **P4 — Comparison + recommendation.** `compare.py` and `recommend.py` over the catalogue.
  *Gate:* `pytest tests/test_compare.py`, `tests/test_recommend.py` pass; comparison table
  uses only catalogue spec fields; recommendation rationale cites catalogue + retrieved docs.

- **P5 — UI.** `ui/app.py` (Streamlit): Q&A with citations, compare, recommend, provider
  status badge showing AMD verification state.
  *Gate:* `uv run streamlit run src/amd_hardware_advisor/ui/app.py` loads; a question returns
  a cited answer; compare and recommend render; badge reflects actual verification state.

- **P6 — AMD integration + real verification.** Wire `llm/token_factory.py` (and/or
  `dev_cloud.py`), populate `.env` with real AMD credentials, run the real test.
  *Gate:* `uv run python scripts/verify_amd.py` passes and writes
  `index/amd_verification.json` with a PASS record (endpoint, model id, host marker,
  latency, sample completion). UI badge flips to "AMD execution: verified". If it cannot
  pass, the app stays on local fallback with "NOT verified" — and we honestly document
  that status (consider AMD AI League, Dec 1, as the fallback target).

## 4. Testing requirements

- `pytest` for unit tests; each phase adds tests for its modules.
- An end-to-end test covers Q&A → citation against a tiny fixed corpus.
- `scripts/verify_amd.py` is the only acceptable proof of AMD execution; it must hit a
  real endpoint and record the host marker.
- No test may assert "AMD execution verified" without a real AMD provider response.
- Tests must not require network unless explicitly marked (`@pytest.mark.network`); the
  default suite runs offline using local fixtures and the Ollama fallback mocked or
  skipped.

## 5. Configuration & security practices

- `.env` for all secrets; `.gitignore` covers `.env`, `index/`, caches, venv.
- `.env.example` lists keys with no values; AMD keys grouped and commented as UNVERIFIED
  until the real test passes.
- pydantic-settings validates config on startup; missing required secrets for a selected
  provider → fall back to local + clear message.
- API keys never logged; verification records redact keys.
- User query input is sanitized; retrieved chunks are fenced in the prompt to limit
  prompt injection; model instructed to cite only by `chunk_id`.
- Catalogue YAML validated against schema; invalid records rejected, not silently coerced.

## 6. AMD requirement handling (honest status)

- Primary: AMD Token Factory (`notebooks.amd.com/tokenfactory`). Status at planning:
  **UNVERIFIED** — login-gated, no public API docs. Must be confirmed by sign-in and a
  real request/response during P6.
- Alternate: AMD Developer Cloud (ROCm/vLLM, Instinct). Requires registration/approval
  (24–48h lead time); initiate early if Token Factory access is uncertain.
- Until `verify_amd.py` passes, the app runs on the local fallback and every user-facing
  surface says "AMD execution NOT verified". No exceptions, no hedged claims.
- If neither AMD path verifies before the ACT III on-site deadline, submit the local
  fallback demo honestly and target AMD AI League (Dec 1) for the verified AMD run.

## 7. Definition of done (per phase and overall)

A phase is done when:
- Its code is implemented per ARCHITECTURE.md module boundaries.
- Its test gate passes (`uv run pytest` + any phase-specific command).
- No new hardcoded secrets or invented specs/citations introduced.
- `main` branch is green (all tests pass).

The project is done (MVP) when:
- PRD §6 acceptance criteria are met.
- The core vertical slice runs end to end via the Streamlit UI.
- `scripts/verify_amd.py` has either PASSED (AMD execution verified) or the app is
  honestly running on local fallback with "NOT verified" surfaced everywhere.
- PRD.md, ARCHITECTURE.md, AGENTS.md reflect the as-built state (no stale claims).

## 8. Open items to verify before/during implementation

- AMD Token Factory: endpoint, auth, models, OpenAI-compatibility (P6).
- AMD Developer Cloud: registration/approval status (initiate if needed).
- Curated AMD doc list: user confirms/trims before ingestion (P1).
- Embedding model: confirm `all-MiniLM-L6-v2` runs acceptably on the laptop CPU (P2).
- On-site feasibility: re-assess after P3 whether the full slice fits the Oct 17–18 window;
  if not, demo the local fallback and move AMD verification to AMD AI League.
