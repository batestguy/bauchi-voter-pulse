import csv
import datetime
import hashlib
import html
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "delivery"
ASSETS = ROOT / "assets" / "brand"
DOCS = ROOT / "docs"
OUT = DOCS / "index.html"

LGAS = [
    "Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
    "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi", "Misau",
    "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki"
]

ASSET_FILES = [
    "apm-logo.png", "yakubu-adamu-hero.png", "yakubu-adamu-portrait.png", "bala-mohammed.png"
]

SECTOR_LABELS = {
    "health": "Health and nutrition",
    "education": "Education and skills",
    "wash": "Water and climate resilience",
    "livelihoods": "Jobs and livelihoods",
    "security": "Safety and public trust",
    "agriculture": "Agriculture and food systems",
    "governance": "Service delivery and governance",
    "infrastructure": "Infrastructure and connectivity",
}

SECTOR_HA = {
    "health": "Kafi lafiya da ciwon suji",
    "education": "Ilimi da koyarwa",
    "wash": "Ruwan sha da bambancin yanayi",
    "livelihoods": "Aiki da rayuwa",
    "security": "Tsaro da aminci",
    "agriculture": "Noma da abinci",
    "governance": "Isar da g hanyayi da gwaji",
    "infrastructure": "Infastructure da haɗi",
}


