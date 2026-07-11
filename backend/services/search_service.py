"""
Live web search grounding via Tavily (https://tavily.com), a search API built
for LLM grounding rather than human browsing.

Design contract — graceful degradation is mandatory:
  * With NO API key set (TAVILY_API_KEY / TAVILY_SEARCH_API_KEY), search_enabled()
    is False and web_search() returns [] without touching the network. The chat
    path then behaves exactly as before (honest "no live access").
  * With a key set, web_search() returns a small list of {title, url, content}
    dicts. ANY error, timeout, or malformed response also yields [] — this
    function NEVER raises into the request path. Failures are logged at warning.

httpx is already a project dependency; no new dependency is introduced.
"""

import logging
import os

import httpx

logger = logging.getLogger("murya.search")

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_TIMEOUT_SECONDS = 6.0


def _get_api_key() -> str | None:
    """Read the Tavily key from env, preferring TAVILY_API_KEY and falling back
    to TAVILY_SEARCH_API_KEY. Empty strings count as unset."""
    return (
        os.getenv("TAVILY_API_KEY")
        or os.getenv("TAVILY_SEARCH_API_KEY")
        or None
    )


def search_enabled() -> bool:
    """True iff a Tavily API key is configured. Callers gate live search on this
    so no network call is attempted (and no latency added) when unconfigured."""
    return _get_api_key() is not None


async def web_search(query: str, max_results: int = 4) -> list[dict]:
    """Run a live web search for `query` and return up to `max_results` results
    as [{title, url, content}]. Returns [] on missing key, timeout, or any error
    — never raises. If Tavily supplies a synthesized "answer", it is prepended
    as the first result with title "Tavily summary"."""
    api_key = _get_api_key()
    if not api_key:
        return []

    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(_TAVILY_ENDPOINT, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as err:  # noqa: BLE001 — must never propagate into request path
        logger.warning("Tavily search failed (%s: %s)", type(err).__name__, err)
        return []

    results: list[dict] = []

    # Tavily's optional synthesized answer is the most useful single line for
    # grounding, so surface it first as a pseudo-result.
    answer = data.get("answer")
    if isinstance(answer, str) and answer.strip():
        results.append({
            "title": "Tavily summary",
            "url": "",
            "content": answer.strip(),
        })

    for item in data.get("results", []) or []:
        if not isinstance(item, dict):
            continue
        results.append({
            "title": (item.get("title") or "").strip(),
            "url": (item.get("url") or "").strip(),
            "content": (item.get("content") or "").strip(),
        })

    return results[:max_results]
