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
and attribution in `data/derived/lga_paths.json`. The footer contributor credit adds **4
more** ("Mai ba da daɗi", the role line, "Darasi:", and the portrait `alt`).

S5 adds more in the poll, including the area and demographic fields and the dashboard
copy. The nine sector labels are reused from the request form and are not new.

**Four poll strings are known-suspect and need a native speaker before the poll is
connected:** `ba zafi ba` should be `ba zabi ba` (*zafi* is "pain", not "vote"); the
"not a survey" sentence has no word for *survey* in Hausa at all; `jagoranta` in
"self-selected visitors" is not a recognised Hausa word; and `maƙalashin` (file attachment)
was used where `sharhi` (comment) was meant, contradicting the label above it. These were
found by reading the strings, not by a structural test, and the disclosure is a mitigation
rather than a fix.

The owner has reviewed and accepted the S1–S4 set (69 strings) as written on
29 September 2026. **The 24 poll strings are new and not yet reviewed.** The disclosure
stays in place so a Hausa-reading visitor can see which strings it applies to.

`abdulkadir-ahmad-hammayo.png` is a derived square crop of a campaign-supplied portrait of
the named contributor, registered in `asset_register.csv` with owner approval on
29 September 2026. It is the subject's own photograph and no third-party rights were
cleared.

## Next implementation phase

The six-page split (S0–S3) and the Bauchi map (S4) have shipped. **S5, the opinion poll,
is built and ships disabled** — connecting it is an owner decision, documented in
`docs/POLL_SETUP.md`. Next is S6 (CI and release gate) and S7 (documentation).

ℹ️ Four release traps are closed and test-guarded. The weekly cron stages `docs/*.html`
and fails if any page is missing; the staging allowlist in `HANDOFF.md` §18 names all six;
the asset-authorization gate parses `asset_register.csv` with `csv.DictReader` instead of
`awk -F,`, which had split inside quoted fields; and the snapshot manifest is verified
against the bytes git actually committed, not the working copy, because `.gitattributes`
was added after the snapshots were first committed and had left git and the manifest
disagreeing about the same files. The last two each made the weekly cron fail on its first
scheduled run, and neither was visible in a local test run. See `HANDOFF.md` §20.

ℹ️ `services3.arcgis.com` serves **403 for `robots.txt` under every
user agent**, so the boundary fetch carries a narrowly-scoped, explicitly justified
robots exemption recorded in `src/ingestion/common.py::ROBOTS_UNREACHABLE_HOSTS`. The
registrable domain `arcgis.com` serves a retrievable permissive robots.txt, and the layer
is openly CC BY 4.0, but the default conservative skip is unchanged for every other host.
**The owner ratified this exemption on 29 September 2026.**

## The opinion poll (phase S5)

`poll.html` carries a one-question poll — which sector should APM prioritise first — plus
its results panel. **It ships disabled.** `POLL_ENDPOINT` is `""`, the vote button renders
`disabled`, and a test asserts no code path in `POLL_SCRIPT` can send before the endpoint
guard. `docs/POLL_SETUP.md` is the owner guide for connecting it via Google Sheets and
Apps Script.

The page carries a **public dashboard**: two charts (sector priorities, responses by LGA),
an LGA dropdown that filters both, and an exact-count table.

Four properties are enforced rather than merely intended:

- **No direct identity.** No name, phone, email, address, NIN, BVN, voter ID or exact age.
  Exact-age aliases are refused by name, because the form collects age *bands* and those
  are the keys someone would reach for to defeat that.
- **Area and demographics ARE collected** — required LGA, optional registration area,
  optional age group, optional gender from a closed list. This is a deliberate owner
  decision to allow an area breakdown, and it is why the next rule is load-bearing.
- **Small-cell suppression is mandatory, with a hard floor of 2.** A published cell of 1
  or 2 from a dataset that records an LGA and a registration area is a published cell of
  identifiable people. A cell of **0 is published**, because "nobody chose this" identifies
  nobody. Suppressed cells render as a dash or a hatched bar, never as a zero — a
  zero-width bar reads as "nobody wants water", which is the opposite of the truth.
- **Q2 never moves a number.** The comment is validated, capped at 300 characters, stored
  for off-site study — and never counted, bucketed or published.

**Expect the ward breakdown to be mostly empty.** At 320 responses in a test fixture, all
20 LGAs were publishable but *no* LGA had a usable registration-area breakdown. That is the
data being honest, and the page says "too few to show" rather than inventing a figure.

The percentage cap is `min(share, 100 - floor)`, so one response can never render as 100%.

## Handoff

See `HANDOFF.md` for the complete operational handoff, deployment runbook, current
release counts, validation evidence, known limitations, preserved local work and
prioritized next steps. Start with `SITE_EXPANSION_PLAN.md`.

The current release is live at `https://batestguy.github.io/bauchi-voter-pulse/`. All six
pages are public and verified in a browser against the live URL, including the Bauchi map
(S4) and the contributor credit. The weekly `rebuild-pages.yml` cron now completes
successfully; it had never once succeeded before 29 September 2026.

**Google retains IP addresses in Apps Script execution logs** regardless of what the Sheet
stores. That is a platform property, not something the code can engineer away, and the
owner should decide about it consciously rather than discover it later.

## Project history

The earlier sentiment/risk pipeline remains in the repository as legacy history only. It is not run by the current Pages workflow and is not a live fallback for the new landing page.

See `IMPLEMENTATION_PLAN.md` for the full revamp phases, data model, evidence hierarchy, UI architecture and acceptance criteria.
