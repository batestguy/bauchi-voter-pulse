# APM Bauchi Progress & Delivery Revamp — Governing Plan (v2)

**Status:** approved direction, not yet implemented
**Supersedes:** the legacy “Bauchi Voter Pulse” sentiment/risk dashboard as the primary product
**Timeframe:** 2023–September 2026
**Audience:** internal campaign strategists first; sanitized public presentation second
**Primary principle:** show verified progress, connect it to public needs, and show how APM will build on that progress.

This section is the new product contract. The historical implementation log remains below for rollback and provenance. The legacy sentiment system is retained for historical reference only and is not run by the current Pages workflow.

## 1. Mission

Build a beautiful, interactive landing page and internal decision dashboard that tells one coherent story:

> Bauchi has real progress to build on. APM will carry that progress forward and complete the next priorities.

The product answers five questions for each LGA and priority sector:

1. What does the public need?
2. What has the current Bauchi State administration delivered or started?
3. What evidence supports that achievement?
4. What does APM promise to build, complete or improve?
5. What result will show that the promise was achieved?

The landing page must not present political claims as private polling, personal promises as completed projects, or unverified numbers as achievements.

## 2. Product identity

**Working title:** APM Bauchi Progress & Delivery

**Hero headline:** A Vision for Progress

**APM official motto:** Integrity, Sacrifice and Service

**APM official slogan:** APM — Nigeria First, Nigeria First – APM

**Campaign positioning:** Building on Bauchi’s progress. Delivering the next priorities.

The official APM motto and slogan are brand elements, not evidence. The candidate campaign’s “A Vision for Progress” is a campaign headline, not the official party motto.

## 3. Central visual model

Every LGA and sector card uses a four-part arrow pathway:

```text
PUBLIC NEED → CURRENT ACHIEVEMENT → APM PROMISE → NEXT RESULT
```

### Public need

A measurable issue or opportunity, such as reliable water, quality education, healthcare access, roads, jobs, food security, security, or youth opportunity.

### Current achievement

A documented project, programme, budget action, service improvement, institutional initiative, or other public record from the current administration or another clearly identified actor.

### APM promise

A campaign commitment or proposed continuation. Promise cards are labelled separately from achievement cards.

### Next result

A future target, service outcome, coverage measure, economic indicator, or implementation milestone. A promise without a measurable result is marked as a promise without a measurement plan.

## 4. Narrative and tone

The page is optimistic, practical and evidence-led. It should communicate:

- Progress made by the current Bauchi State administration.
- Continuity between the governor’s current leadership and APM’s proposed next chapter.
- Specific needs that remain important to communities.
- A positive, non-attack campaign narrative.
- Clear action: APM will build on, complete and expand existing gains.

Preferred status labels:

- Progress delivered
- Project underway
- Promise to complete
- Next priority
- Outcome being measured

Avoid user-facing labels such as failure, failed delivery, at risk, corruption, incompetence, or hostile criticism. The internal evidence register may record neutral facts, conflicts, unknown values and unresolved verification.

## 5. Brand and asset policy

Use approved local copies of official web assets, with source metadata and attribution:

- APM logo from the official APM website
- Dr. Yakubu Adamu candidate photograph from the official campaign website
- Governor Bala Mohammed photograph for the continuity/achievements section, where approved
- Official APM manifesto and campaign page as text sources
- Bauchi State Government and partner report assets where licensing and publication terms permit

Store assets locally rather than hotlinking them from a third-party site. Each asset record must include source URL, retrieval date, content hash, usage status, approver and approval date. The campaign team has approved the current logo and portrait assets; future changes must repeat that approval check.

## 6. Primary data model

The new system uses source-backed delivery records rather than social sentiment records.

### Source record

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

### Need record

```text
need_id
lga
sector
need_text
need_indicator
baseline_value
baseline_year
baseline_source
priority_level
population_or_coverage
```

### Achievement record

```text
achievement_id
actor
lga
sector
project_or_programme
description
start_date
completion_or_status_date
beneficiaries
budget_or_scale
outcome_measure
source_id
evidence_grade
verification_status
```

### Promise record

```text
promise_id
actor
lga_or_scope
sector
promise_text
promise_type
target_date
success_indicator
source_id
approval_status
```

