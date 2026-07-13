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

_A bibliography of Newman's scholarship is archived at
`docs/newman_hausa_bibliography.pdf`._

> ⚠️ **Complete the exact edition details from the physical copy** (ISBN,
> printing, page count) before publishing derivatives — these should be filled
> in by the project owner, who holds the book.

## Copyright / use — READ BEFORE INGESTING

Unlike Robinson (1914), which is **public domain**, Newman's dictionaries are
**in copyright** (Modern Hausa–English Dictionary © 1977; A Hausa–English
Dictionary © 2007, Yale University Press). **Attribution alone does not grant
reproduction or derivative-use rights** for a copyrighted work.

Before this source is ingested into training data or a served product, the
usage basis must be confirmed by the project owner, e.g.:
- a licence or written permission from the rights holder (Oxford University
  Press Nigeria / Yale University Press / the authors), **or**
- limited, transformative reference use consistent with fair use / fair
  dealing (e.g. validation and cross-checking rather than wholesale copying),
  **or**
- the owner's own lawfully-acquired copy used within permitted bounds.

**Status: PENDING owner confirmation.** Credit is prepared here in advance; the
usage right is a separate, required step. This mirrors the project's
[serious-research standard] — credit *and* a clean legal basis.

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
