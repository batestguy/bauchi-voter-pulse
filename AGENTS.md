# AGENTS.md — Bauchi Voter Pulse

Greenfield repo. Only source of truth is `APMreadme.txt` (v1.0 Final Consolidated Framework). No code, build, tests, CI, or `opencode.json` yet. Trust the spec's executable details over any prose summary.

## What this is
Live sentiment + voter-intelligence system for 2027 Bauchi governorship (APM, Dr. Yakubu Adamu). 3 layers: Ingestion → Classification (Jev/TypeSafe) → Aggregation & Prediction. Primary artifact is the 20-LGA heatmap with top-3 negative topics per LGA.

## Build order (matters)
1. Question schema first + pilot on 500 manually-labelled posts before full scrapers.
2. Confidence routing before dashboard.
3. Scrapers → aggregation → static dashboard (`docs/index.html`) → weekly eval loop.
## Jev classification — hard rules
- Primitives only: `Choice` (≤255 mutually-exclusive options), `Score` (ordered rubric, ≤10 levels), `Noul` (yes/no prob). One dimension per question; single API call evaluates all questions in parallel.
- Core schema (v3): `sentiment` (Choice) / `mentions_candidate` (Noul: Yakubu Adamu/APM) / `intensity` (Score Calm→Very strong) / `lga_relevance` (Choice: 20 Bauchi LGAs + `unclear` fallback — never force a post into an LGA) / `opposition_signal` (Noul: PDP/APC sympathizer) / `language` (Choice: english/hausa/mixed/other). Executable spec: `src/schema/jev_pulse_v3.json` (one call answers all six).
- Corpus is English + Hausa + code-mixed. v2 pilot: Hausa review rate ~41% vs English ~1% — Jev is less certain on Hausa, so staff Hausa-capable reviewers and never lower the threshold to compensate. Mixed→hausa label confusion is expected (soft boundary, safe direction).
- Only the schema owner changes question wording. Store `schema_version` + model (`jev-1.13.0` or `jev-latest`) + routing threshold alongside every classified row.
- Confidence routing is non-negotiable: `≥0.80` auto-process, `<0.80` → human review. Never act on low-confidence rows; reviewers must log reasoning.
- Limits: 32K-token context (chunk long threads / post-by-post), ~250K tokens/s, 1,200 req/min. Input $0.042/M tokens, output free.
- Jev cannot do: counting/arithmetic, dates ("last week"), literal matching, NER, images, summarization/briefings, adversarial robustness. Do counting/grouping in pandas; extract dates with regex *before* Jev; NER via spaCy/BERT; narratives via separate frontier LLM.

## Ingestion — hard rules
- Public data only: Nairaland Politics, Punch/Vanguard/Daily Post/The Cable/Tribune, public Facebook pages, `bauchistate.gov.ng` budgets. Never private groups/DMs.
- Respect `robots.txt` + rate-limit delays. Anonymize usernames. Never modify scraped text; preserve `raw_id` integrity.
- Raw columns: `raw_id,source,date_scraped,text,url,lga_keyword_match`. Classified columns: `raw_id,sentiment_label,sentiment_confidence,mentions_candidate_probability,intensity_score,lga_relevance_label,opposition_signal_probability,language_label,language_confidence,routing_decision` (+ `schema_version`, `model` per row).

## Aggregation & prediction
- Group by LGA/date/topic (pandas). Predict **change from Aug-2026 LG baseline** (APM won all 20; range 19,730 Dambam–125,170 Bauchi), not the baseline. Watch narrow margins: Bogoro 25,282; Dambam 19,730; Zaki 19,984.
- Output risk labels `safe / swing / at-risk` + model version + training date per prediction. Run identical Jev schema for APM/PDP/APC mentions.
- Weekly eval: sample 100 posts, human-label, score accuracy by question and LGA. Eval role may pause classification and force schema revision.

## Dashboard (GitHub Pages — decided)
Fully automated per `IMPLEMENTATION_PLAN.md` Ph.5–6: pipeline renders static HTML to `docs/index.html`; `rebuild-pages.yml` weekly cron regenerates + commits; Pages serves `docs/`; no manual Sheet paste. Keep assets static/relative + `workflow_dispatch` for ad-hoc rebuilds.

**In progress:** `SITE_EXPANSION_PLAN.md` splits this single page into six (`index`, `achievements`, `atlas`, `poll`, `agenda`, `sources`) and adds a Bauchi LGA map + opinion poll. Phases S0–S2 are committed and unpushed; **S3 (the split) has not started.** Two silent release traps fire when it does — `rebuild-pages.yml` stages only `docs/index.html`, and the staging allowlist in `HANDOFF.md` §18 names only `docs/index.html`. Fix both in the same change. Full detail in `HANDOFF.md` §20.

## Content integrity rules
These are enforced in code; keep them enforced.
- **Never let two promise rows share `promise_text`.** `validate_unique_promises()` fails the build. A phantom row once duplicated a commitment across two sectors.
- **Never put Hausa in an English content column.** `validate_no_hausain_english_columns()` fails the build, using both an orthography test and a function-word test — the orthography test alone misses sentences that are Hausa but use no `ƙ ɓ ɗ ʙ`.
- **Never leave a required `_ha` column blank.** Enforced by `validate_data()` and the test suite.
- **Source titles are citations** and stay in their original language, untranslated. Our own prose (`usage_note`, `verification_status`, indicator values) must translate.
- **Do not invent published campaign content.** If the source does not state it, it does not go on the page. `promise-wash` is labelled a *clause* of the infrastructure commitment because the campaign published no water pillar.
- **No new assets without approval.** `asset_register.csv` needs a matching SHA-256, `usage_status` in **column 6** (`rebuild-pages.yml` checks by position, not name), and an `approved_at` date. Derived crops must say so in `approval_note`.
- **A duplicate `const` in the inline script silently disables every script on the page** while the HTML still renders. Guarded by a `node --check` parse in `tests/test_header_brand.py`. Run it.

## Legal / ethics
Public sources only; anonymize; disclose outputs are social/news analysis, not private polling. Version everything so any dashboard cell traces to schema + model + data.

53 Hausa strings added in September 2026 are AI-drafted and not native-speaker reviewed. Disclose that wherever they ship, exactly as `.evals/2026-W39.md` discloses its labeler.