### Arrow record

```text
arrow_id
lga
sector
need_id
achievement_ids
promise_id
next_result
coverage_type
last_reviewed
```

## 7. Actors and attribution

The product must distinguish:

- Dr. Yakubu Adamu / APM campaign
- Governor Bala Mohammed
- Bauchi State Government
- Bauchi State ministries and agencies
- Local government authorities
- Federal Government
- Development partners
- Independent researchers and media

A project should not be credited solely to APM or the candidate when the source identifies another implementing actor. Joint delivery is shown as joint delivery. Inherited or pre-existing work is labelled as continuity rather than newly created work.

## 8. Evidence hierarchy

### Grade A — primary official evidence

- Approved and amended budgets
- Budget performance reports
- Audited accounts and audit reports
- Official project lists and procurement records
- Government service dashboards
- Official policy and strategy documents
- Independent institutional datasets with clear methodology

### Grade B — institutional verification

- World Bank
- African Development Bank
- UNICEF
- WHO
- United Nations agencies
- Nigerian national statistical and audit bodies
- Academic or civil-society research with reproducible evidence

### Grade C — corroborating reporting

- Credible independent news reports
- Named project reporting
- Interviews with clearly identified sources

### Grade D — campaign or social material

- Candidate statements
- Party manifestos
- Press releases
- Social posts
- Public speeches

Grade D is suitable for promise or context content. It cannot alone prove a completed outcome or quantitative achievement.

Every displayed number must have a source, period and definition. Missing information remains `UNKNOWN`; it must never be filled with a plausible estimate.

## 9. Sectors and priority needs

Start with a focused set that can be supported by public evidence:

1. Health and maternal/child health
2. Water, sanitation and hygiene
3. Education, skills and digital access
4. Youth employment, agriculture and livelihoods
5. Roads, transport, power and market infrastructure
6. Security, justice and public safety
7. Women, youth and social protection
8. Public finance, governance and service delivery

Each sector requires 3–5 indicators. Examples include facility availability, water functionality, school completion, teacher presence, road condition, youth skills participation, agricultural value-chain activity, emergency response and public-finance execution.

## 10. LGA delivery atlas

The first UI will cover all 20 Bauchi LGAs:

Alkaleri, Bauchi, Bogoro, Dambam, Darazo, Dass, Gamawa, Ganjuwa, Giade, Itas-Gadau, Jamaare, Katagum, Kirfi, Misau, Ningi, Shira, Tafawa-Balewa, Toro, Warji and Zaki.

For each LGA, the page shows:

- Priority needs
- Verified current achievements
- Statewide achievements relevant to the LGA
- APM commitments relevant to the need
- Next measurable result
- Source and evidence status

If an achievement is not specifically attributed to an LGA in the source, label it `Statewide relevance` rather than forcing it into an LGA. If no LGA-specific evidence exists, the card should say so plainly without turning it into an attack.

A real map is used only if an authoritative boundary file is obtained. Otherwise, use a designed 20-LGA atlas grid that remains readable on mobile and avoids implying false geographic precision.

## 11. Landing page information architecture

### 1. Hero

- APM logo
- Dr. Yakubu Adamu image
- Candidate name and title
- `A Vision for Progress`
- `Integrity, Sacrifice and Service`
- One-line continuity statement
- Primary CTA: Explore Bauchi’s Progress
- Secondary CTA: View the LGA atlas

### 2. Bauchi at a glance

Display only sourced facts such as population, number of LGAs, key economic sectors and public-service context.

### 3. Progress in action

Introduce the animated four-stage arrow model with one fully sourced example before the detailed LGA cards.

### 4. Achievement gallery

Use visual project cards for education, health, water, infrastructure, agriculture, youth and governance. Each card shows scale, location, actor, source and outcome.

### 5. 20-LGA atlas

Interactive LGA selector with filters for sector, achievement type and evidence status.

### 6. Current administration continuity

Present verified progress under the current administration and connect it to the statement that APM will build on and complete the gains.

### 7. APM agenda

Show the candidate’s published promises as campaign commitments. Include security, education, infrastructure, youth/women empowerment and agriculture only with approved source wording.

