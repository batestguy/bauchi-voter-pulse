"""Weekly eval sample (Ph.7): stratified sample of classified rows for human
labelling. Seed-fixed; language floors (hausa/mixed >= FLOOR) so the known Hausa
review-rate drift stays detectable instead of drowning in English volume. Emits
model predictions side by side with blank human_* columns, including
intensity + schema/model per row (version everything). Text is emitted VERBATIM —
same carve-out as data/human_review queues and data/raw (never-modify rule; the
human must label exactly what the model saw); published surfaces quote aggregates
only, never text or handles.
Run: python -m src.classification.eval_sample [n]  (default 100)
"""
import csv
import datetime
import json
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CLS_DIR = ROOT / "data" / "classified"
EVAL_DIR = ROOT / ".evals"
SEED = 42
FLOOR = {"hausa": 10, "mixed": 10}

COLUMNS = [
    "raw_id", "source", "language_label", "sentiment_label", "sentiment_confidence",
    "mentions_candidate_probability", "intensity_score", "lga_relevance_label",
    "opposition_signal_probability", "routing_decision", "schema_version", "model",
    "text",
    "human_sentiment", "human_intensity", "human_lga", "human_mentions",
    "human_opp", "human_language",
]


def load_all():
    text, src = {}, {}
    for p in sorted(RAW_DIR.glob("*.jsonl")):
        for line in p.open(encoding="utf-8"):
            line = line.strip()
            if line:
                r = json.loads(line)
                text[r["raw_id"]] = r.get("text", "")
                src[r["raw_id"]] = r.get("source", "")
    rows = []
    for p in sorted(CLS_DIR.glob("*.csv")):
        if p.name.startswith("pilot"):
            continue
        for r in csv.DictReader(p.open(encoding="utf-8")):
            pid = r["raw_id"].split("#")[0]
            r["text"] = text.get(pid, r.get("text") or "")
            r["source"] = src.get(pid, "")
            rows.append(r)
    return rows


def sample(rows, n, seed=SEED):
    rng = random.Random(seed)
    by_lang = {}
    for r in rows:
        by_lang.setdefault(r.get("language_label") or "unknown", []).append(r)
    picked, used = [], set()
    for lang, grp in by_lang.items():
        rng.shuffle(grp)
        take = min(len(grp), FLOOR.get(lang, 0))
        picked.extend(grp[:take])
        used.update(id(x) for x in grp[:take])
    extras = [r for r in rows if id(r) not in used]
    rng.shuffle(extras)
    picked.extend(extras[:max(0, min(n, len(rows)) - len(picked))])
    picked = picked[:min(n, len(rows))]
    rng.shuffle(picked)
    return picked


def main(argv=None):
    argv = argv if argv is not None else []
    n = int(argv[0]) if argv else 100
    rows = load_all()
    if not rows:
        raise SystemExit("eval_sample: no classified rows")
    picked = sample(rows, n)
    week = datetime.date.today().isocalendar()[1]
    out = EVAL_DIR / f"{datetime.date.today().year}-W{week:02d}_sample{len(picked)}.csv"
    EVAL_DIR.mkdir(exist_ok=True)
    blanks = {c: "" for c in COLUMNS if c.startswith("human_")}
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in picked:
            w.writerow({**r, **blanks})
    langs = {}
    for r in picked:
        k = r.get("language_label") or "unknown"
        langs[k] = langs.get(k, 0) + 1
    print(f"wrote {out} n={len(picked)} langs={langs} seed={SEED} from {len(rows)}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
