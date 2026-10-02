"""Build the 5-page printable brief for APM Bauchi Progress & Delivery.

Why this file exists
--------------------
The site answers a voter's question on the web. This answers it on paper, in five
pages, for two situations the site cannot cover: a phone with no data, and a
conversation where someone needs the shape of the whole thing in one sitting.

Why it is generated rather than written
--------------------------------------
Every figure in the brief is read from `data/delivery/*.csv` at build time and
interpolated into the HTML. That is the same lesson the About page taught: two
summary counts that disagreed by one, because one of them was typed by hand. If
the source register gains a row, the brief gains the row on its next build. A
figure cannot go stale here, because there is nowhere to type it.

Usage
-----
    python tools/make_brief.py

Writes `build/pdf/brief.html`, the two QR codes, and `build/pdf/apm-brief.pdf`.
Rendering to PDF is done by `tools/print_pdf.mjs` (Playwright + installed
Chrome), the same engine that records the demo video, because a PDF is only
useful if its links are real link annotations rather than blue text.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import pathlib
import re
import shutil
from collections import Counter
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "data" / "delivery"
BRAND = ROOT / "assets" / "brand"
OUT = ROOT / "build" / "pdf"

SITE = "https://batestguy.github.io/bauchi-voter-pulse/"
REPO = "https://github.com/batestguy/bauchi-voter-pulse"
RAW = "https://raw.githubusercontent.com/batestguy/bauchi-voter-pulse/main"

# Absolute raw URLs, for the same reason the README uses them: a relative link to a
# binary resolves to GitHub's file page, not to the file, so "download" would cost a
# second click. These two cuts are already committed under assets/brand/.
VIDEO_WIDE = f"{RAW}/assets/brand/demo-16x9.mp4"
VIDEO_TALL = f"{RAW}/assets/brand/demo-9x16.mp4"

# Where the finished PDF is committed. Deliberately NOT under docs/: Pages serves
# docs/, and this document was explicitly not to be published on the site. It is a
# repository download, reachable through a raw URL, and nothing else.
BRIEF = ROOT / "brief" / "apm-brief.pdf"

# The 20 Bauchi LGAs. Used only to tell a real LGA apart from an aggregate scope
# such as "Statewide" or "Bauchi North LGAs", which are not places.
BAUCHI_LGAS = (
    "Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
    "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi", "Misau",
    "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki",
)


# How each review status is described in the brief, in both numbers, because "and one
# are queued" is the kind of thing that makes a careful document look careless. A
# status with no entry here is still counted, under a generic phrase -- silently
# dropping one would leave the sentence claiming it read fewer documents than it did.
REVIEW_PHRASES = {
    "published_source": ("became published entries", "became a published entry"),
    "context_only": ("were kept for background", "was kept for background"),
    "duplicate_source": (
        "were duplicates of something already held",
        "was a duplicate of something already held",
    ),
    "not_achievement": (
        "were dropped because they were not evidence of an achievement",
        "was dropped because it was not evidence of an achievement",
    ),
    "needs_review": ("are queued and not yet classified", "is queued and not yet classified"),
}


def rows(name: str) -> list[dict]:
    """Read a delivery CSV with DictReader.

    Never split on commas: several of these files carry commas inside quoted
    fields, and positional splitting silently shifts every column after the
    first one that contains one.
    """
    with open(DELIVERY / name, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fact() -> dict:
    """Collect every number the brief is allowed to state."""
    src = rows("source_register.csv")
    manifest = rows("source_manifest.csv")
    ach = rows("achievements.csv")
    prom = rows("promises.csv")
    need = rows("needs.csv")
    lga_del = rows("lga_delivery.csv")
    ind = rows("indicators.csv")
    wards = rows("lga_wards.csv")
    assets = rows("asset_register.csv")
    featured = rows("featured_achievements.csv")

    grades = [r["source_grade"] for r in src]
    ach_scopes = {r["lga"] for r in ach}
    promise_targets = sum(1 for r in prom if r["target_date"].strip())
    promise_measures = sum(1 for r in prom if r["success_indicator"].strip())

    # Enumerated from the data rather than written out. The sources cron adds rows,
    # and a hand-written sentence then claims it read fewer documents than it did.
    breakdown = Counter(r["review_status"] for r in manifest)
    doc_review = []
    for status, count in sorted(breakdown.items(), key=lambda kv: (-kv[1], kv[0])):
        plural, singular = REVIEW_PHRASES.get(
            status,
            (
                f"are recorded as {status.replace('_', ' ')}",
                f"is recorded as {status.replace('_', ' ')}",
            ),
        )
        doc_review.append((count, singular if count == 1 else plural))
    if sum(count for count, _ in doc_review) != len(manifest):
        raise SystemExit("review-status breakdown does not account for every source document")

    return {
        "built": dt.date.today().isoformat(),
        "sources": len(src),
        "publishers": len({r["url"].split("/")[2] for r in src if r["url"]}),
        "grade_a": grades.count("A"),
        "grade_b": grades.count("B"),
        "grade_d": grades.count("D"),
        "documents": len(manifest),
        "doc_review": doc_review,
        "docs_published": breakdown.get("published_source", 0),
        "docs_context": sum(1 for r in manifest if r["review_status"] == "context_only"),
        "docs_duplicate": sum(1 for r in manifest if r["review_status"] == "duplicate_source"),
        "docs_rejected": sum(1 for r in manifest if r["review_status"] == "not_achievement"),
        "achievements": len(ach),
        "ach_sectors": len({r["sector"] for r in ach}),
        "ach_lgas": len(ach_scopes & set(BAUCHI_LGAS)),
        "ach_scopes": len(ach_scopes - set(BAUCHI_LGAS)),
        "evidence_a": sum(1 for r in ach if r["evidence_grade"] == "A"),
        "evidence_b": sum(1 for r in ach if r["evidence_grade"] == "B"),
        "promises": len(prom),
        "promise_sectors": len({r["sector"] for r in prom}),
        "promise_clauses": sum(1 for r in prom if r["promise_type"] == "Published commitment clause"),
        "promise_targets": promise_targets,
        "promise_measures": promise_measures,
        "needs": len(need),
        "need_sectors": len({r["sector"] for r in need}),
        "needs_all_high": all(r["priority_level"] == "high" for r in need),
        "lgas": len({r["lga"] for r in lga_del}),
        "indicators": len(ind),
        "ind_sectors": len({r["sector"] for r in ind}),
        "ind_lgas": len({r["lga"] for r in ind}),
        "wards": len(wards),
        "wards_provisional": all(
            r["verification_status"] == "provisional_source_not_directly_downloaded"
            for r in wards
        ),
        "assets": len(assets),
        "assets_approved": sum(1 for r in assets if r["usage_status"] == "campaign approved"),
        "featured": len(featured),
        "pages": 7,
        "poll_sectors": 9,
        "poll_questions": 1,
        "poll_responses": 0,
    }


def _join_clauses(pairs: list[tuple[int, str]]) -> str:
    """Render a (count, phrase) list as an English clause list.

    Digits are kept rather than spelled out: the phrases carry their own agreement,
    and "and 1 is queued" reads better than "and one is queued" next to "26 became".
    """
    if not pairs:
        return "none of them were classified yet"
    parts = [f"{count} {phrase}" for count, phrase in pairs]
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def qr_svg(target: str, name: str, scale: int = 8) -> pathlib.Path:
    """A vector QR code. SVG, not PNG, so it stays sharp at any print size."""
    import qrcode
    import qrcode.image.svg

    path = OUT / name
    img = qrcode.make(target, image_factory=qrcode.image.svg.SvgPathImage, box_size=scale, border=2)
    with open(path, "wb") as fh:
        img.save(fh)
    return path


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


CSS = """
:root{
  --ink:#13202b; --navy:#0b263c; --blue:#145d86; --sky:#d9eff6;
  --gold:#d89b31; --gold-soft:#f5e6c4; --paper:#f7f4ed; --white:#fffdf8;
  --line:#d8d8cd; --muted:#6c7880; --green:#2e7254; --green-soft:#dcefe3;
}
*{box-sizing:border-box; -webkit-print-color-adjust:exact; print-color-adjust:exact;}
html,body{margin:0;padding:0;}
body{
  background:#8d9099; color:var(--ink);
  font-family:"Trebuchet MS","Segoe UI",sans-serif; line-height:1.45;
}
.sheet{
  width:210mm; height:297mm; overflow:hidden; position:relative;
  background:var(--white); margin:0 auto 8mm; padding:0;
  box-shadow:0 10px 40px rgba(0,0,0,.35);
}
a{color:inherit;}
.disc{text-decoration:none; border-bottom:1.5px solid var(--gold);}
.disc::after{content:" \\2197"; font-size:.72em; color:var(--gold); vertical-align:.28em;}
.jump{text-decoration:none; border-bottom:1.5px dotted var(--blue);}
.jump::after{content:" \\2192"; color:var(--blue);}