### 8. Sources and method

Provide source register, definitions, evidence grades, publication dates, coverage limitations and a clear distinction between public information, campaign commitments and verified outcomes.

## 12. Visual direction

Use a refined civic-editorial aesthetic:

- Deep blue derived from the official APM identity
- Warm ivory and sand backgrounds
- Green for progress delivered
- Gold for APM commitments
- Soft blue for future results
- Editorial serif display typography paired with a highly readable sans-serif body face
- Large documentary photography
- Restrained map-line and woven-pattern motifs inspired by Bauchi’s geography and textile traditions
- Subtle arrow animation, scroll reveals and image hover states
- Reduced-motion support
- Strong contrast, keyboard navigation and meaningful image alt text

The result should feel optimistic, premium, credible and distinctly Bauchi rather than generic campaign-template software.

## 13. Technical direction

The first implementation remains a static, single-file `docs/index.html` generated by Python, compatible with GitHub Pages and local rendering.

Planned modules:

```text
src/
  public_sources/
    discovery.py
    documents.py
    extract.py
  delivery/
    needs.py
    achievements.py
    promises.py
    indicators.py
    scoring.py
  dashboard/
    render.py
    theme.py
    copy_en.py
    copy_ha.py
  brief/
    render_brief.py

data/delivery/
  source_register.csv
  needs.csv
  achievements.csv
  promises.csv
  lga_delivery.csv
  indicators.csv
  evidence_notes.csv

assets/brand/
  apm-logo.*
  yakubu-adamu.*
  bala-mohammed.*

docs/
  index.html
```

The existing `common.py` public-source, robots.txt, rate-limit and stable-ID safeguards should be reused. The old Jev sentiment path is retained only for historical reference and is not invoked by the new delivery workflow.

## 14. Delivery phases

### Phase 0 — Preserve and redirect

- Preserve uncommitted legacy review work.
- Mark the old dashboard as legacy.
- Stop the old system from being the primary narrative.
- Add a new source-backed entry point and data directories.
- Do not delete historical data until the new build has passed QA.

**Acceptance:** the current work remains recoverable; the legacy output is no longer the default product story.

### Phase 1 — Source and brand audit

- Crawl official APM and candidate pages within public-source rules.
- Collect official state, LGA, budget, audit and institutional sources.
- Download approved brand and campaign images locally.
- Record source URL, date, hash, type, usage note and evidence grade.
- Build the first source register.

**Acceptance:** at least one official source, one institutional source and one campaign source are present for every sector selected for the vertical slice.

### Phase 2 — Needs and achievement schema

- Create the six core tables from Section 6.
- Define sector vocabulary and LGA coverage rules.
- Define the four arrow stages and status labels.
- Define positive copy patterns and neutral evidence descriptions.
- Define English/Hausa labels without translating proper names unnecessarily.

**Acceptance:** one sector can be represented from need to APM promise without using sentiment or LGA risk labels.

### Phase 3 — One vertical slice

Build one complete example:

- One LGA
- Two or three sectors
- At least five public needs
- At least five verified or clearly labelled achievements
- At least five APM promises
- At least five sources
- English and Hausa labels
- Responsive landing UI

**Acceptance:** a user can click through one story from public need to next result and inspect every source.

### Phase 4 — Full achievement corpus

- Expand across all 20 LGAs.
- Add all selected sectors.
- Add current-administration achievements.
- Add candidate and party promises as separate records.
- Add outcome indicators and coverage labels.
- Run duplicate, date, actor and LGA checks.

**Acceptance:** all 20 LGAs have a valid card, including an explicit statewide or no-LGA-specific-evidence label where appropriate.

### Phase 5 — Interactive landing page

- Implement the hero, progress pathway, achievement gallery and LGA atlas.
- Add LGA and sector filters.
- Add expandable arrow cards.
- Add source drawer and evidence badges.
- Add English/Hausa toggle.
- Add accessible keyboard and reduced-motion behaviour.
- Add local image assets with fallbacks.

**Acceptance:** the page works at mobile, tablet and desktop widths and can be rendered locally without external build tooling.

### Phase 6 — Internal weekly brief

Generate a short internal brief containing:

