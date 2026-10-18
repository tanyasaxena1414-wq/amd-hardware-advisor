"""P1 gate tests: ingestion (PDF + HTML parsing + domain allowlist + dry-run).

These must pass before P2 starts. PDF tests use a generated fixture (no binary shipped).
HTML parsing tests use a small inline HTML string (no network). URL fetching is a
separate, network-marked test (deselected by default).
"""

from pathlib import Path

import pytest

from amd_hardware_advisor.ingestion import (
    ALLOWED_FETCH_DOMAINS,
    BROWSER_USER_AGENT,
    SourceDoc,
    load_dir,
    load_documents,
    load_pdf,
    _parse_html,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# --- PDF loading (generated fixture, no shipped binary) ---


@pytest.fixture(scope="module")
def fixture_pdf(tmp_path_factory):
    """Generate a tiny 2-page PDF on the fly using fpdf2 (dev-only dep)."""
    from fpdf import FPDF

    d = tmp_path_factory.mktemp("pdfs")
    pdf_path = d / "amd_fixture.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.cell(200, 10, text="AMD Instinct MI300X has 192 GB HBM3 memory.")
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    pdf.cell(200, 10, text="ROCm 10.1 supports Instinct MI355X and MI300X.")
    pdf.output(str(pdf_path))
    return pdf_path


def test_load_pdf_returns_per_page_docs(fixture_pdf):
    docs = load_pdf(fixture_pdf)
    assert len(docs) == 2, "fixture PDF has 2 pages"
    assert all(isinstance(d, SourceDoc) for d in docs)
    assert [d.page for d in docs] == [1, 2]
    assert docs[0].pages == 2
    assert docs[0].source_type == "pdf"
    assert "MI300X" in docs[0].text
    assert "ROCm" in docs[1].text


def test_load_pdf_carries_source_path_for_citations(fixture_pdf):
    docs = load_pdf(fixture_pdf)
    for d in docs:
        assert d.source_url_or_file == str(fixture_pdf)
        assert d.id  # stable id present


def test_load_pdf_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_pdf(tmp_path / "nope.pdf")


def test_load_dir_loads_all_pdfs(fixture_pdf):
    docs = load_dir(Path(fixture_pdf).parent)
    assert len(docs) == 2


# --- HTML parsing (inline, no network) ---


SAMPLE_HTML = """<!DOCTYPE html>
<html><head>
  <title>AMD Instinct MI300X</title>
  <link rel="canonical" href="https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html">
</head><body>
  <nav>skip nav</nav>
  <article>
    <h1>AMD Instinct MI300X Accelerator</h1>
    <p>The MI300X features 192 GB of HBM3 memory and CDNA 3 architecture.</p>
    <p>It is designed for large-scale AI training and generative AI workloads.</p>
  </article>
  <footer>skip footer</footer>
</body></html>"""


def test_parse_html_extracts_article_text():
    doc = _parse_html(
        SAMPLE_HTML,
        request_url="https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html",
        fetched_at="Thu, 17 Oct 2026 12:00:00 GMT",
    )
    assert doc.source_type == "html"
    assert "192 GB" in doc.text
    assert "CDNA 3" in doc.text
    assert "skip nav" not in doc.text  # nav excluded by article-first extraction
    assert "skip footer" not in doc.text


def test_parse_html_uses_canonical_url():
    """Canonical link is preferred over the request URL for citation stability."""
    doc = _parse_html(
        SAMPLE_HTML,
        request_url="https://example.com/redirect-here",
        fetched_at="",
    )
    assert doc.source_url_or_file == (
        "https://www.amd.com/en/products/accelerators/instinct/mi300/mi300x.html"
    )


def test_parse_html_title():
    doc = _parse_html(SAMPLE_HTML, request_url="https://amd.com/x", fetched_at="")
    assert "MI300X" in doc.title


# --- Domain allowlist + User-Agent ---


def test_user_agent_is_realistic_browser():
    """Option A: realistic browser UA so amd.com pages don't reject the fetch."""
    assert "Mozilla/5.0" in BROWSER_USER_AGENT
    assert "Chrome" in BROWSER_USER_AGENT


def test_allowed_domains_include_amd():
    for d in ("amd.com", "docs.amd.com", "rocm.docs.amd.com"):
        assert d in ALLOWED_FETCH_DOMAINS


# --- Dry-run behavior (offline) ---


def test_load_documents_skips_urls_when_fetch_disabled(caplog):
    """Offline dry-run must not attempt network fetches; URL sources are skipped."""
    docs = load_documents(
        ["https://rocm.docs.amd.com/en/latest/about/release-notes.html"],
        fetch_urls=False,
    )
    assert docs == []
    assert any("skipping URL source" in r.message for r in caplog.records)


def test_load_documents_mixed_sources(fixture_pdf):
    """PDF paths load immediately; URLs skipped without --fetch-urls."""
    docs = load_documents(
        [str(fixture_pdf), "https://rocm.docs.amd.com/en/latest/install/rocm.html"],
        fetch_urls=False,
    )
    assert len(docs) == 2
    assert all(d.source_type == "pdf" for d in docs)


# --- Network-gated fetch test (deselected by default) ---


@pytest.mark.network
def test_fetch_mi300x_pdf_live():
    """Real fetch of the official MI300X datasheet PDF. Run with:
    pytest -m network tests/test_ingestion.py::test_fetch_mi300x_pdf_live
    """
    from amd_hardware_advisor.ingestion import load_documents

    docs = load_documents(
        ["https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/data-sheets/amd-instinct-mi300x-data-sheet.pdf"],
        fetch_urls=True,
    )
    assert len(docs) > 0
    assert docs[0].source_type == "pdf"
    assert "MI300X" in docs[0].text or "Instinct" in docs[0].text
