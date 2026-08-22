"""
You.com Answer API — FALLBACK search provider behind Tavily (search_service.py),
for live-search grounding resilience only. Not a parallel Extract/Crawl/Research
pipeline (Tavily already covers that; adding a second one would just duplicate
capability — see docs/murya_roadmap.md discussion). This exists purely so a
Tavily outage or exhausted key doesn't silently take down live search, the same
resilience reasoning applied to the Cerebras -> Ollama -> Gemini chat fallback
chain.

Design contract — identical graceful degradation to search_service.py:
  * With no YOU_API_KEY, you_enabled() is False and web_search_you() returns []
    without touching the network.
  * ANY error, timeout, or malformed response yields [] — never raises into the
    request path.
  * Return shape matches search_service.web_search() exactly:
    [{title, url, content}, ...] — a drop-in fallback for the same caller.
"""

import logging
import os

import httpx

logger = logging.getLogger("murya.you")

_YOU_ENDPOINT = "https://api.you.com/v1/answer"
_TIMEOUT_SECONDS = 8.0


def _get_api_key() -> str | None:
    return os.getenv("YOU_API_KEY") or None


def you_enabled() -> bool:
    """True iff a You.com API key is configured."""
    return _get_api_key() is not None


async def web_search_you(query: str, max_results: int = 4) -> list[dict]:
    """Run a live web search+answer via You.com and return up to `max_results`
    results as [{title, url, content}] — same shape as search_service.web_search
    so it's a drop-in fallback. Returns [] on missing key, timeout, or any
    error — never raises. The synthesized answer (if present) is prepended as
    the first result, matching Tavily's "summary" convention."""
    api_key = _get_api_key()
    if not api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                _YOU_ENDPOINT,
                headers={"X-API-Key": api_key},
                json={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as err:  # noqa: BLE001 — must never propagate into request path
        logger.warning("You.com search failed (%s: %s)", type(err).__name__, err)
        return []

    results: list[dict] = []

    answer = data.get("answer")
    if isinstance(answer, str) and answer.strip():
        results.append({"title": "You.com summary", "url": "", "content": answer.strip()})

    for item in ((data.get("results") or {}).get("web") or []):
        if not isinstance(item, dict):
            continue
        snippets = item.get("snippets") or []
        content = " ".join(s for s in snippets if isinstance(s, str)) or (item.get("description") or "")
        results.append({
            "title": (item.get("title") or "").strip(),
            "url": (item.get("url") or "").strip(),
            "content": content.strip(),
        })

    return results[:max_results]
