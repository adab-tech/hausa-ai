# Permission request — Newman, *A Hausa–English Dictionary* (Yale UP, 2007)

**Purpose:** a ready-to-send request for written permission to use Paul Newman's
*A Hausa–English Dictionary* as a data source in the Murya Hausa-language AI.
Until permission is granted, the dictionary is **not** ingested (see
`data/sources/newman-dictionary/ATTRIBUTION.md`).

**Send to:** Yale University Press — Permissions Department.
Web form: https://yalebooks.yale.edu/permissions/ · Email: permissions@yale.edu
(verify the current address on that page before sending.)

> ⚠️ Before sending, fill the bracketed fields and confirm the exact rights you
> need. Decide up front whether you are asking for (a) *reference/validation*
> use only, or (b) *full ingestion* of the digitized text into training data —
> the fee and terms differ. The draft below asks for (b), the broader grant;
> trim to (a) if that is all you want.

---

## Draft letter

Subject: Permission request — data use of *A Hausa–English Dictionary* (Newman, 2007) in a Hausa-language AI

Dear Permissions Team,

I am writing to request permission to use **Paul Newman's *A Hausa–English
Dictionary*** (Yale University Press, 2007; ISBN 978‑0‑300‑12246‑6) as a
lexical reference source in a non-profit-oriented Hausa language-technology
project.

**About the project.** I am building *Murya*, a sovereign Hausa AI assistant
(voice and text) created by and for Hausa speakers, with the explicit goal of
strengthening the digital presence of the Hausa language. It is developed by
[NAME / Adab Tech Labs], based in [CITY, COUNTRY]. The current lexical layer is
built on the public-domain Robinson (1914) dictionary; Professor Newman's work
is the definitive modern Hausa–English reference, and its accuracy — especially
its tone and vowel-length marking — would materially improve the quality and
scholarly integrity of the system.

**What I am requesting.** Permission to:
- digitize (OCR) the dictionary text from a lawfully-obtained copy, and
- incorporate the resulting Hausa→English lexical entries into the application's
  dictionary/translation feature [and, if you grant it, into the training data
  for the underlying model],
with full and prominent attribution to Paul Newman and Yale University Press in
the product, its documentation, and any publication.

**Scope & safeguards.** [Describe distribution: e.g. free public web app; number
of expected users; whether any revenue is involved.] I am happy to accept
reasonable conditions — attribution wording, a licence fee, limits on
redistribution of the raw text, or scoping the use to internal reference and
validation rather than public redistribution of entries.

Could you let me know whether such permission is available, what terms or fees
would apply, and whether any part of this falls under a standard licence you
already offer? I am also glad to be directed to Professor Newman or any other
rights holder if that is appropriate.

Thank you for your time and for stewarding a work that means so much to Hausa
scholarship.

With respect,

[FULL NAME]
[TITLE / PROJECT — e.g. Founder, Murya / Adab Tech Labs]
[EMAIL] · [PHONE] · [WEBSITE — murya.ng]
[MAILING ADDRESS]

---

## After you hear back

- **If granted:** save the written grant (email/PDF) into
  `data/sources/newman-dictionary/`, update its `ATTRIBUTION.md` status from
  "NOT LICENSED" to the licensed terms, and only then run an ingestion pipeline.
- **If declined or too costly:** the open Wiktionary/Kaikki HA→EN lexicon
  (already wired, CC-BY-SA) remains the shipped source; Newman can still be
  consulted privately for limited validation within fair-use bounds.