- Three strongest verified progress stories
- Three priority needs with the clearest APM opportunity
- Three evidence gaps
- Three recommended next actions
- Claims that are not yet safe to use
- Source dates and confidence status

**Acceptance:** every brief statement links back to the source register and is distinguishable from campaign copy.

### Phase 7 — Quality assurance and release

- Verify every displayed claim against its source.
- Verify no unsupported number is visible.
- Verify no private information is included.
- Verify all assets have attribution and usage status.
- Verify local rendering and GitHub Pages compatibility.
- Test keyboard, screen-reader, contrast and reduced-motion behaviour.
- Test English/Hausa content completeness.
- Remove legacy sentiment metrics from the public-facing narrative.

**Acceptance:** the first release is a useful internal strategy product and a safe, polished public presentation, not an unverified claim bundle.

## 15. Scoring and decision rules

The product should not publish one opaque “APM score.” Instead it shows:

- Evidence coverage
- Verified achievement count
- Delivery status
- Outcome evidence
- Geographic coverage
- Next-priority clarity

A sector is only described as having a verified outcome when the source provides a measurable result, a credible completion record or a corroborated beneficiary/service measure. A launch, promise, budget allocation or speech is not automatically an outcome.

The campaign team may later approve sector weights, but the first release must show the underlying indicators.

## 16. Risks and safeguards

- **Sparse LGA evidence:** show statewide relevance rather than forcing an LGA attribution.
- **Source conflicts:** preserve both claims and mark the field `requires verification`.
- **Joint delivery:** show all actors instead of assigning sole credit.
- **Campaign claims:** separate from achievements with clear labels.
- **Image rights:** use local approved assets and source notes.
- **Public exposure:** keep internal strategy pages private; publish only a sanitized public view.
- **Bilingual drift:** validate Hausa copy with a native speaker before public release.
- **Old data contamination:** keep legacy sentiment files out of the new delivery tables.

## 17. First implementation slice

The next executable slice is:

1. Create `data/delivery/` source and achievement seed files from verified public sources.
2. Add one complete LGA story with two sectors.
3. Replace the legacy dashboard output with the new “Progress in Action” vertical slice.
4. Include official APM branding and the candidate image as local assets with attribution.
5. Add English/Hausa labels and responsive arrow cards.
6. Run source, accessibility and local-render checks.

The old sentiment dashboard remains available only as a historical archive. It is not a live fallback for the new delivery landing page.

## 18. Current build status

- New source-backed landing page is live locally through `docs/index.html`.
- Official APM and campaign assets are approved, hashed, registered and copied to `docs/assets/brand/`.
- Current source-backed corpus contains 27 registered sources, 7 needs, 25 public achievement records, 8 campaign commitments and 20 LGA delivery rows.
- `src/ingestion/delivery_sources.py` archives official and approved institutional web pages and creates review candidates under `data/delivery/review_queue.csv`.
- The current intake has 33 archived pages, 25 sources supporting published achievement records, and 0 candidates still awaiting review; all 20 Bauchi LGAs now have an explicit source-backed evidence row, with caveats preserved where outcomes remain unmeasured.
- `delivery-sources.yml` runs the official-source intake weekly and on demand.
- The Pages workflow renders only the new delivery landing page and fails closed on unapproved assets.
- The legacy sentiment pipeline is historical and is not run by the new Pages workflow.
- The next data task is expanding the approved source allowlist with LGA-level and sector-specific primary records, then adding verified outcomes to the 20-LGA atlas.

# Bauchi Voter Pulse — GitHub Pages Execution Plan

Decision: **Option D — GitHub Pages (fully automated, hands-off)** per `APMreadme.txt` §4.
Weekly flow is machine-run: Actions cron → pipeline regenerates static HTML → commit → Pages serves at public URL. No manual Sheet paste.
Source of truth: `APMreadme.txt` v1.0. Constraints in `AGENTS.md` still apply (public sources only, ≥0.80 routing, version everything).


## Target layout (to be built)

