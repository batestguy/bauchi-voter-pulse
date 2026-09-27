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
| `docs/atlas.html` | The 20-LGA map — the page's only area selector — the selected-area evidence panel and the not-geo-located registration-area list |
| `docs/poll.html` | The bilingual need-request form (the poll arrives in S5) |
| `docs/agenda.html` | The published campaign commitments |
| `docs/sources.html` | Source register, grading legend, build method |
- `src/dashboard/render.py` — static generator/validator for delivery data, carousel, LGA map, bilingual request form
- `data/delivery/` — sources, needs, achievements, promises, indicators, featured achievements, provisional electoral RAs, LGA queue, asset register, source snapshots and review queue
- `src/requests/` — private request validation and privacy-safe aggregation contracts
- `src/ingestion/delivery_sources.py` — official-source discovery, archival and candidate intake
- `src/ingestion/lga_boundaries.py` — one-time fetch and cache of the GRID3 LGA boundaries (CC BY 4.0)
- `src/derived/lga_paths.py` — pure-stdlib simplification and projection into `data/derived/lga_paths.json`
- `data/derived/lga_paths.json` — committed SVG path data, so the weekly Pages rebuild never calls ArcGIS
- `assets/brand/` — locally stored official APM and campaign image assets
- `docs/assets/brand/` — generated copies for GitHub Pages
- `docs/GOOGLE_SHEETS_SETUP.md` — owner-only private request-service setup guide
- `SITE_EXPANSION_PLAN.md` — **governing plan for the remaining phases: opinion poll, CI gate, docs**

The site is bilingual English/Hausa throughout its delivery content, and the chosen
language persists in the browser across navigation and reload. The header uses the APM
emblem (`apm-emblem.png`, cropped from the party logo with a transparent background);
the wordmark beside it is HTML text. The footer carries a sponsor slot that ships as a
labelled placeholder — photo, name and contribution — with nothing invented.

### The atlas map

`atlas.html` draws the 20 Bauchi LGAs as inline SVG from
`data/derived/lga_paths.json`. There is no runtime third-party request, no tile server and
no JavaScript library: the geometry is 20 `<path>` elements plus 20 `<text>` labels, all
inline, so the map works offline.

**The map is the only area selector.** Selecting a shape (click, or Enter/Space when
focused) loads that area's evidence into the panel, which shows three labelled sections —
recorded evidence, APM commitment, and the next result to measure — plus the area's
registration areas. An earlier build also shipped a 20-item tile list beneath the map; it
repeated a name the map already labels plus a badge visible only as a fill colour, so it
was cut. The SVG is `role="group"` with a localized label and each shape is a labelled
focusable button, so assistive technology sees 20 items rather than one opaque picture.

Boundaries are **GRID3 / eHealth Africa operational LGA boundaries, CC BY 4.0**, fetched
once and cached at `data/delivery/source_snapshots/grid3-lga-boundaries-bauchi.geojson`.
They are *operational* boundaries descended from polio-vaccination microplanning data,
which GRID3 states are not validated by government authorities and carry no gazetted
status. The page says so, and the CC BY credit plus the "simplified for display" change
indication ship under the map. **Never use the sibling GRID3 Wards layers** — they are
CC BY-SA and would force ShareAlike onto the whole site.

Registration areas from `lga_wards.csv` are listed in the side panel and labelled
**"not geo-located"**: the file carries no coordinates and none are invented, so they are
never drawn on the map.

Every page carries a faint `apm-emblem.png` watermark. It is decorative (`aria-hidden`,
`pointer-events: none`, hidden in print), sits below the topbar so it never obscures
navigation, and introduces no new asset or new rights — though it does make that emblem
much more prominent, and its rights record is still unratified.

To regenerate the geometry after the cached snapshot changes:

```bash
python -m src.ingestion.lga_boundaries   # only if the snapshot must be re-fetched
python -m src.derived.lga_paths          # rewrites data/derived/lga_paths.json
python src/dashboard/render.py
```