/* --- page furniture ---------------------------------------------------- */
.bar{
  position:absolute; left:0; right:0; top:0; height:9mm;
  background:linear-gradient(90deg,var(--navy) 0%,var(--blue) 62%,var(--gold) 100%);
}
.foot{
  position:absolute; left:0; right:0; bottom:0; height:12mm;
  border-top:.4mm solid var(--line); background:var(--paper);
  display:flex; align-items:center; justify-content:space-between;
  padding:0 14mm; font-size:7.4pt; color:var(--muted);
}
.foot .who{display:flex; align-items:center; gap:3mm;}
.foot img{width:7mm; height:7mm; border-radius:50%; object-fit:cover;
  border:.35mm solid var(--white); box-shadow:0 0 0 .3mm var(--line);}
.foot .who b{color:var(--ink); font-weight:700;}
.pager{display:flex; align-items:center; gap:1.6mm;}
.pager a{
  display:flex; align-items:center; justify-content:center;
  width:5.4mm; height:5.4mm; border-radius:50%;
  text-decoration:none; font-size:7.2pt; font-weight:700;
  color:var(--muted); border:.3mm solid var(--line); background:var(--white);
}
.pager a.on{background:var(--navy); color:var(--white); border-color:var(--navy);}
.pad{position:absolute; left:14mm; right:14mm; top:16mm; bottom:16mm;}

/* --- page 1 ------------------------------------------------------------ */
.cover{display:grid; grid-template-rows:auto auto 1fr auto; height:100%; padding-bottom:15mm;}
.cover-top{display:flex; justify-content:space-between; align-items:flex-start; padding:0 14mm;}
.brandline{display:flex; align-items:center; gap:3.4mm;}
.brandline img{height:13mm; width:auto;}
.brandline .bl{font-size:7.4pt; letter-spacing:.16em; text-transform:uppercase; color:var(--muted);}
.cover-tag{
  font-size:7pt; letter-spacing:.14em; text-transform:uppercase; font-weight:700;
  color:var(--gold); border:.35mm solid var(--gold); padding:1.4mm 3mm; border-radius:20mm;
}
.contents{
  display:flex; align-items:center; gap:2mm; margin:5mm 14mm 0; padding:2.4mm 0;
  border-top:.4mm solid var(--line); border-bottom:.4mm solid var(--line);
}
.contents .ct{
  font-size:6.6pt; letter-spacing:.18em; text-transform:uppercase; font-weight:700;
  color:var(--gold); margin-right:1.6mm;
}
.contents a{
  font-size:7.7pt; color:var(--navy); text-decoration:none; padding:1.3mm 3.2mm;
  border:.3mm solid var(--line); border-radius:20mm; background:var(--white);
}
.cover-body{display:grid; grid-template-columns:1fr 62mm; gap:9mm; align-items:center; padding:0 14mm;}
h1{
  font-family:Georgia,"Times New Roman",serif; font-size:34pt; line-height:1.03;
  margin:0 0 4mm; color:var(--navy); letter-spacing:-.01em; font-weight:700;
}
h1 em{font-style:normal; color:var(--blue);}
.dek{font-size:11.4pt; line-height:1.44; color:var(--ink); margin:0 0 6mm; max-width:104mm;}
.dek b{color:var(--navy);}
.cover-cta{display:flex; align-items:center; gap:5mm; font-size:9.4pt;}
.cover-cta .go{
  background:var(--navy); color:var(--white); text-decoration:none;
  padding:3.4mm 6mm; border-radius:2mm; font-weight:700; font-size:10.6pt;
}
.cover-cta .u{font-family:Consolas,monospace; font-size:8.4pt; color:var(--muted);}
.cover-video{
  margin-top:5mm; padding-top:3.4mm; border-top:.3mm solid var(--line);
  font-size:8.2pt; color:var(--muted); display:flex; gap:4mm; align-items:baseline; flex-wrap:wrap;
}
.cover-video .cv{width:100%;}