```
src/
  schema/          # Jev question definitions, versioned (schema_v1.json, ...)
  ingestion/       # scrapers: nairaland, news, facebook, budgets
  classification/  # Jev batch runner + chunking + routing (≥0.80 auto / <0.80 review)
  aggregation/     # pandas group-by LGA/date/topic, risk model
  dashboard/       # static HTML generator (heatmap + tables + briefing)
data/
  raw/             # raw_id,source,date_scraped,text,url,lga_keyword_match
  classified/      # + sentiment_label, confidence, probs, routing_decision, schema_version
  aggregates/      # daily/weekly LGA aggregates, topic freq, risk labels
docs/              # Pages output (index.html) — committed by Actions
.evals/            # weekly 100-post human-label samples + accuracy reports
.github/workflows/
  scrape.yml       # daily ingestion
  rebuild-pages.yml# weekly cron: classify → aggregate → render HTML → commit to docs/
```

## Phases

### Phase 0 — Repo scaffold
- `git init`, `.gitignore` (data/raw secrets, API keys), `requirements.txt` (`pandas`, `scikit-learn`, `requests`, `beautifulsoup4`, `typesafe-ai` or Jev client, `jinja2`), `README` link to Pages URL.
- Enable GitHub Pages → Serve from `docs/` on `main`.
- Acceptance: empty pipeline runs green; Pages URL live.

### Phase 1 — Question schema + 500-post pilot (FIRST, per §9)
- Define and version the 5 core questions: `sentiment` (Choice) / `mentions_candidate` (Noul) / `intensity` (Score) / `lga_relevance` (Choice 20 LGAs) / `opposition_signal` (Noul). Atomic, mutually exclusive, ordered rubrics.
- Manually label 500 posts; run Jev (`jev-1.13.0` or `jev-latest`); record `schema_version` + model + threshold per row.
- Acceptance: schema v1 frozen; pilot accuracy per question known; single Jev call evaluates all 5 in parallel.

### Phase 2 — Confidence routing
- Implement `≥0.80` auto / `<0.80` → `human_review/` with reviewer reasoning log. Never act on low-confidence rows.
- Acceptance: routing split measured; review queue + log format exist before any dashboard work.

### Phase 3 — Ingestion (public only)
- Scrapers: Nairaland Politics + Punch/Vanguard/Daily Post/The Cable/Tribune + public FB pages (daily); `bauchistate.gov.ng` budgets (monthly).
- Rules: respect `robots.txt` + delays, anonymize usernames, never edit text, keep `raw_id` integrity, exact raw columns.
- `scrape.yml` daily run, dedupe, commit to `data/raw/`.
- Acceptance: 3 consecutive daily runs with valid schema + no private-source data.

### Phase 4 — Aggregation & prediction
- Pandas group-by LGA/date/topic; counts/percentages here, never in Jev. Regex-extract dates pre-Jev. spaCy/BERT for entities; frontier LLM only for briefing prose.
- Model (Random Forest or Logistic Regression on Jev labels) predicts **change from Aug-2026 LG baseline** (APM swept 20; 19,730 Dambam–125,170 Bauchi; watch Bogoro 25,282 / Dambam / Zaki 19,984). Output `safe / swing / at-risk` + model version + training date. Identical schema for APM/PDP/APC.
- Acceptance: aggregates + risk table regenerate deterministically; every prediction traceable to schema+model+data.

### Phase 5 — Static dashboard generator
- `src/dashboard/` renders `docs/index.html` (no JS build step): 20-LGA heatmap + click-through top-3 negative topics per LGA, 7/30-day trends, opposition comparison, risk table, one-insight briefing block.
- Pure static assets only (relative paths) so Pages serves it as-is.
- Acceptance: `python -m src.dashboard.render` rebuilds `docs/index.html` locally; demo leads with one actionable insight (e.g. "Ningi youth-unemployment +40%, APC gaining → town hall in 14 days").

### Phase 6 — Weekly automation (the GitHub Pages payoff)
- `rebuild-pages.yml` weekly cron: scrape → classify → aggregate → render → commit `docs/index.html` + `data/aggregates/`.
- Manual `workflow_dispatch` for ad-hoc rebuilds.
- Acceptance: merge → Actions rebuilds → public URL shows new timestamp with zero manual touches.

