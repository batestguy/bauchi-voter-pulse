"""Delta classification for the weekly CI run: classify raw rows whose parent id is
in NO existing classified CSV, into a fresh batch file. The scratch JSONL is written
to the system temp dir — never to data/raw/ (aggregate globs *.jsonl there and a
temp join file once inflated counts). If the target-date batch already exists a
sequence suffix is used so nothing is overwritten. In CI (env CI set) any runner
failure (missing key/CLI, API down) prints a warning and exits 0 — the cron must
stay green and rendering proceeds on existing classifications.
Run: python -m src.classification.classify_new [YYYY-MM-DD]
"""
import csv
import datetime
import json
import os
import pathlib
import sys
import tempfile

from .classify import main as classify_main

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
CLS_DIR = ROOT / "data" / "classified"


def classified_parents():
    ids = set()
    for p in CLS_DIR.glob("*.csv"):
        if p.name.startswith("pilot"):
            continue
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                ids.add(r["raw_id"].split("#")[0])
    return ids


def unclassified_lines(parents):
    out = []
    for p in sorted(RAW_DIR.glob("*.jsonl")):
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rid = json.loads(line)["raw_id"]
                except (json.JSONDecodeError, KeyError):
                    continue
                if rid not in parents:
                    out.append(line)
    return out


def fresh_dest(date_str):
    dest = CLS_DIR / f"batch_{date_str}.csv"
    n = 2
    while dest.exists():
        dest = CLS_DIR / f"batch_{date_str}_{n}.csv"
        n += 1
    return dest


def main(argv=None):
    try:
        _run(argv)
    except Exception as exc:  # CI must stay green: missing key/CLI, API down, I/O
        if os.environ.get("CI"):
            print(f"classify_new: WARNING skipped in CI: {exc}")
            return
        raise


def _run(argv):
    argv = argv if argv is not None else sys.argv[1:]
    date_str = argv[0] if argv else datetime.date.today().isoformat()
    lines = unclassified_lines(classified_parents())
    if not lines:
        print("classify_new: all raw rows already classified")
        return
    dest = fresh_dest(date_str)
    fd, tmp = tempfile.mkstemp(prefix="to_classify_", suffix=".jsonl")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"classify_new: {len(lines)} unclassified rows -> {dest.name}")
        classify_main(["classify", tmp, str(dest)])
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


if __name__ == "__main__":
    main()
