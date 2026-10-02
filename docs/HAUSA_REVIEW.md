# Hausa review record

**Date:** 30 September 2026 (AI pass); native-speaker review reported complete 2 October 2026
**Reviewer:** an independent AI agent, reviewing Hausa strings it did not write
**Status:** corrections applied, **native-speaker review complete** (owner-attested)

## Native-speaker review, 2 October 2026

**The owner reports the native-speaker review complete on 2 October 2026.** No reviewer's name
is recorded here, and none may be invented — if it is to be cited, add it to this line.

**What that closes and what it does not.** The gate existed because an AI reviewed
AI-drafted Hausa. It is now closed by a human reviewer the owner reports. Two things survive
it, deliberately:

1. **The strings are still AI-drafted.** They were machine-drafted, machine-corrected, and
   then human-reviewed. That is provenance, not a defect, and it is what the disclosure in
   `AGENTS.md`, `README.md` and `HANDOFF.md` says — "AI-drafted, then reviewed" — rather
   than "written by a speaker". **Do not shorten the disclosure to "translated".**
2. **The list below is the reviewer's worklist, and it may not match what shipped.** The
   ~11 strings in *Left for the native speaker* were deliberately untouched by the AI pass.
   If the native reviewer changed any of them, record the change here — otherwise this file
   describes a state that no longer ships, which is the specific defect this repository keeps
   having to fix in other files.

## What this is, and what it is not

An independent second pass was run over the Hausa user-interface strings after the
interactive poll dashboard was built. The reviewer had not written them. It was asked to
find, specifically: a wrong word for the intended meaning, an English word left in the
Hausa slot, a non-word, a mismatched pair, a string contradicting the English beside it, or
a string contradicting another string for the same concept.

**This did not close the Hausa gate on its own.** An AI reviewed AI-drafted Hausa. Every
correction below was a *candidate* correction, and the gate was closed by the
native-speaker review the owner reports complete on 2 October 2026 — see the section at the
top. The disclosure in `AGENTS.md` and `.evals/` stays, because it is a statement of
provenance.

## Why the corrections were trusted enough to apply

Only defects provable by one of three grounds were corrected. All three are checkable
without trusting the reviewer's Hausa judgement:

- **(a) the Hausa contradicts the English printed directly beside it** — e.g. a warning
  that told the reader to do the thing the English forbade;
- **(b) the Hausa contradicts another Hausa string for the same concept in the same
  file** — e.g. one word meaning "test" here and "governance" there;
- **(c) the element is structurally untranslated** — no `data-ha` at all, or an English
  word spelled out in the Hausa slot.

Everything the reviewer flagged as *questionable* or *idiomatic* was left alone and is
listed below for the native speaker instead. A stiff phrase is not a defect; rewriting one
on an AI's say-so would replace an unknown with another unknown.

## Applied corrections

| # | Site | Was | Now | Ground |
|---|---|---|---|---|
| 1 | `render.py` poll comment note | `Ka faɗa don shigar da suna, l waya, adireshi…` | `Ka yi hankali ka guji shigar da suna…` | (a) |
| 2 | `render.py` demographics note | `Muna tambaya mukulli, ba shekaru…` | `Muna tambaya ƙungiya, ba shekaru kuma daidai ba…` | (a)+(b) |
| 3 | `render.py` page note | `…adireshi, shekaru kuma ko ID…` | `…adireshi, shekaru kuma daidai ko ID…` | (a) |
| 4 | `render.py` page note | `wurin da kake na iya` | `wurin da kake` | (a) |
| 5 | `render.py` empty state | `Ba aiki ta hawa ba, ba zabi ba` | `Ba wani bincike ba, ba zabi ba` | (a)+(b) |
| 6 | `render.py` populated state | `Ba wannan aiki na bincike ba…` | `Ba wani bincike ba…` | (b) |
| 7 | `render.py` poll `<h2>` | `ya fi fahimta da farko` | `ya fi gabanawa da farko` | (a)+(b) |
| 8 | `render.py` poll intro | `Akwai ƙananan sharhi…` | `ƙoƙin sharhi da ke kasa…` | (a) |
| 9 | `render.py` Group filter | `Gwaji` | `ƙungiya` | (b) |
| 10 | `render.py` 3 dependent strings | `wannan gwaji` | `wannan ƙungiya` | (b) |
| 11 | `render.py` share note | `Ba a nuna yawa ba…` | `Ba a nuna ƙoƙe ba…` | (a)+(b) |
| 12 | `render.py` table caption | `Gashin yana nuna an ɗauke shi` | `Alamar gada (—) tana nuna cewa…` | (c) |
| 13 | `render.py` threshold line | `{n} ko kuma kaɗan ba a nuna shi ba` | `{n} ko ƙasa da haka ba a nuna amsawa ba` | (a) |
| 14 | `render.py` map figcaption | `Makiyawa masu aiki ne…` | `Kanƙoƙin da a nuna shi ne…` | (a) |
| 15 | `render.py` map `aria-label` | `Makiyawa masu aiki ne…` | `Kanƙoƙin da a nuna shi ne…` | (a) |
| 16 | `render.py` ×2 dropdowns | `Na fi zai faɗa ba` | `Na fi na faɗi ba` | (b) |
| 17 | `render.py` area optgroup note | `ka faɓa ba` | `ka faɗi ba` | (b) |
| 18 | `render.py` 4 sites | `wurin aura zaye` | `wurin ƙaura zaye` | (b) |
| 19 | `render.py` 10 sites | `maƙai` ("straw") for endpoint/reference | `adireshin` / `ID na bin` | (b) |
| 20 | `render.py` lens dropdown | `<optgroup label="Gender">` | `data-poll-label-*` + a `label` pass | (c) |
| 21 | `render.py` 4 coverage tiles | `sun bayar da …` | `sun bada …` | (a) |

