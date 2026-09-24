# APM Bauchi Progress & Delivery — Project Handoff

**Handoff date:** 24 September 2026
**Repository:** `batestguy/bauchi-voter-pulse`
**Branch:** `main`
**Current release:** `22a8914` — `feat(delivery): complete Bauchi LGA evidence coverage`
**Live product:** [APM Bauchi Progress & Delivery](https://batestguy.github.io/bauchi-voter-pulse/)

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

## 2. Release State

### Live deployment

GitHub Pages reports the site as public and built from `main` with `/docs` as the
source directory. The most recent Pages deployment completed successfully on
24 September 2026.

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
| Needs | 7 | `data/delivery/needs.csv` |
| Achievements | 25 | `data/delivery/achievements.csv` |
| APM promises | 8 | `data/delivery/promises.csv` |
| LGA delivery rows | 20 | `data/delivery/lga_delivery.csv` |
| Approved brand assets | 4 | `data/delivery/asset_register.csv` |
| Pending source reviews | 0 | `review_status != needs_review` |

All 20 LGAs currently have an explicit LGA-specific evidence row. This means each
LGA has a source-backed record for the atlas; it does not mean that every sector or
project in every LGA has been comprehensively audited.

## 3. Product Architecture

### Runtime shape

The live product is a static page with inline CSS and JavaScript. It has no server
runtime, database, private API or user account system.

```text
Public/approved source pages
          ↓
src/ingestion/delivery_sources.py
          ↓
source snapshots + manifest + review queue
          ↓
curated delivery CSV tables
          ↓
src/dashboard/render.py
          ↓
docs/index.html + local approved assets
          ↓
GitHub Pages
```

### Main files

| File or directory | Responsibility |
|---|---|
| `docs/index.html` | Generated public landing page |
| `src/dashboard/render.py` | Validates delivery data and generates the page |
| `data/delivery/` | Curated source, evidence, promise and LGA tables |
| `data/delivery/source_snapshots/` | Locally archived source responses |
| `src/ingestion/delivery_sources.py` | Public source discovery, archival and review intake |
| `src/ingestion/common.py` | Shared polite HTTP, robots.txt and rate-limit logic |
| `assets/brand/` | Approved local source assets |
| `docs/assets/brand/` | Generated copies used by the public page |
| `README.md` | Short product and local-run guide |
| `IMPLEMENTATION_PLAN.md` | Product contract, evidence hierarchy and phase history |

### Page features

- APM identity and approved local imagery.
- English/Hausa toggle.
- Four-step public-need-to-next-result pathway.
- Sector filtering for health, education, water/WASH and governance.
- Twenty-LGA selector with source-backed LGA summaries.
- Current-administration continuity framing.
- Separate APM campaign agenda.
- Source list with publication date, retrieval date, usage note and evidence grade.
- Responsive layout and reduced-motion support.
- `Created By Deerflow` attribution in the footer.

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

The latest release was checked on 24 September 2026:

- 27 registered sources.
- 33 archived source pages.
- 25 achievement records.
- 8 APM promise records.
- 20 LGA delivery rows, all currently LGA-specific.
- 0 `needs_review` queue rows.
- All registered and manifest source hashes reconcile.
- All 33 manifest snapshot hashes reconcile.
- Four local brand assets match their registered SHA-256 values.
- GitHub Pages deployment completed successfully.
- Live page returned the expected 33-page/0-pending source status.
- Live page showed 20 LGA tiles and Misau, Toro and Zaki evidence.
- Live browser console returned 0 errors.
- Responsive checks showed no horizontal overflow at 1440px, 1024px, 760px or 375px.
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
M  src/aggregation/aggregate.py
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
- The current arrow-card filter set does not expose a dedicated infrastructure card,
  even though infrastructure records exist.

### Legacy pipeline

- The pilot is not a real 500-post manually labeled corpus.
- Human review is not fully merged.
- The modified aggregation code is uncommitted and has not been fully tested.
- `pipeline_stats.csv` is not currently present.
- Facebook ingestion requires tokens and is inactive without them.
- YouTube ingestion is intentionally excluded because the feed is disallowed by
  robots rules.

## 13. Prioritized Next Steps

### P0 — Strengthen the current product

1. Add an `indicators.csv` or equivalent outcome-indicator table with baseline,
   current value, target, date, LGA/sector scope, source and verification status.
2. Replace remaining delivery-output language with measured outcomes where primary
   evidence exists: service reliability, beneficiaries, learning, health access,
   market access, income and employment.
3. Add a dedicated infrastructure arrow-card path and stronger semantic validation.
4. Run a native-speaker Hausa review of the bilingual labels and dynamic records.
5. Add focused automated tests for CSV validation, source-hash reconciliation,
   language toggling and LGA coverage.

### P1 — Complete legacy evaluation work separately

1. Create the missing `data/human_review/filled/queue_en_part1.csv` without
   overwriting existing parts.
2. Merge completed review parts by `raw_id` into the root queue files.
3. Run the modified aggregation code and inspect `pipeline_stats.csv` and risk
   outputs.
4. Create `.evals/2026-W39.md` from the evaluation template.
5. Disclose that the current filled sample was labelled by
   `mimo-v2.6-ai-reviewer`, not a native Hausa speaker.

### P2 — Operate and improve

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

## 15. Handoff Checklist

A new maintainer should be able to answer “yes” to each question:

- [ ] Can I render the live product locally?
- [ ] Can I explain the four-step narrative model?
- [ ] Can I identify the source register, manifest, review queue and curated tables?
- [ ] Can I distinguish an achievement from an APM promise?
- [ ] Can I explain why `docs/` is the public source directory?
- [ ] Can I run source intake without overwriting raw snapshots?
- [ ] Can I validate source, snapshot and asset hashes?
- [ ] Can I identify the live GitHub Pages URL?
- [ ] Can I preserve the uncommitted aggregation and human-review work?
- [ ] Do I know which pipeline is legacy and not part of the public product?
- [ ] Do I know which outcome claims still require measurement?
- [ ] Do I have a next-step list that does not mix current-product work with
      legacy evaluation work?

The complete project contract remains in `IMPLEMENTATION_PLAN.md`. This handoff is
the operational starting point for maintainers and deployment.