### Phase 7 — Eval loop (ongoing)
- Weekly: sample 100 classified posts, human-label, score accuracy by question and LGA, test adversarial inputs. Eval role may pause classification and force schema revision (bump `schema_version`, re-pilot).
- Acceptance: eval report in `.evals/YYYY-Www.md`; routing/threshold adjustments logged.

## Deliverable → phase map
1. Classified corpus → Ph.1–3 | 2. LGA heatmap → Ph.5 | 3. Opposition dashboard → Ph.4–5 | 4. Risk report → Ph.4–5 | 5. Briefing template → Ph.5 (LLM prose over Jev outputs) | 6. Ops manual → Ph.1–2 + Ph.7

## Status log (2026-09-22)
- Ph.0 done: repo public, Pages live on `docs/`, daily + weekly + monthly workflows.
- Ph.1 done: schema v3 frozen (`src/schema/jev_pulse_v3.json`, model `jev-1.13.0`). 540-post pilot: sentiment 99.6 / mentions 100 / lga 97.6 / opp 100 / language 94.8; intensity ordinal-only (±1: 93%).
- Ph.2 done: `src/classification/` runner + routing gate (auto iff min(sentiment,lga conf) ≥0.80) + review-queue protocol.
- Ph.3 done: 1,618 raw rows (Nairaland board + targeted search, 8 news outlets incl. RFI Hausa). Excluded on purpose: BBC Hausa (terms forbid datasets), TheCable (WAF 403), Facebook (no token — see Ph.3 notes).
- Ph.4 done: `src/aggregation/aggregate.py` + `data/baseline_lg2026.csv` + `risk-v0-heuristic`. Real-data result: 2/1628 usable rows (cycle dominated by Osun-election news) — risk correctly reports unrated/insufficient-data, no fabricated ratings. ML training gated (refuses <200 LGA-weeks).
- Key decisions: v3 `unclear` LGA fallback (v2 forced every post into an LGA); aggregation uses usable rows only (mentions≥0.5, ≠not_about, auto); per-language review rates reported in every eval (Hausa ~41-44%).
- Next: Ph.5 static heatmap/dashboard content; Ph.7 weekly 100-post native-speaker eval.

## Status log (2026-09-23) — keyless discovery shipped (no FB/YT accounts needed)
- Ph.3+ built: `gdelt.py` (query-driven `(Bauchi OR "Yakubu Adamu" OR APM)`, 90-day adaptive windows, PACE 90s/backoff 240s — live API enforces a multi-minute sliding 429 after bursts; seedable via `rows_from_articles`; BBC/TheCable URLs hard-excluded), `legit_hausa.py` (hausa-only sitemap index → **last 3 shards by shard number** — index has no lastmod and shard -0 is 2016-era, verified shard -10 is all-2026 → slug-keyword filter → 36 articles/day cap ≈ 40 reqs), news.py += `guarantee` (guaranteeradio.com, works) + `arewaears` (connection-failing from this host; kept, auto-recovers), robots.txt 404/410 → allow-all in `common.py` (true fetch failures still skip).
- Exclusions finalized: **YouTube** — robots.txt disallows `/feeds/videos.xml`, so even keyless channel RSS is off-limits; Data API key remains the only compliant path (module stays unbuilt). Facebook unchanged (token-gated stub). Leadership exclusion is **feed-endpoint only** — its articles via GDELT are allowed (30 such URLs in seed, kept after review).
- Pipeline: +446 raw rows (09-23 run, incl. 36 evergreen www-legit) + 36 fresh hausa-legit + 172 GDELT seed + 654 classified today (`batch_2026-09-23.csv` 618 + `_hausa.csv` 36); usable rows 2 → **20** (gdelt 17, nairaland_search 2, hausa 1); sentiment 7 pos / 9 neu / 4 neg; risk: named LGAs now appear but stay `unrated` (n<5), `unclear` = safe. Volume — not plumbing — is now the binding constraint.
- Reviewer PASS on robots/gdelt/run_daily/counts/routing (0 violations, 0 batch overlap, no secrets); fixes applied: legit sitemap source, render schema-v3 trace + per-LGA fold, docstrings, domain exclusions.
- Gotcha: never park temp files in `data/raw/` — aggregate globs `*.jsonl`; a temp join file inflated counts (36 → true 19).

