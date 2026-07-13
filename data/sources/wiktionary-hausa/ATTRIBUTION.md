# Wiktionary Hausa lexicon (open HA→EN source)

## Source & credit

Hausa entries extracted from **English Wiktionary** by the **Kaikki.org**
machine-readable dictionary project.

- Upstream: https://en.wiktionary.org (Hausa-language entries)
- Extraction: https://kaikki.org/dictionary/Hausa/ (Tatu Ylonen / Kaikki.org,
  built with the `wiktextract` tool)
- Raw file archived here: `kaikki-Hausa.jsonl` (2,187 Hausa headwords)

## Licence — free to use with attribution + share-alike

Wiktionary text is dual-licensed **Creative Commons Attribution-ShareAlike 4.0
(CC-BY-SA 4.0)** and the **GNU Free Documentation License (GFDL)**. This permits
reuse, redistribution, and derivative works — including in a served product and
in training data — provided that:
1. **Attribution** is given to Wiktionary and its contributors, and
2. **Share-alike** — derivative databases distributed downstream carry the same
   CC-BY-SA licence.

This is a genuinely open source: unlike the copyrighted Newman dictionaries
(see `../newman-dictionary/ATTRIBUTION.md`, NOT licensed for ingestion), nothing
here requires a separate permission grant.

## Suggested attribution string

> Hausa lexical data from Wiktionary (en.wiktionary.org), contributors,
> CC-BY-SA 4.0, via the Kaikki.org wiktextract extraction (kaikki.org).

## Usage in this project

- Powers the **Hausa→English** direction of
  `backend/services/dictionary_service.py`, complementing the public-domain
  Robinson (1914) EN→HA lexicon.
- Build step: `python utils/build_hausa_en_open.py` reads `kaikki-Hausa.jsonl`
  and writes `data/processed/hausa_en_open/ha_en_pairs.jsonl`
  (provenance tag `wiktionary_ha_ccbysa` on every entry).
- **Share-alike obligation:** if the derived lexicon
  (`data/processed/hausa_en_open/…`) is redistributed, keep it under CC-BY-SA 4.0
  and carry this attribution. Murya's own code stays under its own licence; this
  applies to the Wiktionary-derived *data*.
- Refresh: re-download from the Kaikki URL above and re-run the build script.
