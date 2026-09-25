# APM Bauchi Progress & Delivery

A source-backed campaign intelligence landing page for Bauchi State. The product connects:

```text
Public need → Current achievement → APM promise → Next result
```

The new interface uses the official APM identity and approved campaign assets, presents current-administration progress positively, and keeps campaign commitments separate from completed achievements. Asset approval is recorded in `data/delivery/asset_register.csv`.

## Product

- `docs/index.html` — generated interactive landing page, five-slide featured carousel, RA-dependent request form, and aggregate-ready static shell
- `src/dashboard/render.py` — static generator/validator for delivery data, carousel, LGA/RA selector, and bilingual request form
- `data/delivery/` — sources, needs, achievements, promises, indicators, featured achievements, provisional electoral RAs, LGA queue, asset register, source snapshots and review queue
- `src/requests/` — private request validation and privacy-safe aggregation contracts
- `src/ingestion/delivery_sources.py` — official-source discovery, archival and candidate intake
- `assets/brand/` — locally stored official APM and campaign image assets
- `docs/assets/brand/` — generated copies for GitHub Pages
- `docs/GOOGLE_SHEETS_SETUP.md` — owner-only private request-service setup guide

## Run locally

```bash
python -m unittest discover -s tests -v
python src/dashboard/render.py
python -m http.server 8766 --directory docs
```

Open `http://127.0.0.1:8766/index.html`.

The local page includes the interactive in-page carousel and bilingual request
form. The form's submit control is disabled until an approved HTTPS Google Apps
Script endpoint is configured; no request data is sent in the local preview.

## Evidence rules

- Public sources only; robots.txt and rate limits remain enforced.
- Every achievement and promise carries a source record.
- Campaign promises are not displayed as completed achievements.
- Statewide records are not forced into an LGA without evidence.
- Missing data remains unknown and is not estimated.
- The current administration is described as progress that APM can build on and complete.
- The request form never requests an official voter ID; the generated tracking reference is not a voter ID.
- The RA selector uses provisional INEC electoral registration areas and does not claim a current administrative-ward schedule.
- Independent image rights clearance and native-speaker Hausa review remain owner gates before deployment.

## Next implementation phase

The next planned change is a focused full-screen achievement viewer opened from
the existing carousel. It will support next/previous controls, dots, keyboard
navigation, touch/swipe, focus return, scroll lock, and mobile safeguards while
keeping the current in-page carousel as the no-JavaScript fallback. See
`HANDOFF.md` section 16 and `IMPLEMENTATION_PLAN.md` P4.

## Handoff

See `HANDOFF.md` for the complete operational handoff, deployment runbook, current
release counts, validation evidence, known limitations, preserved local work and
prioritized next steps.

The current public release is live at
`https://batestguy.github.io/bauchi-voter-pulse/`.

## Project history

The earlier sentiment/risk pipeline remains in the repository as legacy history only. It is not run by the current Pages workflow and is not a live fallback for the new landing page.

See `IMPLEMENTATION_PLAN.md` for the full revamp phases, data model, evidence hierarchy, UI architecture and acceptance criteria.
