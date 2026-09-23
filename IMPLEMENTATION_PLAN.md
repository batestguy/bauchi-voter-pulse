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
- **Operator action required:** add repo secret `TYPESAFE_API_KEY` (Settings → Secrets → Actions) or weekly classification skips silently (renders on existing data).
- Ph.5 dashboard: `render.py` rewritten — 20-LGA risk-band heatmap tiles (safe/swing/at-risk/unrated colors, anchored click-through), per-LGA top-3 negative topics from new `lga_topics.csv` (per-LGA × topic mentions + neg_share), inline-SVG daily trend, opposition table, full risk table, one-insight briefing block with explicit action line, schema/model/threshold/risk-v0 trace footer. Stdlib-only, no JS/external assets; missing aggregate files degrade to empty sections. Current briefing honest about n=20 (all unrated → "raise collection volume").
- Ph.7 scaffolded: eval sample generator `python -m src.classification.eval_sample` (seed 42, **hausa/mixed floors ≥10** to catch known Hausa review-rate drift) → `.evals/2026-W39_sample100.csv` (100 rows incl. intensity + per-row schema/model + blank `human_*` incl. `human_intensity`). Native-speaker labeling remains the human step; fill, then copy `.evals/eval_template.md` → `.evals/2026-W39.md`.
- Reviewer round 2 FAIL → fixed: (M2) both workflows get `concurrency` + `git pull --rebase origin $GITHUB_REF_NAME` before push (05:30 scrape vs 06:00 rebuild race); (M3) trend SVG bar width now dynamic (was clipping past 13 dates); (M1, policy) eval sample + review queues carry **verbatim text by design** — same content already in `data/raw` (never-modify rule; the human must label what the model saw; redacting would desync label vs input), anonymization = no author/username *columns* anywhere, and published surfaces (dashboard) quote aggregates only — no text, no handles. Also: `run_jev` now fails on short stdout (silent-drop guard), queue written before classified CSV (no orphan classifications), classify_new CI-tolerant around all I/O, risk band thresholds as shared constants (`SAFE_MAX`/`SWING_MAX`/`RISK_MODEL` imported by render), briefing + risk table scoped to the 20 named LGAs with `unclear` footnoted as non-LGA, threshold shown as `0.80`.


## Backlog: targeted Bauchi discovery (Ph.3+, researched 2026-09-22) — BUILT 2026-09-23
Problem: only ~1% of front-page/RSS haul mentions APM — need query-driven sources.
- DONE `src/ingestion/gdelt.py`: GDELT DOC 2.0 `artlist`, query `(Bauchi OR "Yakubu Adamu" OR APM)`, adaptive 250/req windows, now PACE 90s / backoff 240s (sliding multi-minute 429 observed — stricter than the ≥6s probe finding), metadata → `polite_get` article fetch. Free/keyless, 90-day window. Seedable via `rows_from_articles` from a saved response.
- DONE ArewaEars (`arewaears.com/feed/` — currently connection-failing, kept) + Guarantee (`guaranteeradio.com/feed/` — works) into `news.py` FEEDS.
- DONE `src/ingestion/legit_hausa.py` (DAILY, cap ~40 reqs): hausa sitemap index → last 3 shards by shard number (newest; index has no lastmod) → slug-keyword filter → one-fetch title+body. Sitemaps are robots-clean.
- DONE Robots fix: 404/410 on robots.txt = allow-all (needed for GDELT API); skip only on true fetch failures.
- YouTube: **blocked by robots.txt** (`Disallow: /feeds/videos.xml`) — no keyless path compliant with our rules; Data API key-gated module unbuilt. Key-gated (env-only `YT_API_KEY` / `FB_PAGE_TOKEN` + `FB_PAGES`, never in code) remains the only route if keys appear.
- Standing exclusions: BBC Hausa (terms forbid datasets/AI use), TheCable (WAF 403), Leadership (dead endpoint), VOA/Aminiya (unreachable).