Both files are **required by the build** — `validate_data()` fails closed without the
cached snapshot, and `load_lga_paths()` fails closed without the derived JSON — so both
must be committed alongside any map change.

## Run locally

```bash
python -m unittest discover -s tests -v
python src/dashboard/render.py
python -m http.server 8766 --directory docs
```

Open `http://127.0.0.1:8766/index.html`, then follow the nav to the other five pages.
The suite is **162 `unittest` tests**; no pytest, lint or typecheck suite is installed.

`tests/test_browser_layout.py` needs a browser and is **skipped** unless Playwright is
present, because Playwright is deliberately not a runtime dependency:

```bash
pip install playwright && python -m playwright install chromium
python -m unittest tests.test_browser_layout -v
```

It is the only thing that measures real horizontal overflow at 375px and confirms the
no-JS `<details>` menu opens. `tests/test_site_structure.py` carries static guards for the
same regressions so they cannot return unnoticed in CI.

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
- Map boundaries are GRID3 operational boundaries shown as **indicative and not gazetted**, with the CC BY credit and change indication on the page. Registration areas are listed as **not geo-located** and are never drawn.
- Source titles are citations and are shown in their original language, untranslated.
- Independent image rights clearance and native-speaker Hausa review remain owner gates before deployment.

## Known disclosure

53 Hausa strings added in September 2026 (`usage_note_ha`, `verification_status_ha` and
the wash-promise clause) are **AI-drafted and not native-speaker reviewed**. They cover
integrity caveats a Hausa-reading visitor now sees, so they are an owner gate before
deployment. `apm-emblem.png` is a derived crop of the already-approved `apm-logo.png`
with no new rights cleared; its `approval_note` still needs owner ratification.

S4 adds **6 more AI-drafted Hausa strings** on the atlas — the map `aria-label`, the
cavity/credit labels, the registration-area "not geo-located" label, and the Hausa caveat
and attribution in `data/derived/lga_paths.json`. The total unreviewed Hausa count is
therefore **59**. The "not gazetted" disclaimer is the one that matters most to get right
for a Hausa-reading visitor, so it is included rather than left English-only.

## Next implementation phase

The six-page split (S0–S3) and the Bauchi map (S4) have shipped. Next is **S5, the
opinion poll** on `poll.html`, then S6 (CI and release gate) and S7 (documentation).

⚠️ Both former release traps are closed and test-guarded: the weekly cron stages
`docs/*.html` and fails if any page is missing, and the staging allowlist in
`HANDOFF.md` §18 names all six. See `HANDOFF.md` §20.

⚠️ One new owner gate: `services3.arcgis.com` serves **403 for `robots.txt` under every
user agent**, so the boundary fetch carries a narrowly-scoped, explicitly justified
robots exemption recorded in `src/ingestion/common.py::ROBOTS_UNREACHABLE_HOSTS`. The
registrable domain `arcgis.com` serves a retrievable permissive robots.txt, and the layer
is openly CC BY 4.0, but the default conservative skip is unchanged for every other host.
Owner ratification of that exemption is still open.

## Handoff

See `HANDOFF.md` for the complete operational handoff, deployment runbook, current
release counts, validation evidence, known limitations, preserved local work and
prioritized next steps. Start with `SITE_EXPANSION_PLAN.md`.

The current release is live at
`https://batestguy.github.io/bauchi-voter-pulse/`, deployed 26 September 2026 in Pages
run `36274124728`. All six pages are public and verified in a browser against the live
URL.

## Project history

The earlier sentiment/risk pipeline remains in the repository as legacy history only. It is not run by the current Pages workflow and is not a live fallback for the new landing page.

See `IMPLEMENTATION_PLAN.md` for the full revamp phases, data model, evidence hierarchy, UI architecture and acceptance criteria.
