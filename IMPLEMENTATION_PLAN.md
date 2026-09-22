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

## Backlog: targeted Bauchi discovery (Ph.3+, researched 2026-09-22, approved to build)
Problem: only ~1% of front-page/RSS haul mentions APM — need query-driven sources.
- `src/ingestion/gdelt.py` (new): GDELT DOC 2.0 `artlist`, query `(Bauchi OR "Yakubu Adamu" OR APM)`, 250/req + date-window pagination, ≥6s pacing w/ backoff (429 observed on fast probe), metadata → `polite_get` article fetch. Free/keyless, 3-month window.
- ArewaEars (`/feed/`, 155KB, robots allow) + Guarantee (`/feed/`, no robots.txt) into `news.py` FEEDS. ArewaEars already runs Bauchi-2027 APC-crisis coverage in Hausa.
- `src/ingestion/legit_hausa.py` (new, DAILY, cap ~40 reqs): sitemap index → 3 newest article-sitemaps → filter `hausa.legit.ng` locs on Bauchi keywords → `article_body()` fetch. No RSS exists; sitemaps are crawler-provided and robots-clean.
- Robots fix: 404 on robots.txt = allow-all (needed for Guarantee); skip only on true fetch failures.
- Key-gated (user holds keys, env-only `YT_API_KEY` / `FB_PAGE_TOKEN` + `FB_PAGES`, never in code): YouTube module (Data API search → captions) + activate Facebook stub for Bauchi public pages.
- Standing exclusions: BBC Hausa (terms forbid datasets/AI use), TheCable (WAF 403), Leadership (dead endpoint), VOA/Aminiya (unreachable).