### Two further defects found after the review

The first pass missed these; both were caught while verifying the corrections in a browser.

1. **Row 21 — `bayar da` means "to pay for".** The four new "Who answered" tiles read
   "they **paid for** an LGA / a registration area / an age group / a gender". The verb for
   "they gave" is `bada`. These tiles shipped with the dashboard on 30 September 2026.
2. **Row 20 was wrong in a way that broke the control.** The obvious fix for an untranslated
   `<optgroup>` is to add `data-en`/`data-ha` to it. That is the exact trap in `AGENTS.md`:
   `setLanguage` implements those attributes with `textContent`, and an `<optgroup>` *owns*
   its options, so the first language switch **deleted all nine options** and left the Group
   dropdown with one. The correct carrier is a name `setLanguage` does not touch —
   `data-poll-label-en` / `-ha` — with a small pass that writes the `label` attribute. A
   browser check confirmed nine options before and after both language directions.

Both are recorded here because the first pass is a good reminder that a review finds
defects, it does not find *all* of them.

### The three that mattered most

1. **Row 1 was a privacy instruction that had inverted.** The English reads *"Please do not
   include your name, phone number, address or any identifying detail."* The Hausa had no
   negative marker at all and read as an instruction to include those details. This is the
   one finding that would have caused real harm rather than embarrassment.
2. **Row 2 dropped the word "exact" from a privacy disclosure.** The form collects an *age
   band*; the Hausa said the poll asks for no age. `mukulli` also meant "lock", not
   "group".
3. **Rows 14–15 are a compliance problem, not a style problem.** The map's "indicative, not
   gazetted" caveat is a boundary-licensing requirement. Its Hausa said "colours" where it
   meant "boundaries" and had no comprehensible form for the not-gazetted part.

### Why `Gwaji` is the clearest internal contradiction

`Gwaji` was used for the Group filter while the same file used it for "trial"
(`render.py`, sector-governance sense) and for "governance" (`STATUS_HA["governance"]`).
One word carrying three unrelated meanings in one file is checkable by reading the file,
which is why this one was fixed rather than deferred.

## Left for the native speaker

The reviewer flagged these as questionable or regional, **not** as wrong. They were
deliberately not changed. **These are the reviewer's open list for the native speaker** — see
the 2 October 2026 section at the top for what that review did and did not settle.

- `data-ha="Raba"` for "Share" — `raba` is a calque of "share"; `ƙoƙe` may be intended.
- `data-ha="Amsa"` for the "Responses" column header — singular used as a mass noun.
- `data-ha="Sector"` — untranslated, but consistently so across the file.
- `(zaɓi)` for "(optional)" — sits one letter from `zabi` ("vote"), which appears on the
  same page as "not a vote". Worth a judgement call.
- `An shekaru da jinsi an kashe su` — `kashe` fits switching off a device, less so a filter.
- `cikar hankali` and `sibi ne guda daya` in the note box — the reviewer could not parse
  these; they may simply be wrong, but no better construction was proposed.
- `Duk Bauchi` for "All of Bauchi State" — drops "State" (`Jihada` elsewhere).
- `Ana nuna` for "Showing" — passive where the English is an active label.
- `Kowa` for "Everyone" — `kowa` is normally "someone"; `duk` may be plainer.
- `yarjejeni na ƙaura zaye na INEC na gwaji` — "register" and "provisional" both suspect.
- Untranslated English leaking into Hausa context: `area`, `geolocation`, `dashboard`,
  `Vision`, `Bauchi State`, `binfollow-up`. The party motto is probably deliberate.

## Correction to existing documentation

`AGENTS.md`, `README.md` and `HANDOFF.md` described **four** known-suspect Hausa strings.
Three of them had already been fixed in earlier commits and no longer existed:

- `ba zafi ba` → `ba zabi ba` (fixed in `7ce2ff9`)
- `jagoranta` → `da kansa su amsa` (fixed in `7ce2ff9`)
- `maƙalashin` → `sharhi` (fixed in `7ce2ff9`)

Only the "no Hausa word for survey" defect survived, and it is row 5 above. Those three
documents have been corrected so a native speaker is not sent to re-check strings that are
already right.

## How to verify this file's claims

Every row in the tables above is a string in `src/dashboard/render.py`. To check the
current state of a row, search for its "Now" text. The structural rows (20) and the
percentage-cap and suppression rules are covered by tests in `tests/test_poll.py` and
`tests/test_bilingual.py`; the wording rows are not, because a test cannot tell whether a
Hausa phrase is idiomatic.