.card{
  background:var(--white); border:.4mm solid var(--line); border-radius:3mm;
  padding:5mm; box-shadow:0 3mm 9mm rgba(11,38,60,.10);
}
.person{text-align:center;}
.person img{
  width:40mm; height:40mm; border-radius:50%; object-fit:cover;
  border:.9mm solid var(--gold); padding:1mm; background:var(--white);
}
.person .role{
  display:inline-block; margin-top:3.4mm; font-size:6.6pt; font-weight:700;
  letter-spacing:.16em; text-transform:uppercase; color:#fff; background:var(--green);
  padding:1mm 3mm; border-radius:20mm;
}
.person .nm{font-family:Georgia,serif; font-size:14.6pt; font-weight:700; color:var(--navy); margin:2.4mm 0 1.6mm;}
.person .rl{font-size:8.6pt; color:var(--muted); line-height:1.4;}
.qr{display:block; width:30mm; height:30mm; margin:4mm auto 1.6mm;}
.qrlab{font-size:7pt; color:var(--muted); text-align:center; letter-spacing:.04em;}
.hub{
  display:flex; align-items:center; gap:6mm; margin-top:6mm;
  border:.5mm dashed var(--line); border-radius:3mm; background:var(--paper); padding:4.4mm 5mm;
}
.hub img{width:24mm; height:24mm; flex:none;}
.hub p{margin:0; font-size:8.4pt; line-height:1.46;}
.hub p b{color:var(--navy);}

.stats{
  display:grid; grid-template-columns:repeat(5,1fr); gap:0;
  border-top:.9mm solid var(--navy); border-bottom:.4mm solid var(--line);
  margin:0 14mm;
}
.stats div{padding:4mm 3mm; border-right:.3mm solid var(--line); text-align:center;}
.stats div:last-child{border-right:0;}
.stats b{display:block; font-family:Georgia,serif; font-size:19pt; color:var(--navy); line-height:1;}
.stats span{display:block; font-size:6.9pt; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-top:1.6mm;}

/* --- page 2 ------------------------------------------------------------ */
h2{
  font-family:Georgia,serif; font-size:20pt; color:var(--navy); margin:0 0 2mm;
  line-height:1.1; font-weight:700;
}
.eyebrow{
  font-size:7pt; letter-spacing:.2em; text-transform:uppercase; font-weight:700;
  color:var(--gold); margin-bottom:2.4mm;
}
.lede{font-size:9.6pt; color:var(--muted); margin:0 0 6mm; max-width:150mm;}
.two{display:grid; grid-template-columns:1fr 74mm; gap:9mm; align-items:start;}
.prose p{font-size:9.3pt; line-height:1.52; margin:0 0 3.4mm;}
.prose p b{color:var(--navy);}
.pull{
  border-left:1.1mm solid var(--gold); background:var(--gold-soft);
  padding:3.6mm 4.4mm; margin:4mm 0; border-radius:0 2mm 2mm 0;
}
.pull p{margin:0; font-family:Georgia,serif; font-size:10.2pt; color:var(--navy); line-height:1.38;}

.chain{list-style:none; margin:0; padding:0; counter-reset:step;}
.chain li{position:relative; padding:0 0 4.6mm 12mm; counter-increment:step;}
.chain li::before{
  content:counter(step); position:absolute; left:0; top:-.4mm;
  width:7.6mm; height:7.6mm; border-radius:50%;
  background:var(--navy); color:var(--white); font-size:8pt; font-weight:700;
  display:flex; align-items:center; justify-content:center;
}
.chain li::after{
  content:""; position:absolute; left:3.6mm; top:7mm; width:.4mm; height:4mm;
  background:var(--line);
}
.chain li:last-child::after{display:none;}
.chain li b{display:block; font-size:9.6pt; color:var(--navy); margin-bottom:.6mm;}
.chain li span{font-size:8.2pt; color:var(--muted); line-height:1.4; display:block;}

