"""Streamlit UI for AMD Hardware Advisor.

Provides tabs for:
1. Q&A Chat: Grounded answers with verifiable source citations and fallback handling.
2. Catalogue & Comparison: Browse curated AMD hardware specs and compare products side-by-side.
3. Workload Recommender: Match AI workloads to suitable AMD hardware with rationale.
4. System & Verification Status: Check LLM provider state and AMD execution verification record.
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

import streamlit as st

# Ensure src/ and config/ are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from amd_hardware_advisor.answer import answer_query
from amd_hardware_advisor.catalogue import load_catalogue
from amd_hardware_advisor.compare import compare_models
from amd_hardware_advisor.llm.provider import get_llm_provider
from amd_hardware_advisor.recommend import WorkloadProfile, recommend_hardware
from amd_hardware_advisor.retrieval import retrieve
from amd_hardware_advisor.vector_index import VectorIndex
from config.settings import get_settings

logger = logging.getLogger("streamlit_app")

# Page config
st.set_page_config(
    page_title="AMD Hardware Advisor",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load settings, provider, and catalogue
@st.cache_resource
def get_cached_settings():
    return get_settings()

@st.cache_resource
def get_cached_provider():
    return get_llm_provider()

@st.cache_resource
def get_cached_catalogue():
    catalogue_path = PROJECT_ROOT / "data" / "catalogue" / "catalogue.yaml"
    try:
        return load_catalogue(catalogue_path)
    except Exception as exc:
        logger.error("failed to load catalogue: %s", exc)
        return []

settings = get_cached_settings()
provider = get_cached_provider()
catalogue = get_cached_catalogue()

# --- Sidebar ---
st.sidebar.title("🖥️ AMD Hardware Advisor")
st.sidebar.markdown(
    "RAG-powered assistant for official AMD documentation, product comparisons, "
    "and AI workload recommendations."
)

st.sidebar.markdown("---")
st.sidebar.subheader("System Status")
st.sidebar.text(f"LLM Provider: {provider.provider_name} ({provider.model_id})")
st.sidebar.text(f"Embeddings: {settings.embedding_model}")

# Check AMD verification status record
ver_path = PROJECT_ROOT / "index" / "amd_verification.json"
is_verified = False
if ver_path.exists():
    import json
    try:
        ver_data = json.loads(ver_path.read_text(encoding="utf-8"))
        is_verified = ver_data.get("verified", False)
    except Exception:
        pass

if is_verified:
    st.sidebar.success("✅ AMD Execution: VERIFIED")
else:
    st.sidebar.warning("⚠️ AMD Execution: NOT VERIFIED\n(Running on local fallback / unverified endpoint)")

st.sidebar.markdown("---")
st.sidebar.info(
    "**Hackathon MVP**\n"
    "Built for lablab.ai × AMD hackathons.\n"
    "All specs & citations trace directly to official AMD documentation."
)

# --- Main Tabs ---
tab_chat, tab_catalogue, tab_compare, tab_recommend, tab_status = st.tabs([
    "💬 Q&A Chat",
    "📚 Hardware Catalogue",
    "⚖️ Side-by-Side Compare",
    "🎯 Workload Recommender",
    "⚙️ Verification & Config",
])

# ==========================================
# TAB 1: Q&A Chat
# ==========================================
with tab_chat:
    st.header("Ask AMD Hardware Advisor")
    st.markdown(
        "Ask questions about AMD Instinct accelerators, EPYC CPUs, Radeon GPUs, or ROCm software. "
        "Answers are grounded strictly in official ingested documentation with verifiable source citations."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "citations" in message and message["citations"]:
                with st.expander("🔍 Verifiable Source Citations"):
                    for cit in message["citations"]:
                        page_str = f" (page {cit.page})" if cit.page else ""
                        st.markdown(f"- [{cit.source_url_or_file}{page_str}] (chunk: `{cit.chunk_id}`)")

    # User input
    if prompt := st.chat_input("e.g. What is the memory capacity and TDP of AMD Instinct MI300X?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Retrieving official documentation and generating grounded answer..."):
                try:
                    retrieved = retrieve(prompt, top_k=settings.top_k)
                    result = answer_query(prompt, retrieved, provider=provider)
                    answer_text = result.answer
                    citations = result.citations
                except Exception as exc:
                    answer_text = f"An error occurred while generating the answer: {exc}"
                    citations = []

                st.markdown(answer_text)
                if citations:
                    with st.expander("🔍 Verifiable Source Citations"):
                        for cit in citations:
                            page_str = f" (page {cit.page})" if cit.page else ""
                            st.markdown(f"- [{cit.source_url_or_file}{page_str}] (chunk: `{cit.chunk_id}`)")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer_text,
                    "citations": citations,
                })

# ==========================================
# TAB 2: Hardware Catalogue
# ==========================================
with tab_catalogue:
    st.header("AMD Hardware Catalogue")
    st.markdown(
        "Structured, human-curated catalogue of AMD hardware products. Every record is backed by "
        "official AMD source documentation. Unverified numeric specs remain null until confirmed."
    )

    if not catalogue:
        st.warning("No catalogue products found. Ensure `data/catalogue/catalogue.yaml` exists.")
    else:
        # Filter by family
        families = sorted(list({p.family for p in catalogue}))
        selected_family = st.selectbox("Filter by Product Family", ["All"] + families)

        filtered_products = catalogue if selected_family == "All" else [p for p in catalogue if p.family == selected_family]

        for p in filtered_products:
            with st.container():
                cols = st.columns([3, 2, 2])
                with cols[0]:
                    st.subheader(f"{p.family} {p.model}")
                    if p.architecture:
                        st.text(f"Architecture: {p.architecture} (gfx: {p.gfx_id or 'N/A'})")
                with cols[1]:
                    mem = f"{p.memory_gb} GB {p.memory_type}" if p.memory_gb else "Specs unverified / null"
                    st.text(f"Memory: {mem}")
                    tdp = f"{p.tdp_w}W TDP" if p.tdp_w else "TDP: N/A"
                    st.text(tdp)
                with cols[2]:
                    verified_badge = "✅ Verified Spec" if p.source_verified else "⚠️ Unverified Seed Spec"
                    st.markdown(f"**Status:** {verified_badge}")
                    st.markdown(f"[Official Source]({p.source_url})")
                st.markdown("---")

# ==========================================
# TAB 3: Side-by-Side Compare
# ==========================================
with tab_compare:
    st.header("Side-by-Side Product Comparison")
    st.markdown(
        "Compare two or more AMD hardware products across core specification fields drawn strictly "
        "from the structured hardware catalogue."
    )

    if not catalogue:
        st.warning("Catalogue is empty.")
    else:
        all_models = [p.model for p in catalogue]
        selected_models = st.multiselect(
            "Select 2 or more models to compare",
            options=all_models,
            default=all_models[:2] if len(all_models) >= 2 else all_models,
        )

        if len(selected_models) < 2:
            st.info("Please select at least two models to generate a comparison table.")
        else:
            try:
                table = compare_models(selected_models, catalogue)
                # Render table
                import pandas as pd
                df_data = []
                for field_name in table.fields:
                    row_dict = {"Specification": field_name.replace("_", " ").title()}
                    for m in table.models:
                        row_dict[m] = table.rows[m].get(field_name, "N/A")
                    df_data.append(row_dict)

                df = pd.DataFrame(df_data)
                st.table(df)

                st.subheader("Source Provenance Links")
                for m in table.models:
                    st.markdown(f"- **{m}**: [{table.source_urls[m]}]({table.source_urls[m]})")

            except Exception as exc:
                st.error(f"Comparison error: {exc}")

# ==========================================
# TAB 4: Workload Recommender
# ==========================================
with tab_recommend:
    st.header("AI Workload Hardware Recommender")
    st.markdown(
        "Describe your AI workload parameters to receive suitable AMD hardware recommendations "
        "ranked by capability, backed by catalogue specs and retrieved documentation rationale."
    )

    col1, col2 = st.columns(2)
    with col1:
        task_type = st.selectbox(
            "Workload Type",
            ["llm_inference", "llm_training", "hpc_simulation", "general_ai"],
        )
        min_mem = st.number_input("Minimum Memory Required (GB)", min_value=0.0, value=128.0, step=16.0)
    with col2:
        framework = st.selectbox("Preferred Framework / Stack", ["ROCm", "PyTorch", "ONNX-RT", "Any"])
        prefer_apu = st.checkbox("Prefer APU (Unified CPU+GPU Memory, e.g. MI300A)", value=False)

    if st.button("Generate Recommendations", type="primary"):
        with st.spinner("Scoring hardware and retrieving documentation rationale..."):
            profile = WorkloadProfile(
                task_type=task_type,
                min_memory_gb=min_mem if min_mem > 0 else None,
                framework=framework if framework != "Any" else None,
                prefer_apu=prefer_apu,
            )
            recs = recommend_hardware(profile, catalogue, top_n=3)

            if not recs:
                st.warning("No recommendations could be generated.")
            else:
                for rec in recs:
                    with st.container():
                        st.subheader(f"Rank #{rec.rank}: {rec.product.family} {rec.product.model} (Score: {rec.score:.1f})")
                        st.markdown(f"**Rationale:** {rec.rationale}")
                        st.markdown(f"**Source Document:** [{rec.product.source_url}]({rec.product.source_url})")
                        st.markdown("---")

# ==========================================
# TAB 5: Verification & Config
# ==========================================
with tab_status:
    st.header("System Configuration & AMD Verification Record")
    st.markdown(
        "Inspect the active runtime configuration, provider backend, and the cryptographic/structured "
        "verification record proving AMD execution state."
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Runtime Settings")
        st.json({
            "llm_provider": provider.provider_name,
            "model_id": provider.model_id,
            "embedding_model": settings.embedding_model,
            "top_k": settings.top_k,
            "chunk_size": settings.chunk_size,
            "is_amd_provider": provider.is_amd_hosted,
        })
    with col2:
        st.subheader("AMD Verification Record (`index/amd_verification.json`)")
        if ver_path.exists():
            try:
                ver_content = json.loads(ver_path.read_text(encoding="utf-8"))
                st.json(ver_content)
            except Exception as e:
                st.error(f"Error reading verification record: {e}")
        else:
            st.info("No verification record found. Run `scripts/verify_amd.py` to generate one.")

    if st.button("Run Verification Probe"):
        with st.spinner("Executing verification probe against active provider endpoint..."):
            import subprocess
            res = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_amd.py")],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                st.success("Verification probe completed successfully!")
                st.code(res.stdout)
            else:
                st.error("Verification probe encountered an error or failed:")
                st.code(res.stderr or res.stdout)
