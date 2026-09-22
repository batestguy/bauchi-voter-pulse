# Bauchi Voter Pulse

Live sentiment + voter-intelligence for 2027 Bauchi governorship (APM). Dashboard: **GitHub Pages, fully automated** — Actions rebuilds `docs/index.html` weekly, zero manual touches.

- Spec: `APMreadme.txt` (v1.0) · Agent rules: `AGENTS.md` · Phases: `IMPLEMENTATION_PLAN.md`
- Live URL (after Pages is enabled on `docs/`): `https://<owner>.github.io/<repo>/`
- Pipeline: `src/schema/` → `src/ingestion/` → `src/classification/` (Jev, ≥0.80 routing) → `src/aggregation/` → `src/dashboard/render.py` → `docs/index.html`

## Quick start

```bash
pip install -r requirements.txt
python src/dashboard/render.py   # rebuilds docs/index.html locally
```

## Tracking

- `data/raw|classified|aggregates/` — pipeline tables (see `AGENTS.md` for exact columns)
- `data/human_review/` — Jev confidence <0.80 queue + reasoning logs
- `.evals/` — weekly 100-post human-label eval reports
- `.github/workflows/` — `scrape.yml` (daily) + `rebuild-pages.yml` (weekly Pages rebuild)