def read_csv(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def esc(value):
    return html.escape(str(value or ""), quote=True)


def attr(en, ha):
    return f'data-en="{esc(en)}" data-ha="{esc(ha)}"'


def copy(en, ha):
    return f'<span {attr(en, ha)}>{esc(en)}</span>'


def localized(en, ha):
    return f'<span {attr(en, ha)}>{esc(en)}</span>'


def status_class(status):
    return {
        "Progress delivered": "status-progress",
        "Project underway": "status-underway",
        "Approval milestone": "status-milestone",
        "Promise to complete": "status-promise",
        "Next priority": "status-next",
        "Outcome being measured": "status-measured",
    }.get(status, "status-underway")


def source_link(source_id, sources, label="Source", label_ha=""):
    source = sources.get(source_id, {})
    if not source.get("url"):
        return ""
    return (f'<a class="source-link" href="{esc(source["url"])}" '
            f'target="_blank" rel="noopener noreferrer">{localized(label, label_ha or label)} <span aria-hidden="true">↗</span></a>')


def status_badge(status, ha=""):
    return f'<span class="status {status_class(status)}" {attr(status, ha)}>{esc(status)}</span>'



def prepare_assets():
    target = DOCS / "assets" / "brand"
    target.mkdir(parents=True, exist_ok=True)
    for name in ASSET_FILES:
        source = ASSETS / name
        if source.exists():
            shutil.copy2(source, target / name)


def build_sources():
    return {row.get("source_id", ""): row for row in read_csv("source_register.csv")}


def build_needs():
    return {row.get("sector", ""): row for row in read_csv("needs.csv") if row.get("sector")}


def build_promises():
    return {row.get("sector", ""): row for row in read_csv("promises.csv") if row.get("sector")}


def build_achievements():
    rows = read_csv("achievements.csv")
    grouped = {}
    for row in rows:
        sector = row.get("sector") or "other"
        grouped.setdefault(sector, []).append(row)
    return rows, grouped


def validate_indicator_rows(rows):
    indicator_ids = [row.get("indicator_id", "") for row in rows]
    if len(indicator_ids) != len(set(indicator_ids)):
        raise ValueError("duplicate indicator_id")
    allowed_statuses = {"Progress delivered", "Project underway", "Outcome being measured", "Approval milestone"}
    required_fields = ["indicator_id", "sector", "lga", "indicator", "indicator_ha", "current_value", "current_unit", "current_year", "status", "source_id", "measurement_note"]
    for row in rows:
        for field in required_fields:
            if not row.get(field):
                raise ValueError(f"blank indicator field: {row.get('indicator_id', '')}:{field}")
        if row["status"] not in allowed_statuses:
            raise ValueError(f"invalid indicator status: {row['status']}")
        for field in ["baseline_year", "current_year", "target_year"]:
            if row.get(field) and (not row[field].isdigit() or not 2000 <= int(row[field]) <= 2100):
                raise ValueError(f"invalid indicator year: {row.get('indicator_id', '')}:{field}")
        if row.get("baseline_value") and (not row.get("baseline_unit") or not row.get("baseline_year")):
            raise ValueError(f"baseline lacks unit or year: {row['indicator_id']}")
        if row.get("target_value") and (not row.get("current_unit") or not row.get("target_year")):
            raise ValueError(f"target lacks unit or year: {row['indicator_id']}")


def validate_data():
    required = {
        "source_register.csv": {"source_id", "url", "content_hash", "source_grade", "usage_note"},
        "needs.csv": {"need_id", "lga", "sector", "need_text", "source_id"},
        "achievements.csv": {"achievement_id", "sector", "status", "source_id", "verification_status"},
        "promises.csv": {"promise_id", "sector", "promise_text", "source_id"},
        "lga_delivery.csv": {"lga", "coverage_type", "status"},
        "asset_register.csv": {"file", "sha256", "usage_status", "approved_by", "approved_at"},
        "source_manifest.csv": {"document_id", "url", "content_hash", "local_file", "review_status"},
        "review_queue.csv": {"candidate_id", "title", "url", "review_status"},
        "indicators.csv": {
            "indicator_id", "sector", "lga", "indicator", "indicator_ha", "baseline_value",
            "baseline_unit", "baseline_year", "current_value", "current_unit", "current_year",
            "target_value", "target_year", "status", "source_id", "measurement_note"
        },
    }
    for name, columns in required.items():
        rows = read_csv(name)
        if not rows:
            raise ValueError(f"empty delivery table: {name}")
        missing = columns - set(rows[0])
        if missing:
            raise ValueError(f"{name} missing columns: {sorted(missing)}")
    sources = read_csv("source_register.csv")
    source_ids = [row["source_id"] for row in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("duplicate source_id")
    indicator_rows = read_csv("indicators.csv")
    validate_indicator_rows(indicator_rows)
    for name in ["needs.csv", "achievements.csv", "promises.csv", "indicators.csv"]:
        for row in read_csv(name):
            if row["source_id"] not in source_ids:
                raise ValueError(f"unknown source_id in {name}: {row['source_id']}")
    for row in read_csv("source_register.csv"):
        if len(row["content_hash"]) != 64:
            raise ValueError(f"invalid source hash: {row['source_id']}")
    for row in read_csv("asset_register.csv"):
        asset = ASSETS / row["file"]
        if not asset.exists():
            raise FileNotFoundError(asset)
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            raise ValueError(f"asset hash mismatch: {row['file']}")
        if row["usage_status"] != "campaign approved" or not row["approved_at"]:
            raise ValueError(f"asset is not approved: {row['file']}")
    manifest_rows = read_csv("source_manifest.csv")
    manifest_by_source = {}
    for row in manifest_rows:
        snapshot = DATA / row["local_file"]
        if not snapshot.exists():
            raise FileNotFoundError(snapshot)
        if hashlib.sha256(snapshot.read_bytes()).hexdigest() != row["content_hash"]:
            raise ValueError(f"source snapshot hash mismatch: {row['document_id']}")
        if not row["source_id"].startswith("discovery-"):
            manifest_by_source[row["source_id"]] = row
    for row in read_csv("source_register.csv"):
        manifest = manifest_by_source.get(row["source_id"])
        if manifest and manifest["content_hash"] != row["content_hash"]:
            raise ValueError(f"source register hash mismatch: {row['source_id']}")


def source_footer(sources):
    return "".join(
        f'<li><span class="source-grade">{esc(row.get("source_grade", "?"))}</span> '
        f'<span><strong>{esc(row.get("title", "Untitled source"))}</strong>'
        f'<small>{copy("Published", "An wallafa")} {esc(row.get("publication_date", "date unknown"))} · {copy("Retrieved", "An ɗauko")} {esc(row.get("retrieved_date", "date unknown"))}</small>'
        f'<small>{esc(row.get("usage_note", ""))}</small></span>'
        f'{source_link(row.get("source_id", ""), sources, "Open", "Buɗe")}</li>'
        for row in sources.values()
    )


def achievement_list(rows, sources):
    items = []
    for row in rows:
        items.append(
            f'<li class="achievement-item"><div class="item-top">'
            f'<strong>{localized(row.get("project_or_programme", ""), row.get("project_or_programme_ha", ""))}</strong>'
            f'{status_badge(row.get("status", ""), row.get("status_ha", ""))}</div>'
            f'<p>{localized(row.get("description", ""), row.get("description_ha", ""))}</p>'
            f'<div class="item-meta"><span>{esc(row.get("date", ""))}</span>'
            f'<span>{esc(row.get("actor", ""))}</span><span>{esc(row.get("verification_status", ""))}</span>{source_link(row.get("source_id", ""), sources, "Source", "Sauro")}</div></li>'
        )
    return "".join(items) or '<li class="empty-item">No public achievement record yet.</li>'


def indicator_cards(rows, sources):
    items = []
    for row in rows:
        baseline = row.get("baseline_value") or "Baseline pending"
        current = row.get("current_value") or "Current value pending"
        unit = row.get("current_unit") or row.get("baseline_unit") or ""
        current_year = row.get("current_year")
        current_label = f"{current} · {current_year}" if current_year else current
        target = row.get("target_value")
        target_year = row.get("target_year")
        target_label = f"Target {target}{(' by ' + target_year) if target_year else ''}" if target else "Target not set"
        items.append(
            f'<article class="indicator-card"><div class="indicator-top"><span class="eyebrow">{esc(row.get("lga", "Statewide"))} · {esc(row.get("sector", ""))}</span>{status_badge(row.get("status", ""), row.get("status", ""))}</div>'
            f'<h3>{localized(row.get("indicator", ""), row.get("indicator_ha", ""))}</h3>'
            f'<div class="indicator-value"><strong>{esc(current_label)}</strong><span>{esc(unit)}</span></div>'
            f'<p>{esc(row.get("measurement_note", ""))}</p>'
            f'<div class="indicator-meta"><span>{copy("Baseline", "Tsarin asal")} {esc(baseline)} · {esc(target_label)}</span>{source_link(row.get("source_id", ""), sources, "Source", "Sauro")}</div></article>'
        )
    return "".join(items)


def arrow_card(sector, need, promise, achievements, sources):
    label = SECTOR_LABELS.get(sector, sector.title())
    ha = SECTOR_HA.get(sector, label)
    need_text = need.get("need_text", "A public priority for Bauchi") if need else "A public priority for Bauchi"
    need_text_ha = need.get("need_text_ha", need_text) if need else need_text
    promise_text = promise.get("promise_text", "Build on progress and complete the next priority.") if promise else "Build on progress and complete the next priority."
    promise_text_ha = promise.get("promise_text_ha", promise_text) if promise else promise_text
    result_text = " · ".join(row.get("outcome_measure", "") for row in achievements if row.get("outcome_measure")) or "Define and measure the next result."
    result_text_ha = " · ".join(row.get("outcome_measure_ha", "") for row in achievements if row.get("outcome_measure_ha")) or "An tsara da aunawa na sakamako na gaba."
    need_source = source_link(need.get("source_id", ""), sources, "Need source", "Sauro na buƙatar") if need else ""
    promise_source = source_link(promise.get("source_id", ""), sources, "Promise source", "Sauro na alkawari") if promise else ""
    return f'''
    <article class="arrow-card reveal" data-sector="{esc(sector)}">
      <div class="arrow-head">
        <div class="eyebrow">{copy(label, ha)}</div>
        <span class="arrow-index">{esc(sector[:2].upper())}</span>
      </div>
      <div class="arrow-path">
        <div class="path-node need-node"><span class="node-number">01</span><h3>{copy("Public need", "Bincike na buƙatar al'umma")}</h3><p>{localized(need_text, need_text_ha)}</p><span class="node-tag">{copy("Needs evidence", "Tabbacin buƙatar")}</span>{need_source}</div>
        <div class="path-arrow" aria-hidden="true">→</div>
        <div class="path-node achievement-node"><span class="node-number">02</span><h3>{copy("Current achievement", "Acikaken sa na yanzu")}</h3><ul class="achievement-list">{achievement_list(achievements, sources)}</ul><span class="node-tag">{copy("Public record", "Bayanan al'umma")}</span></div>
        <div class="path-arrow" aria-hidden="true">→</div>
        <div class="path-node promise-node"><span class="node-number">03</span><h3>{copy("APM promise", "Alkawarin APM")}</h3><p>{localized(promise_text, promise_text_ha)}</p><span class="node-tag">{copy("Campaign commitment", "Alkawarin gaggawa")}</span>{promise_source}</div>
        <div class="path-arrow" aria-hidden="true">→</div>
        <div class="path-node result-node"><span class="node-number">04</span><h3>{copy("Next result", "Sami na gaba")}</h3><p>{localized(result_text, result_text_ha)}</p><span class="node-tag">{copy("Measure what changes", "Auna abin da za ta canza")}</span></div>
      </div>
    </article>'''


def lga_atlas(lga_rows):
    tiles = []
    for lga in LGAS:
        row = next((r for r in lga_rows if r.get("lga") == lga), {})
        specific = row.get("coverage_type") == "lga_specific"
        label = "LGA evidence" if specific else "Statewide"
        label_ha = "Tabbacin LGA" if specific else "Jihada"
        summary = row.get("achievement_summary", "")
        summary_ha = row.get("achievement_summary_ha", summary)
        promise = row.get("apm_promise", "")
        promise_ha = row.get("apm_promise_ha", promise)
        result = row.get("next_result", "")
        result_ha = row.get("next_result_ha", result)
        class_name = "lga-tile lga-specific" if specific else "lga-tile"
        tiles.append(
            f'<button class="{class_name}" type="button" data-lga="{esc(lga)}" '
            f'data-summary="{esc(summary)}" data-summary-ha="{esc(summary_ha)}" '
            f'data-promise="{esc(promise)}" data-promise-ha="{esc(promise_ha)}" '
            f'data-result="{esc(result)}" data-result-ha="{esc(result_ha)}">'
            f'<span class="lga-dot"></span><strong>{esc(lga)}</strong><small {attr(label, label_ha)}>{label}</small></button>'
        )
    return "".join(tiles)


def render():
    validate_data()
    prepare_assets()
    sources = build_sources()
    needs = build_needs()
    promises = build_promises()
    achievement_rows, achievement_groups = build_achievements()
    lga_rows = read_csv("lga_delivery.csv")
    indicator_rows = read_csv("indicators.csv")
    manifest_rows = read_csv("source_manifest.csv")
    review_rows = read_csv("review_queue.csv")
    pending_review_rows = [row for row in review_rows if row.get("review_status") == "needs_review"]
    built = datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y · %H:%M UTC")
    arrow_cards = []
    for sector in ["health", "education", "wash", "infrastructure", "governance", "livelihoods", "security", "agriculture"]:
        rows = achievement_groups.get(sector, [])
        if sector in ["livelihoods", "security", "agriculture"] and not rows:
            continue
        arrow_cards.append(arrow_card(sector, needs.get(sector), promises.get(sector), rows, sources))
    source_count = len(sources)
    achievement_count = len(achievement_rows)
    promise_count = len(read_csv("promises.csv"))
    hero_image = "assets/brand/yakubu-adamu-hero.png"
    portrait_image = "assets/brand/yakubu-adamu-portrait.png"
    governor_image = "assets/brand/bala-mohammed.png"
    indicator_section = f'''<section class="indicator-section" id="indicators"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("Measurement ledger", "Rajista na aunawa")}</div><h2>{copy("Delivery becomes useful when results are visible.", "Isar da sabis tana da sauƙi idan an nuna sakamako.")}</h2></div><p>{copy("These indicators separate reported delivery outputs from the outcomes still being measured. Blank baselines remain blank by design.", "Wannan alamu na bambanta abubuwan da aka isar da sakamako da zuwa da ake aunawa. Babu komai a cikin tushen sai an gani.")}</p></div><div class="indicator-grid">{indicator_cards(indicator_rows, sources)}</div></div></section>'''
    html_doc = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="APM Bauchi Progress and Delivery: public needs, current achievements, campaign commitments and next results.">
<link rel="icon" type="image/png" href="assets/brand/apm-logo.png">
<title>APM Bauchi Progress &amp; Delivery</title>
<style>
:root{{--ink:#13202b;--navy:#0b263c;--blue:#145d86;--sky:#d9eff6;--gold:#d89b31;--gold-soft:#f5e6c4;--paper:#f7f4ed;--white:#fffdf8;--line:#d8d8cd;--muted:#6c7880;--green:#2e7254;--green-soft:#dcefe3;--shadow:0 24px 70px rgba(11,38,60,.14)}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:"Trebuchet MS","Segoe UI",sans-serif;line-height:1.55;overflow-x:hidden}}
body::before{{content:"";position:fixed;inset:0;pointer-events:none;opacity:.12;background-image:radial-gradient(#13202b .55px,transparent .55px);background-size:7px 7px;mix-blend-mode:multiply;z-index:10}}
a{{color:inherit}}
.shell{{width:min(1240px,calc(100% - 40px));margin:auto}}
.topbar{{position:absolute;z-index:2;top:0;left:0;right:0;color:#fff;padding:22px 0}}
.topbar-inner{{display:flex;align-items:center;justify-content:space-between;gap:20px}}
.brand{{display:flex;align-items:center;gap:12px;text-decoration:none}}
.brand img{{width:116px;height:auto;filter:brightness(0) invert(1)}}
.brand small{{display:block;font-size:10px;letter-spacing:.16em;text-transform:uppercase;opacity:.74;margin-top:-3px}}
.nav{{display:flex;align-items:center;gap:24px;font-size:12px;letter-spacing:.06em;text-transform:uppercase}}
.nav a{{opacity:.78;text-decoration:none}}
.nav a:hover{{opacity:1}}
.lang{{display:flex;border:1px solid rgba(255,255,255,.4);border-radius:999px;padding:3px}}
.lang button{{border:0;background:transparent;color:#fff;padding:5px 9px;border-radius:999px;cursor:pointer;font:inherit;font-size:10px}}
.lang button.active{{background:#fff;color:var(--navy)}}
.hero{{min-height:760px;background:var(--navy);color:#fff;position:relative;overflow:hidden;display:flex;align-items:center;padding:128px 0 74px}}
.hero::before{{content:"";position:absolute;width:900px;height:900px;right:-220px;top:-340px;border:1px solid rgba(255,255,255,.13);border-radius:50%;box-shadow:0 0 0 70px rgba(255,255,255,.025),0 0 0 140px rgba(255,255,255,.02)}}
.hero::after{{content:"";position:absolute;inset:auto -10% 0;height:180px;background:linear-gradient(180deg,transparent,rgba(5,20,31,.5));clip-path:polygon(0 100%,100% 22%,100% 100%)}}
.hero-grid{{display:grid;grid-template-columns:1.02fr .98fr;align-items:center;gap:56px;position:relative;z-index:1}}
.eyebrow{{font-size:11px;letter-spacing:.19em;text-transform:uppercase;font-weight:700;color:var(--gold)}}
.hero h1{{font-family:Georgia,"Times New Roman",serif;font-size:clamp(3.5rem,7.3vw,7.3rem);font-weight:400;line-height:.91;letter-spacing:-.06em;margin:22px 0 26px;max-width:760px}}
.hero h1 em{{color:#f4c35d;font-style:normal}}
.hero-lede{{font-size:clamp(1.05rem,1.7vw,1.35rem);color:rgba(255,255,255,.76);max-width:590px;margin:0 0 32px}}
.hero-actions{{display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
.btn{{display:inline-flex;align-items:center;gap:10px;padding:14px 18px;border:1px solid transparent;border-radius:999px;text-decoration:none;font-weight:700;font-size:12px;letter-spacing:.05em;text-transform:uppercase;transition:transform .2s,box-shadow .2s,background .2s}}
.btn:hover{{transform:translateY(-2px)}}
.btn-primary{{background:var(--gold);color:var(--navy);box-shadow:0 12px 24px rgba(216,155,49,.22)}}
.btn-secondary{{color:#fff;border-color:rgba(255,255,255,.28);background:rgba(255,255,255,.04)}}
.hero-note{{margin-top:30px;display:flex;gap:18px;align-items:center;color:rgba(255,255,255,.65);font-size:11px;letter-spacing:.08em;text-transform:uppercase}}
.hero-note::before{{content:"";width:38px;height:1px;background:var(--gold)}}
.portrait-wrap{{min-height:570px;position:relative;display:flex;align-items:end;justify-content:center}}
.portrait-wrap::before{{content:"";position:absolute;width:380px;height:380px;border-radius:50%;background:var(--gold);top:35px;right:25px;opacity:.9}}
.portrait-wrap::after{{content:"";position:absolute;width:420px;height:520px;border:1px solid rgba(255,255,255,.23);right:-20px;top:0;transform:rotate(8deg)}}
.portrait{{position:relative;z-index:1;width:min(100%,520px);max-height:610px;object-fit:contain;object-position:center bottom;filter:drop-shadow(0 30px 35px rgba(0,0,0,.25));mix-blend-mode:screen}}
.portrait-caption{{position:absolute;z-index:2;bottom:20px;left:0;max-width:240px;padding:14px 16px;background:rgba(255,253,248,.95);color:var(--ink);border-radius:3px;box-shadow:var(--shadow);font-size:12px}}
.portrait-caption strong{{display:block;font-family:Georgia,serif;font-size:20px;font-weight:400}}
.motto{{font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.55);margin-top:34px}}
.stats{{background:var(--gold);color:var(--navy);position:relative;z-index:3;margin-top:-1px}}
.stats-grid{{display:grid;grid-template-columns:repeat(4,1fr)}}
.stat{{padding:24px 28px;border-right:1px solid rgba(11,38,60,.18)}}
.stat:last-child{{border-right:0}}
.stat strong{{display:block;font-family:Georgia,serif;font-size:2.25rem;font-weight:400;line-height:1}}
.stat span{{display:block;font-size:10px;letter-spacing:.14em;text-transform:uppercase;margin-top:8px;font-weight:700}}
.section{{padding:100px 0}}
.section-head{{display:flex;justify-content:space-between;align-items:end;gap:30px;margin-bottom:38px}}
.section-head h2,.section-head h3{{font-family:Georgia,serif;font-size:clamp(2.2rem,4vw,4rem);font-weight:400;line-height:.98;letter-spacing:-.05em;margin:12px 0 0;max-width:720px}}
.section-head p{{color:var(--muted);max-width:360px;font-size:14px;margin:0}}
.light-rule{{border-top:1px solid var(--line)}}
.intro-grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:80px;align-items:start}}
.intro-copy{{font-family:Georgia,serif;font-size:clamp(1.7rem,3vw,2.7rem);line-height:1.08;letter-spacing:-.04em;margin:0}}
.note-box{{border-left:3px solid var(--gold);padding:8px 0 8px 22px;color:var(--muted);font-size:14px}}
.progress-path{{background:var(--white);border:1px solid var(--line);box-shadow:var(--shadow);padding:22px;display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-top:60px}}
.path-step{{padding:22px 20px;position:relative;min-height:180px}}
.path-step:not(:last-child)::after{{content:"→";position:absolute;right:-13px;top:76px;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--gold);color:var(--navy);font-size:19px;z-index:2}}
.step-no{{font-size:10px;letter-spacing:.16em;color:var(--gold);font-weight:700}}
.path-step h3{{font-family:Georgia,serif;font-size:1.4rem;font-weight:400;margin:18px 0 8px}}
.path-step p{{font-size:13px;color:var(--muted);margin:0}}
.filter-row{{display:flex;gap:8px;flex-wrap:wrap;margin:28px 0 22px}}
.filter{{border:1px solid var(--line);background:transparent;border-radius:999px;padding:8px 13px;font:inherit;font-size:11px;cursor:pointer;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
.filter.active,.filter:hover{{background:var(--navy);border-color:var(--navy);color:#fff}}
.arrow-list{{display:grid;gap:18px}}
.arrow-card{{background:var(--white);border:1px solid var(--line);padding:0;overflow:hidden;box-shadow:0 12px 35px rgba(11,38,60,.05)}}
.arrow-head{{display:flex;justify-content:space-between;align-items:center;padding:17px 22px;border-bottom:1px solid var(--line);background:#fbfaf6}}
.arrow-index{{font-family:Georgia,serif;font-size:1.2rem;color:var(--gold)}}
.arrow-path{{display:grid;grid-template-columns:1fr 28px 1.45fr 28px 1.2fr 28px 1.1fr;align-items:stretch;padding:22px}}
.path-node{{padding:18px;min-width:0}}
.path-node:nth-child(odd){{background:#f7f8f3;border:1px solid #e4e8df;border-radius:2px}}
.achievement-node{{background:var(--green-soft)!important;border-color:#c9e0ce!important}}
.promise-node{{background:#fff6e5!important;border-color:#efd9ac!important}}
.result-node{{background:#eaf4f7!important;border-color:#c8e0e8!important}}
.path-arrow{{display:grid;place-items:center;color:var(--gold);font-size:24px;padding-top:70px}}
.node-number{{font-size:10px;color:var(--muted);letter-spacing:.15em}}
.path-node h3{{font-family:Georgia,serif;font-size:1.35rem;font-weight:400;line-height:1.1;margin:15px 0 9px}}
.path-node p{{font-size:13px;line-height:1.45;margin:0 0 14px;color:#35434a}}
.node-tag{{display:inline-block;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);border-top:1px solid currentColor;padding-top:6px}}
.achievement-list{{list-style:none;padding:0;margin:0 0 14px;display:grid;gap:9px}}
.achievement-item{{border-bottom:1px solid rgba(46,114,84,.22);padding-bottom:9px}}
.achievement-item:last-child{{border-bottom:0;padding-bottom:0}}
.item-top{{display:flex;align-items:start;justify-content:space-between;gap:10px}}
.item-top strong{{font-size:12px;line-height:1.25}}
.achievement-item p{{font-size:11px;margin:5px 0;color:#4b6259}}
.item-meta{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:9px;color:#567064}}
.status{{display:inline-block;white-space:nowrap;border-radius:999px;padding:3px 6px;font-size:8px;letter-spacing:.06em;text-transform:uppercase;font-weight:700}}
.status-progress{{background:var(--green);color:#fff}}
.status-underway{{background:var(--blue);color:#fff}}
.status-milestone{{background:#765b9e;color:#fff}}
.status-promise{{background:var(--gold);color:var(--navy)}}
.status-next{{background:#b88920;color:#fff}}
.status-measured{{background:#7a6c9b;color:#fff}}
.source-link{{font-size:9px;text-decoration:none;color:var(--blue);font-weight:700;white-space:nowrap}}
.source-link:hover{{text-decoration:underline}}
.empty-item{{font-size:12px;color:var(--muted)}}
.lga-section{{background:var(--navy);color:#fff;position:relative;overflow:hidden}}
.lga-section::before{{content:"";position:absolute;width:600px;height:600px;border:1px solid rgba(255,255,255,.12);border-radius:50%;right:-180px;top:-260px;box-shadow:0 0 0 50px rgba(255,255,255,.025),0 0 0 100px rgba(255,255,255,.02)}}
.lga-section .section-head h2{{color:#fff}}
.lga-section .section-head p{{color:rgba(255,255,255,.65)}}
.lga-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;position:relative;z-index:1}}
.lga-tile{{text-align:left;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.05);color:#fff;padding:18px 16px;min-height:105px;cursor:pointer;font:inherit;position:relative;transition:background .2s,transform .2s,border .2s}}
.lga-tile:hover,.lga-tile.active{{background:rgba(216,155,49,.17);border-color:var(--gold);transform:translateY(-3px)}}
.lga-tile.lga-specific{{border-color:rgba(216,155,49,.62);background:rgba(216,155,49,.08)}}
.lga-tile.lga-specific .lga-dot{{box-shadow:0 0 0 4px rgba(216,155,49,.16)}}
.lga-tile strong{{display:block;font-family:Georgia,serif;font-size:1.25rem;font-weight:400}}
.lga-tile small{{display:block;color:rgba(255,255,255,.55);font-size:9px;letter-spacing:.1em;text-transform:uppercase;margin-top:20px}}
.lga-dot{{display:block;width:7px;height:7px;border-radius:50%;background:var(--gold);margin-bottom:12px}}
.lga-detail{{margin-top:26px;border:1px solid rgba(255,255,255,.2);padding:25px;background:rgba(255,255,255,.06);display:flex;justify-content:space-between;gap:30px;align-items:start}}
.lga-detail h3{{font-family:Georgia,serif;font-size:2rem;font-weight:400;margin:0 0 8px}}
.lga-detail p{{color:rgba(255,255,255,.66);font-size:14px;max-width:620px;margin:0}}
.lga-detail .detail-label{{color:var(--gold);font-size:10px;text-transform:uppercase;letter-spacing:.15em;white-space:nowrap}}
.governance-grid{{display:grid;grid-template-columns:.9fr 1.1fr;gap:64px;align-items:start}}
.governor-card{{background:var(--navy);color:#fff;padding:16px;box-shadow:var(--shadow);position:relative}}
.governor-card img{{width:100%;height:440px;object-fit:cover;object-position:center top;display:block;filter:saturate(.8)}}
.governor-caption{{padding:18px 12px 12px;display:flex;justify-content:space-between;gap:12px;align-items:end}}
.governor-caption strong{{font-family:Georgia,serif;font-size:1.7rem;font-weight:400}}
.governor-caption span{{color:rgba(255,255,255,.55);font-size:10px;text-align:right;line-height:1.4}}
.governance-copy h3{{font-family:Georgia,serif;font-size:clamp(2rem,4vw,3.8rem);font-weight:400;line-height:1;letter-spacing:-.05em;margin:0 0 20px}}
.governance-copy p{{font-size:15px;color:var(--muted);max-width:560px}}
.continuity-list{{display:grid;gap:12px;margin-top:28px}}
.continuity-item{{display:grid;grid-template-columns:32px 1fr;gap:12px;padding:16px 0;border-top:1px solid var(--line)}}
.continuity-item b{{color:var(--gold);font-family:Georgia,serif;font-size:1.5rem;font-weight:400}}
.continuity-item span{{font-size:13px}}
.agenda-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}
.agenda-card{{min-height:250px;background:var(--white);border:1px solid var(--line);padding:20px;display:flex;flex-direction:column;justify-content:space-between;transition:transform .2s,box-shadow .2s}}
.agenda-card:hover{{transform:translateY(-4px);box-shadow:var(--shadow)}}
.agenda-card .agenda-no{{font-family:Georgia,serif;font-size:2.6rem;color:var(--gold);line-height:1}}
.agenda-card h3{{font-family:Georgia,serif;font-size:1.35rem;font-weight:400;line-height:1.1;margin:15px 0 8px}}
.agenda-card p{{font-size:11px;color:var(--muted);margin:0}}
.sources-section{{background:#ecebe4;padding:70px 0}}
.indicator-section{{padding:100px 0;background:#eef5f1;border-top:1px solid var(--line)}}
.indicator-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
.indicator-card{{background:var(--white);border:1px solid var(--line);padding:20px;min-height:220px;box-shadow:0 12px 30px rgba(11,38,60,.05);display:flex;flex-direction:column}}
.indicator-top{{display:flex;justify-content:space-between;align-items:start;gap:10px}}
.indicator-top .eyebrow{{font-size:9px;letter-spacing:.12em}}
.indicator-card h3{{font-family:Georgia,serif;font-size:1.25rem;font-weight:400;line-height:1.15;margin:20px 0 12px}}
.indicator-value{{display:flex;align-items:baseline;gap:8px;color:var(--navy)}}
.indicator-value strong{{font-family:Georgia,serif;font-size:1.7rem;font-weight:400}}
.indicator-value span{{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
.indicator-card p{{font-size:11px;color:var(--muted);line-height:1.45;margin:12px 0 16px}}
.indicator-meta{{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-top:auto;font-size:9px;color:var(--muted)}}
.source-list{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:1fr 1fr;gap:0 32px}}
.source-list li{{display:grid;grid-template-columns:32px 1fr auto;align-items:center;gap:10px;padding:13px 0;border-bottom:1px solid #d4d5cb;font-size:12px}}
.source-list li span:nth-child(2){{display:grid;gap:3px}}
.source-list li small{{font-size:9px;color:var(--muted)}}
.source-legend{{display:flex;flex-wrap:wrap;gap:14px;margin:20px 0 0;font-size:10px;color:var(--muted)}}
.source-grade{{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--navy);color:#fff;font-size:10px;font-weight:700}}
.source-link{{justify-self:end}}
.site-footer{{background:#081d2c;color:#fff;padding:34px 0 28px}}
.footer-inner{{display:flex;justify-content:space-between;gap:30px;align-items:center}}
.footer-inner p{{font-size:11px;color:rgba(255,255,255,.56);margin:0;max-width:650px}}
.footer-inner strong{{font-family:Georgia,serif;font-size:1.3rem;font-weight:400;display:block;margin-bottom:6px}}
.deerflow{{font-size:10px;color:rgba(255,255,255,.45);text-decoration:none;border:1px solid rgba(255,255,255,.2);padding:7px 10px;border-radius:999px;white-space:nowrap}}
.deerflow:hover{{color:#fff;border-color:#fff}}
.reveal{{opacity:0;transform:translateY(15px);animation:rise .7s ease forwards;animation-delay:var(--delay,0s)}}
@keyframes rise{{to{{opacity:1;transform:translateY(0)}}}}
@media (prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;animation:none!important;transition:none!important}}.reveal{{opacity:1;transform:none}}}}
@media (max-width:1050px){{.indicator-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media (max-width:760px){{.indicator-section{{padding:70px 0}}.indicator-grid{{grid-template-columns:1fr}}}}
@media (max-width:1050px){{.nav{{display:none}}.hero-grid{{grid-template-columns:1fr .8fr;gap:20px}}.portrait-wrap{{min-height:470px}}.lga-grid{{grid-template-columns:repeat(4,1fr)}}.agenda-grid{{grid-template-columns:repeat(3,1fr)}}.arrow-path{{grid-template-columns:1fr 20px 1.4fr 20px 1.2fr 20px 1.1fr;padding:14px}}}}
@media (max-width:760px){{.shell{{width:min(100% - 28px,1240px)}}.hero{{min-height:auto;padding-top:112px;padding-bottom:54px}}.hero-grid,.intro-grid,.governance-grid{{grid-template-columns:1fr}}.hero h1{{font-size:clamp(3.2rem,16vw,5.5rem)}}.portrait-wrap{{min-height:390px;margin-top:20px}}.portrait-wrap::before{{width:280px;height:280px;right:4%}}.portrait-wrap::after{{width:320px;height:400px;right:1%}}.portrait{{max-height:420px}}.stats-grid{{grid-template-columns:1fr 1fr}}.stat{{padding:18px 15px;border-bottom:1px solid rgba(11,38,60,.18)}}.stat:nth-child(2){{border-right:0}}.section{{padding:70px 0}}.section-head{{display:block}}.section-head p{{margin-top:18px}}.progress-path{{grid-template-columns:1fr;padding:16px}}.path-step{{min-height:0;padding:14px 16px 24px}}.path-step:not(:last-child)::after{{content:"↓";right:auto;left:18px;top:auto;bottom:-14px}}.arrow-head{{padding:15px 16px}}.arrow-path{{display:block;padding:14px}}.path-node{{margin-bottom:10px;padding:16px}}.path-arrow{{padding:0;height:24px;transform:rotate(90deg)}}.lga-grid{{grid-template-columns:1fr 1fr}}.lga-detail{{display:block}}.lga-detail .detail-label{{display:block;margin-bottom:12px}}.governor-card img{{height:340px}}.agenda-grid{{grid-template-columns:1fr 1fr}}.source-list{{grid-template-columns:1fr}}.footer-inner{{display:block}}.deerflow{{display:inline-block;margin-top:20px}}}}
</style>
</head>
<body>
<header class="hero" id="top">
  <div class="topbar"><div class="shell topbar-inner"><a class="brand" href="#top"><img src="assets/brand/apm-logo.png" alt="Allied Peoples Movement logo"><small>Allied Peoples' Movement</small></a><nav class="nav"><a href="#progress">{copy("Progress", "Ci gaban")}</a><a href="#atlas">{copy("LGA atlas", "Taswirar LGA")}</a><a href="#continuity">{copy("Continuity", "Ci gaba")}</a><a href="#agenda">{copy("APM agenda", "Bayan-APM")}</a><a href="#indicators">{copy("Indicators", "Alamu")}</a><a href="#sources">{copy("Sources", "Bayane")}</a></nav><div class="lang"><button type="button" data-lang="en" class="active" aria-pressed="true">EN</button><button type="button" data-lang="ha" aria-pressed="false">HA</button></div></div></div>
  <div class="shell hero-grid"><div><div class="eyebrow">{copy("Official campaign record · Bauchi State", "Kadairin kowane · Bauchi State")}</div><h1><span data-en="A Vision" data-ha="Vision">A Vision</span><br><span data-en="for" data-ha="don">for</span> <em><span data-en="Progress." data-ha="Ci gaba.">Progress.</span></em></h1><p class="hero-lede">{copy("A visual record of Bauchi’s public needs, the progress already made, and the work APM will carry forward.", "Ganiya da nuna da bukatar al’umma, ci gaban da aka yi, da aiki da APM za ci gaba da shi.")}</p><div class="hero-actions"><a class="btn btn-primary" href="#progress">{copy("Explore the progress", "Duba ci gaban")} <span>→</span></a><a class="btn btn-secondary" href="#atlas">{copy("View LGA atlas", "Duba taswirar LGA")}</a></div><div class="motto" {attr("Integrity · Sacrifice · Service", "Integrity · Sacrifice · Service")}>Integrity · Sacrifice · Service</div></div><div class="portrait-wrap"><img class="portrait" src="{hero_image}" alt="Dr. Yakubu Adamu campaign portrait"><div class="portrait-caption"><strong>Dr. Yakubu Adamu</strong><span {attr("Bauchi State Governor candidate", "Mikaɗin gwamna jihada Bauchi")}>Bauchi State Governor candidate</span></div></div></div>
</header>
<section class="stats"><div class="shell stats-grid"><div class="stat"><strong>{len(LGAS)}</strong><span>{copy("LGAs in the atlas", "LGA a cikin taswirar")}</span></div><div class="stat"><strong>{achievement_count}</strong><span>{copy("Public records mapped", "Bayanan da aka nunawa")}</span></div><div class="stat"><strong>{promise_count}</strong><span>{copy("APM commitments tracked", "Alkawarin APM da aka sa ido")}</span></div><div class="stat"><strong>{len(indicator_rows)}</strong><span>{copy("Outcome indicators", "Alamu na sakamako")}</span></div></div></section>
<main>
<section class="section" id="progress"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("The delivery story", "Labari na isar da sabis")}</div><h2>{copy("From public need to the next result.", "Daga buƙatar al'umma zuwa sakamako na gaba.")}</h2></div><p>{copy("The new dashboard keeps needs, public records, campaign commitments and future measures in one traceable story.", "Sabuwar dashboard tana buƙatar al'umma, bayanan ci gabansu, alkawarin gaggawa da matakan nan zuwa cikin wataƙa mai sauri.")}</p></div><div class="progress-path"><div class="path-step"><span class="step-no">{copy("01 / NEED", "01 / BUƙATAR")}</span><h3>{copy("What matters?", "Me ya fi muhimmanci?")}</h3><p>{copy("Start with the everyday need.", "Fara da buƙatar rayuwar yau.")}</p></div><div class="path-step"><span class="step-no">{copy("02 / RECORD", "02 / BAYANI")}</span><h3>{copy("What exists?", "Me yana nan?")}</h3><p>{copy("Show documented progress.", "Nuna ci gaban da aka tabbatar.")}</p></div><div class="path-step"><span class="step-no">{copy("03 / PROMISE", "03 / ALKAWARI")}</span><h3>{copy("What comes next?", "Me zai zo bayan nan?")}</h3><p>{copy("Make the commitment clear.", "Sanya alkawarin a bayyana.")}</p></div><div class="path-step"><span class="step-no">{copy("04 / RESULT", "04 / SAKAMAKO")}</span><h3>{copy("How will we know?", "Yaya za mu sani?")}</h3><p>{copy("Measure what changes.", "Auna abin da za ta canza.")}</p></div></div><div class="filter-row"><button class="filter active" type="button" data-filter="all" {attr("All records", "Dufin bayanai")}>All records</button><button class="filter" type="button" data-filter="health" {attr("Health", "Lafiya")}>Health</button><button class="filter" type="button" data-filter="education" {attr("Education", "Ilimi")}>Education</button><button class="filter" type="button" data-filter="wash" {attr("Water & climate", "Ruwa da sauroyi")}>Water & climate</button><button class="filter" type="button" data-filter="governance" {attr("Governance", "Gwaji")}>Governance</button><button class="filter" type="button" data-filter="infrastructure" {attr("Infrastructure", "Infastructure")}>Infrastructure</button></div><div class="arrow-list">{''.join(arrow_cards)}</div></div></section>
<section class="section lga-section" id="atlas"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("20 local government areas", "LGA 20")}</div><h2>{copy("A 20-LGA evidence queue for Bauchi.", "Bita na bayanai ga LGA 20 a Bauchi.")}</h2></div><p>{copy("All 20 LGAs now have one curated source-backed evidence row. This is a starting evidence model, not comprehensive sector coverage for every community.", "Yanzu dukan LGA 20 suna da jimayi na bayanai mai goyon bayan sauro. Wannan ba cikakken bayanan kowane bangare ba.")}</p></div><div class="lga-grid">{lga_atlas(lga_rows)}</div><div class="lga-detail" id="lga-detail"><div><div class="detail-label">{copy("Selected area · statewide evidence start", "Wanda za zaɓi · ci gaban jihada")}</div><h3 id="selected-lga">Bauchi</h3><p id="selected-copy" aria-live="polite" data-en="Choose an LGA to preview the evidence queue. The first public records are being tracked as statewide progress while LGA-specific project evidence is verified." data-ha="Zaɓi LGA don duba bita don bayanai. A bayanan farko ana sune a matsayin ci gaban jihada yayin da ake tabbatar da bayanan LGA.">Choose an LGA to preview the evidence queue. The first public records are being tracked as statewide progress while LGA-specific project evidence is verified.</p></div><span class="detail-label" {attr("20 LGAs · 1 evidence model", "LGA 20 · 1 tsarin tabbaci")}>20 LGAs · 1 evidence model</span></div></div></section>
<section class="section" id="continuity"><div class="shell governance-grid"><div class="governor-card"><img src="{governor_image}" alt="Governor Bala Mohammed"><div class="governor-caption"><strong>{copy("Progress with continuity", "Ci gaba mai ci gaba")}</strong><span {attr("Current Bauchi State administration and the next APM chapter", "Ggwamnatin Bauchi ta yanzu da sabon babban darasi na APM")}>Current Bauchi State administration and the next APM chapter</span></div></div><div class="governance-copy"><div class="eyebrow">{copy("Build on what is working", "Ci gaba kan abin da ke aiki")}</div><h3>{copy("The next chapter should finish the journey.", "Babban sabo ya kamata ya kare adireshin da aka fara.")}</h3><p>{copy("This landing page presents the current administration’s public record first, then shows where APM’s published commitments can complete, expand and measure the next priorities.", "Wannan shafi yana nuna bayanan gwamnati na yanzu da farko, sannan ya nuna inda alkawarin APM za ka ci gaba da shi, ya kuma yi aiki, ya sanya ido kan mabambanci na gaba.")}</p><div class="continuity-list"><div class="continuity-item"><b>01</b><span>{copy("Credit progress to the people and institutions delivering it.", "Mayar da ci gaban ga mutane da sashen da ke aiki.")}</span></div><div class="continuity-item"><b>02</b><span>{copy("Show joint delivery honestly, including partners and public institutions.", "Nuna aiki tare da gaskiya, tare da abokan hulɗe da sashen gwamnati.")}</span></div><div class="continuity-item"><b>03</b><span>{copy("Turn every promise into a result that can be tracked.", "Sanya kowane alkawari ya zama sakamako da za a iya sa shi ido a kai.")}</span></div></div></div></div></section>
<section class="section" id="agenda"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("Published campaign commitments", "Alkawarin gaggawa da aka wallafa")}</div><h2>{copy("A focused agenda for the next Bauchi.", "A agenda mai mayar hankali don Bauchi na gaba.")}</h2></div><p>{copy("These are campaign commitments, not completed achievements. They are shown separately so the evidence story stays clear.", "Waannan alkawarin gaggawa ne, ba ayyuka da aka kammala ba. An nuna su a wuri dabewa don bayan ci gabansu ya kasance mai sauƙi.")}</p></div><div class="agenda-grid">'''
    for idx, promise in enumerate(read_csv("promises.csv"), 1):
        sector = promise.get("sector", "")
        label = SECTOR_LABELS.get(sector, sector.title())
        ha = SECTOR_HA.get(sector, label)
        html_doc += f'''<article class="agenda-card"><div><span class="agenda-no">0{idx}</span><h3>{copy(label, ha)}</h3><p>{localized(promise.get("promise_text", ""), promise.get("promise_text_ha", ""))}</p></div>{source_link(promise.get("source_id", ""), sources, "Campaign source", "Sauro gaggawa")}</article>'''
    html_doc += f'''</div></div></section>
{indicator_section}
<section class="sources-section" id="sources"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("Traceable by design", "An tsara shi don sa ido")}</div><h2>{copy("Every record has a source.", "Kowane bayana yana da sauro.")}</h2></div><p>{copy(f"{len(manifest_rows)} source pages archived. {len(pending_review_rows)} candidate records are queued for source review before they can become achievements.", f"An ruƙe shafi {len(manifest_rows)} na bayanai. An sanya bayanan {len(pending_review_rows)} a cikin bita kafin su iya zama ayyuka.")}</p></div><ul class="source-list">{source_footer(sources)}</ul><div class="source-legend"><span><b>A</b> {copy("Primary or institutional record", "Bayanan gwamnati ko institucio")}</span><span><b>B</b> {copy("Programme or corroborating evidence", "Shirin ko tabbacin da ke tabbatar")}</span><span><b>D</b> {copy("Campaign material", "Kayan gaggawa")}</span></div></div></section>
</main>
<footer class="site-footer"><div class="shell footer-inner"><div><strong>APM Bauchi Progress &amp; Delivery</strong><p>{copy("Public-source campaign intelligence. Built", "Basirar gaggawa daga bayanan al'umma. An gina a")} {built}. {copy("Public information and campaign materials are labelled separately; this page is not private polling.", "Bayanan al'umma da kayan gaggawa an bambanta su; wannan shafi ba ita ce private polling.")}</p></div><a class="deerflow" href="https://deerflow.tech" target="_blank" rel="noopener noreferrer" {attr("Created By Deerflow", "An ƙirƙira Deerflow")}>Created By Deerflow</a></div></footer>
<script>
const root=document.documentElement;
let currentLanguage='en';
let selectedLga='';
const renderLgaDetail=()=>{{if(!selectedLga)return;const btn=document.querySelector('[data-lga="'+selectedLga+'"]');if(!btn)return;const summary=currentLanguage==='ha'?btn.dataset.summaryHa:btn.dataset.summary;const promise=currentLanguage==='ha'?btn.dataset.promiseHa:btn.dataset.promise;const result=currentLanguage==='ha'?btn.dataset.resultHa:btn.dataset.result;document.getElementById('selected-lga').textContent=selectedLga;const copy=document.getElementById('selected-copy');copy.textContent=currentLanguage==='ha'?selectedLga+': '+summary+' APM: '+promise+' Bari: '+result:selectedLga+': '+summary+' APM: '+promise+' Next result: '+result;}};
const setLanguage=(lang)=>{{currentLanguage=lang;root.lang=lang;document.querySelectorAll('[data-en][data-ha]').forEach(el=>{{el.textContent=el.dataset[lang]||el.dataset.en}});document.querySelectorAll('[data-lang]').forEach(btn=>{{const active=btn.dataset.lang===lang;btn.classList.toggle('active',active);btn.setAttribute('aria-pressed',String(active));}});renderLgaDetail();}};
document.querySelectorAll('[data-lang]').forEach(btn=>btn.addEventListener('click',()=>setLanguage(btn.dataset.lang)));
document.querySelectorAll('[data-filter]').forEach(btn=>btn.addEventListener('click',()=>{{document.querySelectorAll('[data-filter]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');const filter=btn.dataset.filter;document.querySelectorAll('.arrow-card').forEach(card=>card.hidden=filter!=='all'&&card.dataset.sector!==filter);}}));
document.querySelectorAll('[data-lga]').forEach(btn=>btn.addEventListener('click',()=>{{document.querySelectorAll('[data-lga]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');selectedLga=btn.dataset.lga;renderLgaDetail();}}));
</script>
</body>
</html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html_doc, encoding="utf-8")
    print(f"wrote {OUT} ({achievement_count} achievements, {promise_count} promises, {source_count} sources)")


if __name__ == "__main__":
    render()
