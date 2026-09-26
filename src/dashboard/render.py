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

LGA_WARDS_FILE = "lga_wards.csv"
REQUEST_ENDPOINT = ""
REQUEST_CATEGORIES = (
    ("water", "Water", "Ruwan sha"),
    ("electricity", "Electricity", "Wuta"),
    ("roads", "Roads", "Dabarar kai"),
    ("healthcare", "Healthcare", "Kafi lafiya"),
    ("education", "Education", "Ilimi"),
    ("jobs_agriculture", "Jobs and agriculture", "Aiki da dama"),
    ("security", "Security", "Tsaro"),
    ("housing_environment", "Housing and environment", "Gidaje da yanayi"),
    ("other", "Other", "Wani"),
)

ASSET_FILES = [
    "apm-logo.png", "apm-emblem.png", "yakubu-adamu-hero.png", "yakubu-adamu-portrait.png",
    "bala-mohammed.png"
]

FEATURED_ACHIEVEMENTS_FILE = "featured_achievements.csv"
FEATURED_COLUMNS = {
    "featured_id", "achievement_id", "featured_order", "lga_scope", "lga_names", "sector",
    "image_asset_id", "caption_en", "caption_ha", "image_alt_en", "image_alt_ha",
    "source_id", "approval_status"
}
FEATURED_SCOPES = {"lga", "multi_lga", "statewide"}
FEATURED_SCOPE_LABELS = {
    "lga": ("LGA", "LGA"),
    "multi_lga": ("Multiple LGAs", "LGA daya da yawa"),
    "statewide": ("Statewide", "Jihada"),
}

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
    "governance": "Isar da ganyayi da gwaji",
    "infrastructure": "Infastructure da haɗi",
}


