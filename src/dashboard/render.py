"""Static dashboard generator (Ph.5) — stdlib only, no external assets, no JS build
step, so the Pages cron stays green. Reads data/aggregates/*.csv and renders a
single self-contained docs/index.html: per-LGA risk heatmap (20 tiles, anchored
click-through to per-LGA top-3 negative topics), daily trend (inline SVG),
opposition comparison, full risk table, one-insight briefing block, and the
schema/model/threshold trace footer. Missing files degrade to empty sections —
never crash the weekly rebuild.
Run: python src/dashboard/render.py
"""
import collections
import csv
import datetime
import html
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
AGG = ROOT / "data" / "aggregates"
SCHEMA = ROOT / "src" / "schema" / "jev_pulse_v3.json"
OUT = ROOT / "docs" / "index.html"
sys.path.insert(0, str(ROOT))  # schema json has no version key; routing owns it
from src.classification.routing import SCHEMA_VERSION, THRESHOLD  # noqa: E402

try:  # shared with aggregate when pandas present; fall back to literals standalone
    from src.aggregation.aggregate import RISK_MODEL, SAFE_MAX, SWING_MAX
except Exception:  # pragma: no cover - standalone render without pandas
    RISK_MODEL, SAFE_MAX, SWING_MAX = "risk-v0-heuristic", 0.3, 0.5

LGAS = ["Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
        "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi",
        "Misau", "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki"]

RISK_COLORS = {"safe": "#16a34a", "swing": "#d97706", "at-risk": "#dc2626",
               "unrated": "#64748b"}
SENTIMENT_COLORS = {"positive": "#15803d", "negative": "#b91c1c",
                    "neutral": "#334155", "mixed": "#7c3aed"}


def read_csv(name):
    path = AGG / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def esc(v):
    return html.escape(str(v), quote=True)


def slug(lga):
    return lga.lower().replace(" ", "-")


def fold(rows):
    """Fold multi-row LGA data into dominant sentiment + summed mentions + mean conf."""
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
        "mention_count": d["mentions"],
        "confidence": round(sum(d["conf"]) / len(d["conf"]), 3) if d["conf"] else None,
    } for lga, d in acc.items()}


def heatmap_tiles(by_lga, risk_by_lga):
    tiles = []
    for lga in LGAS:
        risk = risk_by_lga.get(lga, {})
        band = risk.get("risk", "")
        data = by_lga.get(lga, {})
        mentions = data.get("mention_count", 0)
        if not band and not mentions:
            bg, fg, band_txt, m_txt = "#f1f5f9", "#94a3b8", "no data", "—"
        else:
            color = RISK_COLORS.get(band, "#64748b")
            bg, fg = color, "#ffffff"
            band_txt = band or "unrated"
            m_txt = str(mentions) if mentions else "0"
        sent = data.get("sentiment_label") or ""
        detail_id = f"lga-{slug(lga)}" if mentions else ""
        inner = (f"<div class='t-name'>{esc(lga)}</div>"
                 f"<div class='t-band'>{esc(band_txt)}</div>"
                 f"<div class='t-meta'>{m_txt} mentions"
                 + (f" · <span class='t-sent' style='color:{SENTIMENT_COLORS.get(sent, fg)}'>{esc(sent)}</span>" if sent else "")
                 + "</div>")
        if detail_id:
            tiles.append(f"<a class='tile' id='tile-{slug(lga)}' href='#{detail_id}' "
                         f"style='background:{bg};color:{fg}'>{inner}</a>")
        else:
            tiles.append(f"<div class='tile'>{inner}</div>")
    return "\n".join(tiles)


def lga_details(by_lga, lga_topics):
    by_topic_lga = {}
    for r in lga_topics:
        by_topic_lga.setdefault(r.get("lga", ""), []).append(r)
    sections = []
    for lga in LGAS:
        data = by_lga.get(lga)
        if not data or not data.get("mention_count"):
            continue
        rows = sorted(by_topic_lga.get(lga, []),
                      key=lambda r: int(r.get("mentions") or 0), reverse=True)
        neg_rows = [r for r in rows if float(r.get("neg_share") or 0) > 0]
        if neg_rows:
            top3 = "".join(
                f"<li>{esc(r['topic'])} — {esc(r['mentions'])} mentions, "
                f"{float(r['neg_share']):.0%} negative</li>"
                for r in neg_rows[:3])
            topic_html = f"<ul>{top3}</ul>"
        else:
            topic_html = "<p class='muted'>No negative topics in window.</p>"
        conf = data.get("confidence")
        sections.append(
            f"<section class='detail' id='lga-{slug(lga)}'>"
            f"<h3>{esc(lga)}</h3>"
            f"<p class='muted'>{esc(data['mention_count'])} usable mentions · "
            f"dominant {esc(data['sentiment_label'])} · "
            f"mean confidence {conf if conf is not None else '—'}</p>"
            f"<p><strong>Top negative topics</strong></p>{topic_html}</section>")
    return "\n".join(sections)


