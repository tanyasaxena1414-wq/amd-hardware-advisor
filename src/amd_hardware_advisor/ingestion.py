"""Document ingestion for the RAG corpus.

Loads PDFs (with page numbers) and HTML pages (with canonical URL) into a uniform
SourceDoc shape carrying provenance metadata for later citation tracing. No chunking here
(chunking is a separate module); no network calls are made unless a URL source is passed
to load_documents and the caller requests fetching.

Per AGENTS.md P1: only ingestion + catalogue are implemented this phase. No embeddings,
no index, no LLM calls.

Source URLs must be on official AMD domains (amd.com, docs.amd.com, rocm.docs.amd.com).
AMD product pages (amd.com) may block non-browser clients; we send a realistic
User-Agent to reduce that risk. If a fetch fails, we surface the error rather than
silently producing empty docs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Realistic desktop browser User-Agent. Used so AMD product pages don't reject the
# fetch as a bot. Approved by the user for P1 ingestion (option A).
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# Only official AMD documentation domains are allowed as fetch sources. This prevents
# the ingestion path from becoming an arbitrary URL fetcher.
ALLOWED_FETCH_DOMAINS = {
    "amd.com",
    "docs.amd.com",
    "rocm.docs.amd.com",
}

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB cap per page
FETCH_TIMEOUT_SECONDS = 30.0


@dataclass
class SourceDoc:
    """A normalized source document with provenance metadata for citation tracing."""

    id: str
    text: str
    source_type: str  # "pdf" | "html"
    source_url_or_file: str
    title: str
    page: int | None = None  # set per-page when iterating; None for whole-doc HTML
    pages: int = 0  # total pages (PDF) or 0 for HTML
    fetched_at: str = ""  # ISO8601, set on fetch
    extra: dict = field(default_factory=dict)


def _is_allowed_url(url: str) -> bool:
    """Only allow fetching from official AMD documentation domains."""
    try:
        host = urlparse(url).hostname or ""
    except ValueError:
        return False
    host = host.lower()
    return any(host == d or host.endswith("." + d) for d in ALLOWED_FETCH_DOMAINS)


def _doc_id(source: str) -> str:
    """Stable id for a source: hash of the url/file path."""
    import hashlib

    return hashlib.sha1(source.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# PDF loading
# ---------------------------------------------------------------------------


def load_pdf(path: str | Path) -> list[SourceDoc]:
    """Load a PDF file into one SourceDoc per page, each carrying its page number.

    Uses pypdf (pure-Python, no native deps). Page numbers are 1-indexed so they map
    to what a human sees in a PDF viewer — used later for citations like "page 4".
    """
    from pypdf import PdfReader

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    docs: list[SourceDoc] = []
    title = path.stem
    try:
        meta_title = reader.metadata
        if meta_title and meta_title.title:
            title = str(meta_title.title)
    except Exception:  # metadata is best-effort, never fatal
        logger.debug("could not read PDF metadata for %s", path)

    total = len(reader.pages)
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        docs.append(
            SourceDoc(
                id=_doc_id(f"{path}:{i}"),
                text=text,
                source_type="pdf",
                source_url_or_file=str(path),
                title=title,
                page=i,
                pages=total,
            )
        )
    logger.info("loaded PDF %s: %d pages", path, total)
    return docs


# ---------------------------------------------------------------------------
# HTML loading
# ---------------------------------------------------------------------------


def load_html(url: str, *, client: httpx.Client | None = None) -> SourceDoc:
    """Fetch and parse an HTML page into a single SourceDoc with canonical URL.

    Sends a realistic User-Agent (option A) to reduce bot-blocking on amd.com pages.
    Only official AMD domains are allowed. The canonical <link rel="canonical"> URL
    (if present) is preferred for citation stability over the request URL.
    """
    if not _is_allowed_url(url):
        raise ValueError(
            f"Refusing to fetch non-AMD URL: {url} "
            "(only amd.com, docs.amd.com, rocm.docs.amd.com are allowed)"
        )

    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    owns_client = client is None
    client = client or httpx.Client(
        follow_redirects=True, timeout=FETCH_TIMEOUT_SECONDS, headers=headers
    )
    try:
        resp = client.get(url)
        resp.raise_for_status()
        # Cap response size to avoid pulling huge pages into memory.
        body = resp.content[:MAX_RESPONSE_BYTES]
        html_text = body.decode(resp.encoding or "utf-8", errors="replace")
        fetched_at = resp.headers.get("date", "")
    finally:
        if owns_client:
            client.close()

    doc = _parse_html(html_text, request_url=url, fetched_at=fetched_at)
    logger.info("loaded HTML %s: %d chars", url, len(doc.text))
    return doc


def _parse_html(html_text: str, *, request_url: str, fetched_at: str) -> SourceDoc:
    """Extract readable text, title, and canonical URL from an HTML document.

    Uses selectolax (fast, lenient HTML parser). Pulls <article>/<main>/<body> text,
    the <title>, and the canonical <link> for citation stability.
    """
    from selectolax.parser import HTMLParser

    tree = HTMLParser(html_text)

    # Canonical URL (preferred for citations) — falls back to the request URL.
    canonical = request_url
    canonical_link = tree.css_first("link[rel='canonical']")
    if canonical_link is not None:
        href = canonical_link.attributes.get("href")
        if href:
            canonical = href

    # Title
    title = request_url
    title_node = tree.css_first("title")
    if title_node is not None and title_node.text(strip=True):
        title = title_node.text(strip=True)

    # Main readable text: prefer <article>, then <main>, then <body>.
    container = (
        tree.css_first("article")
        or tree.css_first("main")
        or tree.css_first("body")
        or tree
    )
    text = container.text(separator="\n", strip=True) if container is not None else ""

    return SourceDoc(
        id=_doc_id(canonical),
        text=text,
        source_type="html",
        source_url_or_file=canonical,
        title=title,
        page=None,
        pages=0,
        fetched_at=fetched_at,
    )


# ---------------------------------------------------------------------------
# Directory / multi-source loading
# ---------------------------------------------------------------------------


def load_dir(dir_path: str | Path) -> list[SourceDoc]:
    """Load every PDF in a directory as per-page SourceDocs. HTML is not fetched here;
    URL sources are passed explicitly to load_documents so fetches are intentional."""
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    docs: list[SourceDoc] = []
    for pdf_path in sorted(dir_path.glob("*.pdf")):
        docs.extend(load_pdf(pdf_path))
    return docs


def load_documents(
    sources: list[str], *, fetch_urls: bool = False
) -> list[SourceDoc]:
    """Load a mix of local PDF paths and AMD doc URLs into SourceDocs.

    Args:
        sources: file paths ending in .pdf, or URLs.
        fetch_urls: if True, fetch URL sources via httpx (network). If False, URL
            sources are skipped with a warning so offline dry-run don't hang. PDF
            paths are always loaded from disk.
    """
    docs: list[SourceDoc] = []
    for src in sources:
        if src.startswith(("http://", "https://")):
            if src.lower().endswith(".pdf"):
                # Remote PDF URL treated as URL source unless downloaded
                if not fetch_urls:
                    logger.warning("skipping remote PDF URL (fetch_urls=False): %s", src)
                    continue
                # Download remote PDF content via httpx and load pages
                try:
                    import tempfile
                    from urllib.parse import urlparse
                    parsed = urlparse(src)
                    domain = parsed.netloc.lower()
                    if not any(domain == d or domain.endswith("." + d) for d in ALLOWED_FETCH_DOMAINS):
                        logger.warning("domain not allowed for fetching: %s", domain)
                        continue

                    with httpx.Client(headers={"User-Agent": BORDER_USER_AGENT if "BORDER_USER_AGENT" in globals() else BROWSER_USER_AGENT}, follow_redirects=True, timeout=30.0) as client:
                        resp = client.get(src)
                        resp.raise_for_status()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                            tmp.write(resp.content)
                            tmp_path = tmp.name
                    try:
                        docs.extend(load_pdf(tmp_path))
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
                except Exception as exc:
                    logger.error("failed to fetch remote PDF %s: %s", src, exc)
                continue
            if not fetch_urls:
                logger.warning("skipping URL source (fetch_urls=False): %s", src)
                continue
            docs.append(load_html(src))
        elif src.lower().endswith(".pdf"):
            docs.extend(load_pdf(src))
        else:
            logger.warning("unsupported source type, skipping: %s", src)
    return docs


__all__ = [
    "SourceDoc",
    "load_pdf",
    "load_html",
    "load_dir",
    "load_documents",
    "BROWSER_USER_AGENT",
    "ALLOWED_FETCH_DOMAINS",
]
