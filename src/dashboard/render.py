"""Static dashboard generator — stdlib only so the Pages cron stays green pre-pilot.
Reads data/aggregates/lga_weekly.csv if present (columns: date,lga,sentiment_label,mention_count,confidence),
else renders 20-LGA placeholder. Writes docs/index.html with build timestamp + schema/model trace."""
import csv
import datetime
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGG = ROOT / "data" / "aggregates" / "lga_weekly.csv"
SCHEMA = ROOT / "src" / "schema" / "schema_v1.json"
OUT = ROOT / "docs" / "index.html"

LGAS = ["Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
        "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi",
        "Misau", "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki"]


def load_rows():
    if not AGG.exists():
        return []
    with AGG.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    rows = load_rows()
    by_lga = {r.get("lga", ""): r for r in rows}
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
<p class="meta">Built {built} · schema {schema["schema_version"]} · model {schema["model"]} · threshold {schema["routing_threshold"]} · n={len(rows)} aggregate rows</p>
<table><tr><th>LGA</th><th>Sentiment</th><th>Mentions</th><th>Confidence</th></tr>{cards}</table>
<p class="meta">Social/news analysis, not private polling. Placeholder until Ph.1–5 pipeline lands.</p>
</body></html>""", encoding="utf-8")
    print(f"wrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