def trend_svg(daily_rows):
    per_date = collections.OrderedDict()
    for r in sorted(daily_rows, key=lambda x: x.get("date") or ""):
        try:
            n = int(r.get("mention_count") or 0)
        except ValueError:
            n = 0
        per_date[r.get("date") or "?"] = per_date.get(r.get("date") or "?", 0) + n
    items = list(per_date.items())[-30:]
    if not items:
        return "<p class='muted'>No daily data yet.</p>"
    w, h, gap = 640, 140, 6
    max_n = max(n for _, n in items) or 1
    bw = max(4, min(40, (w - 60 - gap * (len(items) - 1)) // len(items)))  # fit all bars
    bars = []
    for i, (date, n) in enumerate(items):
        bh = max(2, int((n / max_n) * (h - 40)))
        x = 30 + i * (bw + gap)
        y = h - 30 - bh
        bars.append(f"<rect x='{x}' y='{y}' width='{bw}' height='{bh}' fill='#2563eb'/>")
        bars.append(f"<text x='{x + bw // 2}' y='{h - 14}' text-anchor='middle' "
                    f"font-size='9' fill='#64748b'>{esc(str(date)[5:])}</text>")
        bars.append(f"<text x='{x + bw // 2}' y='{y - 4}' text-anchor='middle' "
                    f"font-size='10' fill='#0f172a'>{n}</text>")
    return (f"<svg viewBox='0 0 {w} {h}' width='100%' height='{h}' "
            f"role='img' aria-label='Daily usable mentions'>"
            f"<line x1='20' y1='{h - 30}' x2='{w - 10}' y2='{h - 30}' stroke='#cbd5e1'/>"
            + "".join(bars) + "</svg>")


def briefing(by_lga, lga_topics, risk_rows, daily_rows):
    total = sum(d.get("mention_count", 0) for d in by_lga.values())
    bands = collections.Counter(r.get("risk", "") for r in risk_rows)
    at_risk = sorted(r["lga"] for r in risk_rows if r.get("risk") == "at-risk")
    named = [r for r in lga_topics if r.get("lga") in LGAS]  # unclear is not an LGA
    top = max(named, key=lambda r: int(r.get("mentions") or 0), default=None)
    facts = []
    if top:
        facts.append(f"top topic among named LGAs <strong>{esc(top['topic'])}</strong> "
                     f"in {esc(top['lga'])} ({esc(top['mentions'])} mentions, "
                     f"{float(top['neg_share']):.0%} negative there)")
    if at_risk:
        facts.append("<strong>at-risk:</strong> " + esc(", ".join(at_risk)))
    if bands.get("unrated"):
        facts.append(f"{bands['unrated']} LGAs unrated (n<5 — volume below threshold)")
    if not facts:
        return ("<p class='muted'>No usable signal yet — keep collecting; "
                "the briefing activates once auto-routed rows exist.</p>")
    if at_risk:
        action = (f"Field-verify <strong>{esc(', '.join(at_risk))}</strong> "
                  "before treating any band as settled.")
    else:
        action = "No at-risk LGA this window — hold strategy, raise collection volume."
    return (f"<p>Provisional window, <strong>{total} usable mentions</strong> "
            f"(auto-routed ≥{THRESHOLD}): {'; '.join(facts)}.</p>"
            f"<p class='action'>→ {action}</p>")


def main():
    schema = {}
    if SCHEMA.exists():
        import json
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    by_lga = fold(read_csv("lga_weekly.csv"))
    lga_topics = read_csv("lga_topics.csv")
    risk_rows = read_csv("risk.csv")
    opp_rows = read_csv("opposition.csv")
    daily_rows = read_csv("lga_daily.csv")
    risk_by_lga = {(r.get("lga") or ""): r for r in risk_rows}

    built = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tiles = heatmap_tiles(by_lga, risk_by_lga)
    details = lga_details(by_lga, lga_topics) or "<p class='muted'>No LGA detail yet.</p>"
    trend = trend_svg(daily_rows)
    briefing_html = briefing(by_lga, lga_topics, risk_rows, daily_rows)

    named_risks = [r for r in risk_rows if r.get("lga") in LGAS]
    other_risks = [r for r in risk_rows if r.get("lga") not in LGAS]
    risk_table = "".join(
        f"<tr><td>{esc(r.get('lga'))}</td><td><span class='pill' style='background:"
        f"{RISK_COLORS.get(r.get('risk') or '', '#64748b')};color:#fff'>{esc(r.get('risk'))}</span>"
        f"</td><td>{esc(r.get('signals'))}</td></tr>"
        for r in sorted(named_risks, key=lambda x: x.get("lga") or "")) or \
        "<tr><td colspan='3' class='muted'>No risk rows.</td></tr>"
    risk_footnote = "".join(
        f"<p class='muted'>{esc(r.get('lga'))} (not an LGA): band {esc(r.get('risk'))} — "
        f"excluded from heatmap tiles.</p>" for r in other_risks)

    opp_table = "".join(
        f"<tr><td>{esc(r.get('opp'))}</td><td>{esc(r.get('rows'))}</td>"
        f"<td>{float(r.get('neg_share') or 0):.0%}</td>"
        f"<td>{esc(r.get('avg_confidence'))}</td></tr>"
        for r in opp_rows) or \
        "<tr><td colspan='4' class='muted'>No opposition rows yet.</td></tr>"

    unclear_n = by_lga.get("unclear", {}).get("mention_count", 0)

    OUT.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bauchi Voter Pulse</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1100px;margin:1.5rem auto;padding:0 1rem;color:#0f172a}}
h1{{font-size:1.4rem;margin:0 0 .25rem}} h2{{font-size:1.1rem;margin:2rem 0 .75rem}}
.muted{{color:#64748b;font-size:.9rem}} .meta{{color:#64748b;font-size:.85rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.6rem}}
.tile{{border-radius:.5rem;padding:.65rem .7rem;text-decoration:none;display:block;box-shadow:0 1px 2px rgb(0 0 0/.08)}}
a.tile{{transition:transform .1s}} a.tile:hover{{transform:translateY(-2px)}}
.t-name{{font-weight:700;font-size:.95rem}} .t-band{{font-size:.75rem;opacity:.9;text-transform:uppercase;letter-spacing:.03em}}
.t-meta{{font-size:.78rem;opacity:.92;margin-top:.15rem}}
.briefing{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:.6rem;padding:.9rem 1rem;margin-top:.5rem}}
.briefing .action{{background:#fffbe6;border:1px solid #fde68a;border-radius:.4rem;padding:.5rem .7rem;margin:.5rem 0 0}}
.pill{{display:inline-block;border-radius:999px;padding:.1rem .55rem;font-size:.78rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}} th,td{{border:1px solid #e2e8f0;padding:.4rem .6rem;text-align:left}}
.detail{{border-top:1px dashed #cbd5e1;padding:.7rem 0}} .detail h3{{margin:.2rem 0 .3rem}}
.detail ul{{margin:.3rem 0 .3rem 1.1rem;padding:0}}
footer{{margin-top:2.5rem;border-top:1px solid #e2e8f0;padding-top:.8rem;font-size:.82rem;color:#64748b}}
</style></head><body>
<h1>Bauchi Voter Pulse — 20-LGA heatmap</h1>
<p class="meta">Built {built} · schema {SCHEMA_VERSION} · model {esc(schema.get("model", "jev-1.13.0"))} · threshold {THRESHOLD:.2f} · {esc(RISK_MODEL)}</p>
<div class="briefing"><strong>Briefing (one insight)</strong>{briefing_html}</div>
<h2>Heatmap — risk bands (click a tile for top negative topics)</h2>
<div class="grid">{tiles}</div>
<p class="muted">Bands: safe &lt;{SAFE_MAX} neg · swing {SAFE_MAX}–{SWING_MAX} · at-risk &gt;{SWING_MAX} (or narrow-margin penalty) · unrated = n&lt;5 usable.{' ' + str(unclear_n) + ' rows tagged unclear excluded from tiles.' if unclear_n else ''}</p>
<h2>Daily trend — usable mentions</h2>
{trend}
<h2>Per-LGA detail — top-3 negative topics</h2>
{details}
<h2>Opposition comparison</h2>
<table><tr><th>Cohort</th><th>Rows</th><th>Neg share</th><th>Avg confidence</th></tr>{opp_table}</table>
<h2>Risk table</h2>
<table><tr><th>LGA</th><th>Risk</th><th>Signals</th></tr>{risk_table}</table>
{risk_footnote}
<footer>Social/news analysis, not private polling. Auto-route only (confidence ≥{THRESHOLD:.2f}); low-confidence rows await human review. Trace: schema {SCHEMA_VERSION} · model {esc(schema.get("model", "jev-1.13.0"))} · {esc(RISK_MODEL)} · built {built}.</footer>
</body></html>""", encoding="utf-8")
    print(f"wrote {OUT} ({len(by_lga)} LGA rows, {len(lga_topics)} lga-topic rows)")


if __name__ == "__main__":
    main()
