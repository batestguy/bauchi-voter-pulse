# APM Bauchi Progress & Delivery — Project Handoff

**Handoff date:** 2 October 2026, end of session (supersedes the 1 October session; the
closed items below carry their own dates)
**Repository:** `batestguy/bauchi-voter-pulse`
**Branch:** `main` — **in sync with `origin/main`**, nothing unpushed
**Live product:** [APM Bauchi Progress & Delivery](https://batestguy.github.io/bauchi-voter-pulse/)
**Current release:** seven pages, **both public forms live**, 402 tests passing
**Governing plan for the next work:** [`SITE_EXPANSION_PLAN.md`](SITE_EXPANSION_PLAN.md)

> ### ✅ Both intake endpoints are deployed and taking real submissions
>
> This is the single biggest change since the last handoff. Both forms on `poll.html` are
> live and were verified by submitting from a real browser, not only by server-side probe.
>
> | | Poll | Request |
> |---|---|---|
> | Sheet | `APM poll responses` `1uvtVDgg…` | `APM requests` `1Uw93Cd…` |
> | Bound script | `APM poll endpoint` `1dJTeFKE…` | `APM requests endpoint` `1hoBdGyY…` |
> | Tabs created | Responses, Comments, Audit, Retention | Requests, Audit |
> | `setupSheets` run | yes | yes |
> | Retention trigger | installed (`installRetention`) | n/a — no auto-purge, **decided** (§25) |
> | Live receipt | `APM-POLL-2026-000009` | `APM-2026-000003` |
>
> Both scripts were pushed with `clasp push --force`. `.clasp.json` is gitignored for both
> folders. Verification rows from the deployment session were deleted from all four data
> tabs and all four `Audit` tabs; the headers are intact.
>
> ### ⏭ Start here next session
>
> **Shipped on 2 October: a 30-second captioned demo of the live site**, in a 16:9 and a 9:16
> cut, offered for download from `about.html`. Both are registered assets with hashes, so
> the weekly cron publishes them like any other image. Its caption claims the poll has no
> responses yet, so **re-shoot it when the first response arrives** — §30.
>
> **All three owner actions from the 1 October handoff are now closed. One remains, and it
> is blocked on data rather than on a decision:**
>
> 1. **Publishing the poll results — still open, and now measured.** The `Responses` tab was
>    read on 2 October 2026: **headers intact, zero data rows.** The receipts above were
>    verification rows, deleted on 1 October; `Comments` and `Audit` are empty too.
>    `build_snapshot.py` was run against that real export and **exited 1 and wrote
>    nothing**, which is the correct outcome — a committed snapshot of zeroes would replace
>    the page's honest empty state with a chart of nothing.
>    There is nothing to publish until real responses arrive. See §24.
> 2. ~~**Decide retention for the request Sheet.**~~ **Decided 2 October 2026: no automatic
>    purge, no deletion period**, on the reasoning that retained requests are staff workflow
>    data and expiring them would delete needs nobody has actioned. Two costs are permanent
>    and stated rather than described away: Sheet version history keeps anything blanked, and
>    the tab holds a supporter's name and street address indefinitely. See §25.
> 3. ~~**Get a native Hausa speaker over `docs/HAUSA_REVIEW.md`.~~ **Done.** The owner
>    reports the native-speaker review complete on 2 October 2026. The AI-drafted provenance
>    disclosure stays, because the strings are still machine-drafted and machine-corrected.
>    See `docs/HAUSA_REVIEW.md`.
>
> **Also closed on 2 October:** nothing. The work of that session was verification, not
> feature work — see §29.
>
> **Closed on 1 October, for context:** the About page (§23), the CORS defect that stopped
> both forms working at all (§21), the LGA/area constraint that was never enforced in the UI
> (§22), the snapshot builder (§24), and the zero-state dashboard (§26).
>
> ### The one thing to understand before touching the poll
>
> The published dashboard is a **committed static file**, not a live feed, and
> **nothing reads the Sheet automatically**. `POLL_SETUP.md` claimed a "scheduled,
> owner-controlled job" for months with no job behind it. Votes arrived correctly the whole
> time and the page said "no responses" forever, with no error anywhere. That is fixed and
> tested, but it is manual by choice — see §24.

## 1. Handoff Summary

The current primary product is a source-backed, bilingual campaign landing page for
Bauchi State. It presents the narrative:

```text
Public need → Current achievement → APM promise → Next result
```

The page is optimistic about the current Bauchi State administration and presents
APM as the party that will build on, complete and expand verified progress. Campaign
promises are displayed separately from achievements. Public information is labelled
as social/news analysis, not private polling.

The earlier sentiment/risk dashboard remains in the repository as legacy history. It
is not the current product and is not invoked by the current GitHub Pages build.

## Current Checkpoint

**Four phases of the site expansion are complete. S0–S3 are live; S4 is local only.**

| Commit | Phase | What it did |
|---|---|---|
| `9cd101b` | S0 | Added `SITE_EXPANSION_PLAN.md` |
| `be832e0` | S1 | Bilingual correctness across all delivery content |
| `533a210` | S2 | Legible APM emblem, sponsor slot, persistent language control, de-duplicated promises |
| `957d47d` | S3 | **Six-page split**, mobile nav, solid subpage header, both CI release traps closed |
| *uncommitted* | **S4** | **The 20-LGA Bauchi map** on `atlas.html`, from CC BY 4.0 operational boundaries |

The next maintainer should resume from this exact checkpoint:

- **Current local product checkpoint:** seven flat pages in `docs/`, and `atlas.html` now
  carries a real map — 20 inline `<path>` outlines with labels, an evidence panel, and the
  registration-area list labelled "not geo-located". S0–S4 are done. **S5 (the opinion
  poll) has not started**, so `poll.html` still holds only the request form.
- **Last verified live product:** `4871cde` (now `1eac1bc` on `main`), deployed 26 September
  2026 in Pages run `36274124728` (success). The live `atlas.html` still shows the tile
  grid.
- ⚠️ **First unattended cron run not yet observed.** `rebuild-pages.yml` gained a
  multi-page stage and a missing-page check in S3. The next Monday 06:00 UTC run is the
  first live exercise of it.
- **Current local verification:** **162 `unittest` tests pass** (115 before S4). Delivery
  data validation, asset hash checks, the CI asset gate, per-page `node --check`, and a
  `node --check` on the new atlas script all pass. Browser checks covered 375px/1440px,
  EN↔Hausa switching, language persistence, the map surviving a language switch, map↔list
  selection sync, **0px horizontal overflow on all six pages**, and **zero console
  errors**.
- **Two files are build-required and must be committed with S4:**
  `data/delivery/source_snapshots/grid3-lga-boundaries-bauchi.geojson` (388 KB;
  `validate_data()` fails closed without it) and `data/derived/lga_paths.json` (95 KB;
  `load_lga_paths()` fails closed without it).
- **Evaluation report:** `.evals/2026-W39.md` is intentionally local-only because
  its 100-row source sample is not approved for release staging.
- **Preserve local work:** do not reset or stage `src/aggregation/aggregate.py`,
  `.evals/2026-W39_sample100_filled.csv`, `.evals/2026-W39.md`,
  `data/human_review/filled/`, or `.playwright-mcp/`. The last path is a local
  browser artifact and is not part of the release.


## 2. Release State

### Live deployment

GitHub Pages reports the site as public and built from `main` with `/docs` as the
source directory. The current indicator-ledger release completed successfully in
Pages run `35972044982` on 24 September 2026.

```text
https://batestguy.github.io/bauchi-voter-pulse/
```

The source workflow commits changes to `main`; GitHub Pages builds the `docs/`
directory. The `rebuild-pages` workflow itself renders and commits `docs/`; it does
not call an explicit Pages deployment action.

### Current data inventory

| Area | Count | Source |
|---|---:|---|
| Registered sources | 28 | `data/delivery/source_register.csv` |
| Archived source pages | 34 | `data/delivery/source_manifest.csv` |
| Review queue records | 33 | `data/delivery/review_queue.csv` |
| Needs | 8 | `data/delivery/needs.csv` |
| Achievements | 25 | `data/delivery/achievements.csv` |
| APM promises | 8 (7 published pillars + 1 published clause) | `data/delivery/promises.csv` |
| LGA delivery rows | 20 | `data/delivery/lga_delivery.csv` |
| Approved assets | 10 | `data/delivery/asset_register.csv` |
| Featured achievement records | 5 | `data/delivery/featured_achievements.csv` |
| Provisional electoral RAs | 212 | `data/delivery/lga_wards.csv` |
| Outcome indicators | 8 | `data/delivery/indicators.csv` |
| Mapped LGA outlines | 20 | `data/derived/lga_paths.json` |
| Pending source reviews | 0 | `review_status == needs_review` |
| Local `unittest` tests | 162 | `tests/` |

**New in S4:** source `source-grid3-lga-boundaries` is registered at **grade B** in
`source_register.csv`, with the cached snapshot registered in `source_manifest.csv` as
`grid3-lga-boundaries-bauchi`. Both rows carry the SHA-256 of the cached GeoJSON, and
`validate_data()` cross-checks them.

All 20 LGAs currently have an explicit LGA-specific evidence row. This means each
LGA has a source-backed record for the atlas; it does not mean that every sector or
project in every LGA has been comprehensively audited.

### Promise count caveat

`promises.csv` has 8 rows but only **7 distinct published campaign commitments**. The
archived campaign page (`delivery-89aec627d08a.html`) publishes five pillars plus health
and governance statements. There is **no standalone water pillar**: `water` appears twice
in that document and `sanitation`, `WASH`, `borehole`, `toilet`, `drainage` and `climate`
appear zero times.

`promise-wash` is therefore the water **clause** of the published Infrastructure
Development commitment, labelled `promise_type = Published commitment clause`. It is not a
separate pillar. `validate_unique_promises()` in `render.py` fails the build if any two
promise rows ever share `promise_text` again.

### Approved assets

| File | Note |
|---|---|
| `apm-logo.png` | Original party logo, 1516×337, **opaque white background**. Retained; no longer used in the header. |
| `apm-emblem.png` | **New in S2.** 274×314 crop of the above with a transparent background, used in the header and as the favicon. |
| `yakubu-adamu-hero.png`, `yakubu-adamu-portrait.png`, `bala-mohammed.png` | Candidate and governor imagery |
| `achievement-*.jpg` / `.webp` (5) | Featured carousel images, source-attributed |

✅ `apm-emblem.png` was registered as `campaign approved` by `campaign team` on
26 September 2026 to unblock the build, recorded as a derived crop of the already-approved
`apm-logo.png` with no new rights cleared. **The owner ratified that attribution on
29 September 2026.** `asset_register.csv` is the rights record and `rebuild-pages.yml`
fails closed on any row whose `usage_status` is not `campaign approved` or whose
`approved_at` is empty.


## 3. Product Architecture

### Runtime shape

The live product is **seven static pages** with inline CSS and JavaScript, generated by one
renderer. It has no server runtime, database, private API or user account system.

```text
Public/approved source pages
          ↓
src/ingestion/delivery_sources.py
          ↓
source snapshots + manifest + review queue
          ↓
curated delivery CSV tables
          ↓
src/dashboard/render.py   (PAGE_BUILDERS → one body per page)
          ↓
docs/*.html  (index, achievements, atlas, poll, agenda, sources) + local approved assets
          ↓
GitHub Pages
```

### Main files

| File or directory | Responsibility |
|---|---|
| `docs/index.html` | Home: hero, stats, four-step story, sector filter, continuity, cards into every subpage |
| `docs/achievements.html` | Featured carousel, all 25 achievement records, measurement ledger |
| `docs/atlas.html` | The 20-LGA map (the only selector), the selected-area evidence panel, the map legend, and the not-geo-located registration-area list |
| `docs/poll.html` | The bilingual need-request form. **The opinion poll arrives in S5.** |
| `docs/agenda.html` | The 8 published campaign commitments |
| `docs/sources.html` | Source register, grading legend, build method |
| `src/dashboard/render.py` | Validates delivery data and generates all seven pages via `PAGE_BUILDERS`. Owns the shared shell (`document`, `topbar`, `subpage_open`, `page_hero`, `site_footer`), the nav registry (`PAGE_NAV`), script routing (`PAGE_SCRIPTS`), the bilingual helpers (`attr`, `copy`, `localized`, `status_badge`), the controlled status vocabulary and the delivery validators. |
| `data/delivery/` | Curated source, evidence, promise, indicator, featured-achievement, provisional electoral-RA and LGA tables |
| `data/delivery/source_snapshots/` | Locally archived source responses |
| `src/ingestion/delivery_sources.py` | Public source discovery, archival and review intake |
| `src/ingestion/lga_boundaries.py` | **New in S4.** One-time fetch and cache of the GRID3 operational LGA boundaries (CC BY 4.0), with the `lgacode` → canonical-name table |
| `src/ingestion/common.py` | Shared polite HTTP, robots.txt and rate-limit logic. **Also owns `ROBOTS_UNREACHABLE_HOSTS`**, the justified per-host robots exemption (see §21) |
| `src/derived/lga_paths.py` | **New in S4.** Pure-stdlib quantization, explicit-stack Douglas-Peucker, seam-safe vertex retention, equirectangular projection with the `cos(latMid)` correction, and SVG path serialisation |
| `data/derived/lga_paths.json` | **New in S4, committed.** Path data, viewBox, bounds, licence, attribution and the recorded seam metrics. The weekly build reads this and never calls ArcGIS |
| `data/delivery/source_snapshots/grid3-lga-boundaries-bauchi.geojson` | **New in S4, committed and build-required.** The raw cached boundaries, 388,559 bytes, SHA-256 `34b59f64…7ff596` |
| `tests/test_atlas_map.py` | **New in S4.** 38 guards: licence, grade B, the `lgacode` join, the 3 dp floor, the explicit stack, seam tear of 0, projection, the CC BY attribution, the not-geo-located label, and the language-switch integrity guard |
| `tests/test_browser_layout.py` | **New in S4.** Real-browser checks (375px overflow, the mobile `<details>` menu, map↔list sync, map survives a language switch, zero console errors). Skipped without Playwright, which is deliberately not a runtime dependency; carries static guards that always run |
| `src/requests/validation.py` | Pure bilingual-safe private request validation contract |
| `src/requests/aggregate.py` | Contact-free public request aggregation contract |
| `docs/GOOGLE_SHEETS_SETUP.md` | Owner-only Google Sheet/Apps Script setup and privacy guide |
| `assets/brand/` | Approved local source assets, including the derived `apm-emblem.png` |
| `docs/assets/brand/` | Generated copies used by the public page |
| `tests/test_bilingual.py` | Guards the S1 bilingual fixes: denylist of untranslated UI strings, Hausa-in-English-column detection, required Hausa columns |
| `tests/test_header_brand.py` | Guards the S2 fixes: emblem registration and transparency, no invert filter, favicon, sponsor slot placeholders, language persistence, promise de-duplication, and a `node --check` parse of the inline script |
| `tests/test_site_structure.py` | Guards the page split: all seven pages generated, nav and asset paths resolve, heavy sections on exactly one page, one `aria-current` per page, mobile menu is JS-free, subpage solid header, script routing, per-page `node --check`, and both release traps stay closed |
| `SITE_EXPANSION_PLAN.md` | **Governing plan for S3–S7**: six-page split, map, poll. Read this first. |
| `README.md` | Short product and local-run guide |
| `IMPLEMENTATION_PLAN.md` | Product contract, evidence hierarchy and phase history |

### Page features

- APM identity: the colour **emblem** in the header (transparent background, no CSS
  filter) with the "Allied Peoples' Movement" wordmark as text beside it. The same emblem
  is the favicon.
- **Labelled** English/Hausa toggle (globe glyph + `Language` / `Harshe`), whose choice
  persists in `localStorage` across navigation and reload.
- **Sponsor slot** in the footer with three labelled fields — photo, name, and a
  prominent contribution line. Ships deliberately unfilled; a test forbids invented
  content.
- Four-step public-need-to-next-result pathway.
- Five-slide approved featured-achievement carousel with source and image attribution.
- LGA/electoral-RA dependent request selector using 20 LGAs and 212 provisional RAs.
- Bilingual one-primary-request form with optional private follow-up details, consent and honeypot.
- Submission remains disabled until an explicitly approved HTTPS Apps Script endpoint is configured.
- Sector filtering for health, education, water/WASH, infrastructure and governance.
- Twenty-LGA selector with source-backed LGA summaries.
- Current-administration continuity framing.
- Separate APM campaign agenda, with the water entry labelled a published *clause* rather
  than a standalone pillar.
- Measurement ledger separating reported outputs from outcomes still being measured.
- Every integrity caveat (achievement `verification_status`, source `usage_note`,
  indicator values and notes) now switches between English and Hausa.

- Source list with publication date, retrieval date, usage note and evidence grade.
- Responsive layout, bilingual validation and reduced-motion support.
- Full-screen achievement viewer is deferred; the in-page carousel remains the fallback.
- `Created By Deerflow` attribution in the footer.

### Shell features added in S3

- **Seven flat pages** generated from one renderer, sharing the header, footer, sponsor slot
  and language control. Flat rather than nested so `assets/brand/...` keeps resolving.
- **Per-page `<title>` and meta description**, so a shared link names the right page.
- **`aria-current="page"`** on the active nav item, in both the desktop nav and the mobile
  panel.
- **A no-JS `<details>` mobile menu.** `.nav` is `display:none` below 1050px, so this is
  the only phone path to any subpage. The bar is `position:relative` because the panel is
  absolutely positioned at `top:100%` of it.
- **A solid subpage header** (`.page-head`) because `.topbar` is white-on-navy
  `position:absolute` over a hero that subpages do not have.
- **Home-page cards** linking into all five subpages, so the split is discoverable.
- **Skip-to-content link** as the first focusable element.
- **Visible focus rings** on nav, menu, cards and the language buttons.
- **A "what happens to this form" section** on `poll.html` restating that no voter ID is
  requested and that nothing is sent from an unconfigured build.
- **A build-method section** on `sources.html`: discover, review, curate, publish.

## 4. Delivery Data Model

All delivery tables are CSV files under `data/delivery/`. The renderer fails closed
when a required table, field, source reference, asset approval or hash is invalid.

### Source register

`source_register.csv` contains the source metadata used by the page:

```text
source_id
publisher
source_type
title
url
publication_date
retrieved_date
document_type
source_grade
usage_note
content_hash
```

Evidence grades:

- `A`: primary government, statutory or institutional record.
- `B`: programme or implementing-partner evidence, or reputable corroborating report.
- `C`: provisional or weakly corroborated source; do not promote without review.
- `D`: campaign material; use for promises and positioning, not completed outcomes.

### Outcome indicators

`indicators.csv` is the measurement ledger shown on the public page. It separates
reported delivery outputs from outcomes that still need follow-up. Fields include
baseline, current value, unit, year, target, status, LGA/sector scope, source and a
measurement note. Blank baselines are intentional when no verified baseline exists.

### Needs

`needs.csv` stores the public problem/opportunity used by each sector pathway.
Baseline fields are not currently quantified. Missing baselines remain unknown and
must not be estimated.

### Achievements

`achievements.csv` stores current-administration or partner records. Important fields
include actor, LGA, sector, project, description, status, date, beneficiaries,
scale, outcome measure, evidence grade, verification status and source ID.

Status labels are deliberately cautious:

- `Progress delivered`
- `Project underway`
- `Outcome being measured`
- `Approval milestone`

A launch, handover, approval or commissioning event is not automatically a completed
outcome. The verification field must state what remains unmeasured.

### Promises

`promises.csv` stores APM campaign commitments separately. Promise records must not be
presented as completed achievements and should define a measurable next result.

### LGA delivery

`lga_delivery.csv` contains one curated row for each of the 20 Bauchi LGAs. Each row
contains:

```text
lga
focus_sector
need_text
need_text_ha
achievement_summary
achievement_summary_ha
apm_promise
apm_promise_ha
next_result
next_result_ha
coverage_type
source_id
status
```

The current atlas uses LGA-specific evidence where available. It is a designed
20-LGA grid, not an authoritative geographic map.

### Assets

`asset_register.csv` records the source URL, SHA-256, usage status, approver and
approval date for each asset. Current local assets are:

- `assets/brand/apm-logo.png`
- `assets/brand/yakubu-adamu-hero.png`
- `assets/brand/yakubu-adamu-portrait.png`
- `assets/brand/bala-mohammed.png`
- `assets/brand/achievement-estrra-outcomes.jpg`
- `assets/brand/achievement-giade-mill.jpg`
- `assets/brand/achievement-toro-odf.jpg`
- `assets/brand/achievement-education-scorecard.webp`
- `assets/brand/achievement-maternal-services.jpg`

Never hotlink or replace these assets without repeating the approval and hash check.

## 5. Source Intake Pipeline

Run the delivery source intake from the repository root:

```powershell
python -m src.ingestion.delivery_sources
```

The pipeline:

1. Reads registered source URLs and fixed seed pages.
2. Allows only configured public domains.
3. Uses `polite_get()` for robots.txt, rate limiting, timeouts and public HTTP.
4. Extracts title, text and publication date.
5. Hashes the raw HTML response.
6. Stores a local response snapshot under `data/delivery/source_snapshots/`.
7. Updates `source_manifest.csv`.
8. Queues candidates in `review_queue.csv`.
9. Updates registered source hashes when a matching source is archived.
10. Marks already-published supporting sources as `published_source`.

The pipeline does not automatically promote a candidate into an achievement. Editorial
review is required before editing `achievements.csv` or `lga_delivery.csv`.

### Intake failure handling

A source may be researched but not archived by the automated worker because of a
403, timeout, robots restriction, redirect or unavailable page. Do not create a
source-register row with a fabricated hash. Either leave the record as a review
candidate or archive the response through a separately verified public fetch.

## 6. Local Development

### Prerequisites

- Python 3.12 recommended for GitHub Actions parity.
- Git.
- A browser for responsive interaction checks.

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

The current dependency file is intentionally small because the public delivery page
uses Python standard-library CSV/HTML generation plus `beautifulsoup4` and `requests`
for intake. The legacy pipeline also uses pandas and scikit-learn.

### Render the current product

```powershell
python src/dashboard/render.py
```

Equivalent module form:

```powershell
python -m src.dashboard.render
```

Serve locally:

```powershell
python -m http.server 8766 --directory docs
```

Open:

```text
http://127.0.0.1:8766/index.html
```

### Run source intake

```powershell
python -m src.ingestion.delivery_sources
```

This changes files under `data/delivery/`. Review the diff before committing.

### Validate a release

The current project has no installed automated pytest/lint/typecheck suite. Use the
following release checks:

```powershell
python -m py_compile src/dashboard/render.py src/ingestion/delivery_sources.py
python src/dashboard/render.py
python -c "import yaml; from pathlib import Path; paths=list(Path('.github/workflows').glob('*.yml')); [yaml.safe_load(p.read_text(encoding='utf-8')) for p in paths]; print(len(paths))"
git diff --check -- . ':(exclude)data/delivery/source_snapshots/**'
```

The renderer validates required columns, source references, source/snapshot hashes,
asset hashes and campaign asset approval. Raw HTML snapshots are intentionally kept
byte-for-byte and may contain trailing whitespace.

Manual browser checks should cover:

- 1440px, 1024px, 760px and 375px widths.
- No horizontal overflow.
- Brand images load locally.
- English/Hausa toggle changes dynamic copy.
- Sector filters show the expected cards.
- All 20 LGA tiles render.
- Misau, Toro and Zaki show their new evidence.
- Browser console has no errors.

## 7. GitHub Workflows

Workflow directory: `.github/workflows/`

### `delivery-sources.yml`

- Schedule: Fridays at `04:00 UTC`.
- Manual dispatch: enabled.
- Runs `python -m src.ingestion.delivery_sources`.
- Commits only `data/delivery/`.
- Rebases before pushing.
- Uses concurrency group `repo-pages-write`.

### `rebuild-pages.yml`

- Schedule: Mondays at `06:00 UTC`.
- Manual dispatch: enabled.
- Checks every `asset_register.csv` row is `campaign approved`.
- Runs `python src/dashboard/render.py`.
- Commits only `docs/index.html` and `docs/assets/`.
- Rebases before pushing.
- Uses concurrency group `repo-pages-write`.

### Legacy workflows

- `scrape.yml`: manual-only raw social/news ingestion; legacy path.
- `budgets.yml`: monthly budget collection; legacy path, and `data/budgets/` is not
  currently present in the repository.

All active write workflows share the `repo-pages-write` concurrency group to prevent
conflicting pushes.

## 8. Deployment Runbook

### Source/data update

```powershell
python -m src.ingestion.delivery_sources
```

Review changes in:

```text
data/delivery/source_register.csv
data/delivery/source_manifest.csv
data/delivery/review_queue.csv
data/delivery/source_snapshots/
```

Curate only verified records in `achievements.csv`, `promises.csv` and
`lga_delivery.csv`. Then run:

```powershell
python src/dashboard/render.py
```

Run the integrity checks, inspect the diff, and commit only intended release files.

### GitHub Actions release

The normal automated path is:

1. `delivery-sources.yml` archives new sources and queues candidates.
2. A human reviews and promotes only supported claims.
3. `rebuild-pages.yml` renders the approved data into `docs/`.
4. GitHub Pages builds `main/docs` and serves the public page.

For an immediate manual refresh, use `workflow_dispatch` on the relevant workflow.
Check the Actions run and verify the live page after completion.

### Current deployment caveat

The `rebuild-pages.yml` workflow renders and commits `docs/`; it does not invoke the
modern `actions/deploy-pages` action. The repository currently relies on the
repository's configured GitHub Pages `main` + `/docs` build behavior. Confirm Pages
settings in GitHub if that configuration changes.

## 9. Current Validation and Release Evidence

### Last deployed release (checked 24 September 2026)

- 27 registered sources.
- 33 archived source pages.
- 25 achievement records.
- 8 APM promise records.
- 20 LGA delivery rows, all currently LGA-specific.
- 0 `needs_review` queue rows.
- All registered and manifest source hashes reconcile.
- All 33 manifest snapshot hashes reconcile.
- Four local brand assets match their registered SHA-256 values.
- Current GitHub Pages deployment completed successfully in run `35972044982`.
- Live page returned the expected 33-page/0-pending source status.
- Live page showed 20 LGA tiles, 8 indicators and Misau/Toro/Zaki evidence.
- Live browser console returned 0 errors.
- ⚠️ **CORRECTED IN S4.** This section previously recorded "Responsive checks showed no
  horizontal overflow at 1440px, 1024px, 760px or 375px." **That was wrong at 375px.** S4
  measured the topbar overflowing the shell by **27px at exactly 375px, on every page**,
  forcing the whole page to scroll sideways. The claim was evidently never measured at that
  width. S4 fixed it and the number is now genuinely 0px on all six pages, measured in a
  browser by `tests/test_browser_layout.py`. Treat any "no overflow" claim in this file
  as unverified unless a test asserts it.

### State after S4 and the contributor credit (29 September 2026, pushed)

- **165 `unittest` tests pass** (115 after S3, 162 after S4, 165 after the contributor credit).
- `python src/dashboard/render.py` writes **all seven pages** and prints their sizes.
- `render.validate_data()` passes, and now also cross-checks the GRID3 boundary snapshot's
  SHA-256 against both `source_register.csv` and `source_manifest.csv`.
- The cached boundary snapshot reproduces **every** measured value in
  `SITE_EXPANSION_PLAN.md` §2.4: 20 features, Polygon only, one ring each, 10,632 vertices,
  largest ring 1,223 (`Itas/Gadau`), all rings closed, bbox 8.7450736484–11.0085317052 /
  9.4473215106–12.5324657447, 388,559 bytes, and the two name mismatches
  `Itas/Gadau` / `Jama'Are`.
- Derived geometry: `viewBox="0 0 1000 1388.09"`, 7,452 vertices, 95,650 bytes.
  **Seam tear 0 m, seam fidelity 0 m, quantization retention 3,353/3,538 = 94.8%**
  (floor 90%).
- `python -m src.derived.lga_paths` is **byte-for-byte deterministic** across runs.
- Both build-required data files are confirmed necessary: removing the snapshot raises
  `FileNotFoundError` from `validate_data()`, and removing the derived JSON raises from
  `load_lga_paths()`.
- The map survives EN→HA→EN with all 20 outlines intact. The first implementation did
  **not**: `attr()` on the `<svg>` made `setLanguage` wipe the whole map. Fixed with a new
  `render.py::aria()` helper; guarded by `tests/test_atlas_map.py::BilingualIntegrityTests`,
  which was **verified to fail** when the bug is reintroduced.
- 🔴 **A missing `}` in a single-line `@media` block broke every page's styling.** A
  scripted CSS edit removed the brace closing `.indicator-grid` inside
  `@media (max-width:1050px)`, so the rest of the stylesheet was parsed *inside* that media
  query and stopped applying at desktop widths — the hero lost its navy background, the
  white topbar text went invisible on cream, and the emblem overlapped the page title. The
  pages still rendered, which is what made it expensive to spot. Restored verbatim from
  `git HEAD`. `test_site_structure.py` now asserts both that brace counts balance and that
  **every `@media` query begins at depth 0**, and that guard was **verified to fail** when
  the bug is reintroduced.
- Browser-verified at 375px and 1440px: the map renders with all 20 labels legible and
  seamless borders; map click and list click drive the same selection in both directions;
  the "not geo-located" RA list follows the selection; the map caveat and CC BY credit both
  translate; **0px horizontal overflow on all six pages**; **0 console errors**.
- ⚠️ `tests/test_browser_layout.py` is the only suite that measures real layout, and it
  **skips** because Playwright is not installed here. It was left out of `requirements.txt`
  deliberately so CI does not download Chromium on every run. The static guards in the same
  file and in `test_site_structure.py` cover the same regressions and always run.

### Local state after S0–S3 (26 September 2026, now deployed)

- **115 `unittest` tests pass** (40 before this work).
- `python src/dashboard/render.py` writes **all seven pages** and prints their sizes.
- `render.validate_data()` passes, including `validate_no_hausain_english_columns()`
  and `validate_unique_promises()`.
- **224** `data-en`/`data-ha` pairs are byte-identical and **every one is legitimate**:
  electoral RA proper nouns, LGA names, the `LGA` acronym, the party motto, and numeric
  values that are genuinely identical in both languages. Zero unexplained.
- 11 approved assets; all SHA-256 values reconcile, including `apm-emblem.png` and the
  contributor portrait.
- The CI asset gate (`usage_status` read by column name from `asset_register.csv`) passes.
- **All six** pages have a unique `<title>` and meta description, resolve every relative
  asset and nav path, and use no `../`.
- Each heavy section appears on exactly one page: source register, request form, agenda,
  indicators, atlas, carousel.
- **All six** inline scripts pass `node --check`; no page has a duplicate top-level
  `const`/`let`/`var` declaration, and `setLanguage` is declared exactly once.
- Browser-verified at 375px and 1440px: all six pages load; the mobile menu opens inside
  the viewport with all six links and the current page marked; the emblem renders in
  colour; the language label switches EN↔Hausa; the chosen language **survives full page
  reload and page-to-page navigation**; `aria-label` translates; the sponsor slot renders
  and translates; the agenda shows 8 distinct cards; the LGA selector updates its detail
  panel; the carousel navigates and scope-filters; the request form is still disabled
  with no endpoint configured; **0 console errors**. (⚠️ The 375px overflow claim in this
  section was wrong — see the S4 correction above.)
- No pytest, lint or typecheck suite is installed in the current project.

## 10. Legacy Sentiment/Risk Pipeline

The following files remain for historical and evaluation work but are not the current
public product:

```text
src/ingestion/run_daily.py
src/ingestion/nairaland.py
src/ingestion/nairaland_search.py
src/ingestion/news.py
src/ingestion/gdelt.py
src/ingestion/legit_hausa.py
src/ingestion/facebook.py
src/classification/classify.py
src/classification/classify_new.py
src/classification/routing.py
src/aggregation/aggregate.py
```

Legacy raw schema:

```text
raw_id, source, date_scraped, text, url, lga_keyword_match
```

Legacy classification schema:

```text
src/schema/jev_pulse_v3.json
```

Legacy classification requires `TYPESAFE_API_KEY` and the Jev/TypeSafe client. The
current delivery workflow does not call it.

Legacy routing rule:

```text
auto iff min(sentiment_confidence, lga_confidence) >= 0.80
otherwise human_review
```

The current risk outputs are provisional and do not provide meaningful ratings for
LGAs with fewer than five usable rows. Do not use legacy risk output as a substitute
for the current source-backed delivery page.

## 11. Local Work That Must Be Preserved

The worktree is intentionally not clean. These changes are local work and were not
part of the public delivery release:

```text
 M src/aggregation/aggregate.py
?? .evals/2026-W39.md
?? .evals/2026-W39_sample100_filled.csv
?? data/human_review/filled/
```

Do not reset, clean, stash permanently or overwrite these paths without confirming
with the repository owner. The filled review work currently includes intermediate
parts for English and Hausa queues. The missing English part and merged root queues
still need completion.

## 12. Known Limitations

### Current delivery product

- `AGENTS.md` and `APMreadme.txt` retain substantial legacy sentiment-system
  assumptions; use this handoff, `README.md` and `IMPLEMENTATION_PLAN.md` for the
  current product contract.
- The corpus is source-backed, not a comprehensive audit of all Bauchi government
  performance.
- Some records are launches, approvals, handovers or reported milestones rather than
  independently measured outcomes.
- `needs.csv` has no quantified baselines.
- The 20-LGA display is an **indicative map on operational boundaries**, not an
  authoritative or gazetted map. It is simplified for display at a 223 m tolerance.
- Map boundaries descend from eHealth Africa polio-vaccination microplanning data and are
  not validated by government authorities.
- Registration areas are listed as "not geo-located"; `lga_wards.csv` carries no
  coordinates and none are invented.
- LGA rows provide one evidence record per LGA, not exhaustive sector coverage.
- The ESTRRA outcome is Bauchi North-wide and is not a single-LGA claim.
- The 20-LGA display is now an **indicative map on operational boundaries**, not an
  authoritative map. Simplified for display; see the S4 correction in §9.
- English/Hausa copy exists, but native-speaker review is not documented. **59** strings are
  AI-drafted and unreviewed, including the map's "not gazetted" disclaimer.
- The ArcGIS boundary fetch uses a documented robots.txt exemption that the owner has not
  yet ratified. See §21.
- `tests/test_browser_layout.py` skips without Playwright, so real layout is not asserted
  on a machine that lacks it.
- There is no automated semantic duplicate checker, date validator or claim verifier.
- Baselines in `indicators.csv` remain blank where no verified baseline is available.

### Legacy pipeline

- The pilot is not a real 500-post manually labeled corpus.
- Human review is not fully merged.
- The modified aggregation code is uncommitted and has not been fully tested.
- `pipeline_stats.csv` is not currently present.
- Facebook ingestion requires tokens and is inactive without them.
- YouTube ingestion is intentionally excluded because the feed is disallowed by
  robots rules.

## 13. Prioritized Next Steps

### Done — S4, the Bauchi map

`atlas.html` now carries a real 20-LGA map. Full record, including the three seam
measurements and the two bugs that mattered, in `SITE_EXPANSION_PLAN.md` §9.

1. ✅ `src/ingestion/lga_boundaries.py` fetches the boundaries once and caches them.
   Registered as `source-grid3-lga-boundaries`, **grade B**, CC BY 4.0, with the licence
   and the "simplified for display" change note.
2. ✅ The licence is CC BY 4.0 with no ShareAlike, as planned. The sibling GRID3 **Wards**
   layers are BY-SA and were never touched; a test asserts the module never references
   one.
3. ✅ Derived path strings are committed to `data/derived/lga_paths.json`, so the weekly
   Pages rebuild never calls ArcGIS. Regeneration is byte-for-byte deterministic.
4. ✅ Pure stdlib: quantize to **3 dp**, Douglas-Peucker with an **explicit stack** (the
   `Itas-Gadau` ring is 1,223 points, past the 1000-frame recursion limit), projected with
   the `cos(latMid)` correction. `viewBox="0 0 1000 1388.09"`.
5. ⚠️ **The plan's "snap neighbours back together" step was abandoned, with measurements.**
   Position-welding cannot repair a *subset* disagreement, and after 3 dp quantization it
   is a guaranteed no-op. The shipped approach retains every shared-border vertex:
   **tear 0 m, fidelity 0 m**, at 7,452 vertices / 95 KB instead of the planned
   3,070 / 36 KB. A test asserts the naive pipeline still tears.
6. ✅ The join is on `lgacode` (5001–5020). The two name mismatches (`Itas/Gadau`,
   `Jama'Are`) are absorbed structurally.
7. ✅ The CC BY attribution and the "operational, simplified, indicative — not gazetted"
   caveat both ship, in English and Hausa.
8. ✅ The RA list is in the side panel labelled **"not geo-located"** and is never drawn on
   the map.
9. ✅ **The 20-LGA tile grid was cut.** It repeated a name the map already labels plus a
   badge visible only as a fill colour, so it was duplication and exactly the "competing
   primary navigation" the plan warned against. Each path now carries the per-LGA text via
   the same `data-lga` contract the core script already speaks, so `renderLgaDetail` needed
   no change, and the SVG became `role="group"` with 20 labelled focusable shapes. A
   data-derived legend replaced the removed coverage badges.
10. ✅ **The evidence panel is three labelled sections** — recorded evidence, APM
    commitment, next result to measure — as a `<dl>`, instead of one concatenated
    sentence. This was raised against the Dambam row, which read as a run-on paragraph.
11. ✅ **A faint `apm-emblem.png` watermark now ships on all six pages.** Decorative,
    `aria-hidden`, `pointer-events: none`, hidden in print, and below the topbar in
    z-order so it never obscures navigation. It reuses an already-approved asset, so no
    new rights — but it makes the emblem far more prominent and its rights record is still
    unratified.

### P0 — Do next: commit and ship S4, then S5

1. **Ratify the `services3.arcgis.com` robots exemption** (§21). This is the one S4 item
   that needs an owner decision rather than code.
2. Stage S4 using the §18 allowlist, which now names the two build-required data files.
3. Push is **not** standing authorisation. Ask the owner.
4. Then **S5, the opinion poll**, per `SITE_EXPANSION_PLAN.md` §4 S5.

### P1 — The opinion poll (phase S5)

5. New `src/poll/` package mirroring `src/requests/`. Q1 is a required single choice over
   the **existing 9 `REQUEST_CATEGORIES`** so results stay comparable with the request
   queue; Q2 is an optional ≤300-char free text that must be **excluded from the tally**.
6. `POLL_ENDPOINT = ""` ships it disabled, mirroring `REQUEST_ENDPOINT`. On a static
   host, live results mean: read the endpoint when configured, else fall back to a
   committed `data/delivery/poll_snapshot.json` the weekly cron regenerates.
7. Minimum PII: no name, phone or email. Honeypot, consent, one submission per browser.
   Never seed, example or placeholder results — an empty set must render as empty.
8. Show `N` prominently with a self-selected-respondent disclosure, and hold percentages
   behind a configurable floor (default 10) so one vote cannot read as 100%.

### P2 — Housekeeping on the current product

1. Extend `indicators.csv` with more verified baselines and targets; keep missing
   baselines blank rather than estimating them.
2. Replace remaining delivery-output language with measured outcomes where primary
   evidence exists: service reliability, beneficiaries, learning, health access,
   market access, income and employment.
3. Add semantic validation for date validity and actor/source consistency.
   Duplicate promise text is now covered by `validate_unique_promises()`.
4. **Run a native-speaker Hausa review.** The count is now **59**: 53 from S1/S2 (27
   `usage_note_ha`, 25 `verification_status_ha`, plus the wash-promise clause) and **6 from
   S4** (the map `aria-label`, the caveat and credit labels, the registration-area
   "not geo-located" label, and the Hausa map caveat and attribution). The "not gazetted"
   disclaimer is the one that matters most to get right.
5. Ratify or correct the `apm-emblem.png` rights record in `asset_register.csv`.
6. Decide whether to narrow the `wash` sector label. It renders as "Water and climate
   resilience", but the published campaign source contains **zero** climate content.
7. Consider adding Playwright as a CI-only dependency so `tests/test_browser_layout.py`
   actually runs. It was left out of `requirements.txt` to avoid a Chromium download on
   every build; the static guards cover the same regressions meanwhile.

### P3 — Complete legacy evaluation work separately

1. Create the missing `data/human_review/filled/queue_en_part1.csv` without
   overwriting existing parts.
2. Merge completed review parts by `raw_id` into the root queue files.
3. Run the modified aggregation code and inspect `pipeline_stats.csv` and risk
   outputs.
4. Maintain a local `.evals/2026-W39.md` for each evaluation cycle. The current report
   is local-only because its 100-row filled sample is not approved for release staging.
5. Disclose that the current filled sample was labelled by
   `mimo-v2.6-ai-reviewer`, not a native Hausa speaker.

### P4 — Operate and improve

1. Monitor `delivery-sources.yml` weekly and review all new candidates.
2. Add sector-specific primary sources for water, health, education, roads,
   agriculture, governance and youth livelihoods.
3. Add a release checklist for semantic claims, source dates, LGA attribution and
   asset approval.
4. Keep legacy sentiment/risk work isolated from `data/delivery/` and the public
   landing page.

## 14. Claims the Next Handoff Must Not Make

Do not claim that:

- The current product is the legacy sentiment/risk heatmap.
- The current Pages workflow runs classification, aggregation or daily scraping.
- All 25 achievements have independently verified outcomes.
- All 20 LGAs have comprehensive sector coverage.
- The current 100-row evaluation is native-speaker or human ground truth.
- The pilot is a real 500-post manually labeled corpus.
- Human review is fully merged.
- The modified aggregation code has been tested.
- `pipeline_stats.csv` exists.
- The risk model is trained or producing meaningful LGA ratings.
- Facebook ingestion is active without tokens.
- YouTube ingestion is implemented.
- A launch or handover is automatically a completed outcome.
- A statewide record can be assigned to an LGA without explicit LGA evidence.

Claims that became false or newly unsafe with the S1/S2 work:

- ❌ **Do not claim the site is fully bilingual.** It is bilingual throughout the
  delivery content, but the 59 Hausa strings added in S1/S2/S4 are **AI-drafted and not
  native-speaker reviewed**. Disclose this, exactly as `.evals/2026-W39.md` already does
  for its labeler.
- ❌ **Do not claim the campaign published a water/sanitation policy.** It did not. The
  published manifesto has five pillars and no water pillar; `promise-wash` is the water
  **clause** of the Infrastructure Development commitment and is labelled as such.
- ✅ **The sponsor slot is now filled** — but only with what the owner supplied. The footer
  names **Abdulkadir Ahmad (Hammayo)** and states the role as "A dedicated member of his
  campaign team." Nothing was invented around it: no amount, no organisation, no extra
  title. `test_no_invented_sponsor_content` still fails on any of those, and
  `test_no_placeholder_brackets_remain` fails if the credit drifts back to `[ ... ]`.
- ❌ **Do not claim the emblem is a separately cleared asset.** It is a derived crop of the
  already-approved `apm-logo.png` with no new rights cleared. The `approval_note` was
  ratified by the owner on 29 September 2026.
- ❌ **Do not claim the contributor's portrait is a stock image.** It is a derived square
  crop of a campaign-supplied photograph of the named person, registered with owner
  approval on 29 September 2026. No third-party rights were cleared, which is why the
  register records it as the subject's own photograph.

Claims that became false with S4:

- ✅ **The map is pushed and the pages are committed.** `82eb16a` is on `origin/main` as of
  29 September 2026 and included the regenerated `docs/*.html`, so GitHub Pages publishes
  the map on the normal deploy-on-push. `docs/` is a tracked tree, and the cron regenerates
  and commits it weekly to catch drift. Confirm against a live deployment run before
  claiming the map is serving.
- ❌ **Do not claim the map boundaries are official.** They are GRID3 *operational*
  boundaries descended from polio-vaccination microplanning data. GRID3 states they are
  not validated by government authorities and carry no gazetted status. The page says
  "indicative, not gazetted" and a test asserts it.
- ❌ **Do not claim the boundaries are surveyed or precise.** They are simplified for
  display at a 223 m tolerance, and the simplification is what guarantees a seamless map.
- ❌ **Do not claim the registration areas are geo-located.** `lga_wards.csv` has no
  coordinates and none were invented. They are listed as "not geo-located" and are never
  drawn on the map.
- ❌ **Do not claim the map is a comprehensive sector picture.** It is 20 source-backed
  evidence rows on indicative outlines — one curated row per LGA, not exhaustive coverage.
- ❌ **Do not claim zero horizontal overflow was verified before S4.** It was not; the
  topbar overflowed by 27px at 375px on every page until S4 fixed it. The claim in the
  S3 handoff was wrong. It is genuinely 0px now, and measured.

## 15. Approved Interactive Site Expansion Plan

This section records the approved plan and the current implementation state. The
featured carousel, RA dataset, bilingual request form, request validation, and
privacy-safe aggregation are implemented locally. The Apps Script adapter,
private Google Sheet deployment, and weekly aggregate publishing are not
implemented yet; the form's submit control stays disabled until an approved
HTTPS endpoint is configured.

### Product decisions confirmed

- Extend the current static `docs/index.html` delivery site, not the legacy
  sentiment/risk dashboard.
- Add a highly interactive achievement experience with a five-slide curated
  showcase.
- Use real, verified achievement photographs, not a live social/news feed.
  Each image must be stored locally, approved, and linked to its source record.
- The five featured achievements are selected and approved by the campaign owner;
  they are not automatically ranked.
- Add an LGA achievement explorer. Statewide or multi-LGA records must retain an
  explicit scope and must not be falsely assigned to one LGA.
- Add a public request form with one primary request per person. The form is not
  an official voter-registration or voter-ID system.
- Generate a non-sensitive request tracking ID such as `APM-2026-0001`.
- Request location fields: LGA dropdown, dependent ward dropdown, and free-text
  address/location field.
- Request categories: water, electricity, roads, healthcare, education,
  jobs/agriculture, security, housing/environment, and other.
- Add an optional short description/details field.
- Optional private name, phone, or email fields may be collected for follow-up.
  They must never be published in the public dashboard or committed to the repo.
- Public request output is aggregate-only: counts by LGA, category, and reporting
  period. No names, contact details, addresses, request IDs, or free text appear
  publicly.
- The public dashboard refreshes weekly.
- The feature is bilingual in English and Hausa, including form validation,
  categories, dashboard labels, and confirmation text.
- Ward names must be researched from authoritative/public sources and validated
  before the ward dropdown is published. Do not infer or invent the ward list.
- Submitted requests are campaign input only. They must not automatically become
  verified needs, achievements, evidence records, or outcome claims.

### Target architecture

```text
Approved achievement data + approved local images
                    ↓
           src/dashboard/render.py
                    ↓
      interactive static docs/index.html
                    ↓
              GitHub Pages

Public request form
        ↓
Google Apps Script web endpoint
        ↓
Private Google Sheet + private contact fields
        ↓
Weekly aggregate generation
        ↓
Public aggregate-only request dashboard
```

GitHub Pages cannot receive or persist form submissions by itself. The Google
Sheet and Apps Script endpoint therefore form a separate public write path from
the static page. The raw Sheet, Apps Script source, service credentials, and
contact details are not stored in this repository.

### Implementation phases

#### Phase 0 — Data and policy preparation

1. Complete the RA naming/limitation review and owner confirmation of the
   provisional 212-row dataset.
2. Review the five rendered captions, scope labels, source-attributed images and
   context-image notes before public deployment.
3. Confirm optional contact collection, consent copy, retention/deletion policy,
   duplicate-retry rule, and privacy threshold.
4. Confirm the private Google Sheet owner, Apps Script deployment account, and
   access list before collecting any personal information.

#### Phase 1 — Achievement carousel and explorer (implemented locally)

1. Add a curated featured-achievement data contract, separate from the complete
   achievement table.
2. Add image references and metadata to the existing asset approval model.
3. Render five accessible carousel slides with captions, alt text, keyboard
   controls, previous/next controls, and a no-JavaScript text fallback.
4. Add LGA scope handling for `lga`, `multi_lga`, and `statewide` records, with
   canonical `lga_names` validation and visible scope labels.
5. Preserve the distinction between verified achievement, campaign promise, and
   unmeasured outcome.
6. **Deferred:** add a full-screen achievement viewer as a focused overlay opened
   from the existing carousel. The in-page carousel remains the no-JavaScript
   fallback. The viewer must support next/previous buttons, dots, counter,
   keyboard arrows/Home/End/Escape, touch swipe, focus return, background scroll
   lock, reduced-motion behaviour and mobile overflow safety.

1. Add a curated featured-achievement data contract, separate from the complete
   achievement table.
2. Add image references and metadata to the existing asset approval model.
3. Render five accessible carousel slides with captions, alt text, keyboard
   controls, previous/next controls, and a no-JavaScript text fallback.
4. Add LGA scope handling for `lga`, `multi_lga`, and `statewide` records.
5. Add sector/evidence filters and shareable LGA URL parameters where safe.
6. Preserve the distinction between verified achievement, campaign promise, and
   unmeasured outcome.

#### Phase 2 — Request intake (form implemented locally; backend pending)

1. The bilingual form is implemented with dependent LGA/RA selectors and
   free-text address/details.
2. Generate a request tracking ID server-side; do not ask for an official voter ID.
3. Validate allowed LGA, RA, category, field lengths, consent, and request size
   in the endpoint, not only in the browser.
4. Add a honeypot, rate limiting, safe error handling, and a separately approved
   duplicate/idempotency design.
5. Store the raw request privately and show a confirmation containing only the
   generated tracking ID and neutral next-step text.
6. Do not place contact details, raw requests, credentials, Sheet IDs, or Apps
   Script deployment details in GitHub Pages, `docs/`, logs, or public source
   files.

#### Phase 3 — Weekly aggregate dashboard

1. Compute totals by LGA, category, and reporting period from approved/private
   request records.
2. Publish only aggregate data to the static site or a sanitized aggregate file.
3. Display the reporting date and a clear privacy/moderation notice.
4. Add an interactive, accessible bar chart and LGA/category matrix.
5. Suppress ward-level public counts below the approved privacy threshold,
   provisionally five requests, until the campaign owner approves another value.
6. Refresh weekly through the approved operational workflow.

### Acceptance criteria

- The existing static render and GitHub Pages deployment continue to work.
- Exactly five approved featured achievements appear in the showcase.
- Every featured image loads locally and has valid provenance and approval data.
- LGA selection never mislabels statewide or multi-LGA evidence.
- The RA selector contains the approved provisional 212-row INEC electoral-RA
  dataset, with the limitation visibly stated.
- One submission creates one request with one primary category.
- The form supports English/Hausa, keyboard use, mobile layout, clear validation,
  and accessible error/confirmation states.
- The public dashboard contains no personal data, request IDs, addresses, or
  free-text descriptions.
- Weekly output clearly states its reporting date; no ward-level cells are
  published, and any future ward-level output requires the approved suppression
  rule.
- Spam, invalid categories, oversized descriptions, invalid ward/LGA pairs, and
  duplicate retries are handled safely.
- Existing integrity tests, rendering, evidence validation, and responsive checks
  continue to pass.

### Risks and unresolved dependencies

- The 212 RA labels are provisional electoral-registration data, not a verified
  current administrative-ward schedule; the public form must say RA.
- The five source-attributed images are owner-approved for use, but independent
  rights clearance is not verified. The education and maternal images are
  visibly contextual rather than project close-ups and are labelled as such.
- Google Apps Script deployment permissions, quotas, and abuse controls need a
  real account test.
- Optional contact details require a documented retention and deletion policy.
- Aggregate counts can still create privacy risk in small locations; exact
  LGA/category cells remain owner-review items, and no ward-level cells are
  published.
- The suite passed 40 `unittest` tests **at that checkpoint**; it now passes 87 after S1/S2. Browser verification covers
  375px/1440px rendering, Hausa toggling, LGA→RA selection, carousel navigation,
  scope filters, zero console errors, and disabled submission with the empty
  endpoint.
- The public static site cannot provide reliable real-time request updates; the
  agreed dashboard is weekly.

### Implementation checkpoint — 25 September 2026

The following first safe slice is implemented but not connected to production or
published:

- The five approved featured records and source-attributed local images are now
  present and rendered. The current carousel is live locally in `docs/index.html`
  with exactly one section, five slides, bilingual captions, scope badges, and
  visible achievement-source and image-source links.
- The 212-row `lga_wards.csv` is an explicitly provisional INEC electoral-RA
  dataset for the owner-approved MVP. It is not a verified current administrative
  council-ward schedule.
- `src/requests/validation.py` and `src/requests/request_schema.json` define the
  private request contract, consent, honeypot, LGA/ward/category rules, length
  limits, optional contact fields, and a fixed PII-free public projection.
- `src/requests/aggregate.py` produces deterministic LGA/category aggregates with
  consent/status/period checks, timezone-aware timestamps, and small ward-count
  suppression.
- `tests/test_request_validation.py`, `tests/test_request_aggregation.py`,
  `tests/test_ward_dataset.py`, and `tests/test_request_form.py` cover the new
  contracts. The current local suite passes 40 tests.

Not implemented yet: the Google Apps Script adapter, Google Sheet
schema/deployment, rate limiting, moderation workflow, aggregate snapshot file,
weekly aggregate job, and release/deployment changes. The static bilingual form
and RA-dependent selector are implemented locally, but submission is disabled
until an explicitly approved HTTPS Apps Script endpoint is configured.

### P0 research checkpoint — 25 September 2026

Two read-only research agents completed the first evidence pass:

#### Ward research

- The 20 Bauchi LGA names are high-confidence and supported by the Bauchi State
  Ministry of Local Government and Chieftaincy Affairs and INEC-aligned sources.
- A 212-item electoral Registration Area (RA) list was found through INEC-aligned
  and secondary sources. It is suitable only as a **provisional electoral-RA**
  dataset, not as a verified current statutory administrative-ward schedule.
- The recommended public label is `LGA and electoral registration area (RA)`.
- Key official INEC PDFs returned 404/403 or were JavaScript-rendered; no current
  official administrative ward gazette was located.
- The dataset must be manually reviewed before production, especially slash-
  combined labels, A/B wards, and spelling variants such as Dambam/Damban,
  Kirfi/Krifi, Misau/Miau, Alkaleri/Alakali, and Dagauda/Dagaurda.

#### Achievement review packet

The campaign owner approved these five candidates for the carousel. Their current
records retain the original research caveats:

1. `achievement-estrra-outcomes` — ESTRRA livelihoods outcomes; Grade A;
   `multi_lga`/Bauchi North scope; quantitative reported outcomes, not
   independently audited.
2. `achievement-giade-mill` — Kurba rice milling hub; Grade A; `lga`; reported
   operating-capacity improvement, with income/skills outcomes still to measure.
3. `achievement-toro-odf` — Toro open-defecation-free validation; Grade A; `lga`;
   institutional validation milestone with continued behaviour/maintenance
   follow-up needed.
4. `achievement-education-scorecard` — education delivery scorecard; Grade A;
   `statewide`; reported delivery outputs, not measured learning outcomes.
5. `achievement-maternal-services` — maternal and child health services; Grade A;
   `statewide`; service-reach milestone, not measured health outcomes.

Five source-attributed project/context images are now registered and approved
for owner-directed public use. Independent rights clearance is not verified.
The ESTRRA, Toro, education, and maternal images are explicitly marked as
context images; only the Giade Kurba mill image is a direct project image.

## 16. Next Session — Full-Screen Achievement Viewer (Deferred)

Do not start this until the current local checkpoint is committed. The viewer
will be a new focused overlay rather than a redesign of the whole page.

1. Add an `Open full-screen slides` control to the existing featured section.
2. Render the same five approved records in a fixed full-viewport dialog.
3. Support next/previous controls, dot navigation, slide counter, scope filters,
   `ArrowLeft`, `ArrowRight`, `Home`, `End`, and `Escape`.
4. Support touch/swipe movement without an external library.
5. Trap focus while open, return focus to the opener on close, lock background
   scrolling, and close via button, `Escape`, or backdrop activation.
6. Keep the current in-page carousel as the no-JavaScript fallback.
7. Add reduced-motion and mobile overflow handling.
8. Add renderer contract tests plus browser checks for open, navigate, filter,
   keyboard close, focus return, and 375px/1440px layout.
9. Run the independent review before staging or committing the viewer change.

### External human-only deployment gates

1. Owner review of the five rendered captions, scope labels and source/image
   attribution presentation.
2. Independent image rights/licensing confirmation. The five images are recorded
   as owner-directed source-attributed use, but rights clearance is not verified.
3. Owner review of the provisional 212-row electoral-RA list and its limitation
   wording, especially slash-combined labels and spelling variants.
4. Native-speaker Hausa review of public copy.
5. Owner provision of the private Google Sheet, Apps Script execution account,
   staff access list, deployment audience, consent wording, optional-contact
   decision, retention/deletion policy, duplicate/idempotency policy, rate limit,
   privacy threshold and weekly reporting schedule.
6. Agents cannot create or operate the private Google account without owner
   credentials. See `docs/GOOGLE_SHEETS_SETUP.md`.


## 17. OpenCode Session Restart and Navigation

### Global mouse configuration

The global OpenCode TUI configuration is stored at:

```text
C:\Users\TOSHIBA\.config\opencode\tui.json
```

It currently contains:

```json
{
  "$schema": "https://opencode.ai/tui.json",
  "mouse": true,
  "scroll_speed": 3
}
```

Quit and restart OpenCode after changing this file. The setting applies globally,
not only to this project.

### Manual message scrolling

These are the current default OpenCode message-navigation shortcuts:

- `PageUp` — previous page
- `PageDown` — next page
- `Ctrl+Alt+B` — previous page
- `Ctrl+Alt+F` — next page
- `Ctrl+Alt+Y` — one line up
- `Ctrl+Alt+E` — one line down
- `Ctrl+Alt+U` — half page up
- `Ctrl+Alt+D` — half page down
- `Home` or `Ctrl+G` — first message
- `End` or `Ctrl+Alt+G` — last message

On some terminals, `PageUp` and `PageDown` may be intercepted by the terminal
itself. If that happens, use the `Ctrl+Alt+B` and `Ctrl+Alt+F` alternatives.
Mouse scrolling should work after the OpenCode restart when terminal mouse
capture is enabled.

## 18. Commit Boundary and Working Tree

`main` is **fully pushed**; there is no local-only commit. The list below is the staging
allowlist for the *next* change (S4), not a record of pending work. Push was authorised
once, on 26 September 2026, and is **not** standing authorisation.

History leading to the first push, for provenance:

```text
2fd12fa  feat(delivery): add interactive achievements and request intake   (pre-existing)
9cd101b  docs: add site expansion plan                                       (S0)
be832e0  fix(i18n): correct Hausa rendering across delivery content          (S1)
533a210  fix(header): legible APM emblem, sponsor slot, persistent language  (S2)
27a7a76  docs: handoff for the next session after S0-S2
957d47d  feat(site): six-page split, mobile nav, both release traps closed  (S3)
1eac1bc  docs: record the S0-S3 release as deployed
```

### Staging allowlist used for the S4 commit

```text
AGENTS.md
HANDOFF.md
README.md
SITE_EXPANSION_PLAN.md
data/delivery/source_register.csv
data/delivery/source_manifest.csv
data/delivery/source_snapshots/grid3-lga-boundaries-bauchi.geojson
data/derived/lga_paths.json
src/dashboard/render.py
src/ingestion/common.py
src/ingestion/lga_boundaries.py
src/derived/__init__.py
src/derived/lga_paths.py
docs/index.html
docs/achievements.html
docs/atlas.html
docs/poll.html
docs/agenda.html
docs/sources.html
docs/about.html
tests/test_bilingual.py
tests/test_site_structure.py
tests/test_atlas_map.py
tests/test_browser_layout.py
```

⚠️ **The two `data/` entries are build-required, not optional.** `validate_data()` raises
`FileNotFoundError` without the cached snapshot, and `load_lga_paths()` raises without the
derived JSON. A commit that stages the code but not the data is a red build.

`IMPLEMENTATION_PLAN.md` is not modified by S4. `docs/*.html` other than `atlas.html`
changed only because the S4 CSS and the watermark are shared, which is expected.

**The site is now seven pages.** `python src/dashboard/render.py` writes all seven; the
weekly cron stages `docs/*.html` and fails if any page is missing. See §20 for how both
traps were closed.

Never stage or commit these preserved/local paths without explicit owner
confirmation:

```text
src/aggregation/aggregate.py
.evals/
.playwright-mcp/
Abdulkadir Hammayo .png    untracked original 1139x1381 / 2.1 MB supplied portrait
```

`data/human_review/filled/` is **no longer on this list** as of 1 October 2026. It held 160
completed, signed, reasoned reviews that no code could see, and the human-review feature was
inert because of it. The reviews are now loaded, validated and folded into the aggregates by
`src/aggregation/reviews.py`, and they are committed — an untracked review corpus would make
the fix unreproducible from a clean checkout, which is how it stayed broken for as long as
it did.

The last one is the full-size original behind `assets/brand/abdulkadir-ahmad-hammayo.png`.
It is deliberately not committed — it is 2.1 MB of the same photograph, and the registered
512x512 crop is the only version the site needs. Do not `git add .`.

### The contributor credit is filled (29 September 2026)

The owner supplied the photograph and the name, and the slot is no longer a placeholder.
The credit now reads, in both languages:

```text
Contributor / Mai ba da daɗi
Abdulkadir Ahmad (Hammayo)
Role: A dedicated member of his campaign team.
```

Four things were load-bearing, and all four are now test-enforced:

1. **The asset had to be derived, not copied.** The supplied file is 1139x1381 and 2.1 MB.
   It is cropped to a 900px square (head-and-shoulders, face centred) and resized to
   512x512 as `assets/brand/abdulkadir-ahmad-hammayo.png` — 339 KB. Its SHA-256
   `71a879eb…` is in `asset_register.csv` with `usage_status` set and
   `approved_at` 2026-09-29, and it is listed in `ASSET_FILES` so `prepare_assets()` copies
   it into `docs/assets/brand/`. A file in `assets/` without an `ASSET_FILES` entry never
   reaches the published tree, and a register row without a matching hash fails
   `validate_data()`.
2. **The dashed placeholder treatment had to go.** The dashed border was the visual tell
   that the slot was empty. With a real name and a real photo it would misdescribe the
   credit, so `.sponsor` and `.sponsor-photo` are now solid, and
   `test_slot_is_no_longer_styled_as_a_placeholder` fails if `dashed` reappears.
3. **The portrait needed a bilingual `alt`.** `setLanguage` rewrites `textContent` for
   every `[data-en][data-ha]` element, so an `img` given `attr()` would be emptied on the
   first language switch — the same defect that once blanked the whole map. The image
   instead uses `data-alt-en`/`data-alt-ha`, which `setLanguage` already handles for `img`,
   and `test_photo_alt_is_bilingual` guards it. Verified in a browser: EN shows
   "Portrait of Abdulkadir Ahmad (Hammayo)", HA shows "Hotun na Abdulkadir Ahmad (Hammayo)",
   and the image is intact in both.
4. **The anti-fabrication test was narrowed, not deleted.**
   `test_no_invented_sponsor_content` still rejects any amount, any four-digit number, and
   any of `Dr. Yakubu Adamu`, `APM`, `Bauchi State Government` inside the slot. The owner's
   own words went in and nothing around them. `test_no_placeholder_brackets_remain` fails if
   `[ Sponsor name ]` or "to be completed by the campaign team" ever comes back.

**Label wording.** The slot is labelled **Contributor**, not Sponsor. The owner's
description of his relationship to the campaign is a team role, not a financial one, and
"Role:" replaced "Contribution:" for the same reason. The CSS class names were left as
`.sponsor*` to avoid a wide rename across the stylesheet and `test_site_structure.py`; the
class name is now historical only.

**Hausa.** "Mai ba da daɗi", "Darasi:", "Memba mai ɗaukar hankali na hukumar sa." and the
portrait `alt` are **4 more AI-drafted strings**, bringing the unreviewed total to **69**.
The owner accepted the set as written on 29 September 2026, and the disclosure stays.

## 20b. S5, the Opinion Poll — Built, and Deliberately Inert

`poll.html` now carries three things: the poll form, the results panel, and the request
form. **The poll ships disabled.** `POLL_ENDPOINT = ""`, the vote button renders `disabled`,
and `test_a_disabled_build_contains_no_code_path_that_can_send` asserts the endpoint guard
appears *before* the `fetch` in `POLL_SCRIPT`. The contract is `src/poll/`, mirroring
`src/requests/`, and `docs/POLL_SETUP.md` is the owner guide for connecting it via Sheets
and Apps Script.

**Why provider-agnostic was the right call.** The storage decision is the owner's, and it
constrains nothing but one constant. Building against a guess would have meant a rewrite
once Sheets was chosen. So the pure contract — schema, validation, tally — is done and
tested now, and connecting is a one-line config change.

### The five properties that make a published poll honest

1. **It collects no direct identity, and that is enforced rather than intended.**
   `FORBIDDEN_IDENTITY_FIELDS` covers `name`, `phone`, `email`, `address`, `nin`, `bvn`,
   the voter-ID names, and the **exact-age aliases** `age`, `age_years`, `exact_age`,
   `years_old`, `date_of_birth`, `dob`. Each is rejected with
   `identity_field_forbidden` *before* the generic unknown-field check, so a misconfigured
   form fails legibly rather than looking like a typo.

   The dangerous alternative is the one that looks harmless: accepting the field,
   stripping it, and returning 200. A dropped identity field is still an identity field on
   the wire and in every log between the browser and the Sheet.

2. **Area and demographics ARE collected — this reversed the original design, and the
   reversal is recorded here rather than quietly rewritten.**

   On 29 September 2026 the owner asked for a dashboard with an LGA **and ward**
   dropdown, and then for age and gender. The poll as built had deliberately collected
   neither, so this was a genuine change of posture rather than a formatting request.
   What ships:

   | Field | Required | Notes |
   |---|---|---|
   | `lga` | yes | 20 broad buckets |
   | `ward_code` | **no** | Optional so nobody is forced to narrow further than they want |
   | `age_band` | **no** | Group only, closed list, with a decline option |
   | `gender` | **no** | Closed list: Woman / Man / Prefer not to say |

   **Why bands and a closed list rather than the literal request.** An exact age plus an
   LGA plus a registration area in a small community is close to naming a person, which is
   the one thing the poll was built to avoid. Bands are the standard answer and they are
   not a compromise: an 18–25 slice tells you what you need about a constituency and
   cannot single anyone out. Free-text gender is a re-identification channel and an abuse
   target. The owner confirmed bands and a closed list.

   **`sectors` is keyword-only on `validate_poll_response`.** The copied positional
   signature put `sectors` second and type checking caught every call passing server time
   where an iterable of strings belonged. Mirroring `src/requests/` is worth doing; copying
   its argument order without thinking was not.

3. **Small-cell suppression is mandatory, and it is the only thing making the above
   publishable.** Any non-zero cell below `small_count_threshold` (default 5) becomes
   `null` and renders as a dash or a hatched bar. The threshold has a hard lower bound of
   2 — `validate_small_count_threshold` **refuses** 0 and 1 rather than honouring them,
   because either would publish single respondents.

   A cell of **0 is published, not suppressed.** "Nobody in this area chose water"
   identifies nobody, and hiding it would make the page say "too few to publish", which is
   a different and weaker statement. This was a bug on the first pass:
   `if count < threshold` suppressed the zeros too.

   **Expect the ward breakdown to be almost entirely empty.** A local fixture with 320
   responses and 154 registration areas produced publishable figures for all 20 LGAs and
   for **zero** LGAs at ward level. 212 areas at a floor of 5 needs roughly 1,000+
   responses concentrated in a few areas to show anything. That is the arithmetic working.
   The page says "too few to show" rather than inventing a figure.

   **Demographics are never crossed with registration areas.** `by_lga_age_band` and
   `by_lga_gender` stop at LGA. Ward × age is the combination that actually identifies
   someone, and a test asserts the tally never builds it.

4. **Q2 never moves a number.** `tally_poll_responses` reads `sector` only.
   `public_projection` excludes the comment outright, so publishing it would turn an
   anonymous preference count into a set of attributable public statements.
   `test_the_comment_can_never_change_a_number` tallies two runs whose comments differ
   wildly and asserts identical `by_sector`. The owner decided comments are kept for
   **off-site qualitative study**, which is compatible — provided the boundary holds and
   nothing derived from free text ever appears as a published figure.

2. **Q2 never moves a number.** `tally_poll_responses` reads `sector` only.
   `public_projection` excludes the comment outright, so publishing it would turn an
   anonymous preference count into a set of attributable public statements.
   `test_the_comment_can_never_change_a_number` tallies two runs whose comments differ
   wildly and asserts identical `by_sector`.

5. **An empty poll renders as empty.** With no `data/delivery/poll_snapshot.json`, the page
   says "No responses have been recorded yet." A row of zero bars reads as data, and it is
   not data. `test_no_placeholder_tally_is_committed_anywhere` fails the build if a
   snapshot is committed while the poll is disconnected. The dashboard was verified in a
   browser against a **temporary local fixture** that was then deleted; nothing seeded
   reaches the repository.

6. **One vote is never 100%.** The cap is `min(share, 100 - floor)`.

### The cap was wrong on the first attempt, and the direction is the point

The initial implementation was `max(share, floor)`, which is the intuitive reading of "a
floor" and is wrong twice over. `max(100, 10)` is 100, so it did not even stop the case it
was written for. And a floor raises a 1-in-9 share to 11.1% for no reason, while
pretending a small share is larger than it is.

The correct shape is a **cap**: `min(share, 100 - floor)`. A single response renders 90%; a
genuine 75% majority is untouched; a small minority is never inflated.
`test_the_cap_never_invents_a_share_the_votes_do_not_support` pins that direction, because
"correcting" it back into a minimum is the obvious and wrong next commit.

### Two bugs worth remembering

- **`render.py` cannot `import src.poll` when run as a script.** The cron runs
  `python src/dashboard/render.py`, so the repo root is not on `sys.path` and the import
  raised `ModuleNotFoundError` on the runner while every local test passed. Loading by
  bare file path was tried first and fails for a different reason: `aggregate.py` uses a
  relative import and needs a real package. `_poll_module` now puts `ROOT` on `sys.path`
  once, if missing, and imports normally. The lesson generalises — *run the real entry
  point the way CI runs it*, which is what `test_a_fresh_checkout_renders` now does for the
  snapshot bytes too.

- **Both scripts share one `<script>` on `poll.html`.** `POLL_SCRIPT` and `REQUEST_SCRIPT`
  are concatenated into a single inline block. A duplicate top-level `const` across two
  blocks is still one parse unit, so a collision would be a `SyntaxError` disabling every
  handler on the page — the S3 trap, reintroduced by adding a second form.
  `test_the_poll_script_never_defines_a_name_the_request_script_defines` asserts the two
  declaration sets are disjoint.

### Hausa review of 30 September 2026 — 20 defects found and corrected; gate closed 2 October 2026

An **independent AI agent** reviewed the Hausa strings after the interactive dashboard was
built. It had not written them. Full record: **`docs/HAUSA_REVIEW.md`**, which lists every
string, the correction, and the ground on which it was provable.

**Why the findings were trusted enough to apply.** Only defects provable by one of three
grounds were corrected, and all three are checkable without trusting the reviewer's Hausa
judgement: **(a)** the Hausa contradicts the English printed beside it, **(b)** it contradicts
another Hausa string for the same concept in the same file, **(c)** the element is
structurally untranslated. Anything the reviewer called *questionable* or *idiomatic* was
left alone — a stiff phrase is not a defect, and rewriting one on an AI's say-so would swap
an unknown for another unknown.

**The three that mattered most.**

1. **A privacy warning had inverted.** *"Please do not include your name, phone number,
   address…"* had no negative marker in the Hausa and read as an instruction to include
   them. The one finding that could have caused real harm.
2. **"Never an exact age" had become "never an age".** The form collects an age *band*; the
   Hausa asserted the poll asks for no age. `mukulli` ("lock") had also been used for
   "group".
3. **The map's "indicative, not gazetted" caveat was unintelligible.** `Makiyawa` means
   *colours*, not *boundaries*, and the not-gazetted clause had no comprehensible form.
   This is a boundary-licensing requirement, so it is a compliance problem, not a style one.

Also: `Gwaji` (test) had been used for the Group filter while the same file used it for
"trial" and "governance"; `maƙai` (straw) had been a calque for "endpoint" and "tracking
reference" at 10 sites while the file already used the right words elsewhere; the
`<optgroup>` headers on the new Group dropdown had no `data-ha` at all, because an
optgroup's visible text is its `label` **attribute** and `setLanguage` only rewrites
`textContent`.

**What this did not do on its own.** An AI reviewed AI-drafted Hausa. Every correction was a
*candidate*, and a list of ~11 strings the reviewer flagged as merely questionable is in
`docs/HAUSA_REVIEW.md` for a human. **The gate was closed on 2 October 2026 by the
native-speaker review the owner reports complete** — not by this pass. **The AI-drafted
provenance disclosure stays**, because the strings are still machine-drafted and
machine-corrected rather than natively translated. If that reviewer changed any of the ~11
strings listed below, record the change in `docs/HAUSA_REVIEW.md` rather than leaving the
file describing a state that no longer ships.

**Correction to §21's earlier claim.** That section named four known-wrong strings. Three
had already been fixed in `7ce2ff9` and no longer existed — `ba zafi ba` → `ba zabi ba`,
`jagoranta` → `da kansa su amsa`, `maƙalashin` → `sharhi`. Only the "no Hausa word for
survey" defect survived, and it is now fixed. Do not send a native speaker to re-check the
three that are already right.

**I am not a native Hausa speaker and cannot certify any of these strings.** The structural
checks — placeholders, terminology drift, untranslated English, identical pairs — all pass.
The four items above are what reading the strings actually found, and a native speaker has
to confirm the fixes. **The owner reports that confirmation done on 2 October 2026; no
reviewer's name is recorded here and none may be invented.**

### Open for the owner

- ~~**Get a native speaker to review the poll strings before connecting the poll.**~~ **Done
  2 October 2026.** A garbled disclosure is worse than an English one, because it looks
  translated — which is why this gate existed and why the disclosure it produced stays.
- **`docs/POLL_SETUP.md` step 6: set a retention period for the comment column, and a
  process that deletes on schedule.** Comments are now explicitly kept for study, which
  makes this a live obligation rather than a hypothetical. A 300-char free-text field held
  indefinitely is not anonymous in any meaningful sense. **Shipped in code**: default 180
  days, `MAX_COMMENT_RETENTION_DAYS = 365` ceiling, daily `purgeExpiredComments` trigger
  installed by `installRetention`.
- **Google retains IP addresses in Apps Script logs** regardless of what the Sheet stores.
  Not fixable in code; a conscious decision, not a discovery.
- Whether the poll closes, and what the page says when it does.
- `small_count_threshold` is 5. The owner may raise it; it must not go below 2.

## 21. The robots.txt Exemption on the ArcGIS Host — Ratified

This is the one S4 decision that is a judgement call rather than code, so it is recorded
prominently rather than buried in a diff.

**What happened.** `src/ingestion/lga_boundaries.py` fetches the GRID3 boundary layer once.
The repo's `common.polite_get` checks `robots.txt` first and treats an *unverifiable*
`robots.txt` as a hard skip. The fetch was refused:

```text
PermissionError: robots.txt disallows or is unverifiable:
  https://services3.arcgis.com/.../query?...
```

**Why.** `services3.arcgis.com/robots.txt` returns **403 Forbidden for every user agent**,
including a full browser UA, so the file is WAF-blocked rather than absent. Meanwhile the
registrable domain serves a retrievable, permissive robots.txt:

```text
$ curl https://www.arcgis.com/robots.txt
User-agent: *

Sitemap: http://static.arcgis.com/sitemap.xml
```

There is no `Disallow`. The data endpoint is ArcGIS's documented public FeatureServer query
API, openly served, and the layer is openly licensed **CC BY 4.0**.

**What was done about it — and what was not.** The global conservative default was **not**
weakened. `common.py` gained a named, justified, per-host list instead:

```python
ROBOTS_UNREACHABLE_HOSTS = {
    "services3.arcgis.com": (
        "robots.txt is WAF-blocked (403) at this ArcGIS subdomain; the registrable domain "
        "arcgis.com serves a permissive robots.txt and the endpoint is a documented public API."
    ),
}
```

`polite_get(url, robots_exemption=...)` refuses any host not on that list, and refuses any
justification shorter than 40 characters, so the exception stays auditable rather than
becoming a blanket "skip robots" flag. Every exemption exercised is recorded in
`robots_exemption_log()`. `lga_boundaries.py` restates the full justification at the call
site and fails fast at import if the query host is ever moved off the list.

**Why it needed the owner.** This is a deliberate, documented deviation from a guard
the repository treats as a hard rule. It is narrow, one host, one cached fetch, and the
weekly build never makes the request — but the judgement that a WAF-blocked robots.txt on
a subdomain with a permissive registrable domain is acceptable to fetch from is the
owner's to make, not the implementer's.

**✅ Owner ratified 29 September 2026.** The exemption stands as written: one host, one
cached fetch, justification restated at the call site, logged on every use, and the
conservative default unchanged everywhere else. The map stays.

**If the owner had declined**, the fallback was to drop the map and revert to the S3 tile
grid. There is no second boundary source in the current data model, and inventing
coordinates is not an option.

## 20. The Two Release Traps — Both Closed in S3

These were the two silent failure modes that would have broken the multi-page release.
Both are fixed, and both fixes are asserted by `tests/test_site_structure.py` so they
cannot regress.

### ✅ Trap 1 — the cron staged only `docs/index.html`

`rebuild-pages.yml` ran `git add docs/index.html docs/assets/`. With six pages that
renders all of them and commits one, so five subpages would silently stay stale forever.

Now:

```text
git add docs/*.html docs/assets/
```

plus a new **Verify every generated page exists** step that iterates all seven slugs and
fails the build if any is missing, so a dropped page is a red run rather than a stale
page.

### ✅ Trap 2 — the handoff allowlist named only `docs/index.html`

A maintainer following §18 would have staged nothing new. All seven pages are now listed,
along with `rebuild-pages.yml` and `tests/test_site_structure.py`.

### ✅ Trap 3 — the asset gate read the CSV with `awk` (found 29 September 2026)

This one was live for a week and nobody saw it, because the failure it caused is not
visible on the site.

The gate was:

```bash
awk -F, 'NR > 1 && $6 != "campaign approved" { bad = 1 } END { exit bad }' data/delivery/asset_register.csv
```

`awk -F,` splits on **every** comma, including the commas inside quoted CSV fields. The
`description` and `approval_note` columns are full of them, so on any such row field 6 is
not `usage_status` at all — it is the sha256:

| Row | `awk` field 6 | Correct value |
|---|---|---|
| `apm-logo.png` | `campaign approved` | `campaign approved` |
| `apm-emblem.png` | `c78a653a…8c8c` | `campaign approved` |
| `abdulkadir-ahmad-hammayo.png` | `71a879eb…8a1c` | `campaign approved` |

The derived `apm-emblem.png` row, added on 26 September, is the one that broke it. The
gate started rejecting a **fully approved** register, so run `36424348032` on 28 September
— the weekly cron's first and only scheduled run — failed with:

```text
##[error]Every campaign asset must be approved before public Pages publication.
```

The site looked fine throughout, because `docs/` is a tracked tree and Pages deploys on
push. The cron's job is to regenerate and commit the pages to catch drift, and that job
had never once run.

The gate now parses with `csv.DictReader` and looks `usage_status` up **by name**, which
is what it always meant to do. Five tests cover it in `ReleaseTrapTests`, including two
that break-test it in opposite directions — a genuinely unapproved row must fail, and an
approved register must pass — so the fix cannot become a check that never fires.

**The lesson, and it generalises:** the two S3 traps were both *staging* problems and both
would have shipped stale pages silently. This third one was a *validation* problem that
failed closed, which is safer, but only because someone read a red build. A cron that has
never run successfully is a cron that has never worked. Check the run list.

### ✅ Trap 4 — the manifest hashed local bytes, git had stored LF

Found in the same session, immediately after trap 3 was fixed and the cron was re-run by
hand. The asset gate passed, and then `render.py` failed:

```text
ValueError: source snapshot hash mismatch: delivery-89aec627d08a
```

`validate_data()` hashes the **working copy** of each snapshot and compares it with
`content_hash` in `source_manifest.csv`. On Windows those match. On the Linux runner they
never could:

| | bytes | sha256 |
|---|---|---|
| `HEAD` blob | 76,524, LF | `374731ad…` |
| Windows working copy | 78,771, CRLF | `527c462b…` |
| `source_manifest.csv` | — | `527c462b…` |

The cause is ordering. `.gitattributes` marks the snapshots `-text` so their bytes are
never normalized — but that rule landed in `d9cf5f8`, *after* the snapshots were first
committed in `3db2fc2`. Git had already converted CRLF to LF on the way into the object
store, and adding `-text` afterwards does not re-normalize what is already there. The
manifest hash was computed from the bytes on disk at fetch time, which is correct; the
blob git was storing was not. Two records of the same fetch disagreed, and only one of
them was right depending on where you stood.

The fix was `git add --renormalize data/delivery/source_snapshots/`, which rewrites the
blobs to the bytes the manifest describes. All 34 now agree. The boundary `.geojson` was
also outside the `.gitattributes` rule, so the same corruption could have reached it; the
rule now covers it and `AGENTS.md` warns against narrowing it back to `*.html`.

**The generalisable lesson, and this is the one worth keeping.** `validate_data()` hashes
the file in front of it. That is the right thing for a validator to do and it is *not
enough*, because the same logical file has different bytes on different machines. A
checksum that is only ever verified against a working copy is a checksum that has never
been tested against what a consumer actually receives. Anything a build validates from
disk needs at least one test that reads it back from the index or a clean checkout —
`test_a_fresh_checkout_renders` now does exactly that, materialising the index into a temp
directory and running the real entry point there.

### Still true after S3

- A duplicate `const` in any page's inline script is a `SyntaxError` that disables every
  handler on that page while the HTML still renders. All seven pages are now parsed with
  `node --check`, and a duplicate top-level declaration detector runs per page.
- Heavy sections must stay on exactly one page each, or pages get large for no reason.
  `test_site_structure.test_heavy_sections_appear_on_exactly_one_page` enforces that the
  source register, request form, agenda, indicators, atlas and carousel each appear once.

## 19. Handoff Checklist

A new maintainer should be able to answer “yes” to each question:

- [ ] Can I render the live product locally and get all seven pages?
- [ ] Do I know the map is live, and that the weekly cron only regenerates the pages?
- [ ] Can I explain why the two build-required map data files must be committed?
- [ ] Can I explain the four-step narrative model?
- [ ] Can I identify the source register, manifest, review queue and curated tables?
- [ ] Can I name all seven generated pages and say which sections live on each?
- [ ] Can I distinguish an achievement from an APM promise?
- [ ] Can I explain why the water promise is a published *clause*, not a pillar?
- [ ] Can I explain why `docs/` is the public source directory?
- [ ] Can I run source intake without overwriting raw snapshots?
- [ ] Can I validate source, snapshot and asset hashes?
- [ ] Can I explain why the header emblem needed a transparent background?
- [ ] Do I know that a duplicate `const` in the inline script silently kills all page
      JavaScript, and that `node --check` guards it?
- [ ] Do I know that `attr()` on an element with children empties it on a language switch,
      and that `aria()` exists for that case?
- [ ] Can I explain why the map quantizes to 3 dp and never less?
- [ ] Can I explain why "simplify then snap neighbours back together" tears the map, with
      the measurements?
- [ ] Can I explain why the boundaries are "indicative, not gazetted"?
- [ ] Do I know why the registration areas are labelled "not geo-located"?
- [ ] Can I state the licence of the boundary layer and why the Wards layer is forbidden?
- [ ] Can I explain the `services3.arcgis.com` robots exemption and that the owner ratified
      it on 29 September 2026?
- [ ] Can I identify the live GitHub Pages URL, and know `docs/` is committed so a push
      publishes rather than waiting for the cron?
- [ ] Can I preserve the uncommitted aggregation and human-review work?
- [ ] Do I know which pipeline is legacy and not part of the public product?
- [ ] Do I know which outcome claims still require measurement?
- [ ] Do I know which **129** Hausa strings are AI-drafted, that the owner accepted the
      first 69 as written, and that the 66 poll strings are still unreviewed?
- [ ] Do I know the poll collects no *direct* identity, and that the comment can never move
      a published number? (It is **connected** as of 1 October 2026 — see §21.)
- [ ] Do I know that area and demographics **are** collected, that this reversed the
      original design, and that small-cell suppression is the only thing making it safe to
      publish?
- [ ] Do I know the percentage cap **lowers** a share and never raises one?
- [ ] Do I know that the poll dashboard has three scope controls (LGA, registration area,
      one Group lens) and that the Group control is **disabled and cleared** whenever an
      area is selected, so the refused `ward x demographic` cross is unreachable?
- [ ] Do I know that a **share is printed only when it is exact**, that the count still
      shows when it is withheld, and that the group size has three states (*N answers* /
      *at least N answers* / *too few to show*)?
- [ ] Do I know which demographic view will actually publish (statewide gender) and which
      will mostly suppress (LGA × age × sector), and that this is the floor working?
- [ ] Can I say why connecting the poll is an owner action and what it needs — a Sheet, a
      bound Apps Script deployment, and the deployment ID?
- [ ] Do I know the independent AI pass of 30 September 2026 found and corrected 20 Hausa
      defects, that `docs/HAUSA_REVIEW.md` holds the record, and that **an AI reviewing
      AI-drafted Hausa does not close the native-speaker gate**?
- [ ] Do I know that three of the four "known-suspect" strings this file once named were
      already fixed in `7ce2ff9`, and that only the "no Hausa word for survey" defect
      survived?
- [ ] Can I name the credited contributor and state that nothing around his name was
      invented?
- [ ] Do I know the four release traps in §20 are closed and test-guarded, and that the
      third and fourth (the `awk` asset gate, and the LF/CRLF manifest mismatch) each made
      the weekly cron fail on its first run?
- [ ] Do I have a next-step list that does not mix current-product work with
      legacy evaluation work?
- [ ] Do I know that **both forms are live** and that a vote and a request were each
      verified end-to-end from a real browser (§21)?
- [ ] Can I explain why `application/json` broke both forms, and that `text/plain` is
      load-bearing rather than sloppy (§21)?
- [ ] Can I explain why the area dropdown needed `disabled` and not `hidden` (§22)?
- [ ] Do I know that **nothing reads the Sheet automatically**, and that
      `build_snapshot.py` is a manual step (§24)?
- [ ] Do I know the dashboard renders a full zero-state, and that it is **not** a
      demonstration-data mode (§26)?
- [ ] Do I know that a standalone Apps Script project returns a null spreadsheet and fails
      confusingly (§27)?
- [ ] Do I know `build_code_gs.py` emits CRLF on Windows and must be normalised (§27)?
- [ ] Can I name the recurring failure this session: a hand-written statement disagreeing
      with the data beside it, four times, each fixed by deriving instead (§28)?

## 22. S6, the About Page - Candidate Portrait and Contributor Credit

`about.html` is a seventh flat page generated by the same renderer, sharing the same
header, footer and language control as the other six. It carries three things.

1. **The candidate's portrait, `yakubu-adamu-single.png`.** It was taken from the
   candidate's own campaign site and is used **unmodified**, so no third-party
   photographer's copyright is in play. It is registered in `asset_register.csv` with
   SHA-256 `2f68e2b9c140`, `usage_status` `campaign approved` and `approved_at`
   2026-09-29, listed in `ASSET_FILES` so `prepare_assets()` copies it into
   `docs/assets/brand/`, and hashed by `validate_data()` on every build. A portrait with
   no register row never renders.

2. **A short account of his public record, and his own published words.** The five
   commitments are **linked to `agenda.html` rather than restated**, so there is exactly
   one authoritative copy of them and the two pages cannot drift apart.

3. **The contributor subsection**, naming Abdulkadir Ahmad (Hammayo) with his
   registered portrait and the same role line the footer carries. It is not a second
   credit with different wording; it is the same credit, given room.

**What is deliberately not there.** No credential claims, no allegations, no
sentiment figures. The owner confirmed the copy he wanted on 1 October 2026: "Dr." is
retained, the tone is positive, and nothing unverified is asserted. Every About-page
string ships in both languages, so it adds to the AI-drafted Hausa total tracked in
`AGENTS.md`.

**Why the page exists at all.** The site had seven ways to explain the campaign and no
way to explain the person. An election-facing site with no page about the candidate is
odd, and the footer contributor credit had nowhere to point.

**Provenance note still open.** The page's source note says the Bauchi State reporting
behind the record is listed on `sources.html`. **Verify that it actually is** before this
is pushed. `data/delivery/source_register.csv` is the record, and a source note that
points at a list the source is not on is a citation that does not resolve.

## 23. S6, the About Page — Shipped

`about.html` is the seventh flat page, generated by the same renderer and sharing the same
header, footer and language control as the other six.

**The portrait is campaign-owned.** `yakubu-adamu-single.png` was taken from the candidate's
own campaign site and used unmodified, so no third-party photographer's copyright is in
play. It is registered in `asset_register.csv` with SHA-256 `2f68e2b9c140`, `usage_status`
`campaign approved` and `approved_at` 2026-09-29, listed in `ASSET_FILES`, and hashed by
`validate_data()` on every build.

**The commitments are linked, not restated.** Five (then eight) chips deep-link into
`agenda.html#promise-<sector>`; each agenda card now carries that `id`. The full text lives
in exactly one place, so the two pages cannot drift. `test_agenda_renders_each_promise_once`
was widened from matching `<article class="agenda-card">` literally to matching the class,
because adding the anchor broke it and the test was asserting that the tag carried no other
attribute — not that one card exists per promise.

### The page shipped with no CSS of its own

Worth recording because eleven string-assertion tests passed while it was broken. The
portrait rendered at its natural 720px, and the commitments section was a heading, a
paragraph and a button stranded in about 200px of nothing. Nothing about a missing
stylesheet is visible in markup, and nothing about it is visible to a test that asserts
strings exist. `test_the_page_carries_its_own_css` now checks that every class the markup
uses is actually present in the inline stylesheet.

### The commitment count was wrong, and the fix was structural

The page claimed **"Five commitments"** over an eight-row `promises.csv`, and enumerated
five sectors that were not the five in it — health, water, livelihoods and governance were
missing from the sentence. A visitor reading About and then the agenda saw two different
campaigns. The heading count and the chip links now derive from the data via
`ABOUT_COMMITMENT_COUNT`, so they cannot disagree. The hand-written enumeration was deleted
rather than corrected, because a hand-written list is the thing that drifts.

**Owner decision, recorded:** "Dr." is retained in the copy. No credential claims, no
allegations, no sentiment figures on this page.

## 21. The CORS Defect That Stopped Both Forms Working

**This is the most important thing in this handoff.** Both endpoints were deployed,
`setupSheets` had run, both were returning correct receipts to a server-side probe — and
neither form worked from a browser at all.

The cause: the forms sent `Content-Type: application/json`. That is not a CORS-safelisted
request content type, so the browser sends an `OPTIONS` preflight before the `POST`. Google
Apps Script answers that preflight with `200 OK` and **no `Access-Control-Allow-*` headers
at all**, so the browser blocks the exchange and `fetch` rejects with a bare
`TypeError: Failed to fetch`.

Measured against the live poll deployment on 1 October 2026, from the page itself:

| Content-Type | Result |
|---|---|
| `application/json` | `TypeError: Failed to fetch` |
| `text/plain;charset=utf-8` | `200 {"response_id":"APM-POLL-2026-000008"}` |

Both scripts now send `text/plain;charset=utf-8`. This is safe because **neither endpoint
inspects `e.contentType`** — both read `e.postData.contents` and `JSON.parse` it, so the
body is identical. `ContentTypePreflightTests` pins all of it, including that neither
endpoint has started *requiring* a JSON content type, which is what would make this
workaround unsafe later.

**Why it survived so long, and why that matters.** Every server-side check passed. Python
and curl probes followed the redirect and read the response happily. The failure only exists
in a real browser talking to a real Google deployment, it produced no console error, no
status code, and a visitor-facing message saying only "we could not send your vote".

## 22. The LGA/Area Constraint Was Never Enforced in the UI

`updateRequestRas` set `option.hidden` and nothing else, which reads like it filters and
does nothing: **Chromium ignores the `hidden` attribute on `<option>`**. All 212
registration areas stayed selectable whatever LGA was chosen.

A visitor picking Bauchi and then the first area in the list sent `RA-001`, which is
**Alkaleri's**, and the endpoint correctly refused it as `invalid_ward` — surfacing only as
"we could not send your request", with nothing in the console. The server-side check was
doing its job perfectly; the UI was lying about what it offered. Playwright now cannot
select a cross-LGA area at all, which is how it was caught.

Fixed by setting `option.disabled`, which a native select does honour, and
`test_area_options_are_disabled_not_merely_hidden` stops it regressing to hidden-only.

## 24. Publishing Results — the Last Gap in the Poll

**The dashboard is a committed static file and nothing read the Sheet.** `POLL_SETUP.md` had
said "a scheduled, owner-controlled job reads the `Responses` tab" for months, with no job
behind it. Votes arrived and were stored correctly; the page said "no responses" forever; no
test failed, because the endpoint was correct and the dashboard was honest and the gap
between those two facts was invisible from either side.

`src/poll/build_snapshot.py` closes it:

```bash
# File > Download > Comma-separated values on the Responses tab
python src/poll/build_snapshot.py ~/Downloads/Sheet1.csv
python src/dashboard/render.py
git add data/delivery/poll_snapshot.json docs/*.html
git commit -m "data(poll): publish the weekly aggregate" && git push
```

It calls `build_public_snapshot`, so the field set matches `PUBLIC_SNAPSHOT_FIELDS` by
construction, suppression is identical to the live path, and no comment or response ID can
reach the file because neither is ever read.

### Two column names that do not match

The `Responses` tab header says **`received_at`**; the aggregator reads **`created_at`**
(`Code.gs.template:578` vs `aggregate.py:277`). One letter apart, nothing upstream checks
it. Passing the Sheet's own name through tallied **zero from twelve good rows** and printed
`counted 0` with no error — a dashboard of nothing, built from real data. CSV also has no
booleans, so `consent` arrives as the string `"TRUE"` where the tally needs the JSON boolean
`true`. Both mappings are explicit in the builder and asserted against the real aggregator.

**An empty export exits non-zero and writes nothing.** The page's own empty state is the
honest answer, and a committed snapshot of zeroes would replace it with a chart of nothing.

### Why this is manual, not automated

A workflow that reads the Sheet needs a Google service-account key committed as a
repository secret. On a public repository that is a real increase in attack surface, and
exporting the tab keeps every credential out of git entirely. At campaign volumes that is
the better trade. Revisit only if the weekly ritual becomes the bottleneck.

### What the first export actually contained (2 October 2026)

**The command was run against the real Sheet and it wrote nothing, which is the answer.**
The `Responses` tab holds its nine headers and **zero data rows** — the receipts recorded in
§27 were verification rows, deleted on 1 October. The builder printed:

```text
no accepted responses in …\Responses.csv (0 row(s) read, all rejected or non-consenting).
Nothing written: an empty poll renders as the page's own empty state, and a committed
snapshot of zeroes would replace that with a chart of nothing.
```

and **exited 1**. `data/delivery/poll_snapshot.json` still does not exist, which is what
`test_no_placeholder_tally_is_committed_anywhere` requires.

**So there is nothing to publish, and this is not a defect to be worked around.** The
dashboard on the live site is already the correct published state: the full control surface
at zero, §26's hatched tracks, and the line that says the figures read zero because nobody has
answered yet. When real responses arrive, the three commands above are the whole procedure.
Read §25a for how to take the export.

## 25. Retention for the Request Sheet — Decided 2 October 2026: Nothing Is Deleted

**This was the one item left with legal weight rather than quality weight. The owner decided
it on 2 October 2026: no automatic purge, no deletion period.** The request form collects a
name, an optional email address and a street address. That is real personal data, unlike the
poll, and **nothing deletes it**. The poll has a retention ceiling, a default, a daily trigger
and a purge; the request form has none of that.

**The reasoning, in full, because a decision recorded without its reasoning reads as an
omission:** a retained request is staff workflow data, and expiring it automatically would
delete needs nobody has actioned. That is the whole basis. It is a legitimate reason and it
is not a technical one.

**Two costs of that decision are permanent, and neither is softened by the reasoning:**

1. **Blanking a cell does not remove it from Sheet version history.** Any future deletion is
   still owner-side, and it stays recoverable until the owner prunes it. That is an owner
   action no code in this repository can reach or audit.
2. **The tab holds a supporter's name and street address indefinitely.** The liability grows
   every day that passes. The mitigations are staff access control and a manual pruning
   rhythm, and **neither is enforced or recorded by anything here** — there is no run log for
   a pruning process that does not exist in code.

**What must not be written about this state:** do not describe the request data as retained
"safely" or "by design" without saying who can read it and that nothing deletes it. That
wording is now in `AGENTS.md` and in `docs/GOOGLE_SHEETS_SETUP.md` §3 and §5, so the next
session inherits the decision *and* its cost rather than one without the other.

## 25a. Reading the Poll Sheet Without a Credential

The snapshot in §24 requires an exported `Responses.csv`. On 2 October 2026 that export was
taken without the owner exporting it by hand, and the route is worth recording because it
needs no credential and no service-account key in git.

**The short version: `/export?format=csv` works. It looks like it fails, and the failure is a
detection error, not a download error.**

```text
https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<TAB_GID>
```

- **Launch Brave against the real profile with a debugging port**, then drive it over CDP:
  `brave.exe --remote-debugging-port=9222`. The port is only read at launch, so this cannot
  attach to an already-running browser — §27's lesson applies again.
- **Find the Sheet ID from Drive search.** `drive.google.com/drive/u/0/search?q=<name>` lists
  every match in a `data-id` attribute. That avoids trusting a truncated ID from a table in
  this file. Poll responses: `1uvtVDggYj09jqmNMPwwgTIJkG4C9qbIuvh1zc58hlEM`.
- **Get the tab GIDs from the tab strip**, by clicking each tab and reading `location.hash`:
  `Responses` `2135492820`, `Comments` `732506979`, `Audit` `2113795227`. The attributes on
  the tab elements repeat and cannot be trusted one-to-one.
- **Navigate to the export URL and then look on disk.** The navigation is *abandoned* — the
  tab stays `about:blank` — and CDP reports `totalBytes: 0` and `state: "canceled"`. **Both
  are lies.** All three files were written anyway.

**Where the file lands is the part that costs time.** It does **not** go to the browser's
normal Downloads folder, and it ignored **both** `Page.setDownloadBehavior` and
`Browser.setDownloadBehavior` with an explicit `downloadPath`. On this machine Brave's
configured download directory is the **repository root**, so the exports appeared as
`APM poll responses - Responses.csv`, `data.csv`, `data (1).csv` and `data (2).csv` in
`D:\APMdeliverable`. **Check the filesystem rather than trusting the CDP event or the path you
asked for, and delete the stray files afterwards** — they are untracked and one of them sits
next to the source tree.

**Two routes that do not work, so they are not tried again:**

- **`gviz` is refused for a private Sheet**, even same-origin with credentials:
  `access_denied / ACCESS_DENIED — requires an OAuth credential`. It returns that as a 200.
- **`Network.getResponseBody` cannot read the CSV response** (`No resource with given
  identifier found`), and `Fetch` cannot intercept it at `ResponseReceived` —
  `Unsupported request stage`.

**And one that works, if you want to read the grid without writing anything:**
click once in the grid (**never double-click — that opens the cell editor**), `Ctrl+A`,
`Ctrl+C`, then `navigator.clipboard.readText()` after `Browser.grantPermissions` for
`origin: https://docs.google.com`. The result is TSV and it reproduces the tab exactly,
empty rows included. **It writes nothing to the Sheet**, which matters, because §27 records a
session where an automated click cleared `A1`.

## 26. The Dashboard at Zero — and What It Is Not

The dashboard renders its **complete control surface** while the poll has no responses:
both charts, the LGA dropdown, the registration-area dropdown, the Group lens, the scope
summary and the exact-counts table, with all 9 sectors, all 20 LGAs and every cell at an
explicit `0`.

**This is not a demonstration-data mode, and the distinction is the point.** A zero is a
true statement: nobody has answered yet. Every control is live and the same markup fills in
as real responses arrive, so nothing has to be removed later and nothing can later be
mistaken for a result. Fabricating non-zero counts would be a claim about what Bauchi
residents want; a zero makes no claim at all.

The line above the figures says so in words:

> Waiting for the first response. Every figure below reads zero because nobody has answered
> yet, not because the answer was no.

That is the same distinction the suppression floor depends on: an explicit zero means "nobody
chose this", a withheld cell means "too few to say", and the two are never drawn the same
way. Zero rows get a **hatched, dashed track** rather than a bare zero-width bar, because a
0-width bar beside a 0 reads as a *measured* nothing.

**A request to publish fabricated numbers was declined**, on the grounds that a chart of
invented counts on a live campaign site is indistinguishable from a real one and would be
visibly false to anyone who downloaded the Sheet and tallied it. The zero scaffold was built
instead: it satisfies "show the dashboard at full capacity" without asserting a single
response that did not happen.

### Two defects in the first render

The `snapshot is None` branch and the `total <= 0` branch described the same state in two
different ways, so the page's own description depended on which code path ran. They are now
one function. And the zero bars nested the label inside a wrapper, which collapsed the
existing three-column `.poll-bar` grid and printed `Water0`, `Roads0` — the JS-built chart
uses label/track/value as direct children, so the scaffold now mirrors that structure.

### Two tests were replaced, not deleted

One asserted the empty poll contained **no bars at all**. It was protecting the right
property — no seeded or placeholder results — by forbidding the whole surface, and that is
exactly what made the site look like it had no dashboard. It now asserts what actually
matters: every bar fill is `0%` wide, every published value is `0`, and no reporting date is
fabricated. The other now asserts the zero scaffold never claims a response exists.

## 27. Deployment Session Notes — 1 October 2026

Procedural, because both were non-obvious and each cost a wrong turn.

**A standalone Apps Script project cannot work.** Both endpoints call
`SpreadsheetApp.getActiveSpreadsheet()`, which returns `null` outside a script *bound* to a
Sheet — and it fails as a bare `null` error that looks like a code bug. Create the Sheet
first, then **Extensions → Apps Script from inside it**.

A standalone `APM Poll` project created before this was understood sat on the account for
part of the session; the **owner removed it**. The two live scripts are `APM poll endpoint`
(`1dJTeFKEompj7tD0MXlLi7BqMO9c_vZLr3FPnMBhAf-DvqIdq2pMLcTTv`) and
`APM requests endpoint` (`1hoBdGyYHQCxTfqN7AmzuUvJZ6l61apfvUnidO2hDmbfjtq5qZS2UKHPI`).
Their `/exec` URLs are in `src/dashboard/render.py` as `POLL_ENDPOINT` and
`REQUEST_ENDPOINT`, and in the rendered pages. **Target any future run by project ID, never
by "the first script.google.com tab"** — doing that ran `setupSheets` against the wrong
project during this session.

**`clasp push` refuses until the Apps Script API is enabled** at
`script.google.com/home/usersettings`, with the error naming the URL. That toggle is an
account-level setting; the owner clicks it.

**`.gitignore` named only one endpoint folder.** It listed
`docs/apps-script/.clasp.json` but not `docs/requests-script/.clasp.json`, so the request
endpoint's script ID was untracked-but-not-ignored — one `git add .` from committing a live
deployment ID to a public repository. Replaced with a `**/.clasp.json` glob and an explicit
negation for the committed examples, so a third endpoint folder cannot repeat it.

**The generator writes CRLF on Windows.** `build_code_gs.py` emitted 554 CRLF lines against a
committed LF blob — identical content, permanently "modified", and a push of bytes nobody
reviewed. This is the same class as the source-snapshot manifest mismatch in §20. **It is
still unfixed at source**: normalise after regenerating, or make the generator write LF.

**Clear data through the Name Box, not by clicking.** An automated click computed from a
wrong bounding box cleared cell `A1` — the `response_id` header — instead of the data rows.
Caught on a screenshot and restored. Select the range by typing `A2:I9` into
`input.waffle-name-box`; the sheet tab strip is `div.docs-sheet-tab`.

**Selecting the wrong Apps Script project is easy** and runs the function against the wrong
Sheet. Always target by project ID, never "the first script.google.com tab".

**For driving a visible browser:** this session's Playwright MCP runs `--headless`
(`~/.config/opencode/opencode.json`), so its window is invisible and cannot be pointed at an
already-running Brave — the remote-debugging flag is only read at launch. A second Brave on
`--remote-debugging-port=9222` attached over CDP with `playwright-core` worked and was what
drove the Sheets and Apps Script UI.

## 28. Session Commit Log

```text
8a530ba  feat(site): About page, live poll endpoint, and the CORS fix that made it work
0197366  feat(requests): connect the request endpoint, and enforce the LGA/area pair in the UI
9ad3d82  chore(pages): rebuild after clearing the verification rows from both Sheets
643443f  fix(index): list the About page on the landing page, and derive the page count
a80078b  feat(poll): build the published snapshot from the poll Sheet
6925f7f  feat(poll): render the full dashboard at zero before anyone has answered
```

All six are **pushed**; `main` is in sync with `origin/main`.

### The recurring lesson

Four of these were the same failure in different clothes: **something true of the data
disagreed with something written beside it, and nothing compared the two.**

- "Five commitments" over eight rows; five listed sectors, four of which were not in the file
- "Five pages, one record" beside a nav of seven
- `received_at` vs `created_at` tallying zero from twelve good rows
- a `.gitignore` that named one of two script IDs

In every case the fix was to **derive the statement from the data** and add a test that
compares the two. Writing the number again next time is what reintroduces it.

## 29. Verification Session — 2 October 2026

**No feature work. One item was measured, two owner decisions were recorded, and the
measurement is why nothing was published.**

### The poll has no responses

The `Responses` tab was read through a real logged-in browser (§25a). Nine headers, **zero
data rows**. The receipts in §27 were verification rows, deleted on 1 October. Running the
documented command against that real export:

```text
python src/poll/build_snapshot.py …\Responses.csv
  → no accepted responses … (0 row(s) read, all rejected or non-consenting).
  → Nothing written …                                     exit 1
```

**A snapshot of zeroes was not committed, and committing one is refused on purpose.** The
page's own empty state is the honest published state, and §26's zero scaffold is already
serving it. So "publish the results" is not done — it is **blocked on responses existing**,
which is a different thing and should not be written up as an outstanding task.

### Two decisions recorded

| Decision | Outcome | Where it is recorded |
|---|---|---|
| Request-Sheet retention | **No automatic purge, no deletion period** | `HANDOFF.md` §25, `AGENTS.md`, `docs/GOOGLE_SHEETS_SETUP.md` §3 and §5 |
| Native Hausa review | **Complete** (owner-attested, 2 Oct 2026) | `docs/HAUSA_REVIEW.md`, `AGENTS.md`, `README.md` |

Both were recorded **with their costs**, not as closed boxes. The retention decision keeps
the two permanent costs visible (Sheet version history outlives a blanked cell; the tab holds
a name and a street address indefinitely). The Hausa decision keeps the provenance disclosure
and the instruction to record any change the reviewer made to the ~11 strings the AI pass
deliberately left alone. **A decision logged without its cost is the same defect as a number
written twice.**

**No reviewer's name is recorded, because none was given, and none may be invented.**

### What did not change

- No code changed. **402 tests pass**, one skipped (Playwright).
- No snapshot exists. `data/delivery/poll_snapshot.json` is still absent.
- The request endpoint is untouched — the decision was about *policy*, not about adding a
  purge nobody wanted.
- The AI-drafted provenance disclosure stays in every place it shipped. The strings are
  machine-drafted and machine-corrected; a human reviewed them afterwards, which is a
  different claim and is worded differently.
- **Nothing has been committed.** Per §Restart step 6, push authorisation is not standing.

## 30. The Demo Video — Built, Published, and Given an Expiry Date

**A 30-second captioned recording of the live site, in two cuts, offered for download from
`about.html`.** Built entirely by script in `tools/`, so it can be re-shot when the site
changes; see the README's *Demo video* section for the commands.

| Cut | File | Format | Length |
|---|---|---|---|
| Desktop | `assets/brand/demo-16x9.mp4` | 1920×1080, H.264 + AAC, 30.2 s | 4.1 MB |
| Phone | `assets/brand/demo-9x16.mp4` | 1080×1920, H.264 + AAC, 26.7 s | 4.0 MB |

**It is a registered asset, not a file dropped in `docs/`.** Both cuts carry
`asset_register.csv` rows with a SHA-256 that `validate_data()` re-hashes on every build,
and they are published through `ASSET_FILES`, so the weekly cron's existing
`git add docs/assets/` ships them without anyone editing the workflow. A test asserts that
the href on the page, the copy under `docs/assets/brand/` and the register row agree — the
first place on the site where a stale path could 404 silently.

**The audio is generated, not licensed.** `tools/make_music.py` synthesises the instrumental
from oscillators on the build machine, so there is no third-party author and therefore no
rights claim to clear. The empty-poll stretch ducks the pad and drops the kick outright;
measured, its beat-pulse ratio is 1.01 against 1.90–2.31 elsewhere, which is the only reason
the hush is audible at all.

### The two guardrails, and how they are enforced

- **Nothing was submitted.** The capture shows the vote button and never presses it, and
  `tools/check_no_submission.mjs` reads the live `Responses`, `Comments` and `Audit` tabs
  and exits non-zero if any holds a row. Run after any re-shoot. Verified on this capture:
  all three tabs hold headers only.
- **The zero-state claim has an expiry, so it is bounded on the page.** The caption reads
  *"nobody has answered yet"*, true only until the first response. The About section carries
  the recording date and the poll's state at that moment, and
  `test_the_demo_video_states_when_it_was_recorded` fails the build if that line is removed.
  **Re-shoot when the poll has responses**, or the video asserts something false on the
  owner's behalf in every feed it is shared into.

### Two defects worth carrying forward

1. **The captions ran about a second and a half late on every shot.** The recorder marked
   shots *after* their settle hold, so each caption inherited the next shot's wait. It now
   logs a mark at the instant the frame changes, and the caption windows, the music arc and
   the head trim are all derived from that log. **Nothing about the edit is hard-coded**,
   because a take drifts by seconds between runs with the network — today's atlas click
   landed at 14.8 s and an earlier take's at 12.6 s.
2. **The README's own data table was stale and nothing compared it.** It said 12 registered
   assets after two more were registered. `ReadmeInventoryTests` now walks that table and
   recomputes every figure from the file it cites; verified by putting the wrong number back
   and watching it fail.

### Also this session

- **`ffmpeg` was a dangling winget shim** pointing into a package folder that did not exist —
  the same failure class as the `rg.exe` shim in §27. Installed; `build_demo.py` resolves the
  binary inside the package directory rather than trusting PATH.
- **8 new AI-drafted Hausa strings** ship with the video section. They are **not**
  native-speaker reviewed, and the provenance disclosure now says so.

---

## Restart and Resume Procedure

1. Start a new session from `D:\APMdeliverable` and follow **Start here next session**
   at the top of this file. That block is the current state; this list is the mechanics.
2. **Verify the baseline before changing anything:**
   ```bash
   cd D:\APMdeliverable
   python -m unittest discover -s tests -q        # expect 402 OK (1 skip: Playwright)
   node docs/apps-script/test_endpoint.mjs        # expect 111/111 checks passed
   node docs/requests-script/test_endpoint.mjs    # expect 215/215 checks passed
   python src/dashboard/render.py                 # expect seven page sizes
   ```
   A drop in any suite means something regressed. Investigate before proceeding. Both
   endpoint harnesses are wired into the Python suite as well, so `unittest discover` runs
   them too — but run each directly when you have touched its `Code.gs`.
3. **Confirm the preserved local work is still untracked, and do not touch it:**
   `.evals/2026-W39.md`, `.evals/2026-W39_sample100_filled.csv`,
   `data/human_review/filled/`, `.playwright-mcp/`. Never `git reset`, `git clean`,
   permanent `git stash`, or `git add .` over them. **Corrected 2 October 2026:** this list
   used to name `src/aggregation/aggregate.py`, which is now tracked and clean — it was
   preserved local work in an earlier session and has since been committed. Verify with
   `git status --porcelain --untracked-files=all` rather than trusting the list.
4. **The one thing left is publishing the poll snapshot, and it is blocked on data, not on
   work.** Both endpoints are deployed and verified (§21); the dashboard renders its full
   layout at zero (§26) and will stay that way until a snapshot is committed. As of
   2 October 2026 the `Responses` tab is empty, so there is nothing to publish (§24, §29).
   Everything else about the poll is done. See §24 for the three commands and §25a for how
   to take the export.
5. **To change the endpoint code, edit `Code.gs.template` and regenerate** — never `Code.gs`
   directly, or the next build discards the change:
   ```bash
   python docs/apps-script/build_code_gs.py   # template + lga_wards.csv -> Code.gs
   clasp push                                 # from docs/apps-script/
   ```
   Then re-run every suite in step 2. `clasp` 3.4.1 is installed globally and `clasp login`
   is authorised for `batesthommie@gmail.com` as of 1 October 2026. **After regenerating,
   normalise the line endings** — the generator writes CRLF on Windows and the committed
   blob is LF (§27):
   ```bash
   python -c "import pathlib,sys; [pathlib.Path(p).write_bytes(pathlib.Path(p).read_bytes().replace(b'\r\n', b'\n')) for p in sys.argv[1:]]" docs/apps-script/Code.gs
   ```
   Then confirm `git status docs/*/Code.gs` is silent before pushing.
6. **Commit only after the owner explicitly asks.** Push was authorised on 26 September
   2026 and again on 1 October 2026, when the owner asked for both endpoints to go live and
   for the session's work to be committed ahead of the next one. It is still **not**
   standing authorisation. `main` is currently in sync with `origin/main` (§28).
7. Both endpoints are deployed and live. Do not change a bound script in place: edit the
   template, regenerate, `clasp push --force`, then re-run `setupSheets` only if the tab
   layout changed. A wrong `/exec` URL is worse than a disabled build, because it discards
   submissions silently.
   build because it discards votes silently.
8. If the boundary snapshot ever needs re-fetching, note that
   `python -m src.ingestion.lga_boundaries` refuses to overwrite an existing snapshot
   without `--force`, and that the snapshot's SHA-256 is recorded in both
   `source_register.csv` and `data/derived/lga_paths.json` - re-fetching changes the hash
   and both records must be regenerated together.

### What the owner still has to decide

**Two of the three items from the 1 October handoff were decided on 2 October 2026. One
remains, and it is a question of timing rather than of policy.**

- ~~**Retention for the request Sheet.**~~ **Decided 2 October 2026: nothing is deleted.**
  §25 carries the reasoning and the two permanent costs. The poll's comment column is
  already handled — default 180 days, 365-day ceiling, daily purge trigger installed.
  Google retains IP addresses in Apps Script execution logs regardless of what either Sheet
  stores, and that remains not fixable in code.
- **Whether to publish poll results, and when — still open.** The machinery is built and
  tested (§24) and **was run against the real Sheet on 2 October 2026 against an empty
  `Responses` tab**, so it wrote nothing. The first real snapshot should be taken once there
  are enough responses that the charts are worth showing, and it will be almost entirely
  suppressed below a floor of 5. **This is not a bug to fix and not a gap to fill by hand:**
  committing a snapshot of zeroes is refused by the builder and by a test.
- ~~**A native Hausa speaker.**~~ **Done.** The owner reports the native-speaker review
  complete on 2 October 2026, covering `docs/HAUSA_REVIEW.md` plus what was added on
  1 October. The AI-drafted provenance disclosure stays. If that reviewer changed any of the
  ~11 strings the AI pass deliberately left alone, **record the change in
  `docs/HAUSA_REVIEW.md`** — otherwise that file describes a state that no longer ships, which
  is the defect this repository keeps meeting in other files.

### Names and titles are retained

The owner confirmed on 1 October 2026 that **"Dr." stays** in all public copy, and that
`Abdulkadir Ahmad (Hammayo)` remains the named contributor with his existing role line. No
placeholder, no invented sponsor content, no added amounts or numbers — the rules in
`AGENTS.md` under "Contributor credit rules" are unchanged and still enforced.

### Closed out this session

- The stray standalone `APM Poll` project on the Google account has been **removed by the
  owner**. It could never have worked: `getActiveSpreadsheet()` returns `null` outside a
  Sheet-bound script (§27).
- All verification rows and probe rejections were deleted from the poll and request
  Sheets, and from all four `Audit` tabs. Headers are intact.

### If you only have time for one thing

Run S1's, S2's, S3's and S4's guards against a change you made:

```text
python -m unittest tests.test_bilingual tests.test_header_brand tests.test_site_structure tests.test_atlas_map -v
```

These cover the defects that are invisible in a visual check — untranslated strings,
Hausa pasted into an English column, a missing emblem hash, an invert filter creeping
back, invented sponsor content, a duplicate `const` that would disable every script on a
page, a nav link pointing at a page that was never generated, a cron that would publish
stale subpages, a seam tearing between LGAs, quantization below the 3 dp floor, and a
language switch that empties the map.

The complete project contract remains in `IMPLEMENTATION_PLAN.md`. This handoff is
the operational starting point for maintainers and deployment.
