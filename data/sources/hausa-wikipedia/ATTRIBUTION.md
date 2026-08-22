# Hausa Wikipedia (open text corpus for the native Hausa LLM)

## Source & credit

Article text from **Hausa Wikipedia** (ha.wikipedia.org), written and
maintained by its volunteer editor community.

- Upstream: https://ha.wikipedia.org
- Extraction: [Tavily](https://tavily.com) Map (URL discovery) + Extract
  (clean content) — see `backend/services/tavily_service.py` and
  `utils/build_hausa_wikipedia_corpus.py`.

## Licence — free to use with attribution + share-alike

Wikipedia text is dual-licensed **Creative Commons Attribution-ShareAlike 4.0
(CC-BY-SA 4.0)** and the **GNU Free Documentation License (GFDL)** — the same
licence family as the Wiktionary data already used for the HA→EN dictionary
(`data/sources/wiktionary-hausa/ATTRIBUTION.md`). Reuse and derivative works
(including training data) are permitted provided:
1. **Attribution** to Hausa Wikipedia and its contributors, and
2. **Share-alike** — any downstream redistribution of the derived corpus
   carries the same CC-BY-SA licence.

**Scope discipline:** this project only extracts from `ha.wikipedia.org`.
Tavily's Extract/Crawl tools can technically pull from any site, but they do
not grant a licence to whatever they pull — the same standard applied to
Newman's dictionaries (credit ≠ licence) applies here in reverse: Wikipedia's
licence is what makes this source safe, not the tool used to fetch it. Do NOT
repoint the corpus builder at copyrighted news sites (BBC Hausa, VOA Hausa,
Aminiya, etc.) without a real licence check first.

## Suggested attribution string

> Hausa-language text from Wikipedia (ha.wikipedia.org), contributors,
> CC-BY-SA 4.0.

## Usage in this project

- Feeds `data/processed/hausa_wikipedia_corpus/articles.jsonl` — raw article
  text (not instruction pairs) for pretraining-style continued training,
  distinct from the Alpaca-style instruction datasets
  (`utils/build_hausa_instruction_dataset.py`, community Q&A).
- Every row carries `source: "hausa_wikipedia_ccbysa"`,
  `license: "CC-BY-SA-4.0"`.
- **Share-alike obligation:** if this derived corpus is redistributed, keep it
  under CC-BY-SA 4.0 with this attribution intact.
- Refresh: rerun `python utils/build_hausa_wikipedia_corpus.py --limit N`
  (costs Tavily credits — check usage before large runs).