def read_csv(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_optional_csv(name):
    path = DATA / name
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, set(reader.fieldnames or [])


def load_lga_wards():
    try:
        return read_optional_csv(LGA_WARDS_FILE)
    except (OSError, csv.Error, UnicodeError):
        return None


def esc(value):
    return html.escape(str(value or ""), quote=True)


def attr(en, ha):
    # A missing Hausa string must degrade to English rather than serialising an empty
    # data-ha, which is indistinguishable from a real untranslated string once rendered.
    return f'data-en="{esc(en)}" data-ha="{esc(ha or en)}"'


def copy(en, ha):
    return f'<span {attr(en, ha)}>{esc(en)}</span>'


def localized(en, ha):
    return f'<span {attr(en, ha)}>{esc(en)}</span>'


# One controlled vocabulary for record status: CSS class, Hausa label, and the
# indicator validator's allowed set all derive from this, so a status cannot ship
# without a translation or drift out of the validator.
STATUS_CLASSES = {
    "Progress delivered": "status-progress",
    "Project underway": "status-underway",
    "Approval milestone": "status-milestone",
    "Promise to complete": "status-promise",
    "Next priority": "status-next",
    "Outcome being measured": "status-measured",
}

STATUS_HA = {
    "Progress delivered": "An ci gaba",
    "Project underway": "Aiki yana ci gaba",
    "Approval milestone": "Matsayin amincewa",
    "Promise to complete": "Alkawarin a kare",
    "Next priority": "Farkashin da gaba",
    "Outcome being measured": "Ana aunawa sakamako",
}

INDICATOR_STATUSES = frozenset(
    {"Progress delivered", "Project underway", "Outcome being measured", "Approval milestone"})


def status_class(status):
    return STATUS_CLASSES.get(status, "status-underway")


def source_link(source_id, sources, label="Source", label_ha=""):
    source = sources.get(source_id, {})
    if not source.get("url"):
        return ""
    return (f'<a class="source-link" href="{esc(source["url"])}" '
            f'target="_blank" rel="noopener noreferrer">{localized(label, label_ha or label)} <span aria-hidden="true">↗</span></a>')


def status_badge(status, ha=None):
    # ha defaults from the controlled vocabulary so an omitted argument can never ship
    # English into both slots. An explicit per-record ha (e.g. achievements.status_ha)
    # still wins.
    return (f'<span class="status {status_class(status)}" '
            f'{attr(status, ha or STATUS_HA.get(status, ""))}>{esc(status)}</span>')



def prepare_assets():
    target = DOCS / "assets" / "brand"
    target.mkdir(parents=True, exist_ok=True)
    for name in ASSET_FILES:
        source = ASSETS / name
        if source.exists():
            shutil.copy2(source, target / name)


def prepare_featured_assets(rows):
    for row in rows:
        source = (ASSETS / row["image_asset_id"]).resolve()
        relative = source.relative_to(ASSETS.resolve())
        target = DOCS / "assets" / "brand" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


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
    allowed_statuses = set(INDICATOR_STATUSES)
    required_fields = ["indicator_id", "sector", "lga", "indicator", "indicator_ha", "current_value", "current_unit", "current_year", "status", "status_ha", "source_id", "measurement_note", "measurement_note_ha"]
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


HAUSA_ORTHOGRAPHY = "ƙɓɗʙƊƘ"

# Distinctively Hausa function words. Deliberately excludes "a" and "na"-like tokens that
# collide with English, so English prose cannot trip the density test.
HAUSA_FUNCTION_WORDS = frozenset("""
    da na ya ka ta mu ku ci cikin tare ba wanda yana suka wasu kuma ko sai don sun tana
    ina sunu mua kuma
""".split())

# Curated content tables whose English columns must stay English. lga_wards.csv and the
# source registers are excluded: they hold proper nouns, URLs and hashes, not prose.
ENGLISH_COLUMN_TABLES = (
    "achievements.csv", "indicators.csv", "needs.csv", "promises.csv",
    "lga_delivery.csv", "featured_achievements.csv",
)

HAUSA_DENSITY_MIN_TOKENS = 6
HAUSA_MIN_HITS = 3


def looks_like_hausa(value):
    """True when a value carries Hausa orthography or function-word evidence.

    The hit count is absolute rather than a ratio: none of the function words above are
    English words, so three occurrences in a six-token cell is conclusive, whereas a
    ratio mis-scores short Hausa sentences padded with Latin proper nouns.
    """
    if not value:
        return False
    if any(char in value for char in HAUSA_ORTHOGRAPHY):
        return True
    tokens = [token.strip(".,;:!?()[]\"'").lower() for token in value.split()]
    if len(tokens) < HAUSA_DENSITY_MIN_TOKENS:
        return False
    return sum(1 for token in tokens if token in HAUSA_FUNCTION_WORDS) >= HAUSA_MIN_HITS


def validate_no_hausain_english_columns():
    """Reject Hausa text in any non-`_ha` column of the curated content tables.

    Three achievements.csv records shipped with the Hausa description pasted into the
    English column, so a Hausa-mode visitor saw nothing change. Two of the three use no
    Hausa-specific characters at all, which is why both an orthography test and a
    function-word density test are required. This makes it a build failure rather than a
    silent content bug.
    """
    offenders = []
    for name in ENGLISH_COLUMN_TABLES:
        for row in read_csv(name):
            for column, value in row.items():
                if column.endswith("_ha"):
                    continue
                if looks_like_hausa(value):
                    key = (row.get("achievement_id") or row.get("indicator_id")
                           or row.get("promise_id") or row.get("need_id")
                           or row.get("lga") or "?")
                    offenders.append(f"{name}:{key}:{column}")
    if offenders:
        raise ValueError(
            "Hausa text found in English column(s): " + ", ".join(sorted(offenders)))


def validate_unique_promises():
    """Reject two promise rows carrying the same commitment text.

    promise-wash once held a byte-for-byte copy of promise-infrastructure, so the agenda
    rendered the same commitment twice under two different sectors. A phantom row had
    been created to fill the sector grid. This guards that bug class, not just the
    instance.
    """
    seen = {}
    for row in read_csv("promises.csv"):
        text = (row.get("promise_text") or "").strip().lower()
        if not text:
            raise ValueError(f"blank promise_text: {row.get('promise_id', '')}")
        if text in seen:
            raise ValueError(
                f"duplicate promise_text shared by {seen[text]} and "
                f"{row.get('promise_id', '')}: {row.get('promise_text', '')[:70]}")
        seen[text] = row.get("promise_id", "")


def validate_data():
    required = {
        "source_register.csv": {"source_id", "url", "content_hash", "source_grade", "usage_note", "usage_note_ha"},
        "needs.csv": {"need_id", "lga", "sector", "need_text", "source_id"},
        "achievements.csv": {"achievement_id", "sector", "status", "source_id", "verification_status", "verification_status_ha"},
        "promises.csv": {"promise_id", "sector", "promise_text", "source_id"},
        "lga_delivery.csv": {"lga", "coverage_type", "status"},
        "asset_register.csv": {"file", "sha256", "usage_status", "approved_by", "approved_at"},
        "source_manifest.csv": {"document_id", "url", "content_hash", "local_file", "review_status"},
        "review_queue.csv": {"candidate_id", "title", "url", "review_status"},
        "indicators.csv": {
            "indicator_id", "sector", "lga", "indicator", "indicator_ha", "baseline_value",
            "baseline_unit", "baseline_year", "current_value", "current_unit", "current_year",
            "target_value", "target_year", "status", "status_ha", "source_id",
            "measurement_note", "measurement_note_ha"
        },
    }
    for name, columns in required.items():
        rows = read_csv(name)
        if not rows:
            raise ValueError(f"empty delivery table: {name}")
        missing = columns - set(rows[0])
        if missing:
            raise ValueError(f"{name} missing columns: {sorted(missing)}")
    validate_no_hausain_english_columns()
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
    validate_unique_promises()
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


def validate_featured_rows(rows, achievement_rows, asset_rows, sources, fieldnames=None):
    if len(rows) != 5:
        raise ValueError("featured achievements must contain exactly five records")
    if fieldnames is None:
        fieldnames = set()
        for row in rows:
            fieldnames.update(row.keys())
    missing = FEATURED_COLUMNS - set(fieldnames)
    if missing:
        raise ValueError(f"featured achievements missing columns: {sorted(missing)}")
    achievement_by_id = {row.get("achievement_id", ""): row for row in achievement_rows}
    if len(achievement_by_id) != len(achievement_rows):
        raise ValueError("duplicate achievement_id")
    asset_by_id = {}
    for asset in asset_rows:
        asset_id = asset.get("file", "")
        if not asset_id:
            raise ValueError("blank asset register file")
        if asset_id in asset_by_id:
            raise ValueError(f"duplicate asset register file: {asset_id}")
        asset_by_id[asset_id] = asset
    if isinstance(sources, dict):
        source_ids = set(sources)
    else:
        source_ids = {row.get("source_id", "") for row in sources}
    featured_ids = set()
    achievement_ids = set()
    orders = set()
    for row in rows:
        featured_id = row.get("featured_id", "")
        achievement_id = row.get("achievement_id", "")
        order = row.get("featured_order", "")
        lga_scope = row.get("lga_scope", "")
        lga_names = [name.strip() for name in row.get("lga_names", "").split("|") if name.strip()]
        sector = row.get("sector", "")
        image_asset_id = row.get("image_asset_id", "")
        caption_en = row.get("caption_en", "")
        caption_ha = row.get("caption_ha", "")
        source_id = row.get("source_id", "")
        if not featured_id or not featured_id.strip() or featured_id in featured_ids:
            raise ValueError("featured achievement IDs must be unique and nonblank")
        if not achievement_id or not achievement_id.strip() or achievement_id in achievement_ids:
            raise ValueError("featured achievement references must be unique and nonblank")
        if not order.isdigit() or str(int(order)) != order or not 1 <= int(order) <= 5:
            raise ValueError(f"invalid featured_order: {order}")
        order_number = int(order)
        if order_number in orders:
            raise ValueError("featured_order must be unique")
        if lga_scope not in FEATURED_SCOPES:
            raise ValueError(f"invalid featured lga_scope: {lga_scope}")
        if len(lga_names) != len(set(lga_names)):
            raise ValueError(f"duplicate featured LGA name: {featured_id}")
        if any(name not in LGAS for name in lga_names):
            raise ValueError(f"unknown featured LGA name: {featured_id}")
        if lga_scope == "lga" and len(lga_names) != 1:
            raise ValueError(f"lga scope requires one LGA name: {featured_id}")
        if lga_scope == "multi_lga" and len(lga_names) < 2:
            raise ValueError(f"multi_lga scope requires multiple LGA names: {featured_id}")
        if lga_scope == "statewide" and lga_names:
            raise ValueError(f"statewide scope must not name LGAs: {featured_id}")
        for field, value in [("sector", sector), ("caption_en", caption_en), ("caption_ha", caption_ha), ("image_alt_en", row.get("image_alt_en", "")), ("image_alt_ha", row.get("image_alt_ha", "")), ("source_id", source_id)]:
            if not value or not value.strip():
                raise ValueError(f"blank featured field: {featured_id}:{field}")
        if source_id not in source_ids:
            raise ValueError(f"unknown featured source_id: {source_id}")
        if not image_asset_id or image_asset_id not in asset_by_id:
            raise ValueError(f"unknown featured image_asset_id: {image_asset_id}")
        asset = asset_by_id[image_asset_id]
        if asset.get("usage_status") != "campaign approved" or not asset.get("approved_at"):
            raise ValueError(f"featured image is not campaign approved: {image_asset_id}")
        asset_path = ASSETS / image_asset_id
        try:
            asset_path.resolve().relative_to(ASSETS.resolve())
        except ValueError as exc:
            raise ValueError(f"featured image escapes approved asset directory: {image_asset_id}") from exc
        if not asset_path.is_file():
            raise FileNotFoundError(asset_path)
        if hashlib.sha256(asset_path.read_bytes()).hexdigest() != asset.get("sha256", ""):
            raise ValueError(f"featured image hash mismatch: {image_asset_id}")
        if row.get("approval_status") != "approved":
            raise ValueError(f"featured achievement is not approved: {featured_id}")
        if achievement_id not in achievement_by_id:
            raise ValueError(f"unknown featured achievement_id: {achievement_id}")
        achievement = achievement_by_id[achievement_id]
        if source_id != achievement.get("source_id"):
            raise ValueError(f"featured source does not match achievement: {featured_id}")
        if sector != achievement.get("sector"):
            raise ValueError(f"featured sector does not match achievement: {featured_id}")
        achievement_lga = achievement.get("lga", "")
        if lga_scope == "lga" and achievement_lga not in LGAS:
            raise ValueError(f"featured lga_scope is not supported by achievement geography: {featured_id}")
        if lga_scope == "statewide" and achievement_lga != "Statewide":
            raise ValueError(f"featured statewide scope does not match achievement geography: {featured_id}")
        if lga_scope == "multi_lga" and achievement_lga == "Statewide":
            raise ValueError(f"featured multi_lga scope does not match achievement geography: {featured_id}")
        featured_ids.add(featured_id)
        achievement_ids.add(achievement_id)
        orders.add(order_number)


def load_featured_achievements(achievement_rows, asset_rows, sources):
    try:
        optional = read_optional_csv(FEATURED_ACHIEVEMENTS_FILE)
    except (OSError, csv.Error, UnicodeError):
        return [], "pending"
    if optional is None:
        return [], None
    rows, fieldnames = optional
    try:
        validate_featured_rows(rows, achievement_rows, asset_rows, sources, fieldnames)
    except (OSError, ValueError, KeyError, csv.Error, UnicodeError):
        return [], "pending"
    return rows, None


def featured_pending_section():
    return f'''<section class="featured-section featured-pending-section" id="featured" data-featured-state="pending" aria-labelledby="featured-pending-title"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("Featured achievements", "Ayyuka da aka zaɓa")}</div><h2 id="featured-pending-title">{copy("Verified featured achievements are pending.", "Ayyuka da aka zaɓa da tabbacin suna jiran.") }</h2></div><p>{copy("No featured records are published until the achievement and local image approvals are complete.", "Bai a wallafa babu bayanai sai an kammama tabbacin ayyuka da hotunan gari na gari.") }</p></div></div></section>'''


def featured_achievement_carousel(rows, achievement_rows, asset_rows, sources):
    achievement_by_id = {row.get("achievement_id", ""): row for row in achievement_rows}
    asset_by_id = {row.get("file", ""): row for row in asset_rows}
    slides = []
    for row in sorted(rows, key=lambda item: int(item["featured_order"])):
        achievement = achievement_by_id[row["achievement_id"]]
        asset_id = row["image_asset_id"]
        asset = asset_by_id[asset_id]
        image_source = asset.get("source_url", "")
        image_source_link = (
            f'<a class="source-link" href="{esc(image_source)}" target="_blank" rel="noopener noreferrer">{localized("Image source", "Sauro hotuna")} <span aria-hidden="true">↗</span></a>'
            if image_source
            else ""
        )
        asset_path = (ASSETS / asset_id).resolve()
        image_path = asset_path.relative_to(ASSETS.resolve()).as_posix()
        caption_en = row["caption_en"]
        caption_ha = row["caption_ha"]
        heading_en = achievement.get("project_or_programme", "") or caption_en
        heading_ha = achievement.get("project_or_programme_ha", "") or caption_ha
        sector = row["sector"]
        sector_en = SECTOR_LABELS.get(sector, sector.title())
        sector_ha = SECTOR_HA.get(sector, sector_en)
        scope = row["lga_scope"]
        scope_en, scope_ha = FEATURED_SCOPE_LABELS[scope]
        lga_names = row.get("lga_names", "")
        lga_scope_label = lga_names if lga_names else scope_en
        lga_scope_detail = f" · {esc(lga_scope_label)}" if lga_scope_label else ""
        alt_en = row.get("image_alt_en", "") or "Source image for featured achievement"
        alt_ha = row.get("image_alt_ha", "") or alt_en
        image_context_note = ""
        if row.get("image_alt_en", "").lower().startswith(("portrait", "seated", "aerial", "a person")):
            image_context_note = (
                f'<span class="featured-image-note" data-en="Context image · verify project-specific depiction" '
                f'data-ha="Hotun bayan kai · tabbatar ko yana nuna aikin daidai">Context image · verify project-specific depiction</span>'
            )
        slides.append(
            f'''<li class="featured-slide" data-featured-slide data-featured-id="{esc(row["featured_id"])}" data-lga-scope="{esc(scope)}" data-featured-lga-scope="{esc(scope)}"><figure class="featured-media"><img src="assets/brand/{esc(image_path)}" alt="{esc(alt_en)}" data-alt-en="{esc(alt_en)}" data-alt-ha="{esc(alt_ha)}" loading="lazy" decoding="async">{image_context_note}<figcaption>{localized(caption_en, caption_ha)}</figcaption></figure><div class="featured-slide-copy"><div class="featured-slide-meta"><span class="featured-sector">{localized(sector_en, sector_ha)}</span><span class="featured-scope-badge" data-lga-names="{esc(lga_scope_label)}">{localized(scope_en, scope_ha)}{lga_scope_detail}</span></div><h3>{localized(heading_en, heading_ha)}</h3><p class="featured-caption">{localized(caption_en, caption_ha)}</p><div class="featured-source">{source_link(row["source_id"], sources, "Featured source", "Sauro da ayyuka")}{image_source_link}</div></div></li>'''
        )
    slide_html = "".join(slides)
    return f'''<section class="featured-section" id="featured" data-featured-state="ready" aria-labelledby="featured-title"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("Featured achievements", "Ayyuka da aka zaɓa")}</div><h2 id="featured-title">{copy("Five approved, source-backed records, with their scope kept clear.", "Bayanai guda da aka amince, tare da nuna iyakin su.") }</h2></div><p>{copy("Each slide keeps the approved caption, source and LGA scope visible. Some source images are context images rather than verified project close-ups; the image note identifies those cases. Statewide evidence is not relabelled as a single-LGA record.", "Kowane mafada yana nuna caption da aka amince da sauro da iyakin LGA. Wasu hotunan ba kwakaiyo aiki ba ne; note na hotun yana nuna wanda ake. Ba a canza bayanan jihada zuwa LGA daya.") }</p></div><div class="featured-carousel" data-featured-carousel tabindex="0" role="region" aria-roledescription="carousel" aria-labelledby="featured-title"><div class="featured-toolbar"><div class="featured-scope-filters" role="group" aria-label="Featured achievement scope filters"><button type="button" class="featured-scope-filter active" data-featured-scope-filter="all" aria-pressed="true" {attr("All scopes", "Dufin firin")}>All scopes</button><button type="button" class="featured-scope-filter" data-featured-scope-filter="lga" aria-pressed="false" {attr("LGA", "LGA")}>LGA</button><button type="button" class="featured-scope-filter" data-featured-scope-filter="multi_lga" aria-pressed="false" {attr("Multiple LGAs", "LGA daya da yawa")}>Multiple LGAs</button><button type="button" class="featured-scope-filter" data-featured-scope-filter="statewide" aria-pressed="false" {attr("Statewide", "Jihada")}>Statewide</button></div><div class="featured-controls"><button type="button" class="featured-control" data-featured-prev aria-label="Previous featured achievement" {attr("Previous", "Baya")}>← <span {attr("Previous", "Baya")}>Previous</span></button><span class="featured-status" data-featured-status aria-live="polite" aria-atomic="true">1 / 5</span><button type="button" class="featured-control" data-featured-next aria-label="Next featured achievement" {attr("Next", "Na gaba")}><span {attr("Next", "Na gaba")}>Next</span> →</button></div></div><ol id="featured-slides" class="featured-slides">{slide_html}</ol></div></div></section>'''


FEATURED_SCRIPT = r'''
const featuredCarousel=document.querySelector('[data-featured-carousel]');
const featuredSlides=featuredCarousel?[...featuredCarousel.querySelectorAll('[data-featured-slide]')]:[];
let featuredIndex=0;
let featuredScope='all';
const featuredVisibleSlides=()=>featuredSlides.filter(slide=>featuredScope==='all'||slide.dataset.lgaScope===featuredScope);
renderFeatured=()=>{
  if(!featuredCarousel)return;
  const visible=featuredVisibleSlides();
  featuredSlides.forEach(slide=>{slide.classList.remove('is-active');slide.setAttribute('aria-hidden','true');});
  if(!visible.length){const status=featuredCarousel.querySelector('[data-featured-status]');if(status)status.textContent=currentLanguage==='ha'?'Babu ayyuka a wannan firin':'No featured achievements in this scope';return;}
  if(featuredIndex>=visible.length)featuredIndex=0;
  const active=visible[featuredIndex];
  active.classList.add('is-active');
  active.setAttribute('aria-hidden','false');
  const status=featuredCarousel.querySelector('[data-featured-status]');
  if(status)status.textContent=currentLanguage==='ha'?'Mafada '+(featuredIndex+1)+' na '+visible.length:'Slide '+(featuredIndex+1)+' of '+visible.length;
  const previous=featuredCarousel.querySelector('[data-featured-prev]');
  const next=featuredCarousel.querySelector('[data-featured-next]');
  if(previous)previous.disabled=visible.length<2;
  if(next)next.disabled=visible.length<2;
};
const moveFeatured=amount=>{
  const visible=featuredVisibleSlides();
  if(visible.length<2)return;
  const current=visible.findIndex(slide=>slide.classList.contains('is-active'));
  featuredIndex=(current+amount+visible.length)%visible.length;
  renderFeatured();
};
if(featuredCarousel){
  featuredCarousel.classList.add('featured-carousel-ready');
  document.querySelectorAll('[data-featured-scope-filter]').forEach(button=>button.addEventListener('click',()=>{
    featuredScope=button.dataset.featuredScopeFilter;
    featuredIndex=0;
    document.querySelectorAll('[data-featured-scope-filter]').forEach(item=>{const active=item===button;item.classList.toggle('active',active);item.setAttribute('aria-pressed',String(active));});
    renderFeatured();
  }));
  const previous=featuredCarousel.querySelector('[data-featured-prev]');
  const next=featuredCarousel.querySelector('[data-featured-next]');
  if(previous)previous.addEventListener('click',()=>moveFeatured(-1));
  if(next)next.addEventListener('click',()=>moveFeatured(1));
  featuredCarousel.addEventListener('keydown',event=>{
    if(event.key==='ArrowLeft'){event.preventDefault();moveFeatured(-1);}
    if(event.key==='ArrowRight'){event.preventDefault();moveFeatured(1);}
    if(event.key==='Home'){event.preventDefault();featuredIndex=0;renderFeatured();}
    if(event.key==='End'){event.preventDefault();featuredIndex=Math.max(0,featuredVisibleSlides().length-1);renderFeatured();}
  });
  renderFeatured();
}
'''


REQUEST_SCRIPT = r'''
const publicRequestForm=document.querySelector('[data-request-form]');
if(publicRequestForm){
  const requestLga=publicRequestForm.querySelector('#request-lga');
  const requestRa=publicRequestForm.querySelector('#request-ward-code');
  const requestStatus=publicRequestForm.querySelector('[data-request-status]');
  const requestConfirmation=publicRequestForm.querySelector('[data-request-confirmation]');
  const requestSubmit=publicRequestForm.querySelector('[data-request-submit]');
  const requestConfigStatus=publicRequestForm.querySelector('[data-request-config-status]');
  const requestHoneypot=publicRequestForm.querySelector('#request-website');
  const requestConsent=publicRequestForm.querySelector('#request-consent');
  const configuredRequestEndpoint=(publicRequestForm.dataset.requestEndpoint||'').trim();
  let requestEndpointUrl=null;
  try{
    const parsedRequestEndpoint=new URL(configuredRequestEndpoint,window.location.href);
    if(configuredRequestEndpoint&&parsedRequestEndpoint.protocol==='https:'&&!parsedRequestEndpoint.username&&!parsedRequestEndpoint.password&&!parsedRequestEndpoint.hash)requestEndpointUrl=parsedRequestEndpoint;
  }catch(error){requestEndpointUrl=null;}
  const requestEndpointReady=Boolean(requestEndpointUrl);
   const showRequestStatus=key=>{
     const english=requestStatus.dataset[key+'En'];
     const hausa=requestStatus.dataset[key+'Ha'];
     requestStatus.textContent=currentLanguage==='ha'?(hausa||requestStatus.dataset.ha):(english||requestStatus.dataset.en);
     requestStatus.classList.toggle('is-error',key==='error');
     requestStatus.hidden=false;
   };
   const applyBilingualValidity=()=>{
     const fields=[
       [document.querySelector('#request-lga'),'Choose an LGA.','Zaɓi LGA.'],
       [document.querySelector('#request-ward-code'),'Choose a registration area.','Zaɓi wurin ƙaura zaye.'],
       [document.querySelector('#request-address'),'Enter the address or location.','Shigar da adireshi ko wuri.'],
       [document.querySelector('#request-category'),'Choose one request category.','Zaɓi nauyin buƙatar daya.'],
       [document.querySelector('#request-details'),'Enter the request details.','Shigar da bayanan buƙatar.'],
        [document.querySelector('#request-email'),'Enter a valid email address.','Shigar da adireshin imil mai yawa.',false],
       [document.querySelector('#request-consent'),'Consent is required.','An buƙatar aminci.'],
     ];
       fields.forEach(([field,english,hausa,required=true])=>{
         if(!field)return;
         field.setCustomValidity('');
         const value=field.type==='checkbox'?'':field.value.trim();
         const invalid=field.type==='checkbox'?!field.checked:(required&&!value)||(field.type==='email'&&value&&field.validity.typeMismatch);
         field.setCustomValidity(invalid?(currentLanguage==='ha'?hausa:english):'');
       });
   };
   document.querySelectorAll('[data-lang]').forEach(button=>button.addEventListener('click',applyBilingualValidity));
  const updateRequestRas=()=>{
    const selectedLga=requestLga.value;
    [...requestRa.options].forEach(option=>{
      if(option.hasAttribute('data-request-ra-lga'))option.hidden=Boolean(selectedLga)&&option.dataset.requestRaLga!==selectedLga;
      else option.hidden=Boolean(selectedLga);
    });
    requestRa.disabled=!selectedLga;
    requestRa.value='';
  };
    publicRequestForm.setAttribute('aria-disabled',String(!requestEndpointReady));
     requestSubmit.disabled=!requestEndpointReady;
     requestStatus.hidden=requestEndpointReady;
  requestLga.addEventListener('change',updateRequestRas);
  updateRequestRas();
  if(!requestEndpointReady){
    requestConfigStatus.textContent=currentLanguage==='ha'?'Ba a saita wata maƙai da ake amfani da ita a wannan gina ba. Ba a tura buƙatar.':'No usable request endpoint is configured in this build. No request is being sent.';
    requestConfigStatus.dataset.en='No usable request endpoint is configured in this build. No request is being sent.';
    requestConfigStatus.dataset.ha='Ba a saita wata maƙai da ake amfani da ita a wannan gina ba. Ba a tura buƙatar.';
    requestSubmit.addEventListener('click',event=>{event.preventDefault();showRequestStatus('unavailable');});
  }
  publicRequestForm.addEventListener('submit',async event=>{
    event.preventDefault();
    if(requestHoneypot.value.trim()){
      publicRequestForm.reset();
      updateRequestRas();
      return;
    }
    if(!requestEndpointReady){
      showRequestStatus('unavailable');
      return;
    }
     applyBilingualValidity();
     if(!publicRequestForm.reportValidity())return;
    const payload={};
    new FormData(publicRequestForm).forEach((value,key)=>{payload[key]=key==='consent'?requestConsent.checked:String(value);});
    requestSubmit.disabled=true;
    showRequestStatus('submitting');
    requestConfirmation.hidden=true;
    try{
      const response=await fetch(requestEndpointUrl.href,{method:'POST',headers:{'Content-Type':'application/json','Accept':'application/json'},body:JSON.stringify(payload),credentials:'omit',referrerPolicy:'no-referrer'});
       if(!response.ok)throw new Error('request_failed');
       const responseData=await response.json().catch(()=>null);
       const responseKeys=responseData&&typeof responseData==='object'&&!Array.isArray(responseData)?Object.keys(responseData):[];
       const trackingId=responseKeys.length===1&&responseKeys[0]==='request_id'&&typeof responseData.request_id==='string'&&/^APM-[0-9]{4}-[0-9]{4,12}$/.test(responseData.request_id)?responseData.request_id:'';
       if(!trackingId)throw new Error('invalid_request_confirmation');
       requestStatus.hidden=true;
       requestConfirmation.dataset.trackingId=trackingId;
       requestConfirmation.textContent=(currentLanguage==='ha'?'An karɓi buƙatar. Maƙai bin: ':'Request received. Tracking reference: ')+trackingId+'.';
       requestConfirmation.hidden=false;
      publicRequestForm.reset();
      updateRequestRas();
    }catch(error){
      showRequestStatus('error');
    }finally{
      requestSubmit.disabled=!requestEndpointReady;
    }
  });
}
'''


def source_footer(sources):
    return "".join(
        f'<li><span class="source-grade">{esc(row.get("source_grade", "?"))}</span> '
        # The title stays in the source's own language: it is a citation, not our copy.
        f'<span><strong>{esc(row.get("title", "Untitled source"))}</strong>'
        f'<small>{copy("Published", "An wallafa")} {esc(row.get("publication_date", "date unknown"))} · {copy("Retrieved", "An ɗauko")} {esc(row.get("retrieved_date", "date unknown"))}</small>'
        f'<small>{localized(row.get("usage_note", ""), row.get("usage_note_ha", ""))}</small></span>'
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
            f'<span>{esc(row.get("actor", ""))}</span>'
            f'<span>{localized(row.get("verification_status", ""), row.get("verification_status_ha", ""))}</span>'
            f'{source_link(row.get("source_id", ""), sources, "Source", "Sauro")}</div></li>'
        )
    return "".join(items) or '<li class="empty-item">No public achievement record yet.</li>'


def indicator_cards(rows, sources):
    items = []
    for row in rows:
        sector = row.get("sector", "")
        sector_en = SECTOR_LABELS.get(sector, sector.title())
        sector_ha = SECTOR_HA.get(sector, sector_en)
        baseline = row.get("baseline_value") or ""
        if baseline:
            baseline_label = esc(baseline)
        else:
            baseline_label = copy("Baseline pending", "Tsarin asal yana jira")
        current = row.get("current_value") or ""
        current_ha = row.get("current_value_ha") or current
        unit = row.get("current_unit") or row.get("baseline_unit") or ""
        unit_ha = row.get("current_unit_ha") or row.get("baseline_unit_ha") or unit
        current_year = row.get("current_year")
        current_label = localized(
            f"{current} · {current_year}" if current_year else current,
            f"{current_ha} · {current_year}" if current_year else current_ha)
        target = row.get("target_value")
        target_year = row.get("target_year")
        if target:
            target_label = localized(
                f"Target {target}{(' by ' + target_year) if target_year else ''}",
                f"Maƙasudin {target}{(' cikin ' + target_year) if target_year else ''}")
        else:
            target_label = localized("Target not set", "Ba a saita makasudi ba")
        items.append(
            f'<article class="indicator-card"><div class="indicator-top">'
            f'<span class="eyebrow">{localized(row.get("lga", "Statewide"), row.get("lga_ha", ""))} · {localized(sector_en, sector_ha)}</span>'
            f'{status_badge(row.get("status", ""), row.get("status_ha", ""))}</div>'
            f'<h3>{localized(row.get("indicator", ""), row.get("indicator_ha", ""))}</h3>'
            f'<div class="indicator-value"><strong>{current_label}</strong><span>{localized(unit, unit_ha)}</span></div>'
            f'<p>{localized(row.get("measurement_note", ""), row.get("measurement_note_ha", ""))}</p>'
            f'<div class="indicator-meta"><span>{copy("Baseline", "Tsarin asal")} {baseline_label} · {target_label}</span>'
            f'{source_link(row.get("source_id", ""), sources, "Source", "Sauro")}</div></article>'
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
        <div class="path-node need-node"><span class="node-number">01</span><h3>{copy("Public need", "Buƙatar al'umma")}</h3><p>{localized(need_text, need_text_ha)}</p><span class="node-tag">{copy("Needs evidence", "Tabbacin buƙatar")}</span>{need_source}</div>
        <div class="path-arrow" aria-hidden="true">→</div>
        <div class="path-node achievement-node"><span class="node-number">02</span><h3>{copy("Current achievement", "Ayyuka da yanzu")}</h3><ul class="achievement-list">{achievement_list(achievements, sources)}</ul><span class="node-tag">{copy("Public record", "Bayanan al'umma")}</span></div>
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


def request_form_section(ward_rows):
    lga_options = "".join(
        f'<option value="{esc(lga)}">{esc(lga)}</option>' for lga in LGAS
    )
    if ward_rows:
        ra_options = "".join(
            f'<option data-request-ra-lga="{esc(row.get("lga", ""))}" '
            f'value="{esc(row.get("ward_code", ""))}" '
            f'{attr(row.get("ra_name_source", ""), row.get("ra_name_source", ""))}>'
            f'{esc(row.get("ra_name_source", ""))}</option>'
            for row in ward_rows
        )
        ra_placeholder = "Choose a registration area"
        ra_placeholder_ha = "Zaɓi wurin ƙaura zaye"
    else:
        ra_options = ""
        ra_placeholder = "Registration areas are not loaded"
        ra_placeholder_ha = "An karɓi sauƙin ƙaura zaye ba a iya nuna shi ba"
    category_options = "".join(
        f'<option value="{esc(key)}" {attr(label_en, label_ha)}>'
        f'{esc(label_en)}</option>'
        for key, label_en, label_ha in REQUEST_CATEGORIES
    )
    endpoint_configured = bool(REQUEST_ENDPOINT.strip())
    form_disabled = "false" if endpoint_configured else "true"
    configured_status_en = (
        "A request endpoint is configured. Submission availability depends on the receiving service."
        if endpoint_configured else
        "Submission is unavailable in this local preview because no Apps Script endpoint is configured. No request is being sent."
    )
    configured_status_ha = (
        "An kunna maƙai don buƙatar. Samun da zarfin ya dogara da sabis da karɓi."
        if endpoint_configured else
        "Ba a samu buƙatar a wannan haskawa na gari ba saboda babu wata adireshin Apps Script da aka saita. A ba a tura buƙatar."
    )
    if ward_rows:
        limitation_en = "Names are based on provisional INEC electoral registration areas (RAs); they are not a current administrative council-ward schedule."
        limitation_ha = "Sunan sun dogara da yarjejeni na ƙaura zaye na INEC na gwaji; ba su ta kasance wata jadawar karkashin gari na yanzu ba."
    else:
        limitation_en = "The registration-area list is not available in this build, so no RA is assigned."
        limitation_ha = "Jadawar yarjejeni za'urewar zaye ba ta samu a wannan gina ba, saboda haka ba a zaɓi RA."
    return f'''
<section class="section requests-section" id="requests" aria-labelledby="requests-title">
  <div class="shell">
    <div class="section-head">
      <div><div class="eyebrow">{copy("One primary request", "Babban buƙatar daya")}</div><h2 id="requests-title">{copy("Tell us one need in your area.", "Faɗa mana buƙatar daya a cikin wurin da kake.")}</h2></div>
      <p>{copy("Submit one clear request. Follow-up details are optional, and any confirmation ID is only a generated request tracking reference—not a voter ID.", "Aika buƙatar daya mai bayani. Bayanan binfollow-up ba gangan ba, kuma ID na tabbaci yana nufin bin buƙatar kawai, ba ID na zabb'ar masu zayyawa ba.")}</p>
    </div>
    <div class="request-layout">
      <form class="request-form" id="public-request-form" method="post" action="about:blank" onsubmit="return false" data-request-form data-request-endpoint="{esc(REQUEST_ENDPOINT)}" data-request-configured="{str(endpoint_configured).lower()}" aria-describedby="request-config-status request-ra-note request-identity-note">
        <p class="request-config-status" id="request-config-status" data-request-config-status data-en="{esc(configured_status_en)}" data-ha="{esc(configured_status_ha)}">{esc(configured_status_en)}</p>
        <div class="request-grid">
          <div class="request-field">
            <label for="request-lga">{copy("LGA", "LGA")} <span class="request-required" aria-hidden="true">*</span></label>
            <select id="request-lga" name="lga" required>
              <option value="" {attr("Choose LGA", "Zaɓi LGA")} selected>Choose LGA</option>
              {lga_options}
            </select>
          </div>
          <div class="request-field">
            <label for="request-ward-code">{copy("Registration area (RA)", "Wurin ƙaura zaye (RA)")} <span class="request-required" aria-hidden="true">*</span></label>
            <select id="request-ward-code" name="ward_code" required disabled>
              <option value="" {attr(ra_placeholder, ra_placeholder_ha)} selected>{esc(ra_placeholder)}</option>
              {ra_options}
            </select>
          </div>
        </div>
        <p class="request-note" id="request-ra-note" data-en="{esc(limitation_en)}" data-ha="{esc(limitation_ha)}">{esc(limitation_en)}</p>
        <div class="request-field">
          <label for="request-address">{copy("Address or location", "Adireshi ko wuri")} <span class="request-required" aria-hidden="true">*</span></label>
          <input id="request-address" name="address" type="text" maxlength="300" autocomplete="street-address" required>
        </div>
        <div class="request-field">
          <label for="request-category">{copy("Primary request category", "Babban nauyin buƙatar")} <span class="request-required" aria-hidden="true">*</span></label>
          <select id="request-category" name="category" required>
            <option value="" {attr("Choose one category", "Zaɓi nauyi daya")} selected>Choose one category</option>
            {category_options}
          </select>
        </div>
        <div class="request-field">
          <label for="request-details">{copy("Details", "Bayani")} <span class="request-required" aria-hidden="true">*</span></label>
          <textarea id="request-details" name="details" rows="6" maxlength="1000" required></textarea>
        </div>
        <fieldset class="request-contact-fields">
          <legend>{copy("Optional follow-up details", "Bayanan binfollow-up (zaɓi)")}</legend>
          <div class="request-grid">
            <div class="request-field"><label for="request-name">{copy("Name (optional)", "Suna (zaɓi)")}</label><input id="request-name" name="name" type="text" maxlength="120" autocomplete="name"></div>
            <div class="request-field"><label for="request-phone">{copy("Phone (optional)", "L waya (zaɓi)")}</label><input id="request-phone" name="phone" type="tel" maxlength="40" autocomplete="tel" inputmode="tel"></div>
            <div class="request-field request-field-wide"><label for="request-email">{copy("Email (optional)", "Imel (zaɓi)")}</label><input id="request-email" name="email" type="email" maxlength="254" autocomplete="email"></div>
          </div>
        </fieldset>
        <div class="request-field request-honeypot" aria-hidden="true"><label for="request-website" data-en="Website" data-ha="Yanayin gari">Website</label><input id="request-website" name="website" type="text" tabindex="-1" autocomplete="off"></div>
        <div class="request-consent">
          <input id="request-consent" name="consent" type="checkbox" required>
          <label for="request-consent">{copy("I consent to the use of these details to receive and follow up on this request.", "Na amince da amfani da waƙannan bayanan don karɓi buƙatar ta kuma sani da ita.")} <span class="request-required" aria-hidden="true">*</span></label>
        </div>
        <p class="request-note" id="request-identity-note" data-en="Do not enter a voter ID. No electoral identity number is requested. Any confirmation ID is a generated request tracking reference, not a voter ID." data-ha="Kada shigar da ID na zabb'ar masu zayyawa. Ba a nemi lambar wayo da zai gano mutum ba. ID na tabbaci yana nufin bin buƙatar kawai, ba ID na zabb'ar masu zayyawa ba.">Do not enter a voter ID. No electoral identity number is requested. Any confirmation ID is a generated request tracking reference, not a voter ID.</p>
         <button class="btn request-submit" type="submit" data-request-submit {'disabled' if not endpoint_configured else ''}><span data-en="Submit request" data-ha="Aika buƙatar">Submit request</span></button>
         <p class="request-status" data-request-status role="status" aria-live="polite" aria-atomic="true" data-en="Submission is currently unavailable. Please check the status above." data-ha="A ba da damar aika buƙatar yanzu. Duba matsayi a sama." data-unavailable-en="Submission is currently unavailable. Please check the status above." data-unavailable-ha="A ba da damar aika buƙatar yanzu. Duba matsayi a sama." data-submitting-en="Sending your request." data-submitting-ha="Ana aika buƙatar." data-error-en="We could not send your request. Please try again later." data-error-ha="Ba mu iya aika buƙatar. Ka sake gwada daga baya.">Submission is currently unavailable. Please check the status above.</p>
        <div class="request-confirmation" data-request-confirmation role="status" aria-live="polite" aria-atomic="true" hidden data-en="Request received. Any confirmation ID is a generated request tracking reference, not a voter ID." data-ha="An karɓi buƙatar. ID na tabbaci yana nufin bin buƙatar kawai, ba ID na zabb'ar masu zayyawa ba.">Request received. Any confirmation ID is a generated request tracking reference, not a voter ID.</div>
      </form>
      <aside class="request-aside" aria-label="Request guidance">
        <div><span>01</span><h3>{copy("Describe the problem", "Bayyana matsala")}</h3><p>{copy("Give the location and what is needed. One request keeps the issue clear for follow-up.", "Yi bayyana wuri da abin da ake buƙata. Buƙatar daya tana sa batun ya kasance mai sauƙi idan a biyo shi.")}</p></div>
        <div><span>02</span><h3>{copy("Keep personal details optional", "Sanya bayanan sirri zaɓi")}</h3><p>{copy("Add contact information only if you want a response. It will be sent only to the configured request service.", "Ƙara bayan tuntu kawai idan kana son amsa. Za a tura shi kawai ga sabis na buƙatar da aka saita.")}</p></div>
        <div><span>03</span><h3>{copy("Use the tracking reference", "Yi amfani da maƙai bin")}</h3><p>{copy("A confirmation reference helps follow up only after the request service accepts a request. It is not a voter ID.", "Maƙai bin ya taimaka ne kawai bayan sabis ɗin buƙatar ya karɓi buƙatar. Ba ID na zabb'ar masu zayyawa ba.")}</p></div>
      </aside>
    </div>
  </div>
</section>'''

# ---------------------------------------------------------------------------
# Multi-page shell (S3)
# ---------------------------------------------------------------------------
# The site is generated as six flat files in docs/. Flat, not nested, so the
# existing assets/brand/... relative paths keep working unchanged on every page.

SITE_CSS = """:root{--ink:#13202b;--navy:#0b263c;--blue:#145d86;--sky:#d9eff6;--gold:#d89b31;--gold-soft:#f5e6c4;--paper:#f7f4ed;--white:#fffdf8;--line:#d8d8cd;--muted:#6c7880;--green:#2e7254;--green-soft:#dcefe3;--shadow:0 24px 70px rgba(11,38,60,.14)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:"Trebuchet MS","Segoe UI",sans-serif;line-height:1.55;overflow-x:hidden}
body::before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.12;background-image:radial-gradient(#13202b .55px,transparent .55px);background-size:7px 7px;mix-blend-mode:multiply;z-index:10}
a{color:inherit}
.shell{width:min(1240px,calc(100% - 40px));margin:auto}
.topbar{position:absolute;z-index:2;top:0;left:0;right:0;color:#fff;padding:22px 0}
.topbar-inner{display:flex;align-items:center;justify-content:space-between;gap:20px}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none}
/* The emblem already has a transparent background, so it needs no colour filter.
   An earlier brightness(0) invert(1) collapsed the logo's opaque white page and the
   whitened artwork into one solid block. */
.brand img{width:38px;height:44px;object-fit:contain;flex:none}
.brand small{display:block;font-size:10px;letter-spacing:.16em;text-transform:uppercase;opacity:.74;margin-top:-3px}
.nav{display:flex;align-items:center;gap:24px;font-size:12px;letter-spacing:.06em;text-transform:uppercase}
.nav a{opacity:.78;text-decoration:none}
.nav a:hover{opacity:1}
.lang{display:flex;align-items:center;gap:9px}
.lang-label{display:flex;align-items:center;gap:6px;font-size:10px;letter-spacing:.11em;text-transform:uppercase;opacity:.72;white-space:nowrap}
.lang-label svg{width:14px;height:14px;flex:none;fill:none;stroke:currentColor;stroke-width:1.6}
.lang-toggle{display:flex;border:1px solid rgba(255,255,255,.4);border-radius:999px;padding:3px}
.lang button{border:0;background:transparent;color:#fff;padding:5px 9px;border-radius:999px;cursor:pointer;font:inherit;font-size:10px}
.lang button.active{background:#fff;color:var(--navy)}
.hero{min-height:760px;background:var(--navy);color:#fff;position:relative;overflow:hidden;display:flex;align-items:center;padding:128px 0 74px}
.hero::before{content:"";position:absolute;width:900px;height:900px;right:-220px;top:-340px;border:1px solid rgba(255,255,255,.13);border-radius:50%;box-shadow:0 0 0 70px rgba(255,255,255,.025),0 0 0 140px rgba(255,255,255,.02)}
.hero::after{content:"";position:absolute;inset:auto -10% 0;height:180px;background:linear-gradient(180deg,transparent,rgba(5,20,31,.5));clip-path:polygon(0 100%,100% 22%,100% 100%)}
.hero-grid{display:grid;grid-template-columns:1.02fr .98fr;align-items:center;gap:56px;position:relative;z-index:1}
.eyebrow{font-size:11px;letter-spacing:.19em;text-transform:uppercase;font-weight:700;color:var(--gold)}
.hero h1{font-family:Georgia,"Times New Roman",serif;font-size:clamp(3.5rem,7.3vw,7.3rem);font-weight:400;line-height:.91;letter-spacing:-.06em;margin:22px 0 26px;max-width:760px}
.hero h1 em{color:#f4c35d;font-style:normal}
.hero-lede{font-size:clamp(1.05rem,1.7vw,1.35rem);color:rgba(255,255,255,.76);max-width:590px;margin:0 0 32px}
.hero-actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.btn{display:inline-flex;align-items:center;gap:10px;padding:14px 18px;border:1px solid transparent;border-radius:999px;text-decoration:none;font-weight:700;font-size:12px;letter-spacing:.05em;text-transform:uppercase;transition:transform .2s,box-shadow .2s,background .2s}
.btn:hover{transform:translateY(-2px)}
.btn-primary{background:var(--gold);color:var(--navy);box-shadow:0 12px 24px rgba(216,155,49,.22)}
.btn-secondary{color:#fff;border-color:rgba(255,255,255,.28);background:rgba(255,255,255,.04)}
.hero-note{margin-top:30px;display:flex;gap:18px;align-items:center;color:rgba(255,255,255,.65);font-size:11px;letter-spacing:.08em;text-transform:uppercase}
.hero-note::before{content:"";width:38px;height:1px;background:var(--gold)}
.portrait-wrap{min-height:570px;position:relative;display:flex;align-items:end;justify-content:center}
.portrait-wrap::before{content:"";position:absolute;width:380px;height:380px;border-radius:50%;background:var(--gold);top:35px;right:25px;opacity:.9}
.portrait-wrap::after{content:"";position:absolute;width:420px;height:520px;border:1px solid rgba(255,255,255,.23);right:-20px;top:0;transform:rotate(8deg)}
.portrait{position:relative;z-index:1;width:min(100%,520px);max-height:610px;object-fit:contain;object-position:center bottom;filter:drop-shadow(0 30px 35px rgba(0,0,0,.25));mix-blend-mode:screen}
.portrait-caption{position:absolute;z-index:2;bottom:20px;left:0;max-width:240px;padding:14px 16px;background:rgba(255,253,248,.95);color:var(--ink);border-radius:3px;box-shadow:var(--shadow);font-size:12px}
.portrait-caption strong{display:block;font-family:Georgia,serif;font-size:20px;font-weight:400}
.motto{font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:rgba(255,255,255,.55);margin-top:34px}
.stats{background:var(--gold);color:var(--navy);position:relative;z-index:3;margin-top:-1px}
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr)}
.stat{padding:24px 28px;border-right:1px solid rgba(11,38,60,.18)}
.stat:last-child{border-right:0}
.stat strong{display:block;font-family:Georgia,serif;font-size:2.25rem;font-weight:400;line-height:1}
.stat span{display:block;font-size:10px;letter-spacing:.14em;text-transform:uppercase;margin-top:8px;font-weight:700}
.section{padding:100px 0}
.section-head{display:flex;justify-content:space-between;align-items:end;gap:30px;margin-bottom:38px}
.section-head h2,.section-head h3{font-family:Georgia,serif;font-size:clamp(2.2rem,4vw,4rem);font-weight:400;line-height:.98;letter-spacing:-.05em;margin:12px 0 0;max-width:720px}
.section-head p{color:var(--muted);max-width:360px;font-size:14px;margin:0}
.light-rule{border-top:1px solid var(--line)}
.intro-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:80px;align-items:start}
.intro-copy{font-family:Georgia,serif;font-size:clamp(1.7rem,3vw,2.7rem);line-height:1.08;letter-spacing:-.04em;margin:0}
.note-box{border-left:3px solid var(--gold);padding:8px 0 8px 22px;color:var(--muted);font-size:14px}
.progress-path{background:var(--white);border:1px solid var(--line);box-shadow:var(--shadow);padding:22px;display:grid;grid-template-columns:repeat(4,1fr);gap:0;margin-top:60px}
.path-step{padding:22px 20px;position:relative;min-height:180px}
.path-step:not(:last-child)::after{content:"→";position:absolute;right:-13px;top:76px;width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--gold);color:var(--navy);font-size:19px;z-index:2}
.step-no{font-size:10px;letter-spacing:.16em;color:var(--gold);font-weight:700}
.path-step h3{font-family:Georgia,serif;font-size:1.4rem;font-weight:400;margin:18px 0 8px}
.path-step p{font-size:13px;color:var(--muted);margin:0}
.filter-row{display:flex;gap:8px;flex-wrap:wrap;margin:28px 0 22px}
.filter{border:1px solid var(--line);background:transparent;border-radius:999px;padding:8px 13px;font:inherit;font-size:11px;cursor:pointer;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.filter.active,.filter:hover{background:var(--navy);border-color:var(--navy);color:#fff}
.arrow-list{display:grid;gap:18px}
.arrow-card{background:var(--white);border:1px solid var(--line);padding:0;overflow:hidden;box-shadow:0 12px 35px rgba(11,38,60,.05)}
.arrow-head{display:flex;justify-content:space-between;align-items:center;padding:17px 22px;border-bottom:1px solid var(--line);background:#fbfaf6}
.arrow-index{font-family:Georgia,serif;font-size:1.2rem;color:var(--gold)}
.arrow-path{display:grid;grid-template-columns:1fr 28px 1.45fr 28px 1.2fr 28px 1.1fr;align-items:stretch;padding:22px}
.path-node{padding:18px;min-width:0}
.path-node:nth-child(odd){background:#f7f8f3;border:1px solid #e4e8df;border-radius:2px}
.achievement-node{background:var(--green-soft)!important;border-color:#c9e0ce!important}
.promise-node{background:#fff6e5!important;border-color:#efd9ac!important}
.result-node{background:#eaf4f7!important;border-color:#c8e0e8!important}
.path-arrow{display:grid;place-items:center;color:var(--gold);font-size:24px;padding-top:70px}
.node-number{font-size:10px;color:var(--muted);letter-spacing:.15em}
.path-node h3{font-family:Georgia,serif;font-size:1.35rem;font-weight:400;line-height:1.1;margin:15px 0 9px}
.path-node p{font-size:13px;line-height:1.45;margin:0 0 14px;color:#35434a}
.node-tag{display:inline-block;font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);border-top:1px solid currentColor;padding-top:6px}
.achievement-list{list-style:none;padding:0;margin:0 0 14px;display:grid;gap:9px}
.achievement-item{border-bottom:1px solid rgba(46,114,84,.22);padding-bottom:9px}
.achievement-item:last-child{border-bottom:0;padding-bottom:0}
.item-top{display:flex;align-items:start;justify-content:space-between;gap:10px}
.item-top strong{font-size:12px;line-height:1.25}
.achievement-item p{font-size:11px;margin:5px 0;color:#4b6259}
.item-meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:9px;color:#567064}
.status{display:inline-block;white-space:nowrap;border-radius:999px;padding:3px 6px;font-size:8px;letter-spacing:.06em;text-transform:uppercase;font-weight:700}
.status-progress{background:var(--green);color:#fff}
.status-underway{background:var(--blue);color:#fff}
.status-milestone{background:#765b9e;color:#fff}
.status-promise{background:var(--gold);color:var(--navy)}
.status-next{background:#b88920;color:#fff}
.status-measured{background:#7a6c9b;color:#fff}
.source-link{font-size:9px;text-decoration:none;color:var(--blue);font-weight:700;white-space:nowrap}
.source-link:hover{text-decoration:underline}
.empty-item{font-size:12px;color:var(--muted)}
.lga-section{background:var(--navy);color:#fff;position:relative;overflow:hidden}
.lga-section::before{content:"";position:absolute;width:600px;height:600px;border:1px solid rgba(255,255,255,.12);border-radius:50%;right:-180px;top:-260px;box-shadow:0 0 0 50px rgba(255,255,255,.025),0 0 0 100px rgba(255,255,255,.02)}
.lga-section .section-head h2{color:#fff}
.lga-section .section-head p{color:rgba(255,255,255,.65)}
.lga-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;position:relative;z-index:1}
.lga-tile{text-align:left;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.05);color:#fff;padding:18px 16px;min-height:105px;cursor:pointer;font:inherit;position:relative;transition:background .2s,transform .2s,border .2s}
.lga-tile:hover,.lga-tile.active{background:rgba(216,155,49,.17);border-color:var(--gold);transform:translateY(-3px)}
.lga-tile.lga-specific{border-color:rgba(216,155,49,.62);background:rgba(216,155,49,.08)}
.lga-tile.lga-specific .lga-dot{box-shadow:0 0 0 4px rgba(216,155,49,.16)}
.lga-tile strong{display:block;font-family:Georgia,serif;font-size:1.25rem;font-weight:400}
.lga-tile small{display:block;color:rgba(255,255,255,.55);font-size:9px;letter-spacing:.1em;text-transform:uppercase;margin-top:20px}
.lga-dot{display:block;width:7px;height:7px;border-radius:50%;background:var(--gold);margin-bottom:12px}
.lga-detail{margin-top:26px;border:1px solid rgba(255,255,255,.2);padding:25px;background:rgba(255,255,255,.06);display:flex;justify-content:space-between;gap:30px;align-items:start}
.lga-detail h3{font-family:Georgia,serif;font-size:2rem;font-weight:400;margin:0 0 8px}
.lga-detail p{color:rgba(255,255,255,.66);font-size:14px;max-width:620px;margin:0}
.lga-detail .detail-label{color:var(--gold);font-size:10px;text-transform:uppercase;letter-spacing:.15em;white-space:nowrap}
.governance-grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:64px;align-items:start}
.governor-card{background:var(--navy);color:#fff;padding:16px;box-shadow:var(--shadow);position:relative}
.governor-card img{width:100%;height:440px;object-fit:cover;object-position:center top;display:block;filter:saturate(.8)}
.governor-caption{padding:18px 12px 12px;display:flex;justify-content:space-between;gap:12px;align-items:end}
.governor-caption strong{font-family:Georgia,serif;font-size:1.7rem;font-weight:400}
.governor-caption span{color:rgba(255,255,255,.55);font-size:10px;text-align:right;line-height:1.4}
.governance-copy h3{font-family:Georgia,serif;font-size:clamp(2rem,4vw,3.8rem);font-weight:400;line-height:1;letter-spacing:-.05em;margin:0 0 20px}
.governance-copy p{font-size:15px;color:var(--muted);max-width:560px}
.continuity-list{display:grid;gap:12px;margin-top:28px}
.continuity-item{display:grid;grid-template-columns:32px 1fr;gap:12px;padding:16px 0;border-top:1px solid var(--line)}
.continuity-item b{color:var(--gold);font-family:Georgia,serif;font-size:1.5rem;font-weight:400}
.continuity-item span{font-size:13px}
.agenda-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.agenda-card{min-height:250px;background:var(--white);border:1px solid var(--line);padding:20px;display:flex;flex-direction:column;justify-content:space-between;transition:transform .2s,box-shadow .2s}
.agenda-card:hover{transform:translateY(-4px);box-shadow:var(--shadow)}
.agenda-card .agenda-no{font-family:Georgia,serif;font-size:2.6rem;color:var(--gold);line-height:1}
.agenda-card h3{font-family:Georgia,serif;font-size:1.35rem;font-weight:400;line-height:1.1;margin:15px 0 8px}
.agenda-card p{font-size:11px;color:var(--muted);margin:0}
.sources-section{background:#ecebe4;padding:70px 0}
.featured-section{padding:100px 0;background:#f1eee5;border-top:1px solid var(--line)}
.featured-section .section-head h2{max-width:780px}
.featured-carousel{border:1px solid var(--line);background:var(--white);padding:18px;box-shadow:var(--shadow)}
.featured-carousel:focus-visible{outline:3px solid var(--gold);outline-offset:4px}
.featured-toolbar{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;padding-bottom:16px;border-bottom:1px solid var(--line)}
.featured-scope-filters{display:flex;gap:8px;flex-wrap:wrap}
.featured-scope-filter,.featured-control{border:1px solid var(--line);background:transparent;border-radius:999px;padding:8px 12px;font:inherit;font-size:10px;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;color:var(--muted)}
.featured-scope-filter.active,.featured-scope-filter:hover,.featured-control:hover{background:var(--navy);border-color:var(--navy);color:#fff}
.featured-controls{display:flex;align-items:center;gap:9px}
.featured-control:disabled{opacity:.4;cursor:not-allowed}
.featured-status{min-width:48px;text-align:center;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--navy);font-weight:700}
.featured-slides{list-style:none;padding:0;margin:22px 0 0;display:grid;gap:18px}
.featured-slide{display:grid;grid-template-columns:minmax(240px,.9fr) minmax(0,1.1fr);gap:24px;padding:18px;border:1px solid var(--line);background:#fbfaf6}
.featured-carousel-ready .featured-slide{display:none}
.featured-carousel-ready .featured-slide.is-active{display:grid}
.featured-media{margin:0;min-width:0}
.featured-media img{display:block;width:100%;height:310px;object-fit:cover;background:#dfe8e5}
.featured-media figcaption{font-size:10px;line-height:1.4;color:var(--muted);padding-top:8px}
.featured-image-note{display:block;margin-top:8px;padding:6px 8px;background:#fff6e5;border:1px solid #efd9ac;color:#6d4a12;font-size:9px;line-height:1.35}
.featured-slide-copy{display:flex;flex-direction:column;justify-content:center;min-width:0}
.featured-slide-meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.featured-sector,.featured-scope-badge{display:inline-block;padding:4px 8px;border-radius:999px;font-size:9px;letter-spacing:.08em;text-transform:uppercase;font-weight:700}
.featured-sector{background:var(--sky);color:var(--navy)}
.featured-scope-badge{background:var(--gold-soft);color:#6d4a12}
.featured-slide h3{font-family:Georgia,serif;font-size:clamp(1.7rem,3vw,2.6rem);font-weight:400;line-height:1.05;letter-spacing:-.04em;margin:18px 0 12px}
.featured-caption{font-size:14px;line-height:1.5;color:#35434a;margin:0}
.featured-source{margin-top:22px}
.featured-pending-section .section-head p{max-width:500px}
.requests-section{background:var(--white);border-top:1px solid var(--line)}
.request-layout{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr);gap:28px;align-items:start}
.request-form{background:#fbfaf6;border:1px solid var(--line);padding:clamp(20px,4vw,40px);box-shadow:var(--shadow);position:relative}
.request-config-status{margin:0 0 26px;padding:12px 14px;border-left:3px solid var(--gold);background:var(--gold-soft);color:#5f4317;font-size:12px;font-weight:700}
.request-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.request-field{display:grid;gap:8px;margin-bottom:18px;min-width:0}
.request-field-wide{grid-column:1/-1}
.request-field label,.request-contact-fields legend{font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--navy)}
.request-required{color:#9a351f}
.request-field input,.request-field select,.request-field textarea{width:100%;border:1px solid #bfc7c6;border-radius:0;background:#fff;color:var(--ink);font:inherit;font-size:14px;padding:12px 13px;transition:border-color .2s,box-shadow .2s,background .2s}
.request-field textarea{resize:vertical;min-height:145px}
.request-field select{min-height:47px}
.request-field input:hover,.request-field select:hover,.request-field textarea:hover{border-color:#829493}
.request-field input:focus,.request-field select:focus,.request-field textarea:focus{outline:3px solid rgba(216,155,49,.38);outline-offset:2px;border-color:var(--blue);background:#fff}
.request-field input:disabled,.request-field select:disabled{background:#ecebe4;color:#788086;cursor:not-allowed}
.request-note{margin:-4px 0 20px;padding:12px 14px;background:#eef5f1;border-left:3px solid var(--green);color:#355448;font-size:11px;line-height:1.55}
.request-contact-fields{margin:2px 0 20px;padding:20px;border:1px solid var(--line);background:#f3f1e9;min-width:0}
.request-contact-fields legend{padding:0 8px}
.request-consent{display:grid;grid-template-columns:22px minmax(0,1fr);gap:10px;align-items:start;margin:22px 0 12px}
.request-consent input{width:20px;height:20px;margin:2px 0 0;accent-color:var(--blue)}
.request-consent label{font-size:12px;line-height:1.5;color:#35434a;cursor:pointer}
.request-honeypot{position:absolute!important;left:-10000px!important;width:1px!important;height:1px!important;overflow:hidden!important}
.request-submit{border:0;background:var(--navy);color:#fff;cursor:pointer;box-shadow:0 10px 22px rgba(11,38,60,.18)}
.request-submit:hover{background:var(--blue)}
.request-submit:focus-visible{outline:3px solid var(--gold);outline-offset:4px}
.request-submit:disabled{opacity:.55;cursor:wait;transform:none}
.request-status,.request-confirmation{margin:16px 0 0;padding:12px 14px;font-size:12px;line-height:1.5}
.request-status{background:#ecebe4;border-left:3px solid #7b8589;color:#46545a}
.request-status.is-error{background:#fff0eb;border-left-color:#9a351f;color:#7a2818}
.request-confirmation{background:var(--green-soft);border-left:3px solid var(--green);color:#244d3a;font-weight:700}
.request-status[hidden],.request-confirmation[hidden]{display:none}
.request-aside{background:var(--navy);color:#fff;padding:8px 28px;box-shadow:var(--shadow)}
.request-aside>div{padding:26px 0;border-bottom:1px solid rgba(255,255,255,.16)}
.request-aside>div:last-child{border-bottom:0}
.request-aside span{display:block;color:var(--gold);font-size:10px;letter-spacing:.16em;font-weight:700;margin-bottom:12px}
.request-aside h3{font-family:Georgia,serif;font-size:1.35rem;font-weight:400;margin:0 0 10px}
.request-aside p{font-size:12px;line-height:1.6;color:rgba(255,255,255,.68);margin:0}
.indicator-section{padding:100px 0;background:#eef5f1;border-top:1px solid var(--line)}
.indicator-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.indicator-card{background:var(--white);border:1px solid var(--line);padding:20px;min-height:220px;box-shadow:0 12px 30px rgba(11,38,60,.05);display:flex;flex-direction:column}
.indicator-top{display:flex;justify-content:space-between;align-items:start;gap:10px}
.indicator-top .eyebrow{font-size:9px;letter-spacing:.12em}
.indicator-card h3{font-family:Georgia,serif;font-size:1.25rem;font-weight:400;line-height:1.15;margin:20px 0 12px}
.indicator-value{display:flex;align-items:baseline;gap:8px;color:var(--navy)}
.indicator-value strong{font-family:Georgia,serif;font-size:1.7rem;font-weight:400}
.indicator-value span{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}
.indicator-card p{font-size:11px;color:var(--muted);line-height:1.45;margin:12px 0 16px}
.indicator-meta{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-top:auto;font-size:9px;color:var(--muted)}
.source-list{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:1fr 1fr;gap:0 32px}
.source-list li{display:grid;grid-template-columns:32px 1fr auto;align-items:center;gap:10px;padding:13px 0;border-bottom:1px solid #d4d5cb;font-size:12px}
.source-list li span:nth-child(2){display:grid;gap:3px}
.source-list li small{font-size:9px;color:var(--muted)}
.source-legend{display:flex;flex-wrap:wrap;gap:14px;margin:20px 0 0;font-size:10px;color:var(--muted)}
.source-grade{display:grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--navy);color:#fff;font-size:10px;font-weight:700}
.source-link{justify-self:end}
.site-footer{background:#081d2c;color:#fff;padding:34px 0 28px}
.footer-inner{display:flex;justify-content:space-between;gap:30px;align-items:center;flex-wrap:wrap}
.footer-inner p{font-size:11px;color:rgba(255,255,255,.56);margin:0;max-width:650px}
.footer-inner strong{font-family:Georgia,serif;font-size:1.3rem;font-weight:400;display:block;margin-bottom:6px}
.deerflow{font-size:10px;color:rgba(255,255,255,.45);text-decoration:none;border:1px solid rgba(255,255,255,.2);padding:7px 10px;border-radius:999px;white-space:nowrap}
.deerflow:hover{color:#fff;border-color:#fff}
/* Sponsor slot. Deliberately reads as an unfilled placeholder: no invented name, no
   invented contribution, no amount. The contribution line is a factual disclosure the
   owner completes, not a claim of delivered achievement. */
.sponsor{display:flex;gap:14px;align-items:center;max-width:400px;padding:12px 16px;border:1px dashed rgba(255,255,255,.28);border-radius:4px;background:rgba(255,255,255,.03)}
.sponsor-photo{width:58px;height:58px;flex:none;border:1px dashed rgba(255,255,255,.3);border-radius:3px;display:grid;place-items:center;text-align:center;padding:4px}
.sponsor-photo span{font-size:8px;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.5);line-height:1.3}
.sponsor-body{min-width:0}
.sponsor-label{display:block;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:3px}
.sponsor-name{display:block;font-family:Georgia,serif;font-size:1.05rem;font-weight:400;color:#fff}
.sponsor-contribution{display:block;font-size:11px;line-height:1.45;color:rgba(255,255,255,.72);margin-top:5px}
.sponsor-contribution b{color:#fff;font-weight:700}
.reveal{opacity:0;transform:translateY(15px);animation:rise .7s ease forwards;animation-delay:var(--delay,0s)}
@keyframes rise{to{opacity:1;transform:translateY(0)}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}.reveal{opacity:1;transform:none}}
@media (max-width:1050px){.indicator-grid{grid-template-columns:repeat(2,1fr)}.featured-slide{grid-template-columns:1fr}.request-layout{grid-template-columns:1fr}.request-aside{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;padding:8px 24px}.request-aside>div{padding:20px 0;border-bottom:0}}
@media (max-width:760px){.indicator-section{padding:70px 0}.indicator-grid{grid-template-columns:1fr}.featured-section{padding:70px 0}.featured-carousel{padding:12px}.featured-toolbar{align-items:flex-start;flex-direction:column}.featured-scope-filters{width:100%}.featured-slide{padding:14px}.featured-media img{height:240px}.request-grid{grid-template-columns:1fr}.request-field-wide{grid-column:auto}.request-aside{grid-template-columns:1fr;padding:8px 20px}.request-form{padding:18px}.request-field input,.request-field select,.request-field textarea{font-size:16px}}
@media (max-width:1050px){.nav{display:none}.hero-grid{grid-template-columns:1fr .8fr;gap:20px}.portrait-wrap{min-height:470px}.lga-grid{grid-template-columns:repeat(4,1fr)}.agenda-grid{grid-template-columns:repeat(3,1fr)}.arrow-path{grid-template-columns:1fr 20px 1.4fr 20px 1.2fr 20px 1.1fr;padding:14px}}
@media (max-width:760px){.shell{width:min(100% - 28px,1240px)}.hero{min-height:auto;padding-top:112px;padding-bottom:54px}.hero-grid,.intro-grid,.governance-grid{grid-template-columns:1fr}.hero h1{font-size:clamp(3.2rem,16vw,5.5rem)}.portrait-wrap{min-height:390px;margin-top:20px}.portrait-wrap::before{width:280px;height:280px;right:4%}.portrait-wrap::after{width:320px;height:400px;right:1%}.portrait{max-height:420px}.stats-grid{grid-template-columns:1fr 1fr}.stat{padding:18px 15px;border-bottom:1px solid rgba(11,38,60,.18)}.stat:nth-child(2){border-right:0}.section{padding:70px 0}.section-head{display:block}.section-head p{margin-top:18px}.progress-path{grid-template-columns:1fr;padding:16px}.path-step{min-height:0;padding:14px 16px 24px}.path-step:not(:last-child)::after{content:"↓";right:auto;left:18px;top:auto;bottom:-14px}.arrow-head{padding:15px 16px}.arrow-path{display:block;padding:14px}.path-node{margin-bottom:10px;padding:16px}.path-arrow{padding:0;height:24px;transform:rotate(90deg)}.lga-grid{grid-template-columns:1fr 1fr}.lga-detail{display:block}.lga-detail .detail-label{display:block;margin-bottom:12px}.governor-card img{height:340px}.agenda-grid{grid-template-columns:1fr 1fr}.source-list{grid-template-columns:1fr}.footer-inner{display:block}.deerflow{display:inline-block;margin-top:20px}}"""

SHELL_CSS = """
/* --- shared multi-page shell ------------------------------------------- */
.page-head{background:var(--navy);position:relative;z-index:2}
/* position:relative, not static: the mobile panel is absolutely positioned at
   top:100% of this bar and needs it as its containing block. */
.page-head .topbar{position:relative;background:var(--navy);padding:18px 0}
.page-hero{background:var(--navy);color:#fff;padding:56px 0 62px;position:relative;overflow:hidden}
.page-hero::before{content:"";position:absolute;width:760px;height:760px;right:-200px;top:-420px;border:1px solid rgba(255,255,255,.13);border-radius:50%;box-shadow:0 0 0 60px rgba(255,255,255,.025),0 0 0 120px rgba(255,255,255,.02)}
.page-hero .shell{position:relative;z-index:1}
.page-hero .eyebrow{color:var(--gold)}
.page-hero h1{font-family:Georgia,"Times New Roman",serif;font-size:clamp(2.2rem,4.6vw,3.9rem);font-weight:400;line-height:1.02;letter-spacing:-.05em;margin:16px 0 18px;max-width:820px}
.page-hero p{font-size:clamp(1rem,1.4vw,1.15rem);color:rgba(255,255,255,.76);max-width:640px;margin:0}
.page-hero .crumbs{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px;font-size:11px;letter-spacing:.09em;text-transform:uppercase}
.page-hero .crumbs a{color:rgba(255,255,255,.66);text-decoration:none;border-bottom:1px solid rgba(255,255,255,.28);padding-bottom:2px}
.page-hero .crumbs a:hover{color:#fff;border-color:#fff}
.page-hero .crumbs span{color:rgba(255,255,255,.4)}

/* Primary nav. Hidden below 1050px, where .navmenu takes over - without that,
   phones get no navigation at all once the site has subpages. */
.navmenu{display:none}
.navmenu-toggle{list-style:none;cursor:pointer;display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:.1em;text-transform:uppercase;border:1px solid rgba(255,255,255,.4);border-radius:999px;padding:7px 12px}
.navmenu-toggle::-webkit-details-marker{display:none}
.navmenu-toggle svg{width:15px;height:15px;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round}
.navmenu-panel{position:absolute;left:0;right:0;top:100%;background:var(--navy);border-top:1px solid rgba(255,255,255,.12);box-shadow:0 22px 44px rgba(5,20,31,.4);padding:10px 0 16px}
.navmenu-panel a{display:block;padding:11px 20px;font-size:12px;letter-spacing:.07em;text-transform:uppercase;color:rgba(255,255,255,.82);text-decoration:none;border-left:2px solid transparent}
.navmenu-panel a:hover{color:#fff;background:rgba(255,255,255,.05)}
.navmenu-panel a[aria-current="page"]{color:var(--gold);border-left-color:var(--gold)}

/* Cross-links from the home page into the subpages. */
.nav-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.nav-card{display:block;text-decoration:none;color:inherit;background:var(--white);border:1px solid var(--line);padding:24px 22px;box-shadow:0 12px 32px rgba(11,38,60,.05);transition:transform .2s,box-shadow .2s,border-color .2s}
.nav-card:hover{transform:translateY(-3px);box-shadow:var(--shadow);border-color:var(--gold)}
.nav-card .nav-card-no{font-size:10px;letter-spacing:.16em;color:var(--gold);font-weight:700}
.nav-card h3{font-family:Georgia,serif;font-size:1.35rem;font-weight:400;margin:12px 0 8px;letter-spacing:-.02em}
.nav-card p{font-size:13px;color:var(--muted);margin:0}
.nav-card .nav-card-go{display:inline-block;margin-top:14px;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--navy);font-weight:700}

.skip-link{position:absolute;left:-9999px;top:0;background:var(--gold);color:var(--navy);padding:10px 16px;z-index:50;font-size:12px;font-weight:700}
.skip-link:focus{left:8px;top:8px}
.nav a:focus-visible,.navmenu-toggle:focus-visible,.nav-card:focus-visible,.lang button:focus-visible{outline:2px solid var(--gold);outline-offset:3px}

@media (max-width:1050px){
.navmenu{display:block}
}
@media (max-width:760px){
.nav-cards{grid-template-columns:1fr}
.page-hero{padding:40px 0 46px}
.nav-card{padding:20px}
}
"""

# Core script. Ships on EVERY page. renderFeatured is seeded as a no-op so the
# carousel script can override it by assignment; setLanguage calls both hooks on
# every page, and a ReferenceError here would kill the language toggle.
SCRIPT_CORE = r"""
const root=document.documentElement;
let currentLanguage='en';
let selectedLga='';
let renderFeatured=()=>{};
const renderLgaDetail=()=>{if(!selectedLga)return;const btn=document.querySelector('[data-lga="'+selectedLga+'"]');if(!btn)return;const titleEl=document.getElementById('selected-lga');const copyEl=document.getElementById('selected-copy');if(!titleEl||!copyEl)return;const summary=currentLanguage==='ha'?btn.dataset.summaryHa:btn.dataset.summary;const promise=currentLanguage==='ha'?btn.dataset.promiseHa:btn.dataset.promise;const result=currentLanguage==='ha'?btn.dataset.resultHa:btn.dataset.result;titleEl.textContent=selectedLga;copyEl.textContent=currentLanguage==='ha'?selectedLga+': '+summary+' APM: '+promise+' Sami na gaba: '+result:selectedLga+': '+summary+' APM: '+promise+' Next result: '+result;};
const LANGUAGE_KEY='apm-lang';
const readStoredLanguage=()=>{try{const stored=window.localStorage.getItem(LANGUAGE_KEY);return stored==='ha'||stored==='en'?stored:null;}catch(error){return null;}};
const storeLanguage=(lang)=>{try{window.localStorage.setItem(LANGUAGE_KEY,lang);}catch(error){/* blocked storage: the toggle still works for this page */}};
const setLanguage=(lang,persist=true)=>{currentLanguage=lang;root.lang=lang;document.querySelectorAll('[data-en][data-ha]').forEach(el=>{if(el.matches('[data-request-confirmation]')&&el.dataset.trackingId)return;el.textContent=el.dataset[lang]||el.dataset.en});document.querySelectorAll('img[data-alt-en][data-alt-ha]').forEach(el=>{el.alt=el.dataset[lang==='ha'?'altHa':'altEn']||el.alt;});document.querySelectorAll('[data-aria-label-en][data-aria-label-ha]').forEach(el=>{el.setAttribute('aria-label',lang==='ha'?el.dataset.ariaLabelHa:el.dataset.ariaLabelEn)});document.querySelectorAll('[data-lang]').forEach(btn=>{const active=btn.dataset.lang===lang;btn.classList.toggle('active',active);btn.setAttribute('aria-pressed',String(active));});renderLgaDetail();renderFeatured();const confirmation=document.querySelector('[data-request-confirmation]');if(confirmation&&confirmation.dataset.trackingId&&!confirmation.hidden)confirmation.textContent=(currentLanguage==='ha'?'An karɓi buƙatar. Maƙai bin: ':'Request received. Tracking reference: ')+confirmation.dataset.trackingId+'.';if(persist)storeLanguage(lang);};
document.querySelectorAll('[data-aria-label-en][data-aria-label-ha]').forEach(el=>{el.setAttribute('aria-label',currentLanguage==='ha'?el.dataset.ariaLabelHa:el.dataset.ariaLabelEn)});
document.querySelectorAll('[data-lang]').forEach(btn=>btn.addEventListener('click',()=>setLanguage(btn.dataset.lang)));
const storedLanguage=readStoredLanguage();if(storedLanguage)setLanguage(storedLanguage,false);
document.querySelectorAll('[data-lga]').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('[data-lga]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');selectedLga=btn.dataset.lga;renderLgaDetail();}));
"""

SCRIPT_INDEX = r"""
document.querySelectorAll('[data-filter]').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');const filter=btn.dataset.filter;document.querySelectorAll('.arrow-card').forEach(card=>card.hidden=filter!=='all'&&card.dataset.sector!==filter);}));
"""

PAGE_NAV = (
    ("index", "Home", "Gida"),
    ("achievements", "Achievements", "Ayyuka da aka yi"),
    ("atlas", "LGA atlas", "Taswirar LGA"),
    ("poll", "Speak to us", "Yi magana da mu"),
    ("agenda", "APM agenda", "Bayan-APM"),
    ("sources", "Sources", "Bayane"),
)

MENU_ICON = ('<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
             '<path d="M4 7h16M4 12h16M4 17h16"/></svg>')


def nav_links(active, css_class=""):
    links = []
    for slug, label_en, label_ha in PAGE_NAV:
        current = ' aria-current="page"' if slug == active else ""
        links.append(
            f'<a class="{esc(css_class)}" href="{esc(slug)}.html"{current}>'
            f'<span data-en="{esc(label_en)}" data-ha="{esc(label_ha)}">{esc(label_en)}</span></a>')
    return "".join(links)


def language_control():
    return (
        '<div class="lang">'
        '<span class="lang-label" id="lang-label">'
        '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M3 12h18M12 3c2.5 2.6 2.5 15.4 0 18M12 3c-2.5 2.6-2.5 15.4 0 18"/></svg>'
        f'{copy("Language", "Harshe")}</span>'
        '<div class="lang-toggle" role="group" aria-labelledby="lang-label">'
        '<button type="button" data-lang="en" class="active" aria-pressed="true">EN</button>'
        '<button type="button" data-lang="ha" aria-pressed="false">HA</button>'
        '</div></div>')


def topbar(active):
    """Shared header. The desktop nav is hidden below 1050px, so the <details>
    menu is the phone path; without it a phone cannot reach any subpage."""
    return (
        '<a class="skip-link" href="#main">Skip to content</a>'
        '<div class="topbar"><div class="shell topbar-inner">'
        '<a class="brand" href="index.html">'
        '<img src="assets/brand/apm-emblem.png" width="38" height="44" '
        'alt="Allied Peoples Movement emblem">'
        '<small>Allied Peoples\' Movement</small></a>'
        '<nav class="nav" data-aria-label-en="Primary navigation" '
        'data-aria-label-ha="Babban menu" aria-label="Primary navigation">'
        f'{nav_links(active)}</nav>'
        f'<details class="navmenu"><summary class="navmenu-toggle">{MENU_ICON}'
        f'<span>{copy("Menu", "Menu")}</span></summary>'
        f'<div class="navmenu-panel">{nav_links(active)}</div></details>'
        f'{language_control()}'
        '</div></div>')


def subpage_open(slug):
    """Subpages have no dark hero, so the header needs its own opaque background.
    .topbar is position:absolute with white text and would otherwise sit on the
    cream page background."""
    return f'<div class="page-head">{topbar(slug)}</div>'


def page_hero(eyebrow_en, eyebrow_ha, title_en, title_ha, lede_en, lede_ha, crumb_en, crumb_ha):
    return (
        '<div class="page-hero"><div class="shell">'
        f'<div class="eyebrow">{localized(eyebrow_en, eyebrow_ha)}</div>'
        f'<h1>{localized(title_en, title_ha)}</h1>'
        f'<p>{localized(lede_en, lede_ha)}</p>'
        '<div class="crumbs"><a href="index.html">'
        f'{copy("Home", "Gida")}</a><span>/</span>'
        f'<span>{localized(crumb_en, crumb_ha)}</span></div>'
        '</div></div>')


def site_footer(built):
    return (
        '<footer class="site-footer"><div class="shell footer-inner">'
        '<div><strong>APM Bauchi Progress &amp; Delivery</strong><p>'
        f'{copy("Public-source campaign intelligence. Built", "Basirar gaggawa daga bayanan al\'umma. An gina a")} {esc(built)}. '
        f'{copy("Public information and campaign materials are labelled separately; this page is not private polling.", "Bayanan al\'umma da kayan gaggawa an bambanta su; wannan shafi ba a ɗauke ra\'yu na ɓoye ba.")}'
        '</p></div>'
        '<div class="sponsor"><div class="sponsor-photo">'
        f'<span>{copy("Sponsor photo", "Hotun mai tallafi")}</span></div>'
        '<div class="sponsor-body">'
        f'<span class="sponsor-label">{copy("Sponsor", "Mai tallafi")}</span>'
        f'<span class="sponsor-name">{copy("[ Sponsor name ]", "[ Suna na mai tallafi ]")}</span>'
        f'<span class="sponsor-contribution">{copy("Contribution:", "Zuciya:")} <b>'
        f'{copy("[ What was contributed and by whom — to be completed by the campaign team ]", "[ Abin da aka ba da da kuɗi — za a cika shi da hukumar gaggawa ]")}'
        '</b></span></div></div>'
        f'<a class="deerflow" href="https://deerflow.tech" target="_blank" rel="noopener noreferrer" '
        f'{attr("Created By Deerflow", "An ƙirƙira Deerflow")}>Created By Deerflow</a>'
        '</div></footer>')


def document(*, slug, title, description, body, scripts="", built=""):
    """Assemble one page. The CSS is concatenated, never f-string interpolated, so
    the stylesheet's braces are never treated as format placeholders."""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<meta name="description" content="{esc(description)}">\n'
        '<link rel="icon" type="image/png" href="assets/brand/apm-emblem.png">\n'
        f'<title>{esc(title)}</title>\n'
        '<style>' + SITE_CSS + SHELL_CSS + '</style>\n'
        '</head>\n'
        f'<body class="page page--{esc(slug)}">\n'
        f'{body}\n'
        f'{site_footer(built)}\n'
        '<script>' + SCRIPT_CORE + scripts + '</script>\n'
        '</body>\n</html>\n'
    )

# ---------------------------------------------------------------------------
# Page bodies
# ---------------------------------------------------------------------------

def _nav_cards():
    cards = [
        ("achievements", "01", "Achievements", "Ayyuka da aka yi",
         "The five approved records, every public achievement, and the measurement ledger.",
         "Mafada guda da aka amince, duk ayyuka na al'umma, da rajista na aunawa."),
        ("atlas", "02", "LGA atlas", "Taswirar LGA",
         "All 20 local government areas with their source-backed evidence rows.",
         "LGA 20 da jimayin bayanai mai goyon bayan sauro."),
        ("poll", "03", "Speak to us", "Yi magana da mu",
         "Tell us one need in your area. No voter ID is ever requested.",
         "Faƙa mana buƙatar daya a cikin wurin da kake. Babba wani ID na zabb'ar masu zayyawa a nemi."),
        ("agenda", "04", "APM agenda", "Bayan-APM",
         "The published campaign commitments, kept separate from achievements.",
         "Alkawarin gaggawa da aka wallafa, an rabu da ayyuka da aka kammala."),
        ("sources", "05", "Sources", "Bayane",
         "Every record traced to a source, with the grading legend and method.",
         "Kowane bayana yana da sauro, tare da ma'ana da hanyar tantawa."),
    ]
    items = []
    for slug, number, label_en, label_ha, blurb_en, blurb_ha in cards:
        items.append(
            f'<a class="nav-card" href="{esc(slug)}.html">'
            f'<span class="nav-card-no">{number}</span>'
            f'<h3>{localized(label_en, label_ha)}</h3>'
            f'<p>{localized(blurb_en, blurb_ha)}</p>'
            f'<span class="nav-card-go">{copy("Open", "Buɗe")} &rarr;</span></a>')
    return '<div class="nav-cards">' + "".join(items) + "</div>"


def body_index(ctx):
    stats = (
        '<section class="stats"><div class="shell stats-grid">'
        f'<div class="stat"><strong>{len(LGAS)}</strong><span>{copy("LGAs in the atlas", "LGA a cikin taswirar")}</span></div>'
        f'<div class="stat"><strong>{ctx["achievement_count"]}</strong><span>{copy("Public records mapped", "Bayanan da aka nunawa")}</span></div>'
        f'<div class="stat"><strong>{ctx["promise_count"]}</strong><span>{copy("APM commitments tracked", "Alkawarin APM da aka sa ido")}</span></div>'
        f'<div class="stat"><strong>{len(ctx["indicator_rows"])}</strong><span>{copy("Outcome indicators", "Alamu na sakamako")}</span></div>'
        '</div></section>')

    hero = (
        '<main id="main">'
        '<header class="hero" id="top">'
        + topbar("index") +
        '<div class="shell hero-grid"><div>'
        f'<div class="eyebrow">{copy("Official campaign record · Bauchi State", "Ƙaƙarar gaggawa · Bauchi State")}</div>'
        f'<h1><span data-en="A Vision" data-ha="Vision">A Vision</span><br>'
        f'<span data-en="for" data-ha="don">for</span> '
        f'<em><span data-en="Progress." data-ha="Ci gaba.">Progress.</span></em></h1>'
        f'<p class="hero-lede">{copy("A visual record of Bauchi’s public needs, the progress already made, and the work APM will carry forward.", "Ganiya da nuna da bukatar al’umma, ci gaban da aka yi, da aiki da APM za ci gaba da shi.")}</p>'
        '<div class="hero-actions">'
        f'<a class="btn btn-primary" href="achievements.html">{copy("Explore the progress", "Duba ci gaban")} <span>→</span></a>'
        f'<a class="btn btn-secondary" href="atlas.html">{copy("View LGA atlas", "Duba taswirar LGA")}</a>'
        f'<a class="btn btn-secondary" href="poll.html">{copy("Speak to us", "Yi magana da mu")}</a>'
        '</div>'
        f'<div class="motto" {attr("Integrity · Sacrifice · Service", "Integrity · Sacrifice · Service")}>Integrity · Sacrifice · Service</div>'
        '</div><div class="portrait-wrap">'
        '<img class="portrait" src="assets/brand/yakubu-adamu-hero.png" alt="Dr. Yakubu Adamu campaign portrait">'
        '<div class="portrait-caption"><strong>Dr. Yakubu Adamu</strong>'
        f'<span {attr("Bauchi State Governor candidate", "Mikaƙin gwamna jihada Bauchi")}>Bauchi State Governor candidate</span>'
        '</div></div></div></header>')

    sections = [
        '<section class="section" id="progress"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("The delivery story", "Labari na isar da sabis")}</div>'
        f'<h2>{copy("From public need to the next result.", "Daga buƙatar al\'umma zuwa sakamako na gaba.")}</h2></div>'
        f'<p>{copy("The new dashboard keeps needs, public records, campaign commitments and future measures in one traceable story.", "Sabuwar dashboard tana buƙatar al\'umma, bayanan ci gabansu, alkawarin gaggawa da matakan nan zuwa cikin wataƙa mai sauri.")}</p>'
        '</div><div class="progress-path">'
        f'<div class="path-step"><span class="step-no">{copy("01 / NEED", "01 / BUƙATAR")}</span><h3>{copy("What matters?", "Me ya fi muhimmanci?")}</h3><p>{copy("Start with the everyday need.", "Fara da buƙatar rayuwar yau.")}</p></div>'
        f'<div class="path-step"><span class="step-no">{copy("02 / RECORD", "02 / BAYANI")}</span><h3>{copy("What exists?", "Me yana nan?")}</h3><p>{copy("Show documented progress.", "Nuna ci gaban da aka tabbatar.")}</p></div>'
        f'<div class="path-step"><span class="step-no">{copy("03 / PROMISE", "03 / ALKAWARI")}</span><h3>{copy("What comes next?", "Me zai zo bayan nan?")}</h3><p>{copy("Make the commitment clear.", "Sanya alkawarin a bayyana.")}</p></div>'
        f'<div class="path-step"><span class="step-no">{copy("04 / RESULT", "04 / SAKAMAKO")}</span><h3>{copy("How will we know?", "Yaya za mu sani?")}</h3><p>{copy("Measure what changes.", "Auna abin da za ta canza.")}</p></div>'
        '</div><div class="filter-row">'
        f'<button class="filter active" type="button" data-filter="all" {attr("All records", "Dufin bayanai")}>All records</button>'
        f'<button class="filter" type="button" data-filter="health" {attr("Health", "Lafiya")}>Health</button>'
        f'<button class="filter" type="button" data-filter="education" {attr("Education", "Ilimi")}>Education</button>'
        f'<button class="filter" type="button" data-filter="wash" {attr("Water & climate", "Ruwa da sauroyi")}>Water &amp; climate</button>'
        f'<button class="filter" type="button" data-filter="governance" {attr("Governance", "Ganyayi")}>Governance</button>'
        f'<button class="filter" type="button" data-filter="infrastructure" {attr("Infrastructure", "Infastructure")}>Infrastructure</button>'
        '</div><div class="arrow-list">' + "".join(ctx["arrow_cards"]) + '</div></div></section>',

        '<section class="section" id="continuity"><div class="shell governance-grid">'
        '<div class="governor-card"><img src="assets/brand/bala-mohammed.png" alt="Governor Bala Mohammed">'
        '<div class="governor-caption">'
        f'<strong>{copy("Progress with continuity", "Ci gaba mai ci gaba")}</strong>'
        f'<span {attr("Current Bauchi State administration and the next APM chapter", "Ggwamnatin Bauchi ta yanzu da sabon babban darasi na APM")}>Current Bauchi State administration and the next APM chapter</span>'
        '</div></div><div class="governance-copy">'
        f'<div class="eyebrow">{copy("Build on what is working", "Ci gaba kan abin da ke aiki")}</div>'
        f'<h3>{copy("The next chapter should finish the journey.", "Babban sabo ya kamata ya kare adireshin da aka fara.")}</h3>'
        f'<p>{copy("This landing page presents the current administration’s public record first, then shows where APM’s published commitments can complete, expand and measure the next priorities.", "Wannan shafi yana nuna bayanan gwamnati na yanzu da farko, sannan ya nuna inda alkawarin APM za ka ci gaba da shi, ya kuma yi aiki, ya sanya ido kan mabambanci na gaba.")}</p>'
        '<div class="continuity-list">'
        f'<div class="continuity-item"><b>01</b><span>{copy("Credit progress to the people and institutions delivering it.", "Mayar da ci gaban ga mutane da sashen da ke aiki.")}</span></div>'
        f'<div class="continuity-item"><b>02</b><span>{copy("Show joint delivery honestly, including partners and public institutions.", "Nuna aiki tare da gaskiya, tare da abokan hulɗe da sashen gwamnati.")}</span></div>'
        f'<div class="continuity-item"><b>03</b><span>{copy("Turn every promise into a result that can be tracked.", "Sanya kowane alkawari ya zama sakamako da za a iya sa shi ido a kai.")}</span></div>'
        '</div></div></div></section>',

        '<section class="section" id="pages"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("Go deeper", "Tafi ciki")}</div>'
        f'<h2>{copy("Five pages, one record.", "Shafi biyu da daya, rubutanci daya.")}</h2></div>'
        f'<p>{copy("Every page keeps its own sources. Nothing here is a private poll.", "Kowane shafi yana da sauro shi. Babu komi a ciki da yake private poll.")}</p>'
        '</div>' + _nav_cards() + '</div></section>',
    ]
    return hero + stats + "".join(sections) + "</main>"


def body_achievements(ctx):
    header = subpage_open("achievements")
    sections = [
        ctx["featured_section"],
        '<section class="section" id="records"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("Every public record", "Kowane bayanan al\'umma")}</div>'
        f'<h2>{copy("All mapped achievements.", "Duk ayyuka da aka nunawa.")}</h2></div>'
        f'<p>{copy("Each record keeps its own verification status, so an unverified claim is never shown as a completed project.", "Kowane bayana yana da yanayin tabbacinsa, don haka ba a nuna wanda ba a tabbatar a shi azaman aikin da aka kammala.")}</p>'
        '</div><div class="arrow-list">' + "".join(ctx["arrow_cards"]) + '</div></div></section>',
        ctx["indicator_section"],
    ]
    return (header + page_hero("Source-backed achievements", "Ayyuka da aka tabbatar",
                      "What has actually been delivered.", "Abin da aka isar da shi gaske.",
                      "Five approved records, every mapped public achievement, and the measurement ledger that separates reported outputs from outcomes still being measured.",
                      "Mafada guda da aka amince, duk ayyukan da aka nunawa, da rajistan aunawa da yake bambanta abubuwan da aka isar da su da sakamako da kuma ake aunawa.",
                      "Achievements", "Ayyuka")
            + '<main id="main">' + "".join(sections) + "</main>")


def body_atlas(ctx):
    header = subpage_open("atlas")
    section = (
        '<section class="section lga-section" id="atlas"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("20 local government areas", "LGA 20")}</div>'
        f'<h2>{copy("A 20-LGA evidence queue for Bauchi.", "Bita na bayanai ga LGA 20 a Bauchi.")}</h2></div>'
        f'<p>{copy("All 20 LGAs have one curated source-backed evidence row. This is a starting evidence model, not comprehensive sector coverage for every community.", "Yanzu dukan LGA 20 suna da jimayi na bayanai mai goyon bayan sauro. Wannan ba cikakken bayanan kowane bangare ba.")}</p>'
        '</div><div class="lga-grid">' + lga_atlas(ctx["lga_rows"]) + '</div>'
        '<div class="lga-detail" id="lga-detail"><div>'
        f'<div class="detail-label">{copy("Selected area · statewide evidence start", "Wanda za zaɓi · ci gaban jihada")}</div>'
        '<h3 id="selected-lga">Bauchi</h3>'
        '<p id="selected-copy" aria-live="polite" data-en="Choose an LGA to preview the evidence queue. The first public records are being tracked as statewide progress while LGA-specific project evidence is verified." '
        'data-ha="Zaɓi LGA don duba bita don bayanai. Ƙa bayanan farko ana sune a matsayin ci gaban jihada yayin da ake tabbatar da bayanan LGA.">Choose an LGA to preview the evidence queue. The first public records are being tracked as statewide progress while LGA-specific project evidence is verified.</p>'
        f'</div><span class="detail-label" {attr("20 LGAs · 1 evidence model", "LGA 20 · 1 tsarin tabbaci")}>20 LGAs · 1 evidence model</span>'
        '</div></div></section>')
    return (header + page_hero("LGA atlas", "Taswirar LGA",
                      "Twenty local government areas.", "LGA ashirin.",
                      "Every Bauchi LGA with its source-backed evidence row. Select an area to read what is recorded for it.",
                      "Kowane LGA na Bauchi tare da jimayin bayanai mai goyon bayan sauro. Zaɓi wani area don karanta abin da aka record shi.",
                      "LGA atlas", "Taswirar LGA")
            + '<main id="main">' + section + "</main>")


def body_poll(ctx):
    header = subpage_open("poll")
    note = (
        '<section class="section" id="how"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("Before you send", "Kafin ka aika")}</div>'
        f'<h2>{copy("What happens to this form.", "Abin da zai faru da wannan fom.")}</h2></div>'
        f'<p>{copy("This form is not connected to a public endpoint yet, so nothing is sent from this build.", "Wannan fom ba a haɗa da wata adireshin da za a iya amfani ba tukuna, don haka ba a tura komai daga wannan gina.")}</p>'
        '</div><div class="note-box">' + copy(
            "No voter ID is requested. No electoral identity number is collected. Any confirmation "
            "reference is a generated request tracking reference, not a voter ID.",
            "Ba a nemi ID na zabb'ar masu zayyawa. Ba a tara lambar wayo da ke gano mutum. ID na tabbaci yana nufin bin buƙatar kawai, ba ID na zabb'ar masu zayyawa ba.") + '</div></div></section>')
    return (header + page_hero("Speak to us", "Yi magana da mu",
                      "Tell us one need in your area.", "Faƙa mana buƙatar daya a cikin wurin da kake.",
                      "Choose your local government area and the specific thing that matters to you. Contact details are optional and are never shown publicly.",
                      "Zaɓi LGA da kuma abin da ke muhimmanci maka. Bayanan hulɗe na zaɗi ne kuma ba a nuna su a fili ba.",
                      "Speak to us", "Yi magana da mu")
            + '<main id="main">' + ctx["request_section"] + note + "</main>")


def body_agenda(ctx):
    header = subpage_open("agenda")
    cards = []
    for idx, promise in enumerate(ctx["promise_rows"], 1):
        sector = promise.get("sector", "")
        label = SECTOR_LABELS.get(sector, sector.title())
        ha = SECTOR_HA.get(sector, label)
        clause = ' <span class="agenda-kind">' + copy("published clause", "bendi da aka wallafa") + "</span>" \
            if promise.get("promise_type") == "Published commitment clause" else ""
        cards.append(
            f'<article class="agenda-card"><div><span class="agenda-no">0{idx}</span>'
            f'<h3>{copy(label, ha)}</h3>'
            f'<p>{localized(promise.get("promise_text", ""), promise.get("promise_text_ha", ""))}</p>'
            f'<p class="agenda-type">{esc(promise.get("promise_type", ""))}{clause}</p>'
            f'<p class="agenda-measure">{copy("Measured by:", "Ana aunawa da:")} '
            f'{localized(promise.get("success_indicator", ""), promise.get("success_indicator_ha", ""))}</p>'
            '</div>'
            f'{source_link(promise.get("source_id", ""), ctx["sources"], "Campaign source", "Sauro gaggawa")}'
            '</article>')
    section = (
        '<section class="section" id="agenda"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("Published campaign commitments", "Alkawarin gaggawa da aka wallafa")}</div>'
        f'<h2>{copy("A focused agenda for the next Bauchi.", "ƙa agenda mai mayar hankali don Bauchi na gaba.")}</h2></div>'
        f'<p>{copy("These are campaign commitments, not completed achievements. They are shown separately so the evidence story stays clear.", "Waannan alkawarin gaggawa ne, ba ayyuka da aka kammala ba. An nuna su a wuri dabewa don bayan ci gabansu ya kasance mai sauƙi.")}</p>'
        '</div><div class="agenda-grid">' + "".join(cards) + '</div></div></section>')
    return (header + page_hero("APM agenda", "Bayan-APM",
                      "Published commitments.", "Alkawarin da aka wallafa.",
                      "These are campaign commitments, not completed projects. One of them is a published clause rather than a standalone pillar, and it is labelled as such.",
                      "Waannan alkawarin gaggawa ne, ba ayyuka da aka kammala ba. Dayan daga cikinsu shi ne bendi na alkawarin da aka wallafa, ba tsari mai zaman kansa ba, an nuna shi haka.",
                      "APM agenda", "Bayan-APM")
            + '<main id="main">' + section + "</main>")


def body_sources(ctx):
    header = subpage_open("sources")
    archived = len(ctx["manifest_rows"])
    pending = len(ctx["pending_review_rows"])
    section = (
        '<section class="sources-section" id="sources"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("Traceable by design", "An tsara shi don sa ido")}</div>'
        f'<h2>{copy("Every record has a source.", "Kowane bayana yana da sauro.")}</h2></div>'
        f'<p>{copy(f"{archived} source pages archived. {pending} candidate records are queued for source review before they can become achievements.", f"An ruƙe shafi {archived} na bayanai. An sanya bayanan {pending} a cikin bita kafin su iya zama ayyuka.")}</p>'
        '</div>'
        f'<p class="note-box">{copy("Source titles are citations and appear in the language they were published in. Our own notes, caveats and indicator values are translated.", "Sunan suna citations ne suna bayyana a cikin harshen da aka wallafa da su. Bayanan mu, gargaɗi da mu da aka nuna alamu suna an fassara.")}</p>'
        '<ul class="source-list">' + source_footer(ctx["sources"]) + '</ul>'
        '<div class="source-legend">'
        f'<span><b>A</b> {copy("Primary or institutional record", "Bayanan gwamna ko instituciya")}</span>'
        f'<span><b>B</b> {copy("Programme or corroborating evidence", "Shirin ko tabbacin da ke tabbatar")}</span>'
        f'<span><b>D</b> {copy("Campaign material", "Kayan gaggawa")}</span>'
        '</div></div></section>')
    method = (
        '<section class="section" id="method"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("Method", "Hanya")}</div>'
        f'<h2>{copy("How this page is built.", "Yaya wannan shafi aka gina.")}</h2></div>'
        f'<p>{copy("Every record on this site comes from a registered, archived public source. Missing data stays missing rather than being estimated.", "Kowane bayana a wannan shafi yana fito daga sauro na al'umma da aka yi riga da adana shi. Babin komai yake babi maimakon a yi kiyaye shi.")}</p>'
        '</div><div class="progress-path">'
        f'<div class="path-step"><span class="step-no">01</span><h3>{copy("Discover", "Nuna")}</h3><p>{copy("Public sources are found and archived with a content hash.", "An same bayanan al'umma an kuma adana tare da hash.")}</p></div>'
        f'<div class="path-step"><span class="step-no">02</span><h3>{copy("Review", "Bita")}</h3><p>{copy("Each candidate is graded before it can become a record.", "Ana bambanta kowane gaskiya kafin ta iya zama bayana.")}</p></div>'
        f'<div class="path-step"><span class="step-no">03</span><h3>{copy("Curate", "Zaɓa")}</h3><p>{copy("Records keep their own verification status and caveat.", "Bayanan sun riƙe yanayin tabbaccinsu da gargaɗi.")}</p></div>'
        f'<div class="path-step"><span class="step-no">04</span><h3>{copy("Publish", "Wallafa")}</h3><p>{copy("A weekly build regenerates the pages from approved data.", "Gina mai yi kowane mako yana sake yin shafuka daga bayanan da aka amince.")}</p></div>'
        '</div></div></section>')
    return (header + page_hero("Sources &amp; method", "Bayane da hanya",
                      "Every record has a source.", "Kowane bayana yana da sauro.",
                      f"{len(ctx['sources'])} registered public sources, archived with content hashes, plus the grading legend and the build method.",
                      f"{len(ctx['sources'])} bayanan al'umma da aka saita, an adana su tare da hash, tare da ma'ana da kuma hanya gina.",
                      "Sources", "Bayane")
            + '<main id="main">' + section + method + "</main>")


PAGE_BUILDERS = {
    "index": (body_index, "APM Bauchi Progress & Delivery",
              "APM Bauchi Progress and Delivery: public needs, current achievements, campaign commitments and next results."),
    "achievements": (body_achievements, "Achievements · APM Bauchi",
                     "Five approved achievements, every mapped public record, and the APM Bauchi measurement ledger."),
    "atlas": (body_atlas, "LGA atlas · APM Bauchi",
              "All 20 Bauchi local government areas with source-backed evidence rows."),
    "poll": (body_poll, "Speak to us · APM Bauchi",
             "Tell APM Bauchi one need in your area. No voter ID is ever requested."),
    "agenda": (body_agenda, "APM agenda · APM Bauchi",
               "Published APM Bauchi campaign commitments, kept separate from completed achievements."),
    "sources": (body_sources, "Sources & method · APM Bauchi",
                f"{len(build_sources())} registered public sources for the APM Bauchi record, with the grading legend and build method."),
}


def load_context():
    sources = build_sources()
    needs = build_needs()
    promises = build_promises()
    achievement_rows, achievement_groups = build_achievements()
    lga_rows = read_csv("lga_delivery.csv")
    indicator_rows = read_csv("indicators.csv")
    manifest_rows = read_csv("source_manifest.csv")
    review_rows = read_csv("review_queue.csv")
    pending_review_rows = [row for row in review_rows if row.get("review_status") == "needs_review"]
    ward_data = load_lga_wards()
    ward_rows = ward_data[0] if ward_data else []
    promise_rows = read_csv("promises.csv")

    arrow_cards = []
    for sector in ["health", "education", "wash", "infrastructure", "governance",
                   "livelihoods", "security", "agriculture"]:
        rows = achievement_groups.get(sector, [])
        if sector in ["livelihoods", "security", "agriculture"] and not rows:
            continue
        arrow_cards.append(arrow_card(sector, needs.get(sector), promises.get(sector), rows, sources))

    asset_rows = read_csv("asset_register.csv")
    featured_rows, featured_state = load_featured_achievements(achievement_rows, asset_rows, sources)
    if featured_rows:
        prepare_featured_assets(featured_rows)
        featured_section = featured_achievement_carousel(featured_rows, achievement_rows, asset_rows, sources)
    elif featured_state:
        featured_section = featured_pending_section()
    else:
        featured_section = ""

    return {
        "sources": sources,
        "lga_rows": lga_rows,
        "indicator_rows": indicator_rows,
        "manifest_rows": manifest_rows,
        "pending_review_rows": pending_review_rows,
        "promise_rows": promise_rows,
        "arrow_cards": arrow_cards,
        "featured_section": featured_section,
        "indicator_section": (
            '<section class="indicator-section" id="indicators"><div class="shell">'
            '<div class="section-head"><div>'
            f'<div class="eyebrow">{copy("Measurement ledger", "Rajista na aunawa")}</div>'
            f'<h2>{copy("Delivery becomes useful when results are visible.", "Isar da sabis tana da sauƙi idan an nuna sakamako.")}</h2></div>'
            f'<p>{copy("These indicators separate reported delivery outputs from the outcomes still being measured. Blank baselines remain blank by design.", "Wannan alamu na bambanta abubuwan da aka isar da sakamako da zuwa da ake aunawa. Babu komai a cikin tushen sai an gani.")}</p>'
            '</div><div class="indicator-grid">' + indicator_cards(indicator_rows, sources) +
            '</div></div></section>'),
        "request_section": request_form_section(ward_rows),
        "achievement_count": len(achievement_rows),
        "promise_count": len(promise_rows),
        "built": datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y · %H:%M UTC"),
    }


PAGE_SCRIPTS = {
    "index": lambda: SCRIPT_INDEX,
    "achievements": lambda: FEATURED_SCRIPT,
    "poll": lambda: REQUEST_SCRIPT,
}


def render():
    validate_data()
    prepare_assets()
    ctx = load_context()

    written = []
    for slug, (builder, title, description) in PAGE_BUILDERS.items():
        scripts = PAGE_SCRIPTS.get(slug, lambda: "")()
        html_doc = document(
            slug=slug,
            title=title,
            description=description,
            body=builder(ctx),
            scripts=scripts,
            built=ctx["built"],
        )
        target = DOCS / f"{slug}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html_doc, encoding="utf-8")
        written.append(target)

    # index.html is the site root; the slug loop already wrote it.
    print(f"wrote {len(written)} pages to {DOCS} "
          f"({ctx['achievement_count']} achievements, {ctx['promise_count']} promises, "
          f"{len(ctx['sources'])} sources)")
    for target in written:
        print(f"  {target.name} {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    render()
