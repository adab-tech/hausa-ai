# Permission requests — Newman Hausa dictionaries

**Purpose:** ready-to-send requests for written permission to use Paul Newman's
Hausa lexicography as a data source in the Murya Hausa-language AI. Confirmed
(2026-07-13) that **no open-licensed edition exists** — the Internet Archive
copies are controlled-digital-lending / in-copyright, and only Newman's
*Bibliography* (not a dictionary) is CC-licensed. So permission is the path.
Until a grant is on record, neither edition is ingested (see
`data/sources/newman-dictionary/ATTRIBUTION.md`).

**Two editions, two (overlapping) rights holders — send whichever you need:**

| Edition | Copyright | Send to |
| :-- | :-- | :-- |
| *A Hausa–English Dictionary*, 2007 | © Yale University | **Yale University Press** — https://yalebooks.yale.edu/permissions/ · permissions@yale.edu |
| *Modern Hausa–English Dictionary* (Sabon Ƙamus), 1977/1979 | © OUP 1977; © University Press Ltd 1979 | **University Press PLC, Ibadan** (Three Crowns Bldg, Jericho, PMB 5095, Ibadan) · + Oxford University Press |

**Also worth a direct, warm note to Prof. Paul Newman** (Indiana University,
emeritus; a noted open-access advocate — he CC-licensed his own bibliography).
Rights on the 1977 edition may have reverted to the authors, and his goodwill /
a supporting word to a publisher could unlock either edition. Draft #2 below.

---

## Letter 1 — Yale University Press (2007 edition)

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

## Letter 2 — University Press PLC, Ibadan (1977 *Modern Hausa–English Dictionary*)

Subject: Permission request — data use of the *Modern Hausa–English Dictionary* (Newman & Newman, 1977) in a Hausa-language AI

Dear Rights & Permissions Team,

I am writing to request permission to use the **Modern Hausa–English Dictionary
(Sabon Ƙamus na Hausa zuwa Turanci)** compiled by Paul Newman and Roxana Ma
Newman with the Centre for the Study of Nigerian Languages, Bayero University —
first published by Oxford University Press in 1977 and published by University
Press PLC, Ibadan (ISBN 0‑19‑575303‑8) — as a lexical reference source in a
Hausa language-technology project.

**About the project.** I am building *Murya*, a sovereign Hausa AI assistant
(voice and text), created by and for Hausa speakers to strengthen the digital
presence of the language. It is developed by [NAME / Adab Tech Labs] in
[CITY, COUNTRY]. This dictionary — compiled in Nigeria, for Nigerians, at Bayero
University — is exactly the standard, modern Hausa I want the system to reflect,
and using it would honour that Nigerian scholarly lineage.

**What I am requesting.** Permission to digitize the Hausa→English entries from a
lawfully-obtained copy and incorporate them into the application's
dictionary/translation feature [and, if granted, the model's training data], with
full and prominent attribution to Paul Newman, Roxana Ma Newman, the Centre for
the Study of Nigerian Languages (Bayero University), and University Press PLC.

**Scope & safeguards.** [Distribution: free public web app; expected users;
whether any revenue is involved.] I welcome reasonable conditions — attribution
wording, a licence fee, limits on redistribution of the raw text, or scoping use
to internal reference/validation rather than public redistribution of entries.

Could you tell me whether such permission is available, what terms or fees apply,
and — as OUP holds the 1977 copyright and University Press PLC the 1979 — whether
I should also approach Oxford University Press? I am grateful for your help.

With respect,

[FULL NAME] · [TITLE / PROJECT] · [EMAIL] · [PHONE] · [WEBSITE — murya.ng]

---

## Letter 3 — direct note to Prof. Paul Newman (optional, recommended)

Subject: A Hausa AI built on your scholarship — a note of thanks and a small request

Dear Professor Newman,

I am a native Hausa speaker building *Murya*, a Hausa AI assistant, and I want
first to thank you: it is genuinely not possible to do serious Hausa language
work without your scholarship, and your dictionaries have shaped how I think
about the language.

I would like, with proper permission, to use your Hausa–English lexicography as a
reference source in the project's dictionary feature. I am approaching
[Yale University Press / University Press PLC] for the formal rights, but I wanted
to write to you directly — both out of respect, and because your guidance (or a
supporting word) would mean a great deal. If any part of the work is one you are
free to share, or if rights have reverted to you, I would be honoured to discuss
it. Either way, you will be credited prominently.

With deep respect and gratitude,

[FULL NAME] · [PROJECT — Murya] · [EMAIL] · [WEBSITE — murya.ng]

---

## After you hear back

- **If granted:** save the written grant (email/PDF) into
  `data/sources/newman-dictionary/`, update its `ATTRIBUTION.md` status from
  "NOT LICENSED" to the licensed terms, and only then run an ingestion pipeline.
- **If declined or too costly:** the open Wiktionary/Kaikki HA→EN lexicon
  (already wired, CC-BY-SA) remains the shipped source; Newman can still be
  consulted privately for limited validation within fair-use bounds.
