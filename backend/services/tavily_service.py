"""
Tavily platform capabilities beyond basic search: Extract, Crawl, Map, and
Research — via the official `tavily-python` SDK (AsyncTavilyClient).

Two concrete uses in this project:
  1. Corpus gathering for the native Hausa LLM (Milestone #1, see
     docs/murya_roadmap.md) — Map + Extract/Crawl pull clean text from
     openly-licensed sources (starting with Hausa Wikipedia, CC-BY-SA) for
     utils/build_hausa_wikipedia_corpus.py. NEVER used to bulk-harvest
     copyrighted sites into training data — see that script's licence-check
     discipline, the same standard applied to Robinson/Wiktionary/Newman.
  2. A "deep research" chat mode (routers/chat.py) — multi-step, cited answers
     for complex questions, as an opt-in alternative to the quick single-shot
     search grounding in search_service.py (left untouched; this module is
     additive, not a replacement).

Design contract — same graceful degradation as search_service.py:
  * With no TAVILY_API_KEY, every function returns None/[]/{} without any
    network call. Callers behave exactly as if the feature didn't exist.
  * Any SDK error, timeout, or malformed response is caught and logged at
    warning — these functions NEVER raise into a request path.
"""

import logging
import os
from typing import Any

from tavily import AsyncTavilyClient

logger = logging.getLogger("murya.tavily")

_EXTRACT_TIMEOUT = 30.0
_CRAWL_MAP_TIMEOUT = 150.0  # Tavily's own max for these endpoints
_RESEARCH_TIMEOUT = 60.0

_client: AsyncTavilyClient | None = None
_client_checked = False


def _get_client() -> AsyncTavilyClient | None:
    """Lazily construct a single shared client, or None if no key is
    configured. Mirrors search_service._get_api_key's env var fallback."""
    global _client, _client_checked
    if _client_checked:
        return _client
    _client_checked = True
    api_key = os.getenv("TAVILY_API_KEY") or os.getenv("TAVILY_SEARCH_API_KEY")
    if api_key:
        _client = AsyncTavilyClient(api_key=api_key)
    return _client


def tavily_enabled() -> bool:
    """True iff a Tavily API key is configured."""
    return _get_client() is not None


async def extract_urls(urls: list[str], extract_depth: str = "basic") -> list[dict]:
    """Pull clean content from known URLs. Returns a list of
    {url, content, license_note} — content is markdown. Failed individual
    URLs are silently omitted (Tavily reports them separately as
    failed_results; not surfaced here since callers just want what worked).
    Returns [] on missing key or any error."""
    client = _get_client()
    if not client or not urls:
        return []
    try:
        resp = await client.extract(
            urls=urls, extract_depth=extract_depth, format="markdown",
            timeout=_EXTRACT_TIMEOUT,
        )
    except Exception as err:  # noqa: BLE001 — must never propagate
        logger.warning("Tavily extract failed (%s: %s)", type(err).__name__, err)
        return []
    out = []
    for item in (resp or {}).get("results", []) or []:
        if not isinstance(item, dict):
            continue
        content = (item.get("raw_content") or "").strip()
        if content:
            out.append({"url": item.get("url", ""), "content": content})
    return out


async def map_site(
    url: str, max_depth: int = 1, limit: int = 100,
    select_paths: list[str] | None = None,
) -> list[str]:
    """Discover URLs on a site (no content extraction — just the map).
    Use before crawl/extract to scope what you're about to pull. Returns []
    on missing key or any error."""
    client = _get_client()
    if not client:
        return []
    try:
        resp = await client.map(
            url=url, max_depth=max_depth, limit=limit,
            select_paths=select_paths, timeout=_CRAWL_MAP_TIMEOUT,
        )
    except Exception as err:  # noqa: BLE001
        logger.warning("Tavily map failed for %s (%s: %s)", url, type(err).__name__, err)
        return []
    results = (resp or {}).get("results", []) or []
    return [u for u in results if isinstance(u, str)]


async def crawl_site(
    url: str, max_depth: int = 1, limit: int = 50,
    instructions: str | None = None, select_paths: list[str] | None = None,
) -> list[dict]:
    """Traverse a site and extract content along the way in one call (map +
    extract combined). Returns a list of {url, content}. Returns [] on
    missing key or any error."""
    client = _get_client()
    if not client:
        return []
    try:
        resp = await client.crawl(
            url=url, max_depth=max_depth, limit=limit, instructions=instructions,
            select_paths=select_paths, format="markdown", timeout=_CRAWL_MAP_TIMEOUT,
        )
    except Exception as err:  # noqa: BLE001
        logger.warning("Tavily crawl failed for %s (%s: %s)", url, type(err).__name__, err)
        return []
    out = []
    for item in (resp or {}).get("results", []) or []:
        if not isinstance(item, dict):
            continue
        content = (item.get("raw_content") or "").strip()
        if content:
            out.append({"url": item.get("url", ""), "content": content})
    return out


async def start_research(
    query: str, model: str = "auto", output_length: str = "standard",
) -> str | None:
    """Kick off an async multi-step research task. Returns the request_id to
    poll with get_research_result(), or None on missing key / any error."""
    client = _get_client()
    if not client:
        return None
    try:
        resp = await client.research(
            input=query, model=model, citation_format="numbered",
            timeout=_RESEARCH_TIMEOUT,
        )
    except Exception as err:  # noqa: BLE001
        logger.warning("Tavily research start failed (%s: %s)", type(err).__name__, err)
        return None
    return (resp or {}).get("request_id")


async def get_research_result(request_id: str) -> dict[str, Any] | None:
    """Poll a research task by id. Returns the raw status dict (has at least
    a 'status' field; when complete, includes the synthesized report/answer
    and citations) or None on missing key / any error."""
    client = _get_client()
    if not client or not request_id:
        return None
    try:
        return await client.get_research(request_id)
    except Exception as err:  # noqa: BLE001
        logger.warning("Tavily get_research failed for %s (%s: %s)", request_id, type(err).__name__, err)
        return None
