# APM Bauchi Progress & Delivery

A source-backed campaign intelligence landing page for Bauchi State. The product connects:

```text
Public need → Current achievement → APM promise → Next result
```

The new interface uses the official APM identity and approved campaign assets, presents current-administration progress positively, and keeps campaign commitments separate from completed achievements. Asset approval is recorded in `data/delivery/asset_register.csv`.

## Product

- `docs/index.html` — generated interactive landing page
- `src/dashboard/render.py` — static dashboard generator
- `data/delivery/` — sources, needs, achievements, promises, outcome indicators, LGA queue, asset register, source snapshots and review queue
- `src/ingestion/delivery_sources.py` — official-source discovery, archival and candidate intake
- `assets/brand/` — locally stored official APM and campaign image assets
- `docs/assets/brand/` — generated copies for GitHub Pages

## Run locally

```bash
python -m unittest discover -s tests -v
python src/dashboard/render.py
python -m http.server 8766 --directory docs
```

Open `http://127.0.0.1:8766/index.html`.

## Evidence rules

- Public sources only; robots.txt and rate limits remain enforced.
- Every achievement and promise carries a source record.
- Campaign promises are not displayed as completed achievements.
- Statewide records are not forced into an LGA without evidence.
- Missing data remains unknown and is not estimated.
- The current administration is described as progress that APM can build on and complete.

## Handoff

See `HANDOFF.md` for the complete operational handoff, deployment runbook, current
release counts, validation evidence, known limitations, preserved local work and
prioritized next steps.

The current public release is live at
`https://batestguy.github.io/bauchi-voter-pulse/`.

## Project history

The earlier sentiment/risk pipeline remains in the repository as legacy history only. It is not run by the current Pages workflow and is not a live fallback for the new landing page.

See `IMPLEMENTATION_PLAN.md` for the full revamp phases, data model, evidence hierarchy, UI architecture and acceptance criteria.
