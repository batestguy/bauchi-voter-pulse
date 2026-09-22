"""Batch classification runner: raw JSONL -> Jev v2 (one call answers all six) ->
classified CSV + human-review queue. Run: python src/classification/classify.py IN.jsonl OUT.csv
Input row: {raw_id, source, date_scraped, text, url, lga_keyword_match}.
Long texts are chunked at ~6000 chars (32K-token state limit); chunks get raw_id#i rows.
Requires the `jev` CLI + TYPESAFE_API_KEY (see skill: jev)."""
import csv
import json
import os
import pathlib
import subprocess
import sys

from .routing import REVIEW_COLUMNS, SCHEMA_VERSION, THRESHOLD, apply_routing

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = ROOT / "src" / "schema" / "jev_pulse_v2.json"
SPEC_MODEL = json.loads(SPEC.read_text(encoding="utf-8")).get("model", "")
REVIEW_DIR = ROOT / "data" / "human_review"
CLASSIFIED_COLUMNS = [
    "raw_id", "sentiment_label", "sentiment_confidence",
    "mentions_candidate_probability", "intensity_score",
    "lga_relevance_label", "lga_confidence", "opposition_signal_probability",
    "language_label", "language_confidence",
    "routing_decision", "schema_version", "model",
]
CHUNK_CHARS = 6000


def chunk_text(text):
    if len(text) <= CHUNK_CHARS:
        return [text]
    chunks, cur = [], ""
    for para in text.split("\n"):
        while len(para) > CHUNK_CHARS:  # oversized single paragraph: hard-split at whitespace
            cut = para.rfind(" ", 0, CHUNK_CHARS)
            cut = cut if cut > 0 else CHUNK_CHARS
            chunks.append(para[:cut])
            para = para[cut:].lstrip()
        if len(cur) + len(para) + 1 > CHUNK_CHARS and cur:
            chunks.append(cur)
            cur = ""
        cur = f"{cur}\n{para}" if cur else para
    if cur:
        chunks.append(cur)
    return chunks


def run_jev(texts):
    payload = "\n".join(json.dumps({"text": t}, ensure_ascii=False) for t in texts)
    proc = subprocess.run(
        ["jev", "run", str(SPEC), "-l", "--field", "text", "--json", "-j", "8"],
        input=payload, capture_output=True, text=True, encoding="utf-8",
        shell=(os.name == "nt"))  # .cmd shim on Windows needs a shell
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"jev failed: {proc.stderr[-2000:]}")
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def classify_texts(texts):
    out = []
    for ans in run_jev(texts):
        a = ans["answers"]
        out.append({
            "sentiment_label": a["sentiment"]["choice"],
            "sentiment_confidence": round(a["sentiment"]["confidence"], 3),
            "mentions_candidate_probability": round(a["mentions_candidate"]["noul"], 3),
            "intensity_score": a["intensity"]["label"],
            "lga_relevance_label": a["lga_relevance"]["choice"],
            "lga_confidence": round(a["lga_relevance"]["confidence"], 3),
            "opposition_signal_probability": round(a["opposition_signal"]["noul"], 3),
            "language_label": a["language"]["choice"],
            "language_confidence": round(a["language"]["confidence"], 3),
            "model": ans.get("model", SPEC_MODEL),
        })
    return out


def main():
    src, dest = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    raws = [json.loads(l) for l in src.open(encoding="utf-8") if l.strip()]
    jobs = [(r, i, chunk) for r in raws for i, chunk in enumerate(chunk_text(r["text"]))]
    results = classify_texts([c for _, _, c in jobs])
    classified_rows, review_rows = [], []
    for (r, i, chunk), c in zip(jobs, results):
        rid = r["raw_id"] if len(chunk_text(r["text"])) == 1 else f"{r['raw_id']}#{i + 1}"
        decision = apply_routing(c["sentiment_confidence"], c["lga_confidence"], THRESHOLD)
        classified_rows.append({"raw_id": rid, **c, "routing_decision": decision,
                                "schema_version": SCHEMA_VERSION})
        if decision == "human_review":
            review_rows.append({k: ({"raw_id": rid, "text": chunk, **c,
                                     "schema_version": SCHEMA_VERSION}.get(k, ""))
                                for k in REVIEW_COLUMNS})
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CLASSIFIED_COLUMNS)
        w.writeheader()
        w.writerows(classified_rows)
    if review_rows:
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        qpath = REVIEW_DIR / f"queue_{dest.stem}.csv"
        with qpath.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
            w.writeheader()
            w.writerows(review_rows)
        print(f"review queue: {qpath} ({len(review_rows)} rows)")
    auto = sum(1 for r in classified_rows if r["routing_decision"] == "auto")
    print(f"classified: {dest} ({len(classified_rows)} rows, {auto} auto, "
          f"{len(classified_rows) - auto} review)")


if __name__ == "__main__":
    main()
