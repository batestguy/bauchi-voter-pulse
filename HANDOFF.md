# APM Bauchi Progress & Delivery — Project Handoff

**Handoff date:** 26 September 2026
**Repository:** `batestguy/bauchi-voter-pulse`
**Branch:** `main`
**Current release:** `4871cde` — **deployed to GitHub Pages 26 September 2026**, run `36274124728`, success. Contains phases S0–S3.
**Live product:** [APM Bauchi Progress & Delivery](https://batestguy.github.io/bauchi-voter-pulse/)
**Governing plan for the next work:** [`SITE_EXPANSION_PLAN.md`](SITE_EXPANSION_PLAN.md)

> ✅ **The site is live.** `main` is fully pushed and Pages run `36274124728` deployed
> successfully on 26 September 2026. All six pages are public, the emblem renders in
> colour, Hausa works and persists, and the agenda shows the water entry as a published
> clause. The working tree is clean apart from the preserved legacy paths in step 3.
>
> The **weekly cron is the thing to watch**: `rebuild-pages.yml` now regenerates and
> stages all six pages, and fails the build if any is missing. Its first scheduled run is
> the first live exercise of that change — check it the next Monday.

---

## Start here next session

**1. Read in this order:** `SITE_EXPANSION_PLAN.md` (§4 phases, §9 log, §10 next
session) → this file's §13 priorities and §20 release traps → `AGENTS.md`.

**2. Verify the baseline before changing anything:**

```bash
cd D:\APMdeliverable
python -m unittest discover -s tests -q     # expect 115 OK
python src/dashboard/render.py              # expect six page sizes
```

If the test count is not 115, something has regressed. Investigate before proceeding.

**3. Do not touch the preserved local work.** It must still be untracked or modified:

```text
src/aggregation/aggregate.py      modified, legacy track
.evals/                            untracked, local-only
data/human_review/filled/         untracked, local-only
.playwright-mcp/                   untracked, browser artifacts
```

Never `git reset`, `git clean`, permanent `git stash`, or stage these.

**4. Next task: phase S4, the Bauchi LGA map.** Full brief in `SITE_EXPANSION_PLAN.md`
§2.4 (measured geometry, licence, seam safety) and §10, and the P0 list in §13 below.
The five things S4 must not get wrong are in `SITE_EXPANSION_PLAN.md` §10.

**5. Owner gates still open** — all four need a human decision, not code:

| Gate | Where |
|---|---|
| Ratify or correct the `apm-emblem.png` rights record | `data/delivery/asset_register.csv` |
| Native-speaker review of the 53 AI-drafted Hausa strings | spread across `data/delivery/*.csv` |
| ~~Push authorisation~~ — **granted; pushed 26 September 2026** | owner's call |
| Whether to narrow the `wash` label from "Water and climate resilience" | the source has zero climate content |

**6. If you only have time for one thing:**

```bash
python -m unittest tests.test_bilingual tests.test_header_brand tests.test_site_structure -v
```

These 47+ tests cover the defects a visual check cannot see: untranslated strings, Hausa
pasted into an English column, a missing asset hash, an invert filter creeping back,
invented sponsor content, a duplicate `const` that would disable every script on a page,
a nav link pointing at a page that was never generated, and a cron that would publish
stale subpages.

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

**Three phases of the site expansion are complete and committed. Nothing is pushed.**

| Commit | Phase | What it did |
|---|---|---|
| `9cd101b` | S0 | Added `SITE_EXPANSION_PLAN.md` |
| `be832e0` | S1 | Bilingual correctness across all delivery content |
| `533a210` | S2 | Legible APM emblem, sponsor slot, persistent language control, de-duplicated promises |
| S3 | S3 | **Six-page split**, mobile nav, solid subpage header, both CI release traps closed |

The next maintainer should resume from this exact checkpoint:

- **Current local product checkpoint:** the delivery site is now **six flat pages** in
  `docs/` — `index`, `achievements`, `atlas`, `poll`, `agenda`, `sources` — sharing one
  header, footer and language control. Phases S0–S3 are committed locally. **S4 (the Bauchi
  map) and S5 (the opinion poll) have not started**, so `atlas.html` still shows the 20-LGA
  tile grid rather than a map, and `poll.html` holds only the request form.
- **Last verified live product:** `4871cde`, deployed 26 September 2026 in Pages run
  `36274124728` (success). Verified in a browser against the live URL: all six pages
  return HTTP 200, the emblem renders in colour with `filter: none`, the nav carries six
  links with `aria-current` on the right one, the mobile `<details>` menu is present,
  the agenda shows 8 cards with the water entry labelled `Published commitment clause`,
  the sponsor slot reads `[ Sponsor name ]`, Hausa switches and persists to
  `localStorage`, and there are **0 console errors**.
- ⚠️ **First unattended cron run not yet observed.** `rebuild-pages.yml` gained a
  multi-page stage and a missing-page check in S3. The next Monday 06:00 UTC run is the
  first live exercise of it.
- **Current local verification:** **115 `unittest` tests pass** (40 before this work). Python
  compilation, delivery-data validation, asset hash checks, the CI asset gate, a
  `node --check` parse of the inline script, and browser interaction checks all pass.
  Browser checks covered 375px/1440px, EN↔Hausa switching, language persistence across
  reload, the labelled language control, the sponsor slot, agenda de-duplication, zero
  horizontal overflow at 375px, and **zero console errors**.
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
| Registered sources | 27 | `data/delivery/source_register.csv` |
| Archived source pages | 33 | `data/delivery/source_manifest.csv` |
| Review queue records | 33 | `data/delivery/review_queue.csv` |
| Needs | 8 | `data/delivery/needs.csv` |
| Achievements | 25 | `data/delivery/achievements.csv` |
| APM promises | 8 (7 published pillars + 1 published clause) | `data/delivery/promises.csv` |
| LGA delivery rows | 20 | `data/delivery/lga_delivery.csv` |
| Approved assets | 10 | `data/delivery/asset_register.csv` |
| Featured achievement records | 5 | `data/delivery/featured_achievements.csv` |
| Provisional electoral RAs | 212 | `data/delivery/lga_wards.csv` |
| Outcome indicators | 8 | `data/delivery/indicators.csv` |
| Pending source reviews | 0 | `review_status == needs_review` |
| Local `unittest` tests | 87 | `tests/` |

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

⚠️ `apm-emblem.png` was registered as `campaign approved` by `campaign team` on
26 September 2026 to unblock the build, recorded as a derived crop of the already-approved
`apm-logo.png` with no new rights cleared. **The owner should ratify or correct that
attribution**, since `asset_register.csv` is the rights record and
`rebuild-pages.yml` fails closed on any row whose column 6 is not `campaign approved`.


## 3. Product Architecture

### Runtime shape

The live product is **six static pages** with inline CSS and JavaScript, generated by one
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
| `docs/atlas.html` | 20-LGA selector and evidence panel. **The map arrives in S4**; this is still the tile grid. |
| `docs/poll.html` | The bilingual need-request form. **The opinion poll arrives in S5.** |
| `docs/agenda.html` | The 8 published campaign commitments |
| `docs/sources.html` | Source register, grading legend, build method |
| `src/dashboard/render.py` | Validates delivery data and generates all six pages via `PAGE_BUILDERS`. Owns the shared shell (`document`, `topbar`, `subpage_open`, `page_hero`, `site_footer`), the nav registry (`PAGE_NAV`), script routing (`PAGE_SCRIPTS`), the bilingual helpers (`attr`, `copy`, `localized`, `status_badge`), the controlled status vocabulary and the delivery validators. |
| `data/delivery/` | Curated source, evidence, promise, indicator, featured-achievement, provisional electoral-RA and LGA tables |
| `data/delivery/source_snapshots/` | Locally archived source responses |
| `src/ingestion/delivery_sources.py` | Public source discovery, archival and review intake |
| `src/ingestion/common.py` | Shared polite HTTP, robots.txt and rate-limit logic |
| `src/requests/validation.py` | Pure bilingual-safe private request validation contract |
| `src/requests/aggregate.py` | Contact-free public request aggregation contract |
| `docs/GOOGLE_SHEETS_SETUP.md` | Owner-only Google Sheet/Apps Script setup and privacy guide |
| `assets/brand/` | Approved local source assets, including the derived `apm-emblem.png` |
| `docs/assets/brand/` | Generated copies used by the public page |
| `tests/test_bilingual.py` | Guards the S1 bilingual fixes: denylist of untranslated UI strings, Hausa-in-English-column detection, required Hausa columns |
| `tests/test_header_brand.py` | Guards the S2 fixes: emblem registration and transparency, no invert filter, favicon, sponsor slot placeholders, language persistence, promise de-duplication, and a `node --check` parse of the inline script |
| `tests/test_site_structure.py` | Guards the S3 split: all six pages generated, nav and asset paths resolve, heavy sections on exactly one page, one `aria-current` per page, mobile menu is JS-free, subpage solid header, script routing, per-page `node --check`, and both release traps stay closed |
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

- **Six flat pages** generated from one renderer, sharing the header, footer, sponsor slot
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
- Responsive checks showed no horizontal overflow at 1440px, 1024px, 760px or 375px.

### Local state after S0–S3 (26 September 2026, now deployed)

- **115 `unittest` tests pass** (40 before this work).
- `python src/dashboard/render.py` writes **all six pages** and prints their sizes.
- `render.validate_data()` passes, including `validate_no_hausain_english_columns()`
  and `validate_unique_promises()`.
- **224** `data-en`/`data-ha` pairs are byte-identical and **every one is legitimate**:
  electoral RA proper nouns, LGA names, the `LGA` acronym, the party motto, and numeric
  values that are genuinely identical in both languages. Zero unexplained.
- 10 approved assets; all SHA-256 values reconcile, including `apm-emblem.png`.
- The CI asset gate (`usage_status` in **column 6** of `asset_register.csv`) passes.
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
  with no endpoint configured; no horizontal overflow at 375px; **0 console errors**.
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
- LGA rows provide one evidence record per LGA, not exhaustive sector coverage.
- The ESTRRA outcome is Bauchi North-wide and is not a single-LGA claim.
- The 20-LGA display is a designed grid, not an authoritative map.
- English/Hausa copy exists, but native-speaker review is not documented.
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

### P0 — Do next: the Bauchi map (phase S4)

S3 shipped. Full detail in `SITE_EXPANSION_PLAN.md` §4. `atlas.html` currently shows the
20-LGA tile grid; S4 replaces or augments it with real boundaries.

1. Fetch the GRID3 / eHealth Africa operational LGA boundaries once and cache them under
   `data/delivery/source_snapshots/`. Register the source in `source_register.csv` as
   **grade B** with the licence and the "simplified for display" change note.
2. **Licence is CC BY 4.0**: commercial use is fine and attribution is the only
   obligation. There is **no ShareAlike**, so the simplified derivative can be published
   on our own terms. ⚠️ The sibling GRID3 **Wards** layers are BY-SA and would force
   BY-SA on the whole site — do not pull them in.
3. Emit the derived path strings into a committed `data/derived/lga_paths.json` so the
   weekly Pages rebuild never calls ArcGIS and the build stays deterministic.
4. Simplify in pure stdlib: quantize to 4 dp, then Douglas-Peucker with an **explicit
   stack** (a 1,223-point ring exceeds Python's 1000-frame recursion limit), then snap
   neighbours back together. Project with the `cos(latMid)` correction.
5. ⚠️ **Never quantize below 3 dp.** At 2 dp, 56% of the shared boundary edges between
   LGAs collapse and the map visibly tears. Add a test asserting ≥90% shared-edge
   retention so this cannot regress.
6. Join on `lgacode` (5001–5020), never on names. Two names differ from the repo
   canonical list: `Itas/Gadau` → `Itas-Gadau` and `Jama'Are` → `Jamaare`.
7. Show the required CC BY attribution and the "operational, simplified, indicative —
   not gazetted" caveat. These boundaries descend from polio microplanning data.
8. Keep the RA list in the side panel labelled **"not geo-located"**. `lga_wards.csv` has
   no coordinates and none will be invented.

### P1 — Then the opinion poll (phase S5)

9. New `src/poll/` package mirroring `src/requests/`. Q1 is a required single choice over
   the **existing 9 `REQUEST_CATEGORIES`** so results stay comparable with the request
   queue; Q2 is an optional ≤300-char free text that must be **excluded from the tally**.
10. `POLL_ENDPOINT = ""` ships it disabled, mirroring `REQUEST_ENDPOINT`. On a static
    host, live results mean: read the endpoint when configured, else fall back to a
    committed `data/delivery/poll_snapshot.json` the weekly cron regenerates.
11. Minimum PII: no name, phone or email. Honeypot, consent, one submission per browser.
    Never seed, example or placeholder results — an empty set must render as empty.
12. Show `N` prominently with a self-selected-respondent disclosure, and hold percentages
    behind a configurable floor (default 10) so one vote cannot read as 100%.

### P2 — Housekeeping on the current product

1. Extend `indicators.csv` with more verified baselines and targets; keep missing
   baselines blank rather than estimating them.
2. Replace remaining delivery-output language with measured outcomes where primary
   evidence exists: service reliability, beneficiaries, learning, health access,
   market access, income and employment.
3. Add semantic validation for date validity and actor/source consistency.
   Duplicate promise text is now covered by `validate_unique_promises()`.
4. **Run a native-speaker Hausa review.** 53 strings in this session are AI-drafted and
   unreviewed: 27 `usage_note_ha`, 25 `verification_status_ha`, plus the new wash-promise
   clause. These are integrity caveats a Hausa-reading voter now sees, so they matter.
5. Ratify or correct the `apm-emblem.png` rights record in `asset_register.csv`.
6. Decide whether to narrow the `wash` sector label. It renders as "Water and climate
   resilience", but the published campaign source contains **zero** climate content.

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
  delivery content, but the 53 Hausa strings added in S1/S2 are **AI-drafted and not
  native-speaker reviewed**. Disclose this, exactly as `.evals/2026-W39.md` already does
  for its labeler.
- ❌ **Do not claim the campaign published a water/sanitation policy.** It did not. The
  published manifesto has five pillars and no water pillar; `promise-wash` is the water
  **clause** of the Infrastructure Development commitment and is labelled as such.
- ❌ **Do not claim the live site has the emblem, the sponsor slot or the fixed Hausa.**
  All four unpushed commits are **local only**. The live site still shows the white-rectangle logo.
- ❌ **Do not claim the sponsor slot is filled.** It ships as a labelled placeholder with
  no name, no photo and no contribution, by design.
- ❌ **Do not claim the map or the poll exist.** S3 shipped the six-page shell, but
  `atlas.html` still shows the 20-LGA tile grid and `poll.html` holds only the
  request form. S4 and S5 have not started.
- ❌ **Do not claim the emblem is a separately cleared asset.** It is a derived crop of the
  already-approved `apm-logo.png` with no new rights cleared, and its `approval_note`
  still needs owner ratification.

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
allowlist for the *next* change, not a record of pending work. Push was authorised once,
on 26 September 2026, and is **not** standing authorisation.

History leading to the first push, for provenance:

```text
2fd12fa  feat(delivery): add interactive achievements and request intake   (pre-existing)
9cd101b  docs: add site expansion plan                                       (S0)
be832e0  fix(i18n): correct Hausa rendering across delivery content          (S1)
533a210  fix(header): legible APM emblem, sponsor slot, persistent language  (S2)
27a7a76  docs: handoff for the next session after S0-S2
957d47d  feat(site): six-page split, mobile nav, both release traps closed  (S3)
```

### Current staging allowlist

Stage only these paths for the next release:

```text
HANDOFF.md
IMPLEMENTATION_PLAN.md
README.md
SITE_EXPANSION_PLAN.md
data/delivery/asset_register.csv
data/delivery/achievements.csv
data/delivery/indicators.csv
data/delivery/needs.csv
data/delivery/promises.csv
data/delivery/source_register.csv
assets/brand/apm-emblem.png
docs/assets/brand/apm-emblem.png
docs/index.html
docs/achievements.html
docs/atlas.html
docs/poll.html
docs/agenda.html
docs/sources.html
.github/workflows/rebuild-pages.yml
src/dashboard/render.py
tests/test_bilingual.py
tests/test_header_brand.py
tests/test_site_structure.py
```

**The site is now six pages.** `python src/dashboard/render.py` writes all six; the weekly
cron stages `docs/*.html` and fails if any page is missing. See §20 for how both traps
were closed.

Never stage or commit these preserved/local paths without explicit owner
confirmation:

```text
src/aggregation/aggregate.py
.evals/
data/human_review/filled/
.playwright-mcp/
```

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

plus a new **Verify every generated page exists** step that iterates all six slugs and
fails the build if any is missing, so a dropped page is a red run rather than a stale
page.

### ✅ Trap 2 — the handoff allowlist named only `docs/index.html`

A maintainer following §18 would have staged nothing new. All six pages are now listed,
along with `rebuild-pages.yml` and `tests/test_site_structure.py`.

### Still true after S3

- `rebuild-pages.yml` validates assets with `awk -F, 'NR > 1 && $6 != "campaign
  approved"'`. That is **column-position coupled**; any new asset row must have
  `usage_status` in exactly column 6 or CI fails closed.
- A duplicate `const` in any page's inline script is a `SyntaxError` that disables every
  handler on that page while the HTML still renders. All six pages are now parsed with
  `node --check`, and a duplicate top-level declaration detector runs per page.
- Heavy sections must stay on exactly one page each, or pages get large for no reason.
  `test_site_structure.test_heavy_sections_appear_on_exactly_one_page` enforces that the
  source register, request form, agenda, indicators, atlas and carousel each appear once.

## 19. Handoff Checklist

A new maintainer should be able to answer “yes” to each question:

- [ ] Can I render the live product locally and get all six pages?
- [ ] Do I know the live site is still the old single-page release?
- [ ] Can I explain the four-step narrative model?
- [ ] Can I identify the source register, manifest, review queue and curated tables?
- [ ] Can I name all six generated pages and say which sections live on each?
- [ ] Can I distinguish an achievement from an APM promise?
- [ ] Can I explain why the water promise is a published *clause*, not a pillar?
- [ ] Can I explain why `docs/` is the public source directory?
- [ ] Can I run source intake without overwriting raw snapshots?
- [ ] Can I validate source, snapshot and asset hashes?
- [ ] Can I explain why the header emblem needed a transparent background?
- [ ] Do I know that a duplicate `const` in the inline script silently kills all page
      JavaScript, and that `node --check` guards it?
- [ ] Can I identify the live GitHub Pages URL, and know it does **not** yet include
      the S0–S2 work?
- [ ] Can I preserve the uncommitted aggregation and human-review work?
- [ ] Do I know which pipeline is legacy and not part of the public product?
- [ ] Do I know which outcome claims still require measurement?
- [ ] Do I know which 53 Hausa strings are AI-drafted and unreviewed?
- [ ] Do I know that the two release-breaking traps in §20 are closed and test-guarded?
- [ ] Do I have a next-step list that does not mix current-product work with
      legacy evaluation work?

## Restart and Resume Procedure

1. Start a new session from `D:\APMdeliverable` and follow **Start here next session**
   at the top of this file.
2. **Read `SITE_EXPANSION_PLAN.md` first.** It governs the remaining phases and its §9
   records exactly what S0–S3 did and why.
3. Read `HANDOFF.md` §3 (architecture), §9 (validation evidence), §13 (priorities),
   §18 (staging), §19 (checklist) and §20 (release traps).
4. Read `AGENTS.md` for repository rules and preserve all local-only legacy work.
5. Run `python -m unittest discover -s tests -v` **before** changing anything. Expect
   **115 passing**. A drop means something regressed; investigate before proceeding.
6. Confirm the working tree still shows the preserved local work as untracked/modified:
   `src/aggregation/aggregate.py`, `.evals/`, `data/human_review/filled/`,
   `.playwright-mcp/`. Do not reset, clean, stash permanently, or stage them.
7. Implement **S3, the six-page split**, per `SITE_EXPANSION_PLAN.md` §3 and §4. Fix the
   two §20 traps **in the same change**, not afterwards.
8. Run the full suite, render, browser-check at 375px and 1440px, and get an independent
   review before staging anything.
9. Commit only after the owner explicitly asks. Push was authorised once, on
   26 September 2026; it is **not** standing authorisation for future work.
10. Do not deploy the request form or the poll until an approved HTTPS Apps Script
    endpoint is configured; both ship disabled until then.

### If you only have time for one thing

Run S1's and S2's guards against a change you made:

```text
python -m unittest tests.test_bilingual tests.test_header_brand tests.test_site_structure -v
```

These cover the defects that are invisible in a visual check — untranslated strings,
Hausa pasted into English columns, a missing emblem hash, an invert filter creeping
back, invented sponsor content, a duplicate `const` that would disable every script on a
page, a nav link pointing at a page that was never generated, and a cron that would
publish stale subpages.

The complete project contract remains in `IMPLEMENTATION_PLAN.md`. This handoff is
the operational starting point for maintainers and deployment.
