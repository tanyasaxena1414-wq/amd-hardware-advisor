# AMD Hardware Advisor — Product Requirements Document

## 1. Problem

Developers, researchers, and builders picking hardware for AI workloads struggle to get
fast, trustworthy answers about AMD hardware (Instinct accelerators, EPYC CPUs, Radeon
GPUs, ROCm software). Official AMD documentation is spread across PDFs, datasheets, and
developer portal pages. Generic LLMs answer from training data, hallucinate specifications,
and cannot cite sources. There is no single grounded assistant that answers from official AMD
docs, compares products side by side, and recommends hardware for a given AI workload —
with citations the user can verify.

## 2. Target users

- AI/ML engineers and researchers choosing AMD accelerators for training or inference.
- System architects evaluating EPYC CPUs and Instinct GPUs for data-center AI stacks.
- Developers new to the AMD/ROCm ecosystem who need quick, sourced answers.
- Hackathon judges and builders who need a credible, demonstrable AMD-native tool.

## 3. Core features

1. **Grounded Q&A.** Answer natural-language questions about AMD hardware using only the
   ingested official AMD documentation. Every answer cites the source document (URL or file,
   page/section, chunk id). If the docs do not support an answer, the assistant says so
   rather than inventing one.
2. **Source citations.** Each answer includes clickable/verifiable references to the exact
   source passages used.
3. **Product comparison.** Compare two or more AMD products side by side on real
   specification fields (memory, TDP, compute units, supported frameworks, etc.) drawn from
   the structured hardware catalogue — never invented.
4. **Workload recommendation.** Given an AI workload description (model size, batch,
   budget, framework), recommend suitable AMD hardware from the catalogue, with rationale
   grounded in catalogue specs and retrieved docs.
5. **Hardware catalogue.** A structured, human-curated catalogue of AMD products with
   fields sourced from official AMD documentation only.
6. **Usable UI.** A minimal web UI (Streamlit) for asking questions, viewing cited answers,
   running comparisons, and getting recommendations.

## 4. MVP scope (ACT III on-site demo, Oct 17–18 2026)

A thin end-to-end **core vertical slice** — runnable, demonstrable — then AMD Token Factory
inference + the real AMD verification test layered on top.

In scope for the demo:
- Small curated set of official AMD documents (URLs/PDFs) ingested and indexed.
- Embeddings + local vector index.
- Retrieval + grounded LLM answers with citations.
- Static hardware catalogue (curated YAML/JSON) with simple compare and recommend.
- Minimal Streamlit UI.
- LLM inference via AMD Token Factory (primary), with a swappable fallback (local Ollama /
  AMD Developer Cloud vLLM) so the slice is never dead if Token Factory access fails.
- A real verification test proving AMD execution before any "runs on AMD" claim.

Explicitly deferred past the on-site demo (post-MVP, if time allows):
- Larger corpus, automated re-ingestion, scheduled crawls.
- Reranking, hybrid search, query rewriting.
- Multi-turn conversation memory, persistent user accounts.
- Authenticated multi-user deployment.

## 5. Out of scope / non-goals

- Recommending non-AMD hardware.
- Pricing or procurement (we show specs and docs, not quotes).
- Real-time benchmarking or running the user's actual models on AMD hardware.
- Any answer or spec not traceable to an official AMD source.

## 6. Acceptance criteria

- [ ] A user can ask a hardware question in the UI and receive an answer with at least one
      verifiable citation linking to an official AMD source.
- [ ] For a question the corpus cannot answer, the assistant explicitly says it cannot
      answer from the provided docs (no hallucinated specs, no fabricated citations).
- [ ] The user can select 2–3 products and see a comparison table populated from the
      catalogue's real spec fields.
- [ ] The user can describe an AI workload and receive a hardware recommendation with
      rationale tied to catalogue specs and/or retrieved docs.
- [ ] The catalogue is populated only from official AMD sources; every spec field has a
      source URL recorded.
- [ ] Inference runs through the configured provider; switching provider is a config-only
      change.
- [ ] **AMD requirement:** a real test logs a chat completion returned from an AMD-hosted
      endpoint (Token Factory or Dev Cloud vLLM), including endpoint URL, model id,
      latency, and a marker confirming the host is AMD-provided. Until this test passes,
      the app never claims AMD execution.

## 7. Hackathon requirements (lablab.ai × AMD)

- Target event: **AMD Developer Hackathon: ACT III** (Oct 12–18 2026; on-site phase
  Oct 17–18). Also eligible for **AMD AI League** (Sep 1 – Dec 1 2026).
- Participants must sign up with AMD and hold an **AMD AI Developer Program (ADP)** account.
- A meaningful part of the working application must actually run on approved AMD
  infrastructure or hardware. AMD execution must be verified by a successful real test, not
  assumed.
- Proposed AMD infra: **AMD Token Factory** (`notebooks.amd.com/tokenfactory`, AMD AI
  Notebooks — GPU-powered Jupyter, ROCm). Status: login-gated, API/models/endpoints not
  publicly documented — **unverified at planning time**. See §8.
- Alternate approved AMD infra: **AMD Developer Cloud** (ROCm sandbox, Instinct MI300X,
  vLLM OpenAI-compatible endpoint). Requires registration/approval (24–48h).

## 8. Open decisions requiring verification before/during implementation

These are unresolved and must be confirmed by real tests or by the user before the
respective code is relied upon. They are flagged inline in ARCHITECTURE.md and AGENTS.md.

1. **AMD Token Factory availability & API shape** — endpoint URL, auth (API key/OAuth?),
   available models, request/response format (OpenAI-compatible?), rate limits. Unverified
   behind login. Must be confirmed by signing in and capturing a real request/response.
2. **AMD Developer Cloud provisioning** — registration approval and sandbox/vLLM
   availability; needed only if Token Factory is unavailable. Lead time 24–48h.
3. **Embedding model compatibility** — whether the chosen embedding model runs on the
   AMD provider or must run locally (sentence-transformers). Default: local embeddings
   regardless of LLM provider.
4. **Corpus selection** — the exact curated AMD URLs/PDFs to ingest. User confirms/trims
   the proposed list before ingestion.
5. **On-site feasibility** — whether a buildable core vertical slice is achievable in the
   remaining on-site window (Oct 17–18). If not, the demo falls back to the local
   inference path with AMD verification deferred to AMD AI League (Dec 1).