## Status log (2026-09-23, cont.) — CI classify gap closed, Ph.5 heatmap, Ph.7 sample
- CI: `rebuild-pages.yml` now delta-classifies (`python -m src.classification.classify_new` — finds raw parents in no batch, scratch file in system temp, sequence-suffix so same-day batches never overwrite) → aggregate → render; commits `data/classified/` + `data/human_review/` too (was aggregates+docs only → CI classifications would otherwise be lost and re-run weekly). Runner failure in CI (missing `TYPESAFE_API_KEY` secret, jev/API down) warns and exits 0 so the cron stays green. `jev` vendored at `third_party/jev/` (Apache-2.0 + LICENSE + NOTICE); `classify.py` takes `JEV_BIN` (CI points it at the vendored script, local keeps the PATH shim).
- **Operator action required:** add repo secret `TYPESAFE_API_KEY` — **DONE 2026-09-23** via `gh secret set` (batestguy/bauchi-voter-pulse; verify `gh secret list`).
- Ph.5 dashboard: `render.py` rewritten — 20-LGA risk-band heatmap tiles (safe/swing/at-risk/unrated colors, anchored click-through), per-LGA top-3 negative topics from new `lga_topics.csv` (per-LGA × topic mentions + neg_share), inline-SVG daily trend, opposition table, full risk table, one-insight briefing block with explicit action line, schema/model/threshold/risk-v0 trace footer. Stdlib-only, no JS/external assets; missing aggregate files degrade to empty sections. Current briefing honest about n=20 (all unrated → "raise collection volume").
- Ph.7 scaffolded: eval sample generator `python -m src.classification.eval_sample` (seed 42, **hausa/mixed floors ≥10** to catch known Hausa review-rate drift) → `.evals/2026-W39_sample100.csv` (100 rows incl. intensity + per-row schema/model + blank `human_*` incl. `human_intensity`). Native-speaker labeling remains the human step; fill, then copy `.evals/eval_template.md` → `.evals/2026-W39.md`.
- Reviewer round 2 FAIL → fixed: (M2) both workflows get `concurrency` + `git pull --rebase origin $GITHUB_REF_NAME` before push (05:30 scrape vs 06:00 rebuild race); (M3) trend SVG bar width now dynamic (was clipping past 13 dates); (M1, policy) eval sample + review queues carry **verbatim text by design** — same content already in `data/raw` (never-modify rule; the human must label what the model saw; redacting would desync label vs input), anonymization = no author/username *columns* anywhere, and published surfaces (dashboard) quote aggregates only — no text, no handles. Also: `run_jev` now fails on short stdout (silent-drop guard), queue written before classified CSV (no orphan classifications), classify_new CI-tolerant around all I/O, risk band thresholds as shared constants (`SAFE_MAX`/`SWING_MAX`/`RISK_MODEL` imported by render), briefing + risk table scoped to the 20 named LGAs with `unclear` footnoted as non-LGA, threshold shown as `0.80`.

## Status log (2026-09-23, labeling round) — HANDOFF: where we stop, next session starts here
Committed: `9eff5d0` (keyless discovery) → `36f1166` (CI classify + Ph.5 heatmap + eval sample + reviewer fixes). GitHub secret `TYPESAFE_API_KEY` set. Dashboard v1 (EN heatmap) openable at `docs/index.html`.

**AI labeling round IN FLIGHT — user directed: AI does the labeling itself (not a human native speaker; disclose in eval report; Hausa native spot-check still recommended).** Protocol (relaunch identical next session): read `src/schema/jev_pulse_v3.json` enums first; judge `text` independently (never copy model cols); write ONLY part files under `data/human_review/filled/` (sole-writer-per-file avoids conflicts); 5 review cols = `reviewer_label` confirmed/corrected (sentiment+lga+mentions match) · `reviewer_reasoning` 1 non-empty sentence · `final_label` single-line JSON `{"sentiment","intensity","lga","mentions":bool,"opposition":bool,"language"}` · `reviewer_label`… `reviewed_by=mimo-v2.6-ai-reviewer` · `reviewed_at=2026-09-23`. Agents returning EMPTY results = dead session → relaunch fresh (happened 3× on part1).

