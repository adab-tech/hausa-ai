"""
Build a Hausa Wikipedia text corpus for Milestone #1 (native Hausa LLM) using
Tavily's Map + Extract — see docs/murya_roadmap.md and
data/sources/hausa-wikipedia/ATTRIBUTION.md.

Licence discipline (same standard as Robinson/Wiktionary/Newman): Hausa
Wikipedia (ha.wikipedia.org) is CC-BY-SA 4.0 — openly licensed, safe to use as
training text with attribution and share-alike on any redistributed derivative.
This script is deliberately scoped to that ONE domain. Do NOT repoint it at
copyrighted news sites (BBC Hausa, VOA Hausa, etc.) without a real licence check
first — Tavily's Extract/Crawl are just tools; they don't grant rights to
whatever they pull.

Pipeline:
  1. Map ha.wikipedia.org for real article URLs (excludes Special:/Wikipedia:/
     Talk:/Category:/Template:/Help:/Portal:/File: namespaces).
  2. Extract each article's content (Tavily markdown).
  3. Clean: Wikipedia's UI chrome (nav, login prompts) always precedes the
     first '# Title' heading in Tavily's markdown output — keep only from
     there onward. Drop stub articles below a minimum length.
  4. Write one JSON row per article: {title, url, text, source, license}.

Cost note: Map + Extract consume Tavily credits (not free). Defaults are
deliberately modest (200 articles) — rerun with --limit for more once you've
checked the output quality and credit budget.

Run:  python utils/build_hausa_wikipedia_corpus.py [--limit 200]
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "backend"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

_OUT_DIR = _REPO / "data" / "processed" / "hausa_wikipedia_corpus"
_OUT = _OUT_DIR / "articles.jsonl"
_MANIFEST = _OUT_DIR / "manifest.json"

_SOURCE_TAG = "hausa_wikipedia_ccbysa"
_LICENSE = "CC-BY-SA-4.0"
_MIN_CHARS = 300  # drop stubs below this length (after cleaning)

# Real article paths only — exclude Wikipedia's non-article namespaces (Hausa
# uses "Musamman" for "Special").
_EXCLUDED_PREFIXES = (
    "Musamman:", "Wikipedia:", "Tattaunawa:", "Category:", "Rukuni:",
    "Template:", "Samfuri:", "Help:", "Taimako:", "Portal:", "Kofa:",
    "File:", "Fayil:", "Talk:", "User:", "Mai amfani:", "Module:",
)
_HEADING_RE = re.compile(r"^#\s+\S.*$", re.MULTILINE)
# Markdown link syntax '[text](url "optional title")'. Titles can contain
# nested parens (e.g. "Taraškievica orthography)"), so match greedily to the
# LAST ')' on the line rather than the first — correct for the single-link-
# per-line chrome lines this is meant to strip, even though it would over-match
# on a line with multiple distinct links (acceptable here: multi-link lines in
# this UI chrome are exactly what we want gone anyway).
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(.*\)")
_MIN_PROSE_CHARS = 40  # visible (non-link) text needed to count as real prose

# Known Wikipedia UI/theme chrome strings that carry no links (so the
# link-density filter above can't catch them) but recur verbatim across many
# pages — the modern Wikipedia skin's dark-mode toggle, "not supported in
# other languages" placeholder, etc. Same pattern as
# dictionary_service._ABBREV_NOISE: a small, maintainable known-junk list
# rather than trying to structurally detect every UI variant.
_KNOWN_CHROME_PHRASES = (
    "the content is as wide as possible for your browser window",
    "color (beta)",
    "this page is always in light mode",
    "page contents not supported in other languages",
    "daga wikipedia, insakulofidiya ta kyauta",  # "From Wikipedia, the free encyclopedia"
    "automatic  light  dark",
)


def _is_known_chrome(line: str) -> bool:
    low = line.strip().lower()
    return any(phrase in low for phrase in _KNOWN_CHROME_PHRASES)


def _visible_text_len(line: str) -> int:
    """Length of `line` with markdown link syntax stripped out — chrome lines
    (interwiki language lists, edit/talk nav bullets) are almost entirely link
    markup and leave little behind; prose leaves most of the line behind."""
    stripped_line = line.strip().lstrip("*-").strip()
    without_links = _MD_LINK_RE.sub("", stripped_line)
    return len(without_links.strip())


def _clean(markdown: str) -> str:
    """Strip Wikipedia's UI chrome, which surrounds the actual article on both
    sides in Tavily's extraction:
      1. Nav/login chrome BEFORE the first '# Title' heading — skip to it.
      2. An interwiki-language-links block AND short edit/talk nav bullets
         AFTER the heading but before real prose — skip line-by-line by
         visible-text density until a genuine prose line appears.
    Returns '' if no heading is found, or no prose line is ever found
    (chrome-only / stub / disambiguation-only page)."""
    m = _HEADING_RE.search(markdown)
    if not m:
        return ""
    heading = m.group(0).strip()
    lines = markdown[m.end():].splitlines()

    start = None
    for i, line in enumerate(lines):
        if not line.strip() or _is_known_chrome(line):
            continue
        if _visible_text_len(line) >= _MIN_PROSE_CHARS:
            start = i
            break
    if start is None:
        return ""
    # Second pass over the kept body: drop image lines ('![...](...)'),
    # table/infobox rows (pipe-delimited — Wikipedia infoboxes render as
    # markdown tables), and known UI chrome — these can recur anywhere in the
    # body, not just at the boundary.
    body_lines = [
        ln for ln in lines[start:]
        if not ln.strip().lstrip("[").startswith("![")  # bare or linked image
        and ln.strip().count("|") < 2
        and not _is_known_chrome(ln)
    ]
    return (heading + "\n\n" + "\n".join(body_lines)).strip()


# Substrings that indicate a non-article page regardless of WHERE they appear
# in the title — Wikipedia has compound namespaces like "Tattaunawar user:..."
# ("talk of user:...") that don't start with any single excluded prefix above.
_EXCLUDED_SUBSTRINGS = ("user:", "tattaunawar",)


def _is_article_url(url: str) -> bool:
    if "/wiki/" not in url:
        return False
    title = unquote(url.split("/wiki/", 1)[1])
    if any(title.startswith(p) for p in _EXCLUDED_PREFIXES):
        return False
    low = title.lower()
    return not any(s in low for s in _EXCLUDED_SUBSTRINGS)


async def build(limit: int) -> int:
    from services import tavily_service as t

    if not t.tavily_enabled():
        print("[error] TAVILY_API_KEY not set — nothing to do.")
        return 1

    print(f"[1/3] Mapping ha.wikipedia.org (limit={limit})...")
    all_urls = await t.map_site("https://ha.wikipedia.org", max_depth=2, limit=limit * 2)
    article_urls = [u for u in all_urls if _is_article_url(u)][:limit]
    print(f"      {len(all_urls)} URLs found, {len(article_urls)} are real articles")
    if not article_urls:
        print("[error] no article URLs discovered — aborting.")
        return 1

    print(f"[2/3] Extracting {len(article_urls)} articles (batches of 20)...")
    rows = []
    for i in range(0, len(article_urls), 20):
        batch = article_urls[i:i + 20]
        extracted = await t.extract_urls(batch, extract_depth="advanced")
        for item in extracted:
            text = _clean(item["content"])
            if len(text) < _MIN_CHARS:
                continue
            title = unquote(item["url"].rsplit("/wiki/", 1)[-1]).replace("_", " ")
            rows.append({
                "title": title, "url": item["url"], "text": text,
                "source": _SOURCE_TAG, "license": _LICENSE,
            })
        print(f"      batch {i // 20 + 1}: {len(extracted)} extracted, {len(rows)} kept so far")

    if not rows:
        print("[error] no usable articles after cleaning — aborting.")
        return 1

    print(f"[3/3] Writing {len(rows)} articles...")
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    with _OUT.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    total_chars = sum(len(r["text"]) for r in rows)
    manifest = {
        "total_articles": len(rows),
        "total_chars": total_chars,
        "source": "Hausa Wikipedia (ha.wikipedia.org)",
        "license": _LICENSE,
        "extraction_tool": "Tavily Map + Extract (advanced)",
        "note": "Raw article text for pretraining-style continued training, "
                "distinct from the instruction-pair datasets. Attribution "
                "required on any redistribution (CC-BY-SA share-alike). "
                "HONEST QUALITY NOTE: cleaning is automated and heuristic "
                "(strips nav/interwiki/edit-UI chrome and known theme-toggle "
                "phrases); most output is genuine prose, but occasional "
                "residual noise remains (short image-caption fragments, rare "
                "artifact characters). Recommend a human spot-check pass "
                "before large-scale training use; a dedicated tool like "
                "wikiextractor would clean more thoroughly if needed.",
    }
    _MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] {len(rows)} articles, {total_chars:,} chars -> {_OUT}")
    print(f"[ok] manifest -> {_MANIFEST}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200, help="max articles to pull (default 200)")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(build(args.limit)))
