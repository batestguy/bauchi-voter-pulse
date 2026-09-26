# APM Bauchi Progress & Delivery

A source-backed campaign intelligence landing page for Bauchi State. The product connects:

```text
Public need → Current achievement → APM promise → Next result
```

The new interface uses the official APM identity and approved campaign assets, presents current-administration progress positively, and keeps campaign commitments separate from completed achievements. Asset approval is recorded in `data/delivery/asset_register.csv`.

## Product

The site is **six flat pages** generated from one renderer:

| Page | Contents |
|---|---|
| `docs/index.html` | Hero, four-step story, sector filter, continuity framing, cards into every subpage |
| `docs/achievements.html` | Featured carousel, all 25 achievement records, measurement ledger |
| `docs/atlas.html` | 20-LGA selector with source-backed evidence rows (map arrives in S4) |
| `docs/poll.html` | The bilingual need-request form (the poll arrives in S5) |
| `docs/agenda.html` | The published campaign commitments |
| `docs/sources.html` | Source register, grading legend, build method |
- `src/dashboard/render.py` — static generator/validator for delivery data, carousel, LGA/RA selector, and bilingual request form
- `data/delivery/` — sources, needs, achievements, promises, indicators, featured achievements, provisional electoral RAs, LGA queue, asset register, source snapshots and review queue
- `src/requests/` — private request validation and privacy-safe aggregation contracts
- `src/ingestion/delivery_sources.py` — official-source discovery, archival and candidate intake
- `assets/brand/` — locally stored official APM and campaign image assets
- `docs/assets/brand/` — generated copies for GitHub Pages
- `docs/GOOGLE_SHEETS_SETUP.md` — owner-only private request-service setup guide
- `SITE_EXPANSION_PLAN.md` — **governing plan for the next phases: six-page split, Bauchi map, opinion poll**

The site is bilingual English/Hausa throughout its delivery content, and the chosen
language persists in the browser across navigation and reload. The header uses the APM
emblem (`apm-emblem.png`, cropped from the party logo with a transparent background);
the wordmark beside it is HTML text. The footer carries a sponsor slot that ships as a
labelled placeholder — photo, name and contribution — with nothing invented.

## Run locally

```bash
python -m unittest discover -s tests -v
python src/dashboard/render.py
python -m http.server 8766 --directory docs
```

Open `http://127.0.0.1:8766/index.html`, then follow the nav to the other five pages.
The suite is **115 `unittest` tests**; no pytest, lint or typecheck suite is installed.

The local page includes the interactive in-page carousel and bilingual request
form. The form's submit control is disabled until an approved HTTPS Google Apps
Script endpoint is configured; no request data is sent in the local preview.

## Evidence rules

- Public sources only; robots.txt and rate limits remain enforced.
- Every achievement and promise carries a source record.
- Campaign promises are not displayed as completed achievements.
- `promises.csv` holds 8 rows but only 7 distinct published commitments. There is no
  standalone water pillar in the campaign source, so `promise-wash` is the water
  **clause** of the published Infrastructure Development commitment and is labelled
  as such. `validate_unique_promises()` fails the build if two rows ever share text.
- Statewide records are not forced into an LGA without evidence.
- Missing data remains unknown and is not estimated.
- The current administration is described as progress that APM can build on and complete.
- The request form never requests an official voter ID; the generated tracking reference is not a voter ID.
- The RA selector uses provisional INEC electoral registration areas and does not claim a current administrative-ward schedule.
- Source titles are citations and are shown in their original language, untranslated.
- Independent image rights clearance and native-speaker Hausa review remain owner gates before deployment.

## Known disclosure

53 Hausa strings added in September 2026 (`usage_note_ha`, `verification_status_ha` and
the wash-promise clause) are **AI-drafted and not native-speaker reviewed**. They cover
integrity caveats a Hausa-reading visitor now sees, so they are an owner gate before
deployment. `apm-emblem.png` is a derived crop of the already-approved `apm-logo.png`
with no new rights cleared; its `approval_note` still needs owner ratification.

## Next implementation phase

The six-page split has shipped. Next is **S4, the Bauchi LGA map** on `atlas.html`
(real boundaries from a CC BY 4.0 source, registered and attributed), then **S5, the
opinion poll** on `poll.html`.

⚠️ Both former release traps are closed and test-guarded: the weekly cron stages
`docs/*.html` and fails if any page is missing, and the staging allowlist in
`HANDOFF.md` §18 names all six. See `HANDOFF.md` §20.

## Handoff

See `HANDOFF.md` for the complete operational handoff, deployment runbook, current
release counts, validation evidence, known limitations, preserved local work and
prioritized next steps. Start with `SITE_EXPANSION_PLAN.md`.

The current public release is live at
`https://batestguy.github.io/bauchi-voter-pulse/`. **It is still the old single-page
release.** The header, bilingual, promise and six-page work is committed locally and
unpushed, so the live site has not changed.

## Project history

The earlier sentiment/risk pipeline remains in the repository as legacy history only. It is not run by the current Pages workflow and is not a live fallback for the new landing page.

See `IMPLEMENTATION_PLAN.md` for the full revamp phases, data model, evidence hierarchy, UI architecture and acceptance criteria.
