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

**Open-license check (2026-07-13, done):** searched for a genuinely open edition.
Result — **none exists.** The dictionaries on the Internet Archive
(`hausaenglishdict0000newm`, etc.) are **access-restricted / controlled digital
lending / in-copyright** ("borrow" only, printdisabled) — free to *read*, not to
reuse. The only openly-licensed Newman work is his *Comprehensive Bibliography of
Chadic and Hausa Linguistics* (CC BY-NC-SA 3.0) — a bibliography, not a
dictionary, and NonCommercial. The 1977 edition's own copyright page reads
"© Oxford University Press 1977 / © University Press Limited, 1979"; the 2007
edition "© 2007 Yale University, all rights reserved." Rights holders to approach:
**University Press PLC, Ibadan** (+ OUP) for 1977; **Yale University Press** for
2007; Paul Newman himself may help (open-access advocate). See
`docs/newman_permission_requests.md`.

**Status: APPROVED BY PROF. PAUL NEWMAN (2026-08-22), via direct email to the
project owner.** Newman's own words (written in Hausa, from his official email):

> "Na yi murna da samun saƙon imel ɗinka. AI a harshen Hausa, ba dama!"
> ("I was delighted to receive your email. Hausa-language AI, why not indeed!")

Followed in English:

> "Although I am now fully retired, I would be happy to support you in your work
> and give you support and permissions."

This is a genuine, direct grant from the author himself — the cleanest possible
basis, stronger than a publisher licence. It sits alongside, not instead of, full
credit (see below) — Newman's own generosity is exactly why the credit matters.

**One precision to close out, in the spirit of this project's [serious-research
standard]:** Newman's message grants permission warmly and in general terms. For
the record to be as precise as everything else here, worth a brief follow-up
reply to him confirming the exact scope in writing — e.g. "to confirm for my
project records: permission to digitize and use both the 1977 *Modern
Hausa–English Dictionary* and the 2007 *A Hausa–English Dictionary* as training
data for Murya, with full credit to you — is that right?" A specific written
"yes" to that closes the loop completely. Not a blocker to starting integration
work — just good practice to have on file.

**Ingestion STARTED (2026-08-22).** Discovered the 1977 PDF's embedded "text
layer" is low-quality legacy OCR (font literally named "InvisibleOCR") that
garbles hooked consonants (ɓ ɗ ƙ) and drops tone marks inconsistently — e.g.
real "bụlà" extracts as "byl&". Verified this by rendering pages to images and
reading them directly: the underlying scan is fully legible, so real ingestion
uses page-image transcription, not the broken text layer. Proof-of-concept done
on page 16 (39 clean entries, `data/processed/newman_1977/ha_en_pairs.jsonl`).
Remaining 143 pages (17-159) of the dictionary body dispatched to 4 parallel
background transcription passes, writing to
`data/processed/newman_1977/ha_en_pairs_chunk{1..4}.jsonl` with per-page
progress logs — merge + dedupe + wire into `dictionary_service.py` once all
chunks land, with a human spot-check before it ships (this project's standard
for new corpora). The 2007 scan (no text layer at all — needs the same
page-image approach across all 262 pages) is not yet started; likely superseded
by the newer 2020/2022 BUK bidirectional edition once acquired (see below), so
deprioritized until that's resolved.

## A better-fit source, flagged by Newman himself (2026-08-22)

In the same email exchange, Prof. Newman pointed to a newer, better-suited work:

> Newman, Paul, and Roxana Ma Newman. *Hausa Dictionary (Hausa–English •
> English–Hausa) / Ƙamusun Hausa (Hausa–Ingilishi • Ingilishi–Hausa).* Kano:
> Bayero University Press, 2020 (revised 2nd printing and e-book, Oxford:
> African Books Collective, 2022).

**Why this is the better source, in his own words and ours:**
- **Bidirectional** — Hausa→English *and* English→Hausa in one work, unlike
  Robinson (EN→HA only) or the earlier Newman editions (HA→EN-oriented).
  Could eventually stand in for both directions at once.
- **Nigerian-published (Bayero University Kano)** — easier and less expensive
  to obtain than the Yale editions; also, fittingly, published by the same
  institution (BUK, successor context to the 1977 Centre for the Study of
  Nigerian Languages) rooted in Northern Nigeria.
- **E-book edition exists** (African Books Collective, Oxford, 2022) — likely a
  much cleaner acquisition path than OCRing an old library scan.
- **Drawback, in Newman's own words:** "the entries are not tone marked" —
  he guessed this is "probably irrelevant for your purposes." **Mostly true,
  worth one honest caveat:** irrelevant for the *dictionary/instruction-data*
  use here, but tone marking would matter for the project's separate
  **tone-channel TTS retrain** milestone (real intonation, see
  `docs/murya_roadmap.md` §4.2) — a future concern, not a reason to hold off
  on this dictionary now.

**Status: not yet acquired.** This falls under Newman's general permission
above, but the project does not have the file — Adamsy needs to obtain the
2022 e-book (African Books Collective) or a physical copy himself; a purchase
like this isn't something to do on his behalf. Once acquired, this should
likely become the PRIMARY Newman source (bidirectional, cleaner digital
format), with the 1977/2007 editions kept as secondary/cross-reference.

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