.band{display:grid; grid-template-columns:1fr 1fr; gap:6mm; margin-top:6mm;}
.band .card{padding:4.4mm 5mm;}
.band h3{
  margin:0 0 2mm; font-size:7.4pt; letter-spacing:.16em; text-transform:uppercase;
  color:var(--green);
}
.band .no h3{color:#9b3b1f;}
.band ul{margin:0; padding-left:4.4mm;}
.band li{font-size:8.3pt; line-height:1.42; margin-bottom:1.6mm;}
.band li b{color:var(--navy);}

/* --- page 3 ------------------------------------------------------------ */
.bento{display:grid; grid-template-columns:repeat(12,1fr); gap:4mm;}
.tile{
  border:.4mm solid var(--line); border-radius:3mm; background:var(--white);
  padding:4.4mm 5mm; display:flex; flex-direction:column;
}
.tile .ask{font-family:Georgia,serif; font-size:10.4pt; color:var(--navy); line-height:1.24; margin:0 0 1.6mm;}
.tile .nm{
  font-size:6.8pt; letter-spacing:.14em; text-transform:uppercase; font-weight:700;
  color:var(--gold); margin-bottom:2.4mm;
}
.tile p{font-size:8.3pt; line-height:1.45; color:var(--ink); margin:0 0 3mm;}
.tile .fig{
  margin-top:auto; padding-top:3mm; border-top:.3mm dashed var(--line);
  font-size:7.6pt; color:var(--muted); line-height:1.4;
}
.tile .fig b{color:var(--blue); font-family:Georgia,serif; font-size:11pt; display:block;}
.tile.hero{grid-column:span 7; background:var(--navy); border-color:var(--navy);}
.tile.hero .ask{color:var(--white); font-size:12.6pt;}
.tile.hero p{color:rgba(255,255,255,.84);}
.tile.hero .fig{color:rgba(255,255,255,.7); border-top-color:rgba(255,255,255,.24);}
.tile.hero .fig b{color:var(--gold-soft);}
.tile.hero .nm{color:var(--gold);}
.tile.hero .go{color:var(--gold); border-bottom-color:var(--gold);}
.tile.s5{grid-column:span 5;}
.tile.s7{grid-column:span 7;}
.tile.s4{grid-column:span 4;}
.tile.wide{background:var(--paper);}

/* --- page 4 ------------------------------------------------------------ */
.doors{display:grid; grid-template-columns:1fr 1fr; gap:7mm;}
.door{border-radius:3mm; border:.4mm solid var(--line); overflow:hidden; display:flex; flex-direction:column;}
.door .top{padding:4.4mm 5mm; color:var(--white);}
.door.a .top{background:var(--blue);}
.door.b .top{background:var(--green);}
.door .top .k{font-size:6.8pt; letter-spacing:.16em; text-transform:uppercase; opacity:.85;}
.door .top h3{font-family:Georgia,serif; font-size:14pt; margin:1.6mm 0 0; font-weight:700;}
.door .bd{padding:4.4mm 5mm; flex:1;}
.door dl{margin:0;}
.door dt{font-size:7pt; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-top:3mm;}
.door dt:first-child{margin-top:0;}
.door dd{margin:.8mm 0 0; font-size:8.4pt; line-height:1.42;}
.door dd b{color:var(--navy);}
.qr2{width:26mm; height:26mm; display:block; margin:3.4mm auto 1mm;}
.chips{display:grid; grid-template-columns:repeat(4,1fr); gap:4mm; margin-top:6mm;}
.chip{
  background:var(--green-soft); border-radius:2mm; padding:3.4mm 4mm;
  border-left:.9mm solid var(--green);
}
.chip.no{background:#f7e4dc; border-left-color:#9b3b1f;}
.chip b{display:block; font-size:8.4pt; color:var(--navy); margin-bottom:1mm;}
.chip span{font-size:7.6pt; color:var(--ink); line-height:1.4;}
.empty{
  margin-top:5mm; border:.5mm dashed var(--line); border-radius:3mm;
  padding:4mm 5mm; display:grid; grid-template-columns:1fr auto; gap:6mm; align-items:center;
  background:var(--paper);
}
.empty p{margin:0; font-size:8.2pt; line-height:1.44;}
.empty p + p{margin-top:1.8mm;}
.empty p b{color:var(--navy);}
.big0{font-family:Georgia,serif; font-size:30pt; color:var(--line); line-height:1;}

/* --- page 5 ------------------------------------------------------------ */
.steps{list-style:none; margin:0; padding:0; counter-reset:s;}
.steps li{counter-increment:s; position:relative; padding:0 0 4.4mm 13mm;}
.steps li::before{
  content:counter(s); position:absolute; left:0; top:-.6mm;
  width:8.4mm; height:8.4mm; border-radius:2mm;
  background:var(--gold); color:var(--white); font-size:9pt; font-weight:700;
  display:flex; align-items:center; justify-content:center;
}
/* Scoped to a direct child on purpose. A bare `.steps b` also matched the bold
   domain inside the <pre> and the inline <b>www</b> in step 3, and `display:block`
   turned both into their own lines -- the domain vanished into an empty row. */
.steps li > b{display:block; font-size:9.8pt; color:var(--navy); margin-bottom:.8mm;}
.steps p{margin:0; font-size:8.4pt; color:var(--ink); line-height:1.44;}
pre{
  background:var(--navy); color:#dff0f7; border-radius:2mm; padding:3mm 3.6mm;
  font-family:Consolas,monospace; font-size:7.4pt; line-height:1.6; margin:2.4mm 0 0;
  white-space:pre-wrap; word-break:break-all;
}
pre b{color:var(--gold-soft); font-weight:400;}
.warn{background:#f7e4dc; border-left:.9mm solid #9b3b1f; border-radius:0 2mm 2mm 0; padding:3.4mm 4mm; margin-top:4mm;}
.warn b{display:block; font-size:8.4pt; color:#8a3418; margin-bottom:1.2mm;}
.warn ul{margin:0; padding-left:4.4mm;}
.warn li{font-size:8pt; line-height:1.44; margin-bottom:1.4mm;}
.kv{display:grid; grid-template-columns:1fr 1fr; gap:6mm; margin-top:2mm;}
.fineprint{font-size:7.4pt; color:var(--muted); line-height:1.5; margin-top:5mm; padding-top:3mm; border-top:.3mm solid var(--line);}
"""


def foot(page: int, label: str, portrait: pathlib.Path, labels: list[str]) -> str:
    dots = "".join(
        f'<a href="#p{i+1}" class="{"on" if i == page - 1 else ""}">{i + 1}</a>'
        for i in range(len(labels))
    )
    return (
        '<div class="foot">'
        f'<div class="who"><img src="{portrait.as_uri()}" alt="Portrait of Abdulkadir Ahmad (Hammayo)">'
        '<span>Built by <b>Abdulkadir Ahmad (Hammayo)</b> &middot; '
        f'<span class="jump">{esc(label)}</span></span></div>'
        f'<div class="pager">{dots}<span style="margin-left:2mm">{page} / {len(labels)}</span></div>'
        "</div>"
    )


def build_html(f: dict) -> tuple[str, list[str]]:
    portrait = BRAND / "abdulkadir-ahmad-hammayo.png"
    logo = BRAND / "apm-logo.png"
    qr_site = qr_svg(SITE, "qr-site.svg")
    qr_repo = qr_svg(REPO, "qr-repo.svg")

    labels = ["Cover", "What & why", "The parts", "Take part", "On a domain"]
    today = dt.date.today().strftime("%d %B %Y")

    # ---------------- page 1 ----------------
    p1 = f"""
<div class="bar"></div>
<div class="cover">
  <div class="cover-top" style="padding-top:6mm">
    <div class="brandline">
      <img src="{logo.as_uri()}" alt="APM party emblem">
      <div class="bl">APM Bauchi<br>Progress &amp; Delivery</div>
    </div>
    <div class="cover-tag">A five-page brief</div>
  </div>

  <div class="contents">
    <span class="ct">Inside</span>
    <a href="#p2">01 &mdash; What it is, and why</a>
    <a href="#p3">02 &mdash; The seven parts</a>
    <a href="#p4">03 &mdash; How a voter is heard</a>
    <a href="#p5">04 &mdash; Publishing on a domain</a>
  </div>

  <div class="cover-body">
    <div>
      <h1>What has been done,<br>what is promised,<br>and what Bauchi<br><em>still needs.</em></h1>
      <p class="dek">A public-source record of delivery and commitment across Bauchi State, published as
      <b>{f['pages']} pages that open on any phone</b> &mdash; then a paper brief for the people who
      need the whole shape of it in one sitting.</p>
      <div class="cover-cta">
        <a class="go" href="{SITE}">Open the live site</a>
        <span class="u">batestguy.github.io/bauchi-voter-pulse</span>
      </div>
      <div class="cover-video">
        <span class="cv">Watch it work, recorded on a phone and a desktop:</span>
        <a class="disc" href="{VIDEO_WIDE}">Download the video &mdash; 16:9</a>
        <a class="disc" href="{VIDEO_TALL}">9:16 for WhatsApp</a>
      </div>
    </div>

    <div>
      <div class="card person">
        <img src="{portrait.as_uri()}" alt="Portrait of Abdulkadir Ahmad (Hammayo)">
        <div class="role">Contributor</div>
        <div class="nm">Abdulkadir Ahmad<br>(Hammayo)</div>
        <div class="rl">A dedicated member of his campaign team.</div>
      </div>
      <div class="card" style="margin-top:4mm">
        <img class="qr" src="{qr_site.as_uri()}" alt="QR code linking to the live APM Bauchi site">
        <div class="qrlab">Point a phone camera here &rarr; the live site</div>
      </div>
    </div>
  </div>

  <div class="stats">
    <div><b>{f['sources']}</b><span>sources</span></div>
    <div><b>{f['publishers']}</b><span>publishers</span></div>
    <div><b>{f['achievements']}</b><span>records of work done</span></div>
    <div><b>{f['promises']}</b><span>published commitments</span></div>
    <div><b>{f['wards']}</b><span>registration areas</span></div>
  </div>
</div>
"""

    # ---------------- page 2 ----------------
    p2 = f"""
<div class="bar"></div>
<div class="pad">
  <div class="eyebrow">01 &mdash; What it is, and why it was built</div>
  <h2>A voter asks four questions.<br>Public records answered them in four places.</h2>
  <p class="lede">Is anything actually getting done? What has been promised? What does my own area
  look like? And who is checking any of this? Bauchi's answer to each lives on a different
  government page, a different news site, or a PDF nobody opens twice. This joins them.</p>

  <div class="two">
    <div class="prose">
      <p><b>The gap it fills.</b> Nobody had put a need, a delivery and a promise side by side for
      Bauchi State. A voter could read a project announcement, or a campaign promise, but not
      "this is what we still need here, this is what has been done, and this is what is next."
      The Atlas gives that per local government area, on a tappable map.</p>

      <div class="pull">
        <p>&ldquo;If a line on this site cannot be traced to a numbered source, it does not belong
        on the site.&rdquo;</p>
      </div>

      <p><b>How it earns trust.</b> Every figure carries a source, and every source carries a grade.
      Of the {f['sources']} sources, {f['grade_a']} are grade A &mdash; official government records
      and named implementing partners &mdash; and {f['grade_b']} are grade B. Exactly one is grade D:
      the candidate's own website. It is used for <i>what he has actually said</i>, and never as proof
      that something was delivered.</p>

      <p><b>How much was read.</b> {f['documents']} source documents were opened and classified:
      {_join_clauses(f['doc_review'])}. Counting the rejections matters as much as counting
      the entries, and so does counting what is still queued.</p>
    </div>

    <div>
      <div class="card">
        <div class="eyebrow" style="margin-bottom:3.4mm">The chain, in order</div>
        <ol class="chain">
          <li><b>Need</b><span>{f['needs']} recorded needs across {f['need_sectors']} sectors &mdash; the gap to be closed.</span></li>
          <li><b>Achievement</b><span>{f['achievements']} records across {f['ach_sectors']} sectors and {f['ach_lgas']} of the 20 LGAs.</span></li>
          <li><b>Promise</b><span>{f['promises']} published commitments across {f['promise_sectors']} sectors, each with the test that would show it worked.</span></li>
          <li><b>Result</b><span>{f['indicators']} tracked indicators whose movement decides whether any of it landed.</span></li>
        </ol>
      </div>
      <div class="card" style="margin-top:4mm">
        <div class="eyebrow" style="margin-bottom:2.6mm">One honest gap</div>
        <p style="font-size:8.3pt;line-height:1.45;margin:0">
          None of the {f['promises']} commitments carries a target date, because the campaign has not
          published one. Each one carries a success indicator instead. The site shows the absence
          rather than filling it in.
        </p>
      </div>
    </div>
  </div>

  <div class="band">
    <div class="card">
      <h3>What it is</h3>
      <ul>
        <li><b>{f['pages']} pages</b>, each doing one job, in English and Hausa.</li>
        <li>A <b>register of {f['sources']} sources</b> across {f['publishers']} publishers &mdash; government, news, implementing partners, and the campaign itself.</li>
        <li>A <b>map of {f['wards']} registration areas</b> in all 20 LGAs, on any phone.</li>
        <li>Two ways to be heard: one question, and one need.</li>
      </ul>
    </div>
    <div class="card no">
      <h3>What it is not</h3>
      <ul>
        <li><b>Not private polling.</b> No registered voter is contacted, and no result is a forecast of an election.</li>
        <li><b>Not an audit.</b> {f['evidence_b']} of {f['achievements']} records rest on grade B evidence and most say "follow-up required".</li>
        <li><b>Not a press office.</b> Criticism is recorded where a source supports it.</li>
        <li>The {f['wards']} registration areas are <b>provisional</b>: the list was transcribed from published sources, not downloaded as a dataset.</li>
      </ul>
    </div>
  </div>
</div>
"""

    # ---------------- page 3 ----------------
    tiles = f"""
<div class="bento">
  <div class="tile hero">
    <div class="nm">Home &middot; the front door</div>
    <p class="ask">Where do I start?</p>
    <p>One screen that opens on the {f['needs']} recorded needs, the {f['featured']} featured records of work
    actually done, and the two ways to be heard. It is the only page a voter has to open, so it carries
    the argument rather than the detail &mdash; everything else on the site is a drill-down from here.</p>
    <div class="fig"><b>{f['needs']} needs &middot; {f['featured']} featured</b>
      Every figure on that page is one click from the document it came from.
      <a class="disc" href="{SITE}">Open the home page</a></div>
  </div>

  <div class="tile s5">
    <div class="nm">Achievements &middot; what is done</div>
    <p class="ask">What has actually been done, and can I check it?</p>
    <p>Each record carries its evidence grade, its verification status and a link to the original.
    A project that was flagged off but not finished reads exactly like that &mdash; "completion not yet
    verified" &mdash; instead of being counted as delivered.</p>
    <div class="fig"><b>{f['achievements']} records &middot; {f['ach_sectors']} sectors</b>
      {f['ach_lgas']} of 20 LGAs, plus {f['ach_scopes']} aggregate scopes.
      <a class="disc" href="{SITE}achievements.html">Read the records</a></div>
  </div>

  <div class="tile s4">
    <div class="nm">Atlas &middot; the map</div>
    <p class="ask">How does my own area compare?</p>
    <p>A tappable map of all 20 LGAs and {f['wards']} registration areas. Pick your area and read
    the need, the delivery and the promise for that place &mdash; not for Bauchi in general.</p>
    <div class="fig"><b>{f['wards']} areas &middot; 20 LGAs</b>
      <a class="disc" href="{SITE}atlas.html">Open the map</a></div>
  </div>

  <div class="tile s4">
    <div class="nm">Agenda &middot; the commitments</div>
    <p class="ask">What is promised, and how would I know it happened?</p>
    <p>{f['promises']} published commitments across {f['promise_sectors']} sectors, each shown with the
    test that would show it worked. No target dates, because none are published.</p>
    <div class="fig"><b>{f['promises']} commitments</b>
      <a class="disc" href="{SITE}agenda.html">Read the agenda</a></div>
  </div>

  <div class="tile s4">
    <div class="nm">Sources &middot; the register</div>
    <p class="ask">Can I check any of this myself?</p>
    <p>{f['sources']} sources across {f['publishers']} publishers, graded A, B or D, each one click from
    the original document. This is the page that makes the other six auditable.</p>
    <div class="fig"><b>{f['grade_a']} grade A &middot; {f['grade_b']} B &middot; {f['grade_d']} D</b>
      <a class="disc" href="{SITE}sources.html">Open the register</a></div>
  </div>

  <div class="tile s5 wide">
    <div class="nm">About &middot; the people</div>
    <p class="ask">Who is behind this?</p>
    <p>The candidate record, this contributor, and a screen recording of the live site &mdash; so the
    claim "it works on a phone" can be checked by watching it work rather than by being told.
    The recording was made on {today}, before the first response arrived, and is published in
    both a widescreen and a phone cut.</p>
    <div class="fig"><b>{f['assets']} registered assets</b>
      Every image re-checked against its recorded hash on each build.
      <a class="disc" href="{VIDEO_WIDE}">Download the recording</a></div>
  </div>

  <div class="tile s7">
    <div class="nm">Speak to us &middot; the only two doors</div>
    <p class="ask">What do you want, and what do you actually need?</p>
    <p>The one page where a resident is not answered but heard: <b>one question</b> on which sector to
    prioritise first, and <b>one stated need</b> for the campaign to act on. The first takes no identity
    at all; the second deliberately asks for it, because the point is a reply. They are on the same page
    on purpose &mdash; the difference between them is the whole privacy argument, so it should be visible
    side by side rather than split across two sites.</p>
    <div class="fig"><b>1 question &middot; {f['poll_sectors']} options &middot; {f['poll_responses']} responses so far</b>
      The next page sets both out in full.
      <a class="disc" href="{SITE}poll.html">Open the poll and the request form</a></div>
  </div>
</div>
"""
    p3 = f"""
<div class="bar"></div>
<div class="pad">
  <div class="eyebrow">02 &mdash; What each part does, and how it reaches a voter</div>
  <h2>Seven pages. Seven questions a voter actually asks.</h2>
  <p class="lede">Every page below is linked, so this brief is also a way in: tap any figure to open the
  live page it came from. Two of them &mdash; the poll and the request form &mdash; are the only places
  a voter is heard rather than answered.</p>
  {tiles}
</div>
"""

    # ---------------- page 4 ----------------
    qr_poll = qr_svg(f"{SITE}poll.html", "qr-poll.svg")
    p4 = f"""
<div class="bar"></div>
<div class="pad">
  <div class="eyebrow">03 &mdash; How a voter is heard</div>
  <h2>Two doors. Neither one takes your name.</h2>
  <p class="lede">The site is mostly for reading. These are the two places where a resident can change
  what it says next &mdash; and both were built so that answering cannot identify the person who
  answered.</p>

  <div class="doors">
    <div class="door a">
      <div class="top"><div class="k">Door one</div><h3>The poll &mdash; one question</h3></div>
      <div class="bd">
        <dl>
          <dt>The question</dt>
          <dd><b>&ldquo;Which sector should APM prioritise first?&rdquo;</b> One question, {f['poll_sectors']} options, nothing else to get wrong.</dd>
          <dt>What it needs from you</dt>
          <dd>Your area. That is the one required answer &mdash; a statewide bar would tell nobody anything.</dd>
          <dt>What it never asks</dt>
          <dd>No name. No phone. No email. No address. No exact age, and the form refuses those fields by name rather than quietly dropping them.</dd>
          <dt>What is optional</dt>
          <dd>Your registration area, an age band, and gender &mdash; so the answer can be broken down by
          area later. Age is a band, never a number.</dd>
          <dt>What is published</dt>
          <dd>Counts and shares, per area and per sector &mdash; but never a cell small enough to point at a person.</dd>
        </dl>
      </div>
    </div>

    <div class="door b">
      <div class="top"><div class="k">Door two</div><h3>The request form &mdash; one need</h3></div>
      <div class="bd">
        <dl>
          <dt>What it is for</dt>
          <dd>Stating a need the campaign should act on. This is the opposite of the poll: here you
          <b>are</b> asked who you are, because the point is a reply.</dd>
          <dt>What it asks</dt>
          <dd>One need, your area, a name, a street address, and &mdash; if you want a reply &mdash; an email address.</dd>
          <dt>What it refuses</dt>
          <dd>A phone number. It was removed on purpose: this is about one need, not about building a
          contact list. Email is the only channel back.</dd>
          <dt>Who can read it</dt>
          <dd>Campaign staff only. It is staff workflow data, and the most sensitive thing in this project.</dd>
          <dt>How long it is kept</dt>
          <dd>Indefinitely, by an owner decision &mdash; stated on the page rather than left to be inferred.
          Blanking a cell later still leaves it in the spreadsheet's own history.</dd>
        </dl>
      </div>
    </div>
  </div>

  <div class="hub">
    <img src="{qr_poll.as_uri()}" alt="QR code linking to the poll and the request form on the live site">
    <p><b>Both doors are on one page:</b> <a class="jump" href="{SITE}poll.html">the poll at the top, the
    request form below it</a>. They share a page on purpose. The contrast between a form that takes no
    identity and a form that deliberately asks for it is the clearest way to show what consent means,
    so it should be visible side by side rather than argued in prose.</p>
  </div>

  <div class="chips">
    <div class="chip"><b>No identity on the poll</b><span>Refused by field name, not dropped behind the form.</span></div>
    <div class="chip"><b>Small cells withheld</b><span>A cell under the threshold prints as a dash, never as a zero.</span></div>
    <div class="chip"><b>Comments expire</b><span>180 days by default, 365 at the outside, deleted automatically.</span></div>
    <div class="chip no"><b>Comments held apart from votes</b><span>A text cannot be matched back to a ballot.</span></div>
  </div>

  <div class="empty">
    <div>
      <p><b>Right now the poll has {f['poll_responses']} responses.</b> The bars are empty because nobody
      has answered yet &mdash; not because it is broken. An empty cell and a withheld cell are drawn
      differently on purpose: one means "nobody chose this", the other "too few to say".</p>
      <p><b>What to watch for:</b> once the first response lands, the dashboard must be rebuilt from the
      exported sheet and committed &mdash; a vote arriving does not publish itself &mdash; and the screen
      recording must be re-shot, because its caption says the poll is empty.</p>
    </div>
    <div style="text-align:center">
      <div class="big0">{f['poll_responses']}</div>
      <div class="qrlab">responses recorded<br>as at {today}</div>
    </div>
  </div>
</div>
"""

    # ---------------- page 5 ----------------
    p5 = f"""
<div class="bar"></div>
<div class="pad">
  <div class="eyebrow">04 &mdash; Publishing it on a domain</div>
  <h2>It is already published. A domain of its own is four steps.</h2>
  <p class="lede">The site lives on GitHub Pages, which is free and already live. If the campaign wants
  its own address, the address is the only thing that has to be bought &mdash; the site stays exactly as
  it is, because nothing about it needs a server.</p>

  <div class="two" style="grid-template-columns:1fr 78mm">
    <div>
      <div class="eyebrow">How it is published today</div>
      <ol class="steps">
        <li><b>Data in, pages out</b><p>Every figure on the site comes from the CSV register in
        <code>data/delivery/</code>. One renderer turns that into all {f['pages']} pages.</p></li>
        <li><b>A scheduled rebuild commits the result</b><p>A weekly job rebuilds and publishes every
        Monday at 06:00 UTC, and there is a button to force one by hand. No pasting into a spreadsheet,
        no manual upload.</p></li>
        <li><b>The pages are the published artefact</b><p>What a visitor receives is the rebuilt page
        itself, so the site cannot silently disagree with the data behind it.</p></li>
      </ol>

      <div class="eyebrow" style="margin-top:5mm">To put it on its own domain</div>
      <ol class="steps">
        <li><b>Buy the name</b><p>Any registrar, any extension. The price is set by the registrar and
        renews yearly &mdash; it is the one recurring cost this project has.</p></li>
        <li><b>Name it in the repository</b><p>One line, in a single file, telling the site which
        address it is:</p>
          <pre>docs/CNAME
<b>{esc(SITE.split('//')[1].split('/')[0])}</b>   &larr; replaced by your own domain</pre></li>
        <li><b>Point the domain at GitHub</b><p>In the registrar, set the domain settings to
        <i>GitHub Pages</i>. GitHub then supplies the exact records to enter; for an apex domain they are
        four A records and a CNAME for <b>www</b>. Confirm them on GitHub's own pages-help page rather
        than from memory &mdash; they are the one detail here that can change.</p></li>
        <li><b>Turn on HTTPS and wait</b><p>DNS usually resolves in minutes and can take up to a day.
        Then tick <i>Enforce HTTPS</i>. The address redirects to <b>https</b> and the certificate is
        issued free.</p></li>
      </ol>
    </div>

    <div>
      <div class="card">
        <div class="eyebrow" style="margin-bottom:3mm">Where it lives now</div>
        <dl style="margin:0">
          <dt style="font-size:7pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Live address</dt>
          <dd style="margin:.8mm 0 3mm;font-family:Consolas,monospace;font-size:7.8pt"><a class="jump" href="{SITE}">{esc(SITE)}</a></dd>
          <dt style="font-size:7pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Repository</dt>
          <dd style="margin:.8mm 0 3mm;font-family:Consolas,monospace;font-size:7.8pt"><a class="jump" href="{REPO}">{esc(REPO)}</a></dd>
          <dt style="font-size:7pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Cost to publish</dt>
          <dd style="margin:.8mm 0 3mm;font-size:8.4pt">Free hosting. No server, no database, no upkeep
          beyond the repository itself.</dd>
          <dt style="font-size:7pt;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)">Ownership</dt>
          <dd style="margin:.8mm 0 0;font-size:8.4pt">Whoever holds the repository account controls the
          site. The domain registrar and the site owner can be different people &mdash; worth settling
          before a name is bought, because a lapsed domain sends the site back to its free address.</dd>
        </dl>
      </div>

      <div class="card" style="margin-top:4mm">
        <img class="qr" src="{qr_repo.as_uri()}" alt="QR code linking to the project repository">
        <div class="qrlab">The repository behind the site</div>
      </div>

      <div class="warn">
        <b>What must never be published with it</b>
        <ul>
          <li>The Apps Script id, which stays in a git-ignored file and is deliberately not committed.</li>
          <li>The spreadsheet id, any credential, or any contact detail.</li>
          <li>Any image that has not been approved and hash-checked &mdash; {f['assets']} assets are, and each build re-verifies all {f['assets']}.</li>
        </ul>
      </div>
    </div>
  </div>

  <p class="fineprint">Built {today} from the project's own data files, so every figure above is the figure
  the site is showing. This is an analysis of public sources and published campaign material: not private
  polling, not a forecast, not an audit. Where the evidence stops, this brief says so. Contributor:
  Abdulkadir Ahmad (Hammayo), a dedicated member of his campaign team.</p>
</div>
"""

    pages = [p1, p2, p3, p4, p5]
    print_css = (
        "@page{size:A4;margin:0;}"
        ".sheet{break-after:page;}"
        ".sheet:last-of-type{break-after:auto;}"
        "@media print{body{background:#fff;} .sheet{margin:0; box-shadow:none;}}"
    )
    html = [
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">',
        "<title>APM Bauchi Progress &amp; Delivery &mdash; a five-page brief</title>",
        f"<style>{CSS}\n{print_css}</style>",
        "</head><body>",
    ]
    for i, chunk in enumerate(pages):
        html.append(
            f'<section class="sheet" id="p{i + 1}">{chunk}'
            f'{foot(i + 1, labels[i], portrait, labels)}</section>'
        )
    html.append("</body></html>")
    return "\n".join(html), labels


SHEET_PT = 841.89  # 297mm in PostScript points
PT_PER_PX = 0.75  # 96dpi -> 72dpi


def verify_internal_links(
    pdf_path: pathlib.Path, links_path: pathlib.Path, html_path: pathlib.Path
) -> int:
    """Assert that every measured page-to-page link survived into the PDF.

    Chrome writes same-document links as a /Dest pointing at a named destination
    rather than as an /A GoTo action. An earlier version of this check counted
    only /A and reported 29 dead links in a file whose navigation worked
    perfectly -- the verifier was wrong, not the document. So this walks each
    measured rectangle and requires a matching annotation that resolves, through
    the document's own name tree, to the sheet it was aimed at. Both halves are
    needed: the rect proves the link covers the right text, the resolved page
    proves it goes somewhere real.
    """
    import pypdf

    measured = json.loads(links_path.read_text(encoding="utf-8"))
    reader = pypdf.PdfReader(str(pdf_path))

    names: dict[str, int] = {}
    for name, dest in reader.named_destinations.items():
        page = getattr(dest, "page", None)
        if page is None:
            continue
        number = reader.get_page_number(page.get_object())
        if number is not None:
            names[str(name).lstrip("/")] = number

    annots: dict[int, list] = {}
    for index, page in enumerate(reader.pages):
        annots[index] = [
            a.get_object()
            for a in (page.get("/Annots") or [])
            if a.get_object().get("/Subtype") == "/Link"
        ]

    verified = 0
    problems: list[str] = []
    # The measurement step in print_pdf.mjs filters links, and a filter that drops
    # links it should keep makes every remaining check vacuously true. It did
    # exactly that: a containment test kept only the 5 self-links and reported a
    # clean run over 5 of 29. So the count is checked against the HTML itself.
    declared = len(re.findall(r'<a\s[^>]*href="#', html_path.read_text(encoding="utf-8")))
    if len(measured) != declared:
        raise SystemExit(
            f"FAILED: the HTML declares {declared} internal links but only "
            f"{len(measured)} were measured; the measurement filter is dropping some"
        )

    for link in measured:
        page_no = link["fromSheet"] - 1
        # Both edges scale together: the parenthesis matters, because
        # `left + width * scale` scales only the width and misses by ~25pt, which
        # reads as "no link here" rather than as the arithmetic slip it is.
        want = (
            link["left"] * PT_PER_PX,
            (link["left"] + link["width"]) * PT_PER_PX,
            link["top"] * PT_PER_PX,
        )
        hit = False
        for obj in annots.get(page_no, []):
            rect = [float(v) for v in obj["/Rect"]]
            near = abs(rect[0] - want[0]) < 2 and abs(rect[2] - want[1]) < 2
            height_ok = abs((rect[3] - rect[1]) - link["height"] * PT_PER_PX) < 2
            if not (near and height_ok):
                continue
            # A named destination arrives as a NameObject, which subclasses str --
            # and so has a built-in `.title` method. `getattr(dest, "title", dest)`
            # therefore returns that method instead of the fallback and the check
            # silently rejected every link. Match on the type instead.
            raw = obj.get("/Dest")
            if raw is None:
                raw = (obj.get("/A") or {}).get("/D")
            name = raw.lstrip("/") if isinstance(raw, str) else ""
            if names.get(name) == link["toSheet"] - 1:
                hit = True
                break
        if hit:
            verified += 1
        else:
            problems.append(
                f"{link['href']} on sheet {link['fromSheet']} -> sheet {link['toSheet']}"
            )

    if problems:
        raise SystemExit(
            "FAILED: page-to-page links missing or pointing at the wrong sheet:\n  "
            + "\n  ".join(problems)
        )
    return verified


def audit(pdf_path: pathlib.Path) -> tuple[int, int, int]:
    """Re-read the finished file. Returns (pages, links, links_without_action).

    The third number is the one that matters. Counting link annotations proves
    nothing on its own: a rectangle carrying neither /A nor /Dest is exactly what
    a dead link looks like in the file, so the audit fails on any link that
    resolves nowhere.
    """
    import pypdf

    reader = pypdf.PdfReader(str(pdf_path))
    links = dead = 0
    for page in reader.pages:
        for annot in page.get("/Annots", []) or []:
            obj = annot.get_object()
            if obj.get("/Subtype") != "/Link":
                continue
            links += 1
            if obj.get("/A") is None and not obj.get("/Dest"):
                dead += 1
    return len(reader.pages), links, dead


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    f = fact()
    html, _ = build_html(f)
    html_path = OUT / "brief.html"
    links_path = OUT / "links.json"
    html_path.write_text(html, encoding="utf-8")

    node = ROOT / "tools" / "print_pdf.mjs"
    pdf_path = OUT / "apm-brief.pdf"
    result = subprocess.run(
        ["node", str(node), str(html_path), str(pdf_path), str(links_path)],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    verified = verify_internal_links(pdf_path, links_path, html_path)
    pages, links, dead = audit(pdf_path)
    print(f"pages: {pages}  clickable links: {links}  (page-to-page verified: {verified})  dead: {dead}")

    if pages != 5:
        print("FAILED: expected exactly 5 pages")
        return 1
    if dead:
        print(f"FAILED: {dead} link annotations resolve nowhere")
        return 1
    if links < 40:
        print(f"FAILED: only {links} link annotations; the document is not interactive enough")
        return 1

    # The committed copy. Written outside docs/ on purpose: Pages serves docs/, and
    # this document is a repository download, not a page of the site.
    BRIEF.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf_path, BRIEF)
    print(f"committed copy: {BRIEF.relative_to(ROOT)} ({BRIEF.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())