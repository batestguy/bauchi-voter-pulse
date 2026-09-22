"""Daily ingestion run: Nairaland + news RSS + (token-gated) Facebook.
Dedupes by raw_id against all existing data/raw/*.jsonl, validates every row,
appends only new rows to data/raw/raw_YYYYMMDD.jsonl. Exit 0 even if a source
fails (per-source errors are logged, not fatal) — the cron must stay green.
Run: python -m src.ingestion.run_daily
"""
import datetime
import json
import pathlib

from . import facebook, nairaland, news
from .common import validate_row

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"


def existing_ids():
    ids = set()
    for path in RAW_DIR.glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        ids.add(json.loads(line)["raw_id"])
                    except (json.JSONDecodeError, KeyError):
                        continue
    return ids


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    seen = existing_ids()
    collected = []
    for name, mod in [("nairaland", nairaland), ("news", news), ("facebook", facebook)]:
        try:
            rows = mod.scrape(today)
        except Exception as exc:
            print(f"{name}: FAILED: {exc}")
            continue
        print(f"{name}: {len(rows)} rows scraped")
        collected.extend(rows)
    fresh = []
    for row in collected:
        try:
            validate_row(row)
        except AssertionError as exc:
            print(f"drop invalid row: {exc}")
            continue
        if row["raw_id"] not in seen:
            seen.add(row["raw_id"])
            fresh.append(row)
    out = RAW_DIR / f"raw_{today}.jsonl"
    with out.open("a" if out.exists() else "w", encoding="utf-8") as f:
        for row in fresh:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"daily: {len(collected)} scraped, {len(fresh)} new -> {out}")


if __name__ == "__main__":
    main()
