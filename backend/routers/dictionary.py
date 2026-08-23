"""
Dictionary search — direct access to the same lexicon chat's hidden "ma'anar
kalmar X" tool trigger already uses (Robinson 1914 + Wiktionary CC-BY-SA +
Newman 1977, ~30,700 entries), but as its own endpoint instead of something
only surfaced when a chat message happens to match a regex.

GET /api/dictionary?q=<term>  — PUBLIC, no auth. Looks `term` up in both
directions (EN->HA and HA->EN), case- and diacritic-insensitive.
"""

from fastapi import APIRouter, Query, Request

import services.dictionary_service as dictionary_service
from rate_limit import limiter

router = APIRouter()

_SOURCE_LABEL = {
    "robinson_1914_vol2": "Robinson (1914)",
    "wiktionary_ha_ccbysa": "Wiktionary (CC-BY-SA)",
    "newman_1977": "Newman (1977)",
}


@router.get("/dictionary")
@limiter.limit("30/minute")
async def search_dictionary(request: Request, q: str = Query(..., min_length=1, max_length=100)):
    """PUBLIC: look up a word/phrase. Returns {ready, query, results: [...]}."""
    if not dictionary_service.dictionary_ready():
        return {"ready": False, "query": q, "results": []}

    results = dictionary_service.define(q, max_results=12)
    return {
        "ready": True,
        "query": q,
        "results": [
            {
                "headword": r["headword"],
                "translation": r["translation"],
                "context": r.get("context", ""),
                "direction": r["direction"],
                "source": _SOURCE_LABEL.get(r.get("provenance", ""), r.get("provenance") or "unknown"),
            }
            for r in results
        ],
    }
