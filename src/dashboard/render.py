"""Static dashboard generator — stdlib only so the Pages cron stays green pre-pilot.
Reads data/aggregates/lga_weekly.csv if present (columns: date,lga,sentiment_label,mention_count,confidence)
else renders 20-LGA placeholder. Folds multiple rows per LGA (multi-day / multi-
sentiment) into dominant sentiment + summed mentions + mean confidence. Writes
docs/index.html with build timestamp + schema v3/model trace."""
import csv
import datetime
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGG = ROOT / "data" / "aggregates" / "lga_weekly.csv"
SCHEMA = ROOT / "src" / "schema" / "jev_pulse_v3.json"
OUT = ROOT / "docs" / "index.html"
sys.path.insert(0, str(ROOT))  # for routing constants (schema file has no version key)
from src.classification.routing import SCHEMA_VERSION  # noqa: E402

LGAS = ["Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
        "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi",
        "Misau", "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki"]


def load_rows():
    if not AGG.exists():
        return []
    with AGG.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fold(rows):
    """Aggregate weekly rows per LGA: dominant sentiment (by mention_count),
    summed mentions, mean confidence — never an arbitrary last-row overwrite."""
    acc = {}
    for r in rows:
        lga = r.get("lga", "")
        if not lga:
            continue
        d = acc.setdefault(lga, {"sent": {}, "mentions": 0, "conf": []})
        try:
            n = int(r.get("mention_count") or 0)
        except ValueError:
            n = 0
        label = r.get("sentiment_label") or ""
        d["sent"][label] = d["sent"].get(label, 0) + n
        d["mentions"] += n
        if r.get("confidence"):
            try:
                d["conf"].append(float(r["confidence"]))
            except ValueError:
                pass
    return {lga: {
        "sentiment_label": max(d["sent"], key=d["sent"].get) if d["sent"] else "",
        "mention_count": str(d["mentions"]),
        "confidence": round(sum(d["conf"]) / len(d["conf"]), 3) if d["conf"] else "",
    } for lga, d in acc.items()}


def main():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    rows = load_rows()
    by_lga = fold(rows)
    built = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cards = "\n".join(
        f"<tr><td>{lga}</td><td>{by_lga.get(lga, {}).get('sentiment_label', 'no data yet')}</td>"
        f"<td>{by_lga.get(lga, {}).get('mention_count', '—')}</td>"
        f"<td>{by_lga.get(lga, {}).get('confidence', '—')}</td></tr>"
        for lga in LGAS
    )
    OUT.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bauchi Voter Pulse</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}}
.meta{{color:#555;font-size:.9rem}}</style></head><body>
<h1>Bauchi Voter Pulse — 20-LGA Sentiment</h1>
<p class="meta">Built {built} · schema {SCHEMA_VERSION} · model {schema["model"]} · threshold {schema.get("threshold", 0.8)} · n={len(rows)} aggregate rows</p>
<table><tr><th>LGA</th><th>Sentiment</th><th>Mentions</th><th>Confidence</th></tr>{cards}</table>
<p class="meta">Social/news analysis, not private polling. Auto-route only (confidence ≥0.80); low-confidence rows await human review.</p>
</body></html>""", encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