| Piece | Rows | Status | Result |
|---|---|---|---|
| `filled/queue_en_part2.csv` (queue 141–279) | 139 | DONE (committed? no — untracked) | 100 confirmed / 39 corrected; big theme: model misread third-party threads (Obi/Kwankwaso) as candidate sentiment + forced LGAs from surnames |
| `filled/queue_hausa.csv` (all 21 hausa queue) | 21 | DONE, verified (21 JSON + reasoning) | 6 confirmed / 15 corrected; uncertain: `legit_hausa-965c779365e6` |
| `.evals/2026-W39_sample100_filled.csv` | 100 | DONE, verified (6/6 human cols) | **11/100 sentiment mismatches vs model** (top: model missed `not_about_candidate`) |
| `filled/queue_en_part1.csv` (queue 1–140) | 140 | **MISSING — relaunch FIRST** | two empty agent returns + third cancelled at session end |

**Uncommitted worktree:** `src/aggregation/aggregate.py` (+`load_reviewed()`, human_cleared override with conf pinned 1.0, usable gate now `auto|human_cleared`, exports `data/aggregates/pipeline_stats.csv` counts/model/risk_model/built) — **written but UNTESTED**; three untracked paths above.

**TODO next session, in order:**
1. Relaunch part1 labeler (rows 1–140 → `filled/queue_en_part1.csv`) with the protocol above.
2. Merge parts back into the original queue files (fill the 5 cols in `queue_batch_2026-09-23.csv` + `_hausa.csv` by `raw_id`; originals are what `load_reviewed()` reads).
3. Run `python -m src.aggregation.aggregate` — expect usable ≫ 20 (cleared rows enter), `pipeline_stats.csv` sanity (classified=usable+pending-not-relevant arithmetic), spot-check risk bands.
4. Eval accuracy: compare model vs `human_*` per question from the filled sample → write `.evals/2026-W39.md` from template; **disclose labeler = AI (mimo), not native speaker; flag 11 mismatches; recommend native Hausa spot-check**.
5. **Bilingual beautiful dashboard** (user's explicit next ask): rewrite `src/dashboard/render.py` per loaded `frontend-design` skill — EN/HA toggle (inline JS or CSS lang-swap; translation dicts for chrome/topics/bands/briefing; LGA names + data values stay as-is for traceability), keep stdlib-generate, single-file static, relative-only, schema/model/threshold/risk trace footer, aggregates-only (no verbatim text/handles). Keep `docs/index.html` as output name (Pages).
6. Verify → `ship-reviewer` → commit.


## Backlog: targeted Bauchi discovery (Ph.3+, researched 2026-09-22) — BUILT 2026-09-23
Problem: only ~1% of front-page/RSS haul mentions APM — need query-driven sources.
- DONE `src/ingestion/gdelt.py`: GDELT DOC 2.0 `artlist`, query `(Bauchi OR "Yakubu Adamu" OR APM)`, adaptive 250/req windows, now PACE 90s / backoff 240s (sliding multi-minute 429 observed — stricter than the ≥6s probe finding), metadata → `polite_get` article fetch. Free/keyless, 90-day window. Seedable via `rows_from_articles` from a saved response.
- DONE ArewaEars (`arewaears.com/feed/` — currently connection-failing, kept) + Guarantee (`guaranteeradio.com/feed/` — works) into `news.py` FEEDS.
- DONE `src/ingestion/legit_hausa.py` (DAILY, cap ~40 reqs): hausa sitemap index → last 3 shards by shard number (newest; index has no lastmod) → slug-keyword filter → one-fetch title+body. Sitemaps are robots-clean.
- DONE Robots fix: 404/410 on robots.txt = allow-all (needed for GDELT API); skip only on true fetch failures.
- YouTube: **blocked by robots.txt** (`Disallow: /feeds/videos.xml`) — no keyless path compliant with our rules; Data API key-gated module unbuilt. Key-gated (env-only `YT_API_KEY` / `FB_PAGE_TOKEN` + `FB_PAGES`, never in code) remains the only route if keys appear.
- Standing exclusions: BBC Hausa (terms forbid datasets/AI use), TheCable (WAF 403), Leadership (dead endpoint), VOA/Aminiya (unreachable).
