# Newman Hausa–English Dictionary (source for the HA→EN track)

## Bibliographic credit

**Primary work (early, widely-used):**
> Newman, Paul & Roxana Ma Newman. *Modern Hausa–English Dictionary /
> Ƙamus na Zamani: Hausa–Turanci.* Ibadan: Oxford University Press (Nigeria),
> 1977.

**Authors:** **Paul Newman** and **Roxana Ma Newman** — foundational scholars of
Hausa linguistics and lexicography. Paul Newman is among the most cited Hausa
linguists worldwide; serious Hausa language technology cannot be done without
engaging his body of work.

**Also acknowledged (Newman's later comprehensive lexicon):**
> Newman, Paul. *A Hausa–English Dictionary.* New Haven: Yale University Press,
> 2007.

_Local copies (git-ignored, in copyright — not committed):_
- _`docs/Modern Hausa English Dictionary.pdf` — the 1977 work above
  (title page: "Sabon Ƙamus na Hausa zuwa Turanci"; Bayero University College,
  Centre for the Study of Nigerian Languages). Has a text layer._
- _`docs/newman_paul_a_hausaenglish_dictionary.pdf` — the 2007 Yale ed. (scanned)._
- _`docs/newman_hausa_bibliography.pdf` — bibliography of Newman's scholarship._

> ⚠️ **Complete the exact edition details from the physical copy** (ISBN,
> printing, page count) before publishing derivatives — these should be filled
> in by the project owner, who holds the book.

## Copyright / use — READ BEFORE INGESTING

The file `docs/newman_paul_a_hausaenglish_dictionary.pdf` is a **262-page scanned
image** of *A Hausa–English Dictionary*, **ISBN 978-0-300-12246-6,
Copyright © 2007 by Yale University**. Its copyright page states, verbatim:
"All rights reserved. This book may not be reproduced, in whole or in part …
without written permission from the publishers."

Unlike Robinson (1914), which is **public domain**, this is an **all-rights-
reserved commercial work with an explicit no-reproduction notice**. Owning a
physical copy does **not** grant the right to digitize the full text (OCR) and
ingest it into a training corpus or a served product — that is a distinct right
Yale University Press has expressly reserved. **Attribution does not substitute
for a licence.**

Permitted paths (project owner to choose / confirm):
- **Written permission / licence** from Yale University Press (they license for
  research and for products) — the clean basis for full ingestion. **[preferred]**
- **Limited, transformative reference use** — consulting *specific* entries to
  validate/correct an independently-built lexicon, without bulk-copying or
  redistributing Newman text. Does **not** extend to OCRing all 262 pages.
- **Openly-licensed sources instead** for the shipped HA→EN direction (Kamusi,
  Wiktionary HA CC-BY-SA, PanLex, etc.), with Newman used only as a private
  reference within the limits above.

**Status: NOT LICENSED for ingestion. Do NOT bulk-OCR / ingest this file into
training data or the served product until a licence or written permission is on
record here.** Credit is prepared; the legal basis is the missing, required
piece. This mirrors the project's [serious-research standard] — credit *and* a
clean legal basis, both.

## Suggested citation

> Newman, Paul, and Roxana Ma Newman. *Modern Hausa–English Dictionary
> (Ƙamus na Zamani: Hausa–Turanci).* Ibadan: Oxford University Press, 1977.

## Planned usage in this project

- **HA→EN direction** of `backend/services/dictionary_service.py` (replacing the
  rougher reverse-lookup over the EN→HA Robinson lexicon). Robinson (1914)
  stays as the public-domain EN→HA source.
- Every derived entry must carry provenance `"Newman 1977"` (or `"Newman 2007"`
  for that edition), just as Robinson entries carry `"robinson_1914_vol2"`.
- Do not remove this attribution file when copying data to other projects.
