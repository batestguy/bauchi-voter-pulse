import csv
import datetime
import functools
import hashlib
import html
import importlib.util
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "delivery"
ASSETS = ROOT / "assets" / "brand"
DERIVED = ROOT / "data" / "derived"
LGA_PATHS_FILE = DERIVED / "lga_paths.json"
DOCS = ROOT / "docs"
OUT = DOCS / "index.html"

LGAS = [
    "Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
    "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi", "Misau",
    "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki"
]

LGA_WARDS_FILE = "lga_wards.csv"
# The request endpoint is deployed and bound to the "APM requests" Sheet, with
# setupSheets run so the Requests and Audit tabs exist. It collects a name, an optional
# email and a street address -- real personal data, unlike the poll -- so unlike the poll
# it has no automatic purge. That is a deliberate owner decision, not an oversight, and it
# is stated in docs/GOOGLE_SHEETS_SETUP.md rather than left to look forgotten.
#
# As with the poll, the `/exec` URL is public by construction: it is the browser-facing
# address of the deployment and anyone reading the page can see it. What protects the data
# is the contract in src/requests/validation.py and the Audit tab, not secrecy.
REQUEST_ENDPOINT = ("https://script.google.com/macros/s/"
                    "AKfycbwsh4IuhBt7EtbgmN_crXzXdUOLLjLzIkCtWLiizJJ56mMk7zJU59DA0Sn6cT3ikT4F/exec")
# The poll endpoint is deployed and bound to the "APM poll responses" Sheet, with
# setupSheets and installRetention both run: the Responses, Comments and Audit tabs exist
# and the daily purge trigger is installed. It was connected only after a real vote
# round-tripped and returned a sequential response_id, because an endpoint that is
# deployed but unwired fails silently and a poll that silently discards votes is worse
# than a poll that is visibly closed.
#
# The `/exec` URL is public by construction -- it is the browser-facing address of the
# deployment and anyone reading the page can see it. What protects the data is the
# contract in src/poll/validation.py, not the secrecy of this string.
POLL_ENDPOINT = ("https://script.google.com/macros/s/"
                 "AKfycbyIWqhapObAv3ysdp1u8eJ9tMjDQLsP136D6PXrwMwNM5ytnS0S2m8i5qJgjC2SF6oj7A/exec")
POLL_SNAPSHOT_FILE = "poll_snapshot.json"
# One response must never render as "100%". The owner can set this to 0 to disable.
POLL_PERCENTAGE_FLOOR = 10
# Mandatory, not cosmetic. The poll records an LGA and an optional registration area, so
# a published cell below this count is a handful of identifiable people. A value of 0 or
# 1 is refused by src/poll/validation.py rather than honoured.
POLL_SMALL_COUNT_THRESHOLD = 5
POLL_AGE_BANDS = (
    ("age_18_25", "18–25", "Shekaru 18–25"),
    ("age_26_35", "26–35", "Shekaru 26–35"),
    ("age_36_45", "36–45", "Shekaru 36–45"),
    ("age_46_55", "46–55", "Shekaru 46–55"),
    ("age_56_65", "56–65", "Shekaru 56–65"),
    ("age_66_plus", "66 and over", "Shekaru 66 da sama"),
)
POLL_GENDER_OPTIONS = (
    ("woman", "Woman", "Mace"),
    ("man", "Man", "Miji"),
)
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
    "yakubu-adamu-single.png", "bala-mohammed.png", "abdulkadir-ahmad-hammayo.png"
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

# The About page states how many commitments there are, and that number comes from the
# promises file rather than from a sentence somebody wrote. It shipped once as "Five
# commitments" over an eight-row file, which is a wrong number on the candidate's own
# agenda -- the one page a voter is most likely to check.
ABOUT_COMMITMENT_COUNT = {
    1: ("One commitment.", "Alkawari daya."),
    2: ("Two commitments.", "Alkawari biyu."),
    3: ("Three commitments.", "Alkawari uku."),
    4: ("Four commitments.", "Alkawari hudu."),
    5: ("Five commitments.", "Alkawarin daya da biyar."),
    6: ("Six commitments.", "Alkawarin shida."),
    7: ("Seven commitments.", "Alkawarin bakwai."),
    8: ("Eight commitments.", "Alkawarin takwas."),
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


def aria(en, ha):
    """A localized accessible name that does NOT become a text-content swap target.

    `setLanguage` rewrites `textContent` for every `[data-en][data-ha]` element, so putting
    `attr()` on a container that has element children -- or is a whole subtree such as an
    `<svg>` -- silently destroys them on the first language switch. Use this on anything
    that carries children.
    """
    return (f'data-aria-label-en="{esc(en)}" data-aria-label-ha="{esc(ha or en)}" '
            f'aria-label="{esc(en)}"')


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
    return f'''<section class="featured-section" id="featured" data-featured-state="ready" aria-labelledby="featured-title"><div class="shell"><div class="section-head"><div><div class="eyebrow">{copy("Featured achievements", "Ayyuka da aka zaɓa")}</div><h2 id="featured-title">{copy("Five approved, source-backed records, with their scope kept clear.", "Bayanai guda da aka amince, tare da nuna iyakin su.") }</h2></div><p>{copy("Each slide keeps the approved caption, source and LGA scope visible. Some source images are context images rather than verified project close-ups; the image note identifies those cases. Statewide evidence is not relabelled as a single-LGA record.", "Kowane mafada yana nuna caption da aka amince da sauro da iyakin LGA. Wasu hotunan ba kwakaiyo aiki ba ne; note na hotun yana nuna wanda ake. Ba a canza bayanan jihada zuwa LGA daya.") }</p></div><div class="featured-carousel" data-featured-carousel tabindex="0" role="region" aria-roledescription="carousel" aria-labelledby="featured-title"><div class="featured-toolbar"><div class="featured-scope-filters" role="group" aria-label="Featured achievement scope filters"><button type="button" class="featured-scope-filter active" data-featured-scope-filter="all" aria-pressed="true" {attr("All scopes", "Dufin firin")}>All scopes</button><button type="button" class="featured-scope-filter" data-featured-scope-filter="lga" aria-pressed="false" {attr("LGA", "LGA")}>LGA</button><button type="button" class="featured-scope-filter" data-featured-scope-filter="multi_lga" aria-pressed="false" {attr("Multiple LGAs", "LGA daya da yawa")}>Multiple LGAs</button><button type="button" class="featured-scope-filter" data-featured-scope-filter="statewide" aria-pressed="false" {attr("Statewide", "Jihada")}>Statewide</button></div><div class="featured-controls"><button type="button" class="featured-control" data-featured-prev aria-label="Previous featured achievement">← <span {attr("Previous", "Baya")}>Previous</span></button><span class="featured-status" data-featured-status aria-live="polite" aria-atomic="true">1 / 5</span><button type="button" class="featured-control" data-featured-next aria-label="Next featured achievement"><span {attr("Next", "Na gaba")}>Next</span> →</button></div></div><ol id="featured-slides" class="featured-slides">{slide_html}</ol></div></div></section>'''


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
      const matches=!option.hasAttribute('data-request-ra-lga')||!selectedLga||option.dataset.requestRaLga===selectedLga;
      // `disabled` is what actually removes an option from a native select. Setting only
      // `hidden` looks correct and does nothing: Chromium ignores the hidden attribute on
      // <option>, so every one of the 212 areas stayed selectable whatever LGA was chosen.
      // A visitor picking Bauchi and then the first area in the list got RA-001, which is
      // Alkaleri's, and the endpoint refused it as invalid_ward -- surfacing only as
      // "we could not send your request", with no indication of why.
      option.hidden=!matches;
      option.disabled=!matches;
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
    requestConfigStatus.textContent=currentLanguage==='ha'?'Ba a saita wata adireshi da ake amfani da ita a wannan gina ba. Ba a tura buƙatar.':'No usable request endpoint is configured in this build. No request is being sent.';
    requestConfigStatus.dataset.en='No usable request endpoint is configured in this build. No request is being sent.';
    requestConfigStatus.dataset.ha='Ba a saita wata adireshi da ake amfani da ita a wannan gina ba. Ba a tura buƙatar.';
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
      const response=await fetch(requestEndpointUrl.href,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8','Accept':'application/json'},body:JSON.stringify(payload),credentials:'omit',referrerPolicy:'no-referrer'});
       if(!response.ok)throw new Error('request_failed');
       const responseData=await response.json().catch(()=>null);
       const responseKeys=responseData&&typeof responseData==='object'&&!Array.isArray(responseData)?Object.keys(responseData):[];
       const trackingId=responseKeys.length===1&&responseKeys[0]==='request_id'&&typeof responseData.request_id==='string'&&/^APM-[0-9]{4}-[0-9]{4,12}$/.test(responseData.request_id)?responseData.request_id:'';
       if(!trackingId)throw new Error('invalid_request_confirmation');
       requestStatus.hidden=true;
       requestConfirmation.dataset.trackingId=trackingId;
       requestConfirmation.textContent=(currentLanguage==='ha'?'An karɓi buƙatar. ID na bin: ':'Request received. Tracking reference: ')+trackingId+'.';
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


POLL_SCRIPT = r'''
const pollDataEl=document.querySelector('[data-poll-snapshot]');
const pollSnapshot=(()=>{try{return pollDataEl?JSON.parse(pollDataEl.textContent):null;}catch(error){return null;}})();
const POLL_SECTOR_LABELS=__POLL_SECTOR_LABEL_JSON__;
const POLL_LGA_ORDER=__POLL_LGA_ORDER_JSON__;
const POLL_AGE_LABELS=__POLL_AGE_LABEL_JSON__;
const POLL_GENDER_LABELS=__POLL_GENDER_LABEL_JSON__;
const POLL_WARD_LABELS=__POLL_WARD_LABEL_JSON__;
const pollT=(lang,en,ha)=>lang==='ha'?(ha||en):en;

// The scope is three controls, and one of them is deliberately impossible to combine with
// another. Age band and gender are ONE mutually-exclusive lens rather than two filters,
// and selecting a registration area switches the lens off entirely. That is not a
// simplification. `src/poll/aggregate.py` refuses to build any cross carrying both a
// registration area and a demographic, so two independent filters plus a ward dropdown
// would be three clicks away from publishing ward x gender x sector. One lens, disabled
// at ward level, means no sequence of clicks can reach the refused cross -- the UI cannot
// offer a combination the snapshot does not contain.
const pollState={lga:'',ward:'',lens:''};
const pollLensKind=key=>key.charAt(0)==='g'?'gender':'age';
const pollLensValue=key=>key.slice(2);
const pollLensLabel=key=>{
  if(!key)return pollT(currentLanguage,'Everyone','Kowa');
  const table=pollLensKind(key)==='gender'?POLL_GENDER_LABELS:POLL_AGE_LABELS;
  const meta=table[pollLensValue(key)];
  return meta?pollT(currentLanguage,meta[0],meta[1]):pollLensValue(key);
};

// Resolve the current scope to the one map that holds it, plus the denominator for the
// share column. Returns `total:null` when the group itself is below the suppression
// floor, which is different from a scope that has publishable cells.
// Resolve the current scope to the one map that holds it.
//
// `total` is the size of the selected group, and it is deliberately allowed to be in three
// states, because they mean different things to a reader and collapsing them would either
// hide a real group or invent one:
//
//   a number   -- the group's size is published, and the share is exact.
//   a string   -- a lower bound: some cells were withheld, so the visible counts sum to
//                 less than the true total. A percentage would understate the group, so
//                 none is printed.
//   null      -- the group itself is below the suppression floor. There is nothing to show.
const pollResolveScope=()=>{
  const snap=pollSnapshot;
  const totalOf=(tree,key)=>{
    const value=((tree||{})[key]);
    return value===undefined?null:value;
  };
  if(pollState.ward){
    return {
      rows:(snap.by_ward_sector||{})[pollState.ward]||null,
      total:totalOf(snap.by_ward,pollState.ward),
      mapName:'by_ward_sector'
    };
  }
  if(pollState.lens){
    const kind=pollLensKind(pollState.lens)==='gender'?'gender':'age';
    const value=pollLensValue(pollState.lens);
    if(pollState.lga){
      // An LGA x demographic scope has a published marginal to divide by.
      const perLga=kind==='gender'
        ?(snap.by_lga_gender_sector||{})
        :(snap.by_lga_age_band_sector||{});
      const margin=kind==='gender'?(snap.by_lga_gender||{}):(snap.by_lga_age_band||{});
      return {
        rows:(((perLga[pollState.lga]||{})[value])||null),
        total:totalOf((margin[pollState.lga]||{}),value),
        mapName:'by_lga_'+kind+'_sector'
      };
    }
    // Statewide x demographic has NO published marginal: the group is the whole state, so
    // the only denominator available is the sum of its own cells. That sum is exact only
    // while nothing has been withheld.
    const wide=kind==='gender'?(snap.by_gender_sector||{}):(snap.by_age_band_sector||{});
    const rows=wide[value]||null;
    const visible=rows?Object.values(rows):[];
    const allPublishable=visible.length>0&&visible.every(cell=>typeof cell==='number');
    return {
      rows:rows,
      total:allPublishable?visible.reduce((sum,cell)=>sum+cell,0):null,
      lowerBound:allPublishable?null:(rows?visible.reduce((sum,cell)=>sum+(cell||0),0):null),
      mapName:'by_'+kind+'_sector'
    };
  }
  if(pollState.lga){
    return {
      rows:(snap.by_lga_sector||{})[pollState.lga]||null,
      total:totalOf(snap.by_lga,pollState.lga),
      mapName:'by_lga_sector'
    };
  }
  return {rows:snap.by_sector||null,total:snap.total_responses,mapName:'by_sector'};
};

// A share is printed only when it is exact. If any cell in the scope was suppressed, the
// true denominator is larger than the sum of the cells we are allowed to show, so a
// percentage computed from the visible cells would understate the group and quietly
// invent precision. In that case the count is shown and the share is a dash, with the
// reason stated on the page.
const pollShareIsExact=scope=>{
  if(!scope.rows)return false;
  if(scope.lowerBound)return false;
  if(typeof scope.total!=='number')return false;
  const values=Object.values(scope.rows);
  if(!values.length)return false;
  return values.every(value=>typeof value==='number');
};

const pollScopeLabel=()=>{
  const parts=[];
  parts.push(pollState.lga?pollState.lga:pollT(currentLanguage,'All of Bauchi State','Duk Bauchi'));
  if(pollState.ward){
    const name=POLL_WARD_LABELS[pollState.ward];
    parts.push(name?name+' ('+pollState.ward+')':pollState.ward);
  }
  if(pollState.lens)parts.push(pollLensLabel(pollState.lens));
  return parts.join(' · ');
};

const pollRenderScopeSummary=()=>{
  const el=document.querySelector('[data-poll-scope-summary]');
  if(!el)return;
  const scope=pollResolveScope();
  el.textContent=pollScopeLabel();
  const totalEl=document.querySelector('[data-poll-scope-total]');
  if(totalEl){
    // Three states, three messages. "Too few to show" and "at least N" are very
    // different facts: one says the group is protected, the other says the group is real
    // and larger than the numbers beneath it. Collapsing them would either hide a
    // substantial group or imply one that does not exist.
    if(typeof scope.total==='number'){
      totalEl.textContent=scope.total+' '+pollT(currentLanguage,'answers','amsa');
    }else if(scope.lowerBound){
      totalEl.textContent=pollT(currentLanguage,'at least ','aƙalla ')+scope.lowerBound
        +' '+pollT(currentLanguage,'answers','amsa');
    }else{
      totalEl.textContent=pollT(currentLanguage,
        'answers in this group: too few to show',
        'amsa a wannan ƙungiya: amsa kaɗan');
    }
  }
};

const pollRenderSectorChart=()=>{
  const target=document.querySelector('[data-poll-sector-chart]');
  if(!target||!pollSnapshot)return;
  const scope=pollResolveScope();
  const exact=pollShareIsExact(scope);
  target.innerHTML='';
  const source=scope.rows;
  const rows=Object.keys(source||{}).map(key=>({key:key,count:source[key]}));
  rows.sort((a,b)=>{
    const av=a.count===null?-1:a.count;
    const bv=b.count===null?-1:b.count;
    return bv-av||a.key.localeCompare(b.key);
  });
  if(!rows.length){
    const li=document.createElement('li');
    li.className='poll-bar-empty';
    li.textContent=pollT(currentLanguage,
      'No publishable figures for this group yet. The people who answered here were too few to report without identifying them.',
      'Babu adadin da za a wallafa don wannan ƙungiya tukuna. Mutanen da amsa a nan sun kaɗan sosai don a wallafa su ba tare da gane su ba.');
    target.appendChild(li);
    return;
  }
  const max=Math.max(...rows.map(r=>r.count===null?0:r.count),1);
  const cap=100-pollSnapshot.percentage_floor;
  rows.forEach(row=>{
    const li=document.createElement('li');
    li.className='poll-bar';
    const label=document.createElement('span');
    label.className='poll-bar-label';
    const meta=POLL_SECTOR_LABELS[row.key]||[row.key,row.key];
    label.textContent=pollT(currentLanguage,meta[0],meta[1]);
    const track=document.createElement('span');
    track.className='poll-bar-track';
    const fill=document.createElement('span');
    const value=document.createElement('span');
    value.className='poll-bar-value';
    if(row.count===null){
      fill.className='poll-bar-fill is-suppressed';
      value.classList.add('is-suppressed');
      value.textContent=pollT(currentLanguage,'too few to show','amsa kaɗan');
    }else{
      fill.className='poll-bar-fill';
      fill.style.width=Math.max((row.count/max)*100,1.5).toFixed(1)+'%';
      let shareText='';
      if(exact){
        shareText=' '+Math.round(Math.min((row.count/scope.total)*100,cap))+'%';
      }
      value.textContent=row.count+shareText;
    }
    track.appendChild(fill);
    li.appendChild(label);
    li.appendChild(track);
    li.appendChild(value);
    target.appendChild(li);
  });
};


const renderPollLgaChart=()=>{
  const target=document.querySelector('[data-poll-lga-chart]');
  if(!target||!pollSnapshot)return;
  const counts=pollSnapshot.by_lga||{};
  target.innerHTML='';
  const max=Math.max(...POLL_LGA_ORDER.map(l=>(counts[l]===null||counts[l]===undefined)?0:counts[l]),1);
  POLL_LGA_ORDER.forEach(lga=>{
    const raw=counts[lga];
    const li=document.createElement('li');
    li.className='poll-bar poll-bar-lga';
    const label=document.createElement('span');
    label.className='poll-bar-label';
    label.textContent=lga;
    const track=document.createElement('span');
    track.className='poll-bar-track';
    const fill=document.createElement('span');
    fill.className='poll-bar-fill is-alt'+(raw===null||raw===undefined?' is-suppressed':'');
    if(raw!==null&&raw!==undefined)fill.style.width=Math.max((raw/max)*100,1.5).toFixed(1)+'%';
    track.appendChild(fill);
    const value=document.createElement('span');
    value.className='poll-bar-value'+((raw===null||raw===undefined)?' is-suppressed':'');
    value.textContent=(raw===null||raw===undefined)?pollT(currentLanguage,'too few to show','amsa kaɗan'):raw;
    li.appendChild(label);li.appendChild(track);li.appendChild(value);
    target.appendChild(li);
  });
};

const renderPollTable=()=>{
  const table=document.querySelector('[data-poll-table]');
  if(!table||!pollSnapshot)return;
  const body=table.querySelector('tbody');
  const scope=pollResolveScope();
  const exact=pollShareIsExact(scope);
  const cap=100-pollSnapshot.percentage_floor;
  body.innerHTML='';
  const source=scope.rows;
  const rows=Object.keys(source||{}).map(key=>({key:key,count:source[key]}));
  rows.sort((a,b)=>{
    const av=a.count===null?-1:a.count;
    const bv=b.count===null?-1:b.count;
    return bv-av||a.key.localeCompare(b.key);
  });
  if(!rows.length){
    const tr=document.createElement('tr');
    const td=document.createElement('td');
    td.colSpan=3;
    td.className='poll-table-empty';
    td.textContent=pollT(currentLanguage,'No published figures for this area.','Babatar adadin da za a wallafa a wannan yanki.');
    tr.appendChild(td);body.appendChild(tr);
    return;
  }
  rows.forEach(row=>{
    const tr=document.createElement('tr');
    const meta=POLL_SECTOR_LABELS[row.key]||[row.key,row.key];
    const th=document.createElement('th');
    th.scope='row';
    th.textContent=pollT(currentLanguage,meta[0],meta[1]);
    const c1=document.createElement('td');
    const c2=document.createElement('td');
    if(row.count===null){
      c1.textContent='—';
      c2.textContent='—';
      tr.className='is-suppressed';
    }else if(!exact){
      // The cell itself clears the floor, but a sibling in the same group did not, so the
      // denominator is unknown. Showing the count is honest; showing a share is not.
      c1.textContent=row.count;
      c2.textContent='—';
      c2.className='is-share-withheld';
    }else{
      c1.textContent=row.count;
      c2.textContent=Math.round(Math.min((row.count/scope.total)*100,cap))+'%';
    }
    tr.appendChild(th);tr.appendChild(c1);tr.appendChild(c2);
    body.appendChild(tr);
  });
};

// The share column needs a reason attached, or a reader counts the dashes and concludes
// the data is broken rather than protected.
const pollRenderShareNote=()=>{
  const el=document.querySelector('[data-poll-share-note]');
  if(!el)return;
  const scope=pollResolveScope();
  const exact=pollShareIsExact(scope);
  el.hidden=exact||!scope.rows||!Object.keys(scope.rows).length;
};

const pollSyncWardOptions=()=>{
  const select=document.querySelector('[data-poll-ward-filter]');
  if(!select)return;
  const previous=pollState.ward;
  const available=pollState.lga?Object.keys((pollSnapshot.by_lga_ward||{})[pollState.lga]||{}):[];
  if(!available.includes(previous))pollState.ward='';
  select.innerHTML='';
  const all=document.createElement('option');
  all.value='';
  all.textContent=pollT(currentLanguage,
    pollState.lga?'No specific area':'Choose an LGA first',
    pollState.lga?'Babatar wuri':'Zaɓi LGA da farko');
  select.appendChild(all);
  available.forEach(code=>{
    const option=document.createElement('option');
    option.value=code;
    const name=POLL_WARD_LABELS[code];
    option.textContent=name?name+' ('+code+')':code;
    select.appendChild(option);
  });
  select.value=pollState.ward;
  select.disabled=!pollState.lga;
};

const pollSyncLensGroupLabels=()=>{
  // `setLanguage` rewrites `textContent`, never the `label` attribute, so <optgroup>
  // headers need their own pass -- and their bilingual pair must NOT be carried as
  // data-en/data-ha, or that same pass would delete the options nested inside them.
  document.querySelectorAll('[data-poll-optgroup]').forEach(group=>{
    const en=group.getAttribute('data-poll-label-en');
    const ha=group.getAttribute('data-poll-label-ha');
    if(!en)return;
    group.setAttribute('label',currentLanguage==='ha'&&ha?ha:en);
  });
};

const pollSyncLensAvailability=()=>{
  const select=document.querySelector('[data-poll-lens-filter]');
  if(!select)return;
  // A registration area and a demographic must never appear in the same figure. When a
  // ward is chosen the lens is reset to "everyone" and disabled, so the refused cross is
  // unreachable rather than merely discouraged.
  const blocked=Boolean(pollState.ward);
  if(blocked)pollState.lens='';
  select.disabled=blocked;
  select.value=pollState.lens;
  const note=document.querySelector('[data-poll-lens-lock]');
  if(note)note.hidden=!blocked;
};

// Declared after the two sync helpers and called from every render, including the one
// setLanguage triggers. That is what keeps the rebuilt area options in the active
// language: the options are created in JavaScript, so no `data-en` attribute exists for
// the core language switcher to rewrite.
const renderPoll=()=>{
  pollSyncWardOptions();
  pollSyncLensAvailability();
  pollSyncLensGroupLabels();
  pollRenderScopeSummary();
  pollRenderSectorChart();
  renderPollLgaChart();
  renderPollTable();
  pollRenderShareNote();
};

const pollControlsInit=()=>{
  const lgaSelect=document.querySelector('[data-poll-filter]');
  const wardSelect=document.querySelector('[data-poll-ward-filter]');
  const lensSelect=document.querySelector('[data-poll-lens-filter]');
  if(!lgaSelect||!lgaSelect.dataset)return false;
  lgaSelect.addEventListener('change',()=>{
    pollState.lga=lgaSelect.value;
    pollState.ward='';
    renderPoll();
  });
  if(wardSelect){
    wardSelect.addEventListener('change',()=>{
      pollState.ward=wardSelect.value;
      renderPoll();
    });
  }
  if(lensSelect){
    lensSelect.addEventListener('change',()=>{
      pollState.lens=lensSelect.value;
      renderPoll();
    });
  }
  return true;
};
if(pollControlsInit())renderPoll();
// The chart labels are built in the active language, so a language switch has to rebuild
// them. SCRIPT_CORE seeds `renderPollHook` as a no-op and calls it from setLanguage, which
// is the same contract `renderFeatured` already uses.
renderPollHook=renderPoll;

const publicPollForm=document.querySelector('[data-poll-form]');
if(publicPollForm){
  const pollLga=publicPollForm.querySelector('#poll-lga');
  const pollWard=publicPollForm.querySelector('#poll-ward');
  const pollStatus=publicPollForm.querySelector('[data-poll-status]');
  const pollConfirmation=publicPollForm.querySelector('[data-poll-confirmation]');
  const pollSubmit=publicPollForm.querySelector('[data-poll-submit]');
  const pollConfigStatus=publicPollForm.querySelector('[data-poll-config-status]');
  const pollConsent=publicPollForm.querySelector('#poll-consent');
  const POLL_SEEN_KEY='apm-poll-voted';
  const POLL_RESPONSE_ID=/^APM-POLL-[0-9]{4}-[0-9]{4,12}$/;
  const configuredPollEndpoint=(publicPollForm.dataset.pollEndpoint||'').trim();
  let pollEndpointUrl=null;
  try{
    const parsedPollEndpoint=new URL(configuredPollEndpoint,window.location.href);
    if(configuredPollEndpoint&&parsedPollEndpoint.protocol==='https:'&&!parsedPollEndpoint.username&&!parsedPollEndpoint.password&&!parsedPollEndpoint.hash)pollEndpointUrl=parsedPollEndpoint;
  }catch(error){pollEndpointUrl=null;}
  const pollEndpointReady=Boolean(pollEndpointUrl);
  const readPollSeen=()=>{try{return window.localStorage.getItem(POLL_SEEN_KEY)==='1';}catch(error){return false;}};
  const storePollSeen=()=>{try{window.localStorage.setItem(POLL_SEEN_KEY,'1');}catch(error){/* blocked storage: the vote still counts server-side */}};
  const showPollStatus=key=>{
    const english=pollStatus.dataset[key+'En'];
    const hausa=pollStatus.dataset[key+'Ha'];
    pollStatus.textContent=currentLanguage==='ha'?(hausa||pollStatus.dataset.ha):(english||pollStatus.dataset.en);
    pollStatus.classList.toggle('is-error',key==='error');
    pollStatus.hidden=false;
  };
  const applyPollBilingualValidity=()=>{
    const sector=publicPollForm.querySelector('#poll-sector');
    const lga=publicPollForm.querySelector('#poll-lga');
    if(sector)sector.setCustomValidity(sector.value?'':'Choose a sector.');
    if(lga)lga.setCustomValidity(lga.value?'':'Choose your LGA.');
    if(pollConsent)pollConsent.setCustomValidity(pollConsent.checked?'':'Tick the consent box to cast your vote.');
  };
  const updatePollWards=()=>{
    const selected=pollLga?pollLga.value:'';
    if(!pollWard)return;
    [...pollWard.options].forEach(option=>{
      if(option.hasAttribute('data-poll-ra-lga'))option.hidden=Boolean(selected)&&option.dataset.pollRaLga!==selected;
      else option.hidden=Boolean(selected);
    });
    pollWard.disabled=!selected;
    pollWard.value='';
  };
  publicPollForm.addEventListener('change',applyPollBilingualValidity);
  if(pollLga)pollLga.addEventListener('change',updatePollWards);
  updatePollWards();
  applyPollBilingualValidity();
  publicPollForm.setAttribute('aria-disabled',String(!pollEndpointReady));
  if(!pollEndpointReady){
    const notConnected=currentLanguage==='ha'?'Ba a saita wata adireshi da ake amfani da ita a wannan gina ba. Ba a yin amsa ba.':'No usable poll endpoint is configured in this build. No vote is being recorded.';
    pollConfigStatus.textContent=notConnected;
    pollConfigStatus.dataset.en=notConnected;
    pollConfigStatus.dataset.ha=notConnected;
    pollSubmit.addEventListener('click',event=>{event.preventDefault();showPollStatus('unavailable');});
  }
  if(readPollSeen()){
    publicPollForm.querySelectorAll('select,textarea,input[type="checkbox"]').forEach(el=>{el.disabled=true;});
    pollSubmit.disabled=true;
  }
  publicPollForm.addEventListener('submit',async event=>{
    event.preventDefault();
    if(!pollEndpointReady){
      showPollStatus('unavailable');
      return;
    }
    const sector=publicPollForm.querySelector('#poll-sector');
    const lga=publicPollForm.querySelector('#poll-lga');
    const comment=publicPollForm.querySelector('#poll-comment');
    const honeypot=publicPollForm.querySelector('#poll-website');
    const ageBand=publicPollForm.querySelector('#poll-age-band');
    const gender=publicPollForm.querySelector('#poll-gender');
    if(!sector||!sector.value||!lga||!lga.value||!pollConsent||!pollConsent.checked){
      showPollStatus('unavailable');
      return;
    }
    // Deliberately minimal. No name, phone, email, address, exact age or voter ID is
    // collected, so there is nothing here that names a respondent.
    const payload={sector:sector.value,lga:lga.value,consent:true,website:(honeypot&&honeypot.value)||''};
    if(pollWard&&pollWard.value)payload.ward_code=pollWard.value;
    if(ageBand&&ageBand.value)payload.age_band=ageBand.value;
    if(gender&&gender.value)payload.gender=gender.value;
    if(comment&&comment.value.trim())payload.comment=comment.value.trim();
    pollSubmit.disabled=true;
    showPollStatus('submitting');
    try{
      // Content-Type is text/plain, NOT application/json, and that is load-bearing.
      // `application/json` is not a CORS-safelisted content type, so the browser sends an
      // OPTIONS preflight first. Google Apps Script answers that preflight with 200 and NO
      // Access-Control-Allow-* headers, the browser blocks the whole exchange, and `fetch`
      // rejects with a bare "Failed to fetch" -- no console error, no status, no clue.
      // text/plain is safelisted, so no preflight happens; the endpoint reads
      // `e.postData.contents` and never inspects the content type, so the JSON still parses.
      // Verified against the live deployment 1 October 2026: application/json failed,
      // text/plain returned a response_id. Do not "correct" this back.
      const response=await fetch(pollEndpointUrl.href,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8','Accept':'application/json'},body:JSON.stringify(payload),credentials:'omit',referrerPolicy:'no-referrer'});
      if(!response.ok)throw new Error('poll_endpoint_rejected');
      const data=await response.json();
      const trackingId=typeof data.response_id==='string'?data.response_id.trim().toUpperCase():'';
      if(!POLL_RESPONSE_ID.test(trackingId))throw new Error('poll_endpoint_contract_violation');
      pollConfirmation.dataset.trackingId=trackingId;
      pollConfirmation.textContent=(currentLanguage==='ha'?'An karɓi amsa. ID na bin: ':'Vote received. Tracking reference: ')+trackingId+'.';
      pollConfirmation.hidden=false;
      publicPollForm.reset();
      updatePollWards();
      storePollSeen();
      applyPollBilingualValidity();
    }catch(error){
      showPollStatus('error');
    }finally{
      pollSubmit.disabled=!pollEndpointReady||readPollSeen();
    }
  });
}
'''


def poll_ward_labels(ward_rows):
    """Registration-area code -> display name, for the results filter.

    The snapshot is keyed by code because that is all the endpoint stores. Showing the
    area's own name is what lets someone recognise their area; the code alone ("RA-001")
    means nothing to the person who lives there.
    """
    labels = {}
    for row in ward_rows or []:
        code = (row.get("ward_code") or "").strip()
        name = (row.get("ra_name_display") or "").strip()
        if code and name:
            labels[code] = name
    return labels


def poll_script(ward_rows=None):
    """The poll's inline script, with the label and LGA tables injected.

    The sector labels are emitted from the same REQUEST_CATEGORIES the form uses, so the
    chart legend and the `<select>` options cannot drift apart, and a language switch
    translates both from one source. The age and gender tables come from the same tuples
    that build the form's own options, for the same reason.
    """
    labels = {key: [en, ha] for key, en, ha in REQUEST_CATEGORIES}
    age_labels = {key: [en, ha] for key, en, ha in POLL_AGE_BANDS}
    gender_labels = {key: [en, ha] for key, en, ha in POLL_GENDER_OPTIONS}
    return (
        POLL_SCRIPT
        .replace("__POLL_SECTOR_LABEL_JSON__", json.dumps(labels, ensure_ascii=False))
        .replace("__POLL_LGA_ORDER_JSON__", json.dumps(list(LGAS), ensure_ascii=False))
        .replace("__POLL_AGE_LABEL_JSON__", json.dumps(age_labels, ensure_ascii=False))
        .replace("__POLL_GENDER_LABEL_JSON__", json.dumps(gender_labels, ensure_ascii=False))
        .replace(
            "__POLL_WARD_LABEL_JSON__",
            json.dumps(poll_ward_labels(ward_rows), ensure_ascii=False))
    )


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


def load_lga_paths():
    """Read the committed, pre-simplified boundary geometry.

    The renderer never calls ArcGIS: the weekly Pages rebuild must stay deterministic and
    offline, so the geometry is derived once by `python -m src.derived.lga_paths` and
    committed. Failing closed here means a missing or stale derivative is a red build
    rather than a silently missing map.
    """
    if not LGA_PATHS_FILE.exists():
        raise FileNotFoundError(
            f"{LGA_PATHS_FILE} is missing. Generate it with `python -m src.derived.lga_paths`."
        )
    return json.loads(LGA_PATHS_FILE.read_text(encoding="utf-8"))


def validate_lga_paths(paths, lga_rows):
    """The map must cover exactly the 20 LGAs the rest of the site talks about."""
    names = set(paths["lgas"])
    if names != set(LGAS):
        missing = sorted(set(LGAS) - names)
        extra = sorted(names - set(LGAS))
        raise ValueError(f"atlas geometry does not match LGAS: missing={missing} extra={extra}")
    for lga, shape in paths["lgas"].items():
        if not shape["d"].startswith("M") or not shape["d"].endswith("Z"):
            raise ValueError(f"atlas path for {lga} is not a closed SVG path")
    if paths["seams"]["tear_deg"] > 0:
        raise ValueError(
            f"atlas geometry has a seam tear of {paths['seams']['tear_deg']} deg; "
            "neighbouring LGAs would be drawn with a gap between them"
        )
    if paths["seams"]["quantization_retention"] < 0.90:
        raise ValueError(
            "atlas quantization is below the 90% shared-edge retention floor; "
            "borders would tear"
        )
    covered = {row.get("lga") for row in lga_rows}
    if covered != set(LGAS):
        raise ValueError("lga_delivery.csv does not cover exactly the 20 atlas LGAs")
    return True


def lga_map_svg(paths, lga_rows):
    """Inline SVG of the 20 LGA outlines, each a labelled, focusable control.

    Zero runtime third-party requests: the geometry is inline, so the map works offline
    and adds no dependency to a page that otherwise has none.

    The map is the *only* selector. An earlier build also shipped the 20-item CSS-tile
    list beneath it, but every tile repeated a name the map already labels plus a badge
    visible only as a fill colour, so it was ~460px of duplication and exactly the
    "competing primary navigation" the phase plan warned against. Cutting it is why each
    path now carries the per-LGA text itself, via the same `data-lga` contract the core
    script already speaks, so `renderLgaDetail` needed no changes.

    `role="group"`, not `role="img"`: an image role makes assistive technology treat the
    whole SVG as one picture and hide the children, which would make 20 focusable shapes
    unreachable. A labelled group exposes the paths as the 20 items they are.
    """
    coverage = {row.get("lga"): row for row in lga_rows}
    shapes = []
    labels = []
    for lga in LGAS:
        shape = paths["lgas"][lga]
        row = coverage.get(lga, {})
        specific = row.get("coverage_type") == "lga_specific"
        scope_en = "LGA-specific evidence" if specific else "Statewide evidence"
        scope_ha = "Tabbacin LGA" if specific else "Tabbacin jihada"
        classes = "lga-shape lga-specific" if specific else "lga-shape"
        shapes.append(
            f'<path class="{classes}" data-lga="{esc(lga)}" tabindex="0" role="button" '
            f'd="{shape["d"]}" '
            f'data-summary="{esc(row.get("achievement_summary", ""))}" '
            f'data-summary-ha="{esc(row.get("achievement_summary_ha") or row.get("achievement_summary", ""))}" '
            f'data-promise="{esc(row.get("apm_promise", ""))}" '
            f'data-promise-ha="{esc(row.get("apm_promise_ha") or row.get("apm_promise", ""))}" '
            f'data-result="{esc(row.get("next_result", ""))}" '
            f'data-result-ha="{esc(row.get("next_result_ha") or row.get("next_result", ""))}" '
            f'{aria(f"{lga}, {scope_en}. Select this area.", f"{lga}, {scope_ha}. Zaɓi wannan area.")}>'
            f'<title>{esc(lga)}</title></path>'
        )
        labels.append(
            f'<text class="lga-map-label" x="{shape["label_x"]}" y="{shape["label_y"]}">'
            f'{esc(lga)}</text>'
        )
    return (
        f'<svg class="lga-map" viewBox="{esc(paths["viewbox"])}" role="group" '
        f'{aria("Map of the 20 Bauchi local government areas. Indicative operational boundaries, not official. Select an area to load its evidence.",
               "Taswirar LGA 20 na Bauchi. Kanƙoƙin da a nuna shi ne, ba tsarin gwaji ba. Zaɓi wani wurin don duba bayaninsa.")}>'
        f'<g class="lga-shapes">{"".join(shapes)}</g>'
        f'<g class="lga-map-labels" aria-hidden="true">{"".join(labels)}</g>'
        "</svg>"
    )


def lga_map_legend(lga_rows):
    """Explains the two fills now that the tile badges are gone.

    Derived from the data, not hardcoded: every LGA currently has `lga_specific` coverage, so
    a fixed two-entry legend would advertise a "Statewide" state that never occurs. The
    entry disappears by itself the day one LGA's row actually says `statewide`.
    """
    present = {row.get("lga"): row.get("coverage_type") for row in lga_rows}
    if not any(value != "lga_specific" for value in present.values()):
        return (
            '<div class="lga-map-legend"><span class="lga-legend-item">'
            '<span class="lga-legend-swatch lga-legend-specific"></span>'
            + copy("LGA-specific evidence", "Tabbacin LGA")
            + "</span></div>"
        )
    return (
        '<div class="lga-map-legend">'
        '<span class="lga-legend-item"><span class="lga-legend-swatch lga-legend-specific"></span>'
        + copy("LGA-specific evidence", "Tabbacin LGA")
        + '</span><span class="lga-legend-item"><span class="lga-legend-swatch"></span>'
        + copy("Statewide evidence", "Tabbacin jihada")
        + "</span></div>"
    )


def lga_map_figure(paths, lga_rows, sources):
    """The map plus its licence credit and the caveats that make it honest."""
    return (
        '<figure class="lga-map-figure">'
        + lga_map_svg(paths, lga_rows)
        + '<figcaption class="lga-map-credit">'
        + copy("Indicative operational boundaries, not gazetted. Simplified for display.",
               "Kanƙoƙin da a nuna shi ne, ba a tsara shi da dokofa ba. An sauƙaƙe shi don nunawa.")
        + f'<span class="lga-map-caveat-text" {attr(paths["caveat"], paths["caveat_ha"])}>'
        + esc(paths["caveat"])
        + "</span>"
        + copy("Licence and credit", "Laiƙa da zance")
        + f'<span class="lga-map-licence-text" {attr(paths["attribution"], paths["attribution_ha"])}>'
        + esc(paths["attribution"])
        + "</span>"
        + "</figcaption></figure>"
    )


def lga_ra_list(ward_rows):
    """Registration areas for the selected LGA, from `lga_wards.csv`.

    These are electoral registration-area labels, not council wards, and `lga_wards.csv`
    carries no coordinates. None are invented, so the list is explicitly labelled as not
    geo-located and is never drawn on the map.
    """
    grouped = {}
    for row in ward_rows:
        grouped.setdefault(row.get("lga", ""), []).append(row)
    blocks = []
    for lga in LGAS:
        rows = grouped.get(lga, [])
        items = "".join(f"<li>{esc(row.get('ra_name_display') or row.get('ra_name_source', ''))}</li>"
                        for row in rows)
        blocks.append(
            f'<div class="ra-list" data-ra-lga="{esc(lga)}" hidden>'
            f'<div class="detail-label">'
            + copy("Registration areas · not geo-located",
                   "Wurare ƙaura zaye · ba a tantance su a geolocation ba")
            + "</div>"
            f'<ul class="ra-items">{items}</ul></div>'
        )
    return "".join(blocks)


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
        "An kunna adireshi don buƙatar. Samun da zarfin ya dogara da sabis da karɓi."
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
                <div class="request-field request-field-wide"><label for="request-email">{copy("Email, if you would like a reply (optional)", "Imel idan ka son amsa (ƙoƙari aika imel)")}</label><input id="request-email" name="email" type="email" maxlength="254" autocomplete="email"></div>
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
        <div><span>03</span><h3>{copy("Use the tracking reference", "Yi amfani da ID na bin")}</h3><p>{copy("A confirmation reference helps follow up only after the request service accepts a request. It is not a voter ID.", "Maƙai bin ya taimaka ne kawai bayan sabis ɗin buƙatar ya karɓi buƙatar. Ba ID na zabb'ar masu zayyawa ba.")}</p></div>
      </aside>
    </div>
  </div>
</section>'''


@functools.lru_cache(maxsize=None)
def _poll_module(name):
    """Import a `src/poll/` module.

    `render.py` is executed as a script by the weekly cron, so the repository root is
    not on `sys.path` and `import src.poll...` raises ModuleNotFoundError there while
    working fine under unittest. Putting the root on the path once, only if it is
    missing, makes both contexts behave identically -- and the relative import inside
    `src/poll/aggregate.py` needs a real package, which loading a bare file by path
    would not provide.

    The pure poll modules stay the single source of truth for the vocabulary, the
    length caps and the percentage floor. The page reads them from here rather than
    restating them, so a rule cannot drift between the validator and the form.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module(f"src.poll.{name}")


def load_poll_snapshot():
    """Read the committed aggregate snapshot, or None when it does not exist yet.

    The snapshot holds counts only -- no comment, no response ID, no timestamp of an
    individual response. It is the artefact the weekly cron regenerates, and it is what
    lets results be published on a static host with no live endpoint.
    """
    path = DATA / POLL_SNAPSHOT_FILE
    if not path.exists():
        return None
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(snapshot, dict):
        return None
    return snapshot


def format_snapshot_timestamp(value):
    """Render an ISO-8601 snapshot timestamp as a plain date a reader can parse.

    A raw `2026-09-29T12:00:00Z` is machine output on a public page. The date is enough
    for a reader and avoids implying a precision the poll does not have. An unparseable
    value falls back to the raw string rather than disappearing, because a visible
    malformed stamp is better than no provenance at all.
    """
    if not isinstance(value, str) or not value.strip():
        return ""
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return value.strip()
    return parsed.strftime("%d %B %Y")


def poll_dashboard(snapshot):
    """Two charts, one LGA dropdown, one exact table -- all from the committed snapshot.

    A suppressed cell is `None`, and it is rendered as an explicit "too few to publish"
    state rather than as a zero. A zero bar would read as "nobody in Bogoro wants
    water", which is the opposite of the truth, and a reader could not tell the two
    apart. The count of suppressed cells is stated on the page so a sparse dataset cannot
    masquerade as a complete one.

    The dropdown filters client-side over the embedded snapshot. The site is static, so
    there is nothing to query; the whole dataset is already in the page.
    """
    share_of_total = _poll_module("aggregate").share_of_total

    if snapshot is None:
        body = (
            '<p class="poll-empty" data-en="No responses have been recorded yet. Once the poll is '
            'connected, results will appear here." data-ha="Bai sami amsa ba tukuna. Idan aka haɗa '
            'hawsar, za a nuna sakamako a nan.">No responses have been recorded yet. Once the poll '
            'is connected, results will appear here.</p>'
        )
        # The disclosure ships in the empty state too, not only once data exists. A reader
        # arriving before the first response should learn what this is before they see a
        # number, not after.
        return (
            '<section class="section poll-results" id="poll-results" '
            'aria-labelledby="poll-results-title"><div class="shell"><div class="section-head"><div>'
            f'<div class="eyebrow">{copy("What people have said", "Abin da mutane suka faɗa")}</div>'
            f'<h2 id="poll-results-title">{copy("Sector priorities so far.", "Gabanawa na sectors har yanzu.")}</h2>'
            '</div><p>' + copy(
                "These are self-selected visitors, not a representative sample. It is not a "
                "survey and not a vote, and it does not measure how many people in Bauchi hold "
                "this view.",
                "Wannan mutane da suka zaɓi da kansa su amsa, ba su cikin saminci da ke wakilai ba. "
                "Ba wani bincike ba, ba zabi ba, kuma ba ta aunawa yawanin mutane a Bauchi da wannan "
                "ra'ayi ba.") + '</p></div>'
            f'<div class="poll-chart">{body}</div></div></section>'
        )

    floor = int(snapshot.get("percentage_floor", POLL_PERCENTAGE_FLOOR) or 0)
    threshold = int(snapshot.get("small_count_threshold", POLL_SMALL_COUNT_THRESHOLD) or 5)
    total = int(snapshot.get("total_responses") or 0)

    payload = json.dumps(snapshot, sort_keys=True).replace("</", "<\\/")

    if total <= 0:
        body = (
            '<p class="poll-empty" data-en="No responses have been recorded yet." '
            'data-ha="Bai sami amsa ba tukuna.">No responses have been recorded yet.</p>'
        )
        return (
            '<section class="section poll-results" id="poll-results" '
            'aria-labelledby="poll-results-title"><div class="shell"><div class="section-head"><div>'
            f'<div class="eyebrow">{copy("What people have said", "Abin da mutane suka faɗa")}</div>'
            f'<h2 id="poll-results-title">{copy("Sector priorities so far.", "Gabanawa na sectors har yanzu.")}</h2>'
            '</div></div>'
            f'<div class="poll-chart">{body}</div></div></section>'
        )

    lga_options = "".join(
        f'<option value="{esc(lga)}">{esc(lga)}</option>' for lga in LGAS
    )
    suppressed_count = int(snapshot.get("suppressed_cell_count", 0))
    meta = (
        f'<p class="poll-total"><b data-en="{total} responses" data-ha="{total} amsa">'
        f'{total} responses</b>'
        f'<span data-en="{threshold} or fewer answers are never shown" '
        f'data-ha="{threshold} ko ƙasa da haka ba a nuna amsawa ba">{threshold} or fewer answers are never shown</span></p>'
    )
    suppressed_note = (
        f'<p class="poll-suppressed" data-en="{suppressed_count} '
        f'figures are withheld because they come from too few answers." '
        f'data-ha="An sanya {suppressed_count} lambobi tare ba '
        f'akaiti saboda sun fito daga amsa kaɗan.">'
        f'{suppressed_count} figures are withheld because they come from too few answers.</p>'
    )

    # Who actually answered, as a coverage strip. A demographic filter is only as useful
    # as the number of people behind it, and a filter that silently matches three people is
    # worse than no filter at all. These four counts are the honest context for that.
    coverage = "".join(
        f'<div class="poll-stat"><b>{int(snapshot.get(key) or 0)}</b>'
        f'<span data-en="{esc(en)}" data-ha="{esc(ha)}">{esc(en)}</span></div>'
        for key, en, ha in (
            ("with_area_responses", "gave an LGA", "sun bada LGA"),
            ("with_ward_responses", "gave a registration area", "sun bada wurin ƙaura zaye"),
            ("with_age_band", "gave an age group", "sun bada shekaru"),
            ("with_gender", "gave a gender", "sun bada jinsi"),
        )
    )

    gender_options = "".join(
        f'<option value="g:{esc(key)}" data-en="{esc(en)}" data-ha="{esc(ha)}">{esc(en)}</option>'
        for key, en, ha in POLL_GENDER_OPTIONS
    )
    age_options = "".join(
        f'<option value="a:{esc(key)}" data-en="{esc(en)}" data-ha="{esc(ha)}">{esc(en)}</option>'
        for key, en, ha in POLL_AGE_BANDS
    )

    share_note_en = (
        "No percentage is shown for this group, because some of its answers are withheld "
        "and the total they would be a share of is not known. The counts are exact."
    )
    share_note_ha = (
        "Ba a nuna ƙoƙe ba don wannan ƙungiya, domin wasu daga amsanta an sanya su kuma ba a "
        "san jimillarsu ba. Adadin daidai ne."
    )
    lock_en = (
        "Age group and gender are switched off for a registration area. That pairing is "
        "never published, because a small area plus an age group is enough to identify "
        "individual people."
    )
    lock_ha = (
        "An shekaru da jinsi an kashe su don wurin ƙaura zaye. Wannan tarewa ba a wallafa "
        "ta ba, domin wuri karami tare da shekaru yana iya gane mutane."
    )

    controls = (
        '<div class="poll-scope">'
        '<div class="poll-scope-now">'
        f'<span class="poll-scope-kicker" {attr("Showing", "Ana nuna")}>Showing</span>'
        # These two nodes are rewritten by textContent on every render, so they carry the
        # bilingual attributes directly rather than through `copy()`, which would nest a
        # <span> the first language switch would then wipe along with its own text.
        f'<b data-poll-scope-summary {attr("All of Bauchi State", "Duk Bauchi")}>'
        'All of Bauchi State</b>'
        f'<span class="poll-scope-count" data-poll-scope-total {attr("answers", "amsa")}>'
        f'{total} answers</span>'
        '</div>'
        '<div class="poll-controls">'
        '<div class="poll-control"><label for="poll-lga-filter" '
        + attr("LGA", "LGA") + ">LGA</label>"
        '<select id="poll-lga-filter" data-poll-filter>'
        '<option value="" ' + attr("All of Bauchi State", "Duk Bauchi") + ">"
        "All of Bauchi State</option>"
        + lga_options
        + "</select></div>"
        '<div class="poll-control"><label for="poll-ward-filter" '
        + attr("Registration area", "Wurin ƙaura zaye") + ">Registration area</label>"
        '<select id="poll-ward-filter" data-poll-ward-filter disabled>'
        f'<option value="" {attr("Choose an LGA first", "Zaɓi LGA da farko")}>'
        'Choose an LGA first</option>'
        "</select></div>"
        '<div class="poll-control"><label for="poll-lens-filter" '
        + attr("Group", "ƙungiya") + ">Group</label>"
        '<select id="poll-lens-filter" data-poll-lens-filter>'
        f'<option value="" {attr("Everyone", "Kowa")}>Everyone</option>'
        # An <optgroup>'s visible text is its `label` ATTRIBUTE, so it needs its own
        # translator. The pair is carried as `data-poll-label-en`/`-ha`, deliberately NOT as
        # `data-en`/`data-ha`: `setLanguage` rewrites `textContent` for every
        # `[data-en][data-ha]` element, and on an element that owns children that DELETES
        # them. Using `attr()` here silently emptied the dropdown's options on the first
        # language switch -- the same failure the map suffered. `pollSyncLensGroupLabels`
        # writes the attribute from the untranslated-safe names.
        '<optgroup data-poll-optgroup="gender" data-poll-label-en="Gender" '
        'data-poll-label-ha="Jinsi" label="Gender">'
        f'{gender_options}</optgroup>'
        '<optgroup data-poll-optgroup="age" data-poll-label-en="Age group" '
        'data-poll-label-ha="Shekaru" label="Age group">'
        f'{age_options}</optgroup>'
        "</select></div></div>"
        # Both notes below are written with `attr()` and their own English text rather than
        # with `copy()`. `copy()` emits a child <span>, and `setLanguage` rewrites the
        # textContent of every [data-en][data-ha] element -- so a copy() wrapper inside a
        # node that JavaScript also writes to would be emptied on the first language
        # switch, leaving the reader with a visible but empty box and no explanation.
        f'<p class="poll-lock" data-poll-lens-lock hidden {attr(lock_en, lock_ha)}>'
        f'{esc(lock_en)}</p></div>'
    )

    return (
        '<section class="section poll-results" id="poll-results" '
        'aria-labelledby="poll-results-title"><div class="shell">'
        '<div class="section-head"><div>'
        f'<div class="eyebrow">{copy("What people have said", "Abin da mutane suka faɗa")}</div>'
        f'<h2 id="poll-results-title">{copy("Sector priorities so far.", "Gabanawa na sectors har yanzu.")}</h2>'
        '</div><p>' + copy(
            "These are self-selected visitors, not a representative sample. It is not a "
            "survey and not a vote, and it does not measure how many people in Bauchi hold "
            "this view.",
            "Wannan mutane da suka zaɓi da kansa su amsa, ba su cikin saminci da ke wakilai ba. "
            "Ba wani bincike ba, ba zabi ba, kuma ba ta aunawa yawanin mutane a Bauchi "
            "da wannan ra'ayi ba.") + '</p></div>'
        f'{meta}{suppressed_note}{controls}'
        '<div class="poll-chart poll-chart-sector">'
        '<h3 data-en="Which sector this group put first" '
        'data-ha="Wane sector wannan ƙungiya ya farko">Which sector this group put first</h3>'
        '<ol class="poll-bars" data-poll-sector-chart></ol>'
        '<p class="poll-share-note" data-poll-share-note hidden '
        + attr(share_note_en, share_note_ha) + f">{esc(share_note_en)}</p></div>"
        '<div class="poll-two">'
        '<div class="poll-chart poll-chart-lga"><h3 data-en="Responses by LGA" '
        'data-ha="Amsa ta LGA">Responses by LGA</h3>'
        '<ol class="poll-bars" data-poll-lga-chart></ol></div>'
        '<div class="poll-chart poll-chart-table"><h3 data-en="Exact counts" '
        'data-ha="Adadin daidai">Exact counts</h3>'
        '<div class="poll-table-wrap"><table class="poll-table" data-poll-table>'
        '<caption class="poll-table-cap" data-en="Counts for the selected group. '
        'A dash means too few answers to publish." '
        'data-ha="Adadin da aka zaɓi a cikin ƙungiya. Alamar gada (—) tana nuna cewa amsa kaɗan ce don a wallafa.">'
        'Counts for the selected group. A dash means too few answers to publish.</caption>'
        '<thead><tr><th scope="col" data-en="Sector" data-ha="Sector">Sector</th>'
        '<th scope="col" data-en="Responses" data-ha="Amsa">Responses</th>'
        '<th scope="col" data-en="Share" data-ha="Raba">Share</th></tr></thead>'
        '<tbody></tbody></table></div></div></div>'
        '<div class="poll-coverage"><h3 data-en="Who answered" '
        'data-ha="Wa suka amsa">Who answered</h3>'
        f'<div class="poll-stats">{coverage}</div></div>'
        f'<script type="application/json" data-poll-snapshot>{payload}</script>'
        '<div class="note-box">' + copy(
            "Areas with few answers are shown as a dash rather than a number, because a "
            "count of one or two would be a count of identifiable people. Age and gender are "
            "only ever shown as groups, never below LGA level, and never combined with a "
            "registration area. Age group and gender are alternative views of the same poll, "
            "not filters to be stacked: pick one.",
            "Wurare da ke da amsa kaɗan suna nuna cibiya maimakon lamba, domin adadin daya ko biyu "
            "zai kasance adadin mutane da za a iya gane su. Shekaru da jinsi suna nuna ne kawai a "
            "cikar hankali, ba a taƙa su a karkashin LGA ba, kuma ba a taƙa su tare da wurin aura "
            "zaye ba. Shekaru da jinsi sibi ne guda daya na wannan hawsar, ba filturi da za a "
            "sami a kafa su ba: zaɓi daya.")
        + '</div></div></section>'
    )


def poll_results_section(snapshot):
    """Kept as the historical name for the dashboard section."""
    return poll_dashboard(snapshot)



def poll_section(ward_rows):
    """Q1 sector choice, an area, optional demographics, and an optional Q2 comment.

    The area selectors reuse the request form's cascading LGA -> registration-area
    pattern and the same `lga_wards.csv`. The registration area is OPTIONAL on the poll,
    unlike the request form: nobody should be forced to narrow themselves further than
    they want to in order to be counted.
    """
    _validation = _poll_module("validation")
    ALLOWED_SECTORS = _validation.ALLOWED_SECTORS
    MAX_COMMENT_LENGTH = _validation.MAX_COMMENT_LENGTH

    sector_options = "".join(
        f'<option value="{esc(key)}" {attr(label_en, label_ha)}>{esc(label_en)}</option>'
        for key, label_en, label_ha in REQUEST_CATEGORIES
        if key in ALLOWED_SECTORS
    )
    lga_options = "".join(f'<option value="{esc(lga)}">{esc(lga)}</option>' for lga in LGAS)
    ra_options = "".join(
        f'<option value="{esc(row.get("ward_code", ""))}" '
        f'data-poll-ra-lga="{esc(row.get("lga", ""))}">'
        f'{esc(row.get("ra_name_display") or row.get("ra_name_source", ""))}</option>'
        for row in ward_rows
    )
    age_options = "".join(
        f'<option value="{esc(key)}" {attr(en, ha)}>{esc(en)}</option>'
        for key, en, ha in POLL_AGE_BANDS
    )
    gender_options = "".join(
        f'<option value="{esc(key)}" {attr(en, ha)}>{esc(en)}</option>'
        for key, en, ha in POLL_GENDER_OPTIONS
    )
    endpoint_configured = bool(POLL_ENDPOINT.strip())
    status_en = (
        "A poll endpoint is configured. Submission availability depends on the receiving service."
        if endpoint_configured else
        "The poll is not connected yet, so nothing is sent from this build. No vote is being recorded."
    )
    status_ha = (
        "An kunna adireshi don hawsar. Samun da zarfin ya dogara da sabis da karɓi."
        if endpoint_configured else
        "Ba a haɗa hawsar ba tukuna, don haka ba a tura komai daga wannan gina. Ba a yin amsa ba."
    )
    max_comment = MAX_COMMENT_LENGTH
    return f'''
<section class="section poll-section" id="poll" aria-labelledby="poll-title">
  <div class="shell">
    <div class="section-head">
      <div><div class="eyebrow">{copy("One question", "Ƙa tambaya daya")}</div><h2 id="poll-title">{copy("Which sector should APM prioritise first?", "Wane sector APM ya fi gabanawa da farko?")}</h2></div>
      <p>{copy("Pick one sector. That is the only thing this poll counts. The comment box below is a note attached to your vote, not a second question, and it is never tallied.", "Zaɓi sector daya. Shi kawai abin da wannan hawsar tana ƙirgita. ƙoƙin sharhi da ke kasa yana tare da ita, ba tambaya ta biyu ba.")}</p>
    </div>
    <form class="poll-form" id="public-poll-form" method="post" action="about:blank" onsubmit="return false" data-poll-form data-poll-endpoint="{esc(POLL_ENDPOINT)}" data-poll-configured="{str(endpoint_configured).lower()}" aria-describedby="poll-config-status poll-comment-note poll-identity-note">
      <p class="poll-config-status" id="poll-config-status" data-poll-config-status data-en="{esc(status_en)}" data-ha="{esc(status_ha)}">{esc(status_en)}</p>
      <div class="poll-grid">
        <div class="poll-field">
          <label for="poll-sector">{copy("Sector", "Sector")} <span class="poll-required" aria-hidden="true">*</span></label>
          <select id="poll-sector" name="sector" required>
            <option value="" {attr("Choose a sector", "Zaɓi sector")} selected>Choose a sector</option>
            {sector_options}
          </select>
        </div>
        <div class="poll-field">
          <label for="poll-lga">{copy("Your LGA", "LGA da kake")} <span class="poll-required" aria-hidden="true">*</span></label>
          <select id="poll-lga" name="lga" required>
            <option value="" {attr("Choose your LGA", "Zaɓi LGA da kake")} selected>Choose your LGA</option>
            {lga_options}
          </select>
        </div>
      </div>
      <div class="poll-field">
        <label for="poll-ward">{copy("Registration area (optional)", "Wurin ƙaura zaye (zaɓi)")}</label>
        <select id="poll-ward" name="ward_code" disabled>
          <option value="" {attr("Choose your LGA first", "Zaɓi LGA da kake da farko")} selected>Choose your LGA first</option>
          {ra_options}
        </select>
        <p class="poll-note" data-en="Leave this blank if you would rather not say. Choosing it makes the result more useful for your area, but areas with very few answers are never published." data-ha="Ka bar shi babu komai idan kana son ka faɗi ba. Zaɓi zai sa sakamako ya fi amfani ga yankin ka, amma wurare da ke da amsa kaɗan ba a wallafa su ba.">Leave this blank if you would rather not say.</p>
      </div>
      <fieldset class="poll-demographics">
        <legend>{copy("Optional · helps show who is answering", "Zaɓi · tana nuna ko wa yake amsa")}</legend>
        <div class="poll-grid">
          <div class="poll-field">
            <label for="poll-age-band">{copy("Age group", "Shekaru")}</label>
            <select id="poll-age-band" name="age_band">
              <option value="" {attr("Prefer not to say", "Na fi na faɗi ba")} selected>Prefer not to say</option>
              {age_options}
            </select>
          </div>
          <div class="poll-field">
            <label for="poll-gender">{copy("Gender", "Jinsi")}</label>
            <select id="poll-gender" name="gender">
              <option value="" {attr("Prefer not to say", "Na fi na faɗi ba")} selected>Prefer not to say</option>
              {gender_options}
            </select>
          </div>
        </div>
        <p class="poll-note" data-en="We ask for a group, never an exact age, and never a name, phone number, email or address. You can skip both questions." data-ha="Muna tambaya ƙungiya, ba shekaru kuma daidai ba, kuma ba suna, waya, imel ko adireshi ba. Za ka iya tsayawa duk tambayoyin ba tare da su ba.">We ask for a group, never an exact age, and never a name, phone number, email or address. You can skip both questions.</p>
      </fieldset>
      <div class="poll-field">
        <label for="poll-comment">{copy("Say a bit more (optional)", "Kara bayan aƙari (zaɓi)")}</label>
        <textarea id="poll-comment" name="comment" rows="3" maxlength="{max_comment}" aria-describedby="poll-comment-note"></textarea>
        <p class="poll-note" id="poll-comment-note" data-en="Your note goes with your vote. Please do not include your name, phone number, address or any identifying detail." data-ha="Wannan sharhi yana tare da amsar. Ka yi hankali ka guji shigar da suna, l waya, adireshi ko wani bayan da ke gano mutum.">Your note goes with your vote. Please do not include your name, phone number, address or any identifying detail.</p>
      </div>
      <div class="poll-field poll-honeypot" aria-hidden="true"><label for="poll-website" data-en="Website" data-ha="Yanayin gari">Website</label><input id="poll-website" name="website" type="text" tabindex="-1" autocomplete="off"></div>
      <div class="poll-consent">
        <input id="poll-consent" name="consent" type="checkbox" required>
        <label for="poll-consent">{copy("I consent to this vote being recorded and counted. No name or contact detail is collected.", "Na amince da a lissafa wannan amsar. Ba a tara suna ko bayan hulɗe ba.")} <span class="poll-required" aria-hidden="true">*</span></label>
      </div>
      <p class="poll-note" id="poll-identity-note" data-en="No name, phone, email, address or voter ID is requested. Any reference shown after you vote is a generated response tracking reference, not a voter ID." data-ha="Ba a nemi suna, l waya, imel, adireshi ko ID na zabb'ar masu zayyawa ba. Kowane ID da za a nuna bayan amsa yana nufin bin amsa kawai, ba ID na zabb'ar masu zayyawa ba.">No name, phone, email, address or voter ID is requested.</p>
      <button class="btn poll-submit" type="submit" data-poll-submit {'disabled' if not endpoint_configured else ''}><span data-en="Cast vote" data-ha="Yi amsa">Cast vote</span></button>
      <p class="poll-status" data-poll-status role="status" aria-live="polite" aria-atomic="true" data-en="Voting is currently unavailable. Please check the status above." data-ha="Ba a samu damar yin amsa yanzu. Duba matsayi a sama." data-unavailable-en="Voting is currently unavailable. Please check the status above." data-unavailable-ha="Ba a samu damar yin amsa yanzu. Duba matsayi a sama." data-submitting-en="Sending your vote." data-submitting-ha="Ana aika amsar." data-error-en="We could not send your vote. Please try again later." data-error-ha="Ba mu iya aika amsar. Ka sake gwada daga baya.">Voting is currently unavailable. Please check the status above.</p>
      <div class="poll-confirmation" data-poll-confirmation role="status" aria-live="polite" aria-atomic="true" hidden data-en="Vote received. This reference tracks your response only and is not a voter ID." data-ha="An karɓi amsa. Wannan ID yana bin amsar kawai, ba ID na zabb'ar masu zayyawa ba.">Vote received.</div>
    </form>
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
/* Party identity watermark. Decorative only: aria-hidden, not focusable, and never
   intercepting a click. z-index 1 puts it above the page's own section backgrounds but
   below the topbar (z-index 2), so it reads as texture rather than as an overlay. The
   emblem is kept faint enough to stay clear of body text at full contrast. */
.watermark{position:fixed;inset:0;z-index:1;overflow:hidden;pointer-events:none;display:flex;align-items:center;justify-content:center}
.watermark img{width:min(62vmin,460px);height:auto;opacity:.05;max-width:none}
@media print{.watermark{display:none}}
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
.lga-detail{margin-top:26px;border:1px solid rgba(255,255,255,.2);padding:25px;background:rgba(255,255,255,.06);display:flex;justify-content:space-between;gap:30px;align-items:start;flex-wrap:wrap}
.lga-detail h3{font-family:Georgia,serif;font-size:2rem;font-weight:400;margin:0 0 8px;min-height:1.1em}
.lga-detail p{color:rgba(255,255,255,.66);font-size:14px;max-width:620px;margin:0}
.lga-detail .detail-label{color:var(--gold);font-size:10px;text-transform:uppercase;letter-spacing:.15em;white-space:nowrap}
.lga-detail-head{flex:1 1 260px;min-width:0}
.evidence-rows{flex:1 1 320px;min-width:0;margin:0;display:grid;gap:16px}
.evidence-row dt{color:var(--gold);font-size:10px;text-transform:uppercase;letter-spacing:.15em;margin-bottom:5px}
.evidence-row dd{margin:0;font-size:14px;line-height:1.55;color:rgba(255,255,255,.82)}
.lga-map-legend{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:12px;font-size:11px;color:rgba(255,255,255,.62)}
.lga-legend-item{display:flex;align-items:center;gap:7px}
.lga-legend-swatch{width:13px;height:13px;flex:none;background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.35)}
.lga-legend-swatch.lga-legend-specific{background:rgba(216,155,49,.45);border-color:rgba(216,155,49,.8)}
.lga-map-layout{display:grid;grid-template-columns:1.15fr .85fr;gap:28px;align-items:start;position:relative;z-index:1;margin-top:8px}
.lga-map-column{position:sticky;top:96px}
.lga-map-figure{margin:0}
.lga-map{width:100%;height:auto;display:block;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.16)}
.lga-shape{fill:rgba(255,255,255,.09);stroke:var(--navy);stroke-width:1.6;stroke-linejoin:round;cursor:pointer;transition:fill .18s,stroke .18s}
.lga-shape.lga-specific{fill:rgba(216,155,49,.2)}
.lga-shape:hover{fill:rgba(216,155,49,.42)}
.lga-shape.active{fill:var(--gold);stroke:#fff;stroke-width:2.4}
.lga-shape:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
.lga-map-label{fill:rgba(255,255,255,.82);font-family:Georgia,serif;font-size:19px;text-anchor:middle;dominant-baseline:middle;pointer-events:none;paint-order:stroke;stroke:rgba(11,38,60,.85);stroke-width:3px;stroke-linejoin:round}
.lga-map-credit{display:block;margin-top:12px;font-size:11px;line-height:1.55;color:rgba(255,255,255,.55)}
.lga-map-credit span{display:block}
.lga-map-credit .lga-map-caveat-text{color:rgba(255,255,255,.72);margin-top:3px}
.lga-map-credit .lga-map-licence-text{color:rgba(255,255,255,.45);margin-top:7px}
.lga-panel .lga-detail{margin-top:0}
.ra-list{margin-top:18px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.04);padding:16px 18px}
.ra-list .detail-label{color:var(--gold);font-size:10px;text-transform:uppercase;letter-spacing:.15em}
.ra-items{list-style:none;margin:10px 0 0;padding:0;display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}
.ra-items li{font-size:12px;color:rgba(255,255,255,.7);line-height:1.5}
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
.poll-section .section-head p{max-width:62ch}
.poll-form{background:var(--white);border:1px solid var(--line);border-radius:6px;padding:26px;display:grid;gap:18px;box-shadow:var(--shadow);max-width:720px}
.poll-config-status{margin:0;font-size:12px;line-height:1.5;color:var(--muted);border-left:3px solid var(--gold);padding-left:12px}
.poll-field{display:grid;gap:7px}
.poll-field label{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--navy);font-weight:700}
.poll-field select,.poll-field textarea{font-family:inherit;font-size:16px;padding:11px 12px;border:1px solid var(--line);border-radius:4px;background:var(--white);color:var(--ink);width:100%}
.poll-field textarea{resize:vertical;min-height:84px;line-height:1.5}
.poll-field select:focus-visible,.poll-field textarea:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.poll-required{color:var(--gold)}
.poll-note{margin:0;font-size:11px;line-height:1.55;color:var(--muted)}
.poll-honeypot{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.poll-consent{display:grid;grid-template-columns:20px 1fr;gap:11px;align-items:start}
.poll-consent input{width:20px;height:20px;margin:2px 0 0;accent-color:var(--navy)}
.poll-consent label{font-size:12px;line-height:1.55;color:var(--ink);text-transform:none;letter-spacing:0;font-weight:400}
.poll-submit{justify-self:start;border:0;background:var(--navy);color:#fff;cursor:pointer;padding:13px 24px;font-size:13px;letter-spacing:.06em;text-transform:uppercase;box-shadow:0 10px 22px rgba(11,38,60,.18)}
.poll-submit:hover{background:var(--blue)}
.poll-submit:focus-visible{outline:3px solid var(--gold);outline-offset:3px}
.poll-submit:disabled{opacity:.55;cursor:not-allowed;box-shadow:none}
.poll-status{margin:0;font-size:12px;line-height:1.5;color:var(--muted)}
.poll-status.is-error{color:#a3341f}
.poll-confirmation{margin:0;font-size:12px;line-height:1.5;color:var(--green);background:var(--green-soft);border:1px solid rgba(46,114,84,.3);border-radius:4px;padding:12px 14px}
.poll-results{background:var(--sky)}
.poll-chart{background:var(--white);border:1px solid var(--line);border-radius:6px;padding:24px 26px;box-shadow:var(--shadow)}
.poll-total{margin:0 0 16px;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.poll-total b{font-family:Georgia,serif;font-size:1.5rem;color:var(--navy);font-weight:400;letter-spacing:0;text-transform:none;margin-right:8px}
.poll-bars{list-style:none;margin:0;padding:0;display:grid;gap:11px;counter-reset:pollbar}
.poll-bar{display:grid;grid-template-columns:minmax(120px,1.1fr) minmax(90px,2.4fr) auto;align-items:center;gap:14px}
.poll-bar-label{font-size:12px;color:var(--ink);font-weight:700}
.poll-bar-track{height:14px;background:rgba(11,38,60,.08);border-radius:2px;overflow:hidden}
.poll-bar-fill{display:block;height:100%;background:var(--navy);border-radius:2px;min-width:2px}
.poll-bar-value{font-size:12px;color:var(--navy);font-weight:700;white-space:nowrap}
.poll-bar-pct{color:var(--muted);font-weight:400;margin-left:6px}
.poll-empty{margin:0;font-size:13px;line-height:1.6;color:var(--muted)}
.poll-stamp{margin:16px 0 0;font-size:11px;line-height:1.55;color:var(--muted)}
.poll-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.poll-demographics{border:1px solid var(--line);border-radius:4px;padding:16px;margin:0;display:grid;gap:14px;background:rgba(11,38,60,.02)}
.poll-demographics legend{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--navy);font-weight:700;padding:0 6px}
.poll-controls{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin:0 0 20px}
.poll-controls label{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700}
.poll-controls select{font-family:inherit;font-size:15px;padding:10px 12px;border:1px solid var(--line);border-radius:4px;background:var(--white);color:var(--ink);min-width:210px}
.poll-controls select:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.poll-chart{margin:0 0 22px;background:var(--white);border:1px solid var(--line);border-radius:6px;padding:22px 24px;box-shadow:var(--shadow)}
.poll-chart h3{margin:0 0 16px;font-family:Georgia,serif;font-size:1.15rem;font-weight:400;color:var(--navy)}
.poll-total{margin:0 0 14px;display:flex;flex-wrap:wrap;align-items:baseline;gap:12px;font-size:12px;color:var(--muted)}
.poll-total b{font-family:Georgia,serif;font-size:1.6rem;color:var(--navy);font-weight:400;letter-spacing:0;text-transform:none}
.poll-suppressed{margin:0 0 18px;font-size:11px;line-height:1.55;color:var(--muted);border-left:3px solid var(--gold);padding-left:12px}
.poll-bars{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.poll-bar{display:grid;grid-template-columns:minmax(110px,1.2fr) minmax(80px,2.4fr) auto;align-items:center;gap:14px}
.poll-bar-label{font-size:12px;color:var(--ink);font-weight:700}
.poll-bar-track{height:14px;background:rgba(11,38,60,.08);border-radius:2px;overflow:hidden}
.poll-bar-fill{display:block;height:100%;background:var(--navy);border-radius:2px;min-width:3px}
.poll-bar-fill.is-alt{background:var(--blue)}
/* A suppressed cell is drawn as an empty hatched track, never as a zero-width bar. A
   zero bar reads as "nobody chose this", which is the opposite of "too few to publish". */
.poll-bar-fill.is-suppressed{background:repeating-linear-gradient(45deg,rgba(11,38,60,.18) 0 4px,transparent 4px 8px);min-width:0;width:100%}
.poll-bar-value{font-size:12px;color:var(--navy);font-weight:700;white-space:nowrap}
.poll-bar-value.is-suppressed{color:var(--muted);font-weight:400;font-size:11px;white-space:normal}
.poll-bar-empty{min-height:20px}
.poll-table-wrap{overflow-x:auto}
.poll-table{width:100%;border-collapse:collapse;font-size:12px}
.poll-table caption{text-align:left;font-size:11px;line-height:1.55;color:var(--muted);padding-bottom:10px}
.poll-table th,.poll-table td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line)}
.poll-table thead th{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700}
.poll-table tbody th{font-weight:700;color:var(--ink)}
.poll-table tbody td{color:var(--navy);font-variant-numeric:tabular-nums}
.poll-table tr.is-suppressed td,.poll-table tr.is-suppressed th{color:var(--muted)}
.poll-table-empty{color:var(--muted);font-style:italic}
.poll-table td.is-share-withheld{color:var(--muted)}
/* The scope block is the control surface for every figure on the page, so it is styled as
   a panel rather than a loose row of dropdowns: the reader should be able to see, at a
   glance, which population the numbers underneath belong to. */
.poll-scope{background:var(--white);border:1px solid var(--line);border-radius:6px;padding:20px 22px;box-shadow:var(--shadow);margin:0 0 22px}
.poll-scope-now{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;padding-bottom:16px;margin-bottom:16px;border-bottom:1px solid var(--line)}
.poll-scope-kicker{font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700}
.poll-scope-now b{font-family:Georgia,serif;font-size:1.15rem;font-weight:400;color:var(--navy)}
.poll-scope-count{margin-left:auto;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
.poll-control{display:grid;gap:6px;min-width:190px;flex:1 1 190px}
.poll-control label{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700}
.poll-control select{font-family:inherit;font-size:15px;padding:10px 12px;border:1px solid var(--line);border-radius:4px;background:var(--white);color:var(--ink);width:100%}
.poll-control select:focus-visible{outline:3px solid var(--gold);outline-offset:2px}
.poll-control select:disabled{background:rgba(11,38,60,.04);color:var(--muted);cursor:not-allowed}
.poll-lock{margin:16px 0 0;padding:12px 14px;font-size:12px;line-height:1.6;color:var(--ink);background:rgba(176,141,36,.1);border-left:3px solid var(--gold)}
.poll-lock[hidden]{display:none}
.poll-two{display:grid;grid-template-columns:1fr 1fr;gap:22px;align-items:start}
.poll-two .poll-chart{margin:0}
.poll-share-note{margin:16px 0 0;padding:12px 14px;font-size:11px;line-height:1.6;color:var(--muted);background:rgba(11,38,60,.04);border-left:3px solid var(--navy)}
.poll-share-note[hidden]{display:none}
.poll-coverage{margin:0 0 22px}
.poll-coverage h3{font-family:Georgia,serif;font-size:1.15rem;font-weight:400;color:var(--navy);margin:0 0 14px}
.poll-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:6px;overflow:hidden}
.poll-stat{background:var(--white);padding:16px 18px;display:grid;gap:4px}
.poll-stat b{font-family:Georgia,serif;font-size:1.6rem;font-weight:400;color:var(--navy);font-variant-numeric:tabular-nums;line-height:1}
.poll-stat span{font-size:11px;line-height:1.45;color:var(--muted)}
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
/* Contributor credit. No longer a placeholder: the owner named the contributor and supplied
   the portrait, so the dashed placeholder treatment is gone. No amount and no organisation
   is stated -- the line is a factual role disclosure, not a claim of delivered achievement. */
.sponsor{display:flex;gap:14px;align-items:center;max-width:400px;padding:12px 16px;border:1px solid rgba(255,255,255,.28);border-radius:4px;background:rgba(255,255,255,.03)}
.sponsor-photo{width:58px;height:58px;flex:none;border:1px solid rgba(255,255,255,.3);border-radius:3px;overflow:hidden;background:#fff}
.sponsor-photo img{display:block;width:100%;height:100%;object-fit:cover}
.sponsor-body{min-width:0}
.sponsor-label{display:block;font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:rgba(255,255,255,.5);margin-bottom:3px}
.sponsor-name{display:block;font-family:Georgia,serif;font-size:1.05rem;font-weight:400;color:#fff}
.sponsor-contribution{display:block;font-size:11px;line-height:1.45;color:rgba(255,255,255,.72);margin-top:5px}
.sponsor-contribution b{color:#fff;font-weight:700}
.reveal{opacity:0;transform:translateY(15px);animation:rise .7s ease forwards;animation-delay:var(--delay,0s)}
@keyframes rise{to{opacity:1;transform:translateY(0)}}
/* --- about page ----------------------------------------------------------
   The About page shipped with no rules of its own, so the portrait rendered at
   its natural 720px and the commitments section was a heading, a paragraph and a
   button stranded in 200px of nothing. These are ordinary section rules in the
   same house style as .agenda-grid and .featured-slide. */
.about-grid{display:grid;grid-template-columns:minmax(0,.85fr) minmax(0,1fr);gap:48px;align-items:start}
.about-figure{margin:0}
.about-portrait{display:block;width:100%;height:auto;aspect-ratio:6/5;object-fit:cover;object-position:center 18%;border:1px solid var(--line);border-radius:4px;background:var(--sky)}
.about-portrait--credit{aspect-ratio:1;object-position:center 22%;max-width:260px}
.about-figure figcaption{margin-top:11px;font-size:12px;line-height:1.5;color:var(--muted)}
.about-copy h2{font-family:Georgia,serif;font-size:clamp(1.7rem,2.7vw,2.6rem);font-weight:400;line-height:1.04;letter-spacing:-.03em;margin:12px 0 18px}
.about-copy p{color:var(--muted);font-size:15px;line-height:1.68;max-width:56ch}
.about-quote{margin:44px 0 0;padding:26px 0 26px 28px;border-left:3px solid var(--gold);max-width:760px}
.about-quote p{font-family:Georgia,serif;font-size:clamp(1.1rem,1.9vw,1.45rem);font-style:italic;line-height:1.42;color:var(--ink);margin:0}
.about-quote cite{display:block;margin-top:12px;font-family:inherit;font-size:12px;font-style:normal;letter-spacing:.12em;text-transform:uppercase;color:var(--gold);font-weight:700}
.about-source{margin-top:18px;font-size:12.5px;line-height:1.6;color:var(--muted);max-width:70ch}
.about-chips{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:10px;max-width:900px}
.about-chip{display:inline-flex;align-items:center;padding:11px 18px;border:1px solid var(--line);border-radius:999px;background:var(--white);color:var(--ink);font-size:13px;font-weight:600;text-decoration:none;transition:border-color .2s,transform .2s,box-shadow .2s}
.about-chip:hover{border-color:var(--gold);transform:translateY(-2px);box-shadow:0 10px 22px rgba(11,38,60,.1)}
.about-cta{margin:30px 0 0}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important;animation:none!important;transition:none!important}.reveal{opacity:1;transform:none}}
@media (max-width:1050px){.about-grid{grid-template-columns:1fr;gap:30px}.about-portrait{max-width:520px}.about-portrait--credit{max-width:190px}}
@media (max-width:1050px){.indicator-grid{grid-template-columns:repeat(2,1fr)}.featured-slide{grid-template-columns:1fr}.request-layout{grid-template-columns:1fr}.request-aside{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;padding:8px 24px}.request-aside>div{padding:20px 0;border-bottom:0}}
@media (max-width:760px){.indicator-section{padding:70px 0}.indicator-grid{grid-template-columns:1fr}.featured-section{padding:70px 0}.featured-carousel{padding:12px}.featured-toolbar{align-items:flex-start;flex-direction:column}.featured-scope-filters{width:100%}.featured-slide{padding:14px}.featured-media img{height:240px}.request-grid{grid-template-columns:1fr}.request-field-wide{grid-column:auto}.request-aside{grid-template-columns:1fr;padding:8px 20px}.request-form{padding:18px}.request-field input,.request-field select,.request-field textarea{font-size:16px}.poll-form{padding:18px}.poll-grid{grid-template-columns:1fr}.poll-bar{grid-template-columns:1fr;gap:5px}.poll-bar-track{height:12px}.poll-chart{padding:18px}.poll-controls select{min-width:0;width:100%}.poll-two{grid-template-columns:1fr;gap:18px}.poll-stats{grid-template-columns:1fr 1fr}.poll-scope{padding:16px}.poll-scope-count{margin-left:0;flex-basis:100%}}
@media (max-width:1050px){.nav{display:none}.hero-grid{grid-template-columns:1fr .8fr;gap:20px}.portrait-wrap{min-height:470px}.lga-map-layout{grid-template-columns:1fr;gap:22px}.lga-map-column{position:static}.agenda-grid{grid-template-columns:repeat(3,1fr)}.arrow-path{grid-template-columns:1fr 20px 1.4fr 20px 1.2fr 20px 1.1fr;padding:14px}}
@media (max-width:760px){.shell{width:min(100% - 28px,1240px)}.hero{min-height:auto;padding-top:112px;padding-bottom:54px}.hero-grid,.intro-grid,.governance-grid{grid-template-columns:1fr}.hero h1{font-size:clamp(3.2rem,16vw,5.5rem)}.portrait-wrap{min-height:390px;margin-top:20px}.portrait-wrap::before{width:280px;height:280px;right:4%}.portrait-wrap::after{width:320px;height:400px;right:1%}.portrait{max-height:420px}.stats-grid{grid-template-columns:1fr 1fr}.stat{padding:18px 15px;border-bottom:1px solid rgba(11,38,60,.18)}.stat:nth-child(2){border-right:0}.section{padding:70px 0}.section-head{display:block}.section-head p{margin-top:18px}.progress-path{grid-template-columns:1fr;padding:16px}.path-step{min-height:0;padding:14px 16px 24px}.path-step:not(:last-child)::after{content:"↓";right:auto;left:18px;top:auto;bottom:-14px}.arrow-head{padding:15px 16px}.arrow-path{display:block;padding:14px}.path-node{margin-bottom:10px;padding:16px}.path-arrow{padding:0;height:24px;transform:rotate(90deg)}.lga-detail{display:block}.lga-detail .detail-label{display:block;margin-bottom:12px}.governor-card img{height:340px}.agenda-grid{grid-template-columns:1fr 1fr}.source-list{grid-template-columns:1fr}.footer-inner{display:block}.deerflow{display:inline-block;margin-top:20px}}"""

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
/* The topbar row is brand + language control + menu button. At 375px the three together
   overflowed the shell by 27px and forced the whole page to scroll sideways. Tighten the
   gaps and the type rather than dropping the "Language" label, which is what makes the
   control self-describing. */
.topbar-inner{gap:10px}
.brand{gap:8px}
.lang{gap:6px}
.lang-label{font-size:9px;letter-spacing:.04em;gap:4px}
.lang button{padding:5px 7px}
.navmenu-toggle{font-size:10px;letter-spacing:.06em;padding:8px 10px}
}
"""

# Core script. Ships on EVERY page. renderFeatured and renderPollHook are seeded as
# no-ops so the page scripts can override them by assignment; setLanguage calls all three
# hooks on every page, and a ReferenceError here would kill the language toggle.
SCRIPT_CORE = r"""
const root=document.documentElement;
let currentLanguage='en';
let selectedLga='';
let renderFeatured=()=>{};
let renderPollHook=()=>{};
const renderLgaDetail=()=>{const titleEl=document.getElementById('selected-lga');if(!titleEl)return;const hintEl=document.getElementById('selected-hint');const rowsEl=document.getElementById('selected-rows');const evidenceEl=document.getElementById('selected-evidence');const promiseEl=document.getElementById('selected-promise');const resultEl=document.getElementById('selected-result');if(!evidenceEl||!promiseEl||!resultEl)return;if(!selectedLga){if(hintEl)hintEl.hidden=false;if(rowsEl)rowsEl.hidden=true;titleEl.textContent='';evidenceEl.textContent='';promiseEl.textContent='';resultEl.textContent='';return;}const btn=document.querySelector('[data-lga="'+selectedLga+'"]');if(!btn)return;const hausa=currentLanguage==='ha';titleEl.textContent=selectedLga;evidenceEl.textContent=(hausa?btn.dataset.summaryHa:btn.dataset.summary)||'—';promiseEl.textContent=(hausa?btn.dataset.promiseHa:btn.dataset.promise)||'—';resultEl.textContent=(hausa?btn.dataset.resultHa:btn.dataset.result)||'—';if(hintEl)hintEl.hidden=true;if(rowsEl)rowsEl.hidden=false;};
const LANGUAGE_KEY='apm-lang';
const readStoredLanguage=()=>{try{const stored=window.localStorage.getItem(LANGUAGE_KEY);return stored==='ha'||stored==='en'?stored:null;}catch(error){return null;}};
const storeLanguage=(lang)=>{try{window.localStorage.setItem(LANGUAGE_KEY,lang);}catch(error){/* blocked storage: the toggle still works for this page */}};
const setLanguage=(lang,persist=true)=>{currentLanguage=lang;root.lang=lang;document.querySelectorAll('[data-en][data-ha]').forEach(el=>{if(el.matches('[data-request-confirmation]')&&el.dataset.trackingId)return;el.textContent=el.dataset[lang]||el.dataset.en});document.querySelectorAll('img[data-alt-en][data-alt-ha]').forEach(el=>{el.alt=el.dataset[lang==='ha'?'altHa':'altEn']||el.alt;});document.querySelectorAll('[data-aria-label-en][data-aria-label-ha]').forEach(el=>{el.setAttribute('aria-label',lang==='ha'?el.dataset.ariaLabelHa:el.dataset.ariaLabelEn)});document.querySelectorAll('[data-lang]').forEach(btn=>{const active=btn.dataset.lang===lang;btn.classList.toggle('active',active);btn.setAttribute('aria-pressed',String(active));});renderLgaDetail();renderFeatured();renderPollHook();const confirmation=document.querySelector('[data-request-confirmation]');if(confirmation&&confirmation.dataset.trackingId&&!confirmation.hidden)confirmation.textContent=(currentLanguage==='ha'?'An karɓi buƙatar. ID na bin: ':'Request received. Tracking reference: ')+confirmation.dataset.trackingId+'.';if(persist)storeLanguage(lang);};
document.querySelectorAll('[data-aria-label-en][data-aria-label-ha]').forEach(el=>{el.setAttribute('aria-label',currentLanguage==='ha'?el.dataset.ariaLabelHa:el.dataset.ariaLabelEn)});
document.querySelectorAll('[data-lang]').forEach(btn=>btn.addEventListener('click',()=>setLanguage(btn.dataset.lang)));
const storedLanguage=readStoredLanguage();if(storedLanguage)setLanguage(storedLanguage,false);
document.querySelectorAll('[data-lga]').forEach(btn=>{const select=()=>{document.querySelectorAll('[data-lga]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');selectedLga=btn.dataset.lga;renderLgaDetail();if(typeof lgaSelected==='function')lgaSelected(selectedLga);};btn.addEventListener('click',select);if(btn.tagName.toLowerCase()==='path'){btn.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '||event.key==='Spacebar'){event.preventDefault();select();}});}});
"""

SCRIPT_INDEX = r"""
document.querySelectorAll('[data-filter]').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.classList.remove('active'));btn.classList.add('active');const filter=btn.dataset.filter;document.querySelectorAll('.arrow-card').forEach(card=>card.hidden=filter!=='all'&&card.dataset.sector!==filter);}));
"""

# Atlas-only. The core script owns selection: it binds every `[data-lga]` element, and the
# map paths now carry that same attribute, so the core click/keyboard handler drives the map
# with no help. All that is left here is the one thing the map cannot do for itself -- reveal
# the selected area's registration areas. `lgaSelected` is declared here and called by the
# core handler through a `typeof` guard, so pages without this script are unaffected.
ATLAS_SCRIPT = r"""
const atlasRaBlocks=Array.from(document.querySelectorAll('[data-ra-lga]'));
const lgaSelected=lga=>{atlasRaBlocks.forEach(block=>{block.hidden=block.dataset.raLga!==lga});};
"""

PAGE_NAV = (
    ("index", "Home", "Gida"),
    ("achievements", "Achievements", "Ayyuka da aka yi"),
    ("atlas", "LGA atlas", "Taswirar LGA"),
    ("poll", "Speak to us", "Yi magana da mu"),
    ("agenda", "APM agenda", "Bayan-APM"),
    ("about", "About", "Game da shi"),
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
        f'<img src="assets/brand/abdulkadir-ahmad-hammayo.png" alt="Portrait of Abdulkadir Ahmad (Hammayo)" '
        'data-alt-en="Portrait of Abdulkadir Ahmad (Hammayo)" '
        'data-alt-ha="Hotun na Abdulkadir Ahmad (Hammayo)" width="58" height="58" loading="lazy" decoding="async">'
        '</div>'
        '<div class="sponsor-body">'
        f'<span class="sponsor-label">{copy("Contributor", "Mai ba da daɗi")}</span>'
        f'<span class="sponsor-name">{copy("Abdulkadir Ahmad (Hammayo)", "Abdulkadir Ahmad (Hammayo)")}</span>'
        f'<span class="sponsor-contribution">{copy("Role:", "Darasi:")} <b>'
        f'{copy("A dedicated member of his campaign team.", "Memba mai ɗaukar hankali na hukumar sa.")}'
        '</b></span></div></div>'
        f'<a class="deerflow" href="https://deerflow.tech" target="_blank" rel="noopener noreferrer" '
        f'{attr("Created By Deerflow", "An ƙirƙira Deerflow")}>Created By Deerflow</a>'
        '</div></footer>')


def watermark():
    """A faint APM emblem behind the content of every page.

    Decorative and identity-only, so it is `aria-hidden` and must never be announced or
    focusable. It sits at `z-index: 1`, which paints it above the page's own section
    backgrounds but below `.topbar` (z-index 2) -- so it reads as paper texture rather than
    as an overlay sitting on top of the navigation. `pointer-events: none` keeps every click
    on the page, including the map shapes, landing on the real control underneath.

    ⚠️ This reuses the already-approved `apm-emblem.png`, so no new asset and no new rights
    are introduced -- but it does make that emblem far more prominent, and its rights record
    is still unratified. See `HANDOFF.md` §21.
    """
    return (
        '<div class="watermark" aria-hidden="true">'
        '<img src="assets/brand/apm-emblem.png" alt="" width="274" height="314" '
        'loading="eager" decoding="async">'
        "</div>"
    )


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
        f'{watermark()}\n'
        f'{body}\n'
        f'{site_footer(built)}\n'
        '<script>' + SCRIPT_CORE + scripts + '</script>\n'
        '</body>\n</html>\n'
    )

# ---------------------------------------------------------------------------
# Page bodies
# ---------------------------------------------------------------------------

def _nav_cards():
    # One row per subpage. This list was written when there were five and About was
    # appended to PAGE_NAV without being added here, so the home page advertised five
    # pages while the nav linked to six and the site shipped seven. Derive the count in the
    # heading from this list rather than writing a number beside it.
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
        ("about", "05", "About", "Game da shi",
         "The candidate's record, his own words, and who built this site.",
         "Karautu da mai tambaya, kalmar kansa, da wanda ya gina wannan shafi."),
        ("sources", "06", "Sources", "Bayane",
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
    return '<div class="nav-cards">' + "".join(items) + "</div>", len(cards)


# The heading beside the page cards used to read "Five pages, one record." as a literal,
# written when there were five cards. Adding About to the nav without adding it here left
# the home page advertising fewer pages than the site had -- so the number is derived.
PAGE_COUNT_WORDS = {
    1: ("One page", "Shafi daya"),
    2: ("Two pages", "Shafi biyu"),
    3: ("Three pages", "Shafi uku"),
    4: ("Four pages", "Shafi hudu"),
    5: ("Five pages", "Shafi biyar"),
    6: ("Six pages", "Shafi shida"),
    7: ("Seven pages", "Shafi bakwai"),
    8: ("Eight pages", "Shafi takwas"),
    9: ("Nine pages", "Shafi bakwai"),
    10: ("Ten pages", "Shafi shina"),
}


def page_count_heading(count: int) -> str:
    english, hausa = PAGE_COUNT_WORDS.get(count, (f"{count} pages", f"Shafi {count}"))
    return copy(f"{english}, one record.", f"{hausa}, rubutanci daya.")


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

    nav_cards_html, nav_card_count = _nav_cards()

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
        + f'<div class="eyebrow">{copy("Go deeper", "Tafi ciki")}</div>'
        + f'<h2>{page_count_heading(nav_card_count)}</h2></div>'
        + f'<p>{copy("Every page keeps its own sources. Nothing here is a private poll.", "Kowane shafi yana da sauro shi. Babu komi a ciki da yake private poll.")}</p>'
        + '</div>' + nav_cards_html + '</div></section>',
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
    paths = load_lga_paths()
    validate_lga_paths(paths, ctx["lga_rows"])
    section = (
        '<section class="section lga-section" id="atlas"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("20 local government areas", "LGA 20")}</div>'
        f'<h2>{copy("A 20-LGA evidence queue for Bauchi.", "Bita na bayanai ga LGA 20 a Bauchi.")}</h2></div>'
        f'<p>{copy("All 20 LGAs have one curated source-backed evidence row. This is a starting evidence model, not comprehensive sector coverage for every community.", "Yanzu dukan LGA 20 suna da jimayi na bayanai mai goyon bayan sauro. Wannan ba cikakken bayanan kowane bangare ba.")}</p>'
        '</div><div class="lga-map-layout">'
        '<div class="lga-map-column">' + lga_map_figure(paths, ctx["lga_rows"], ctx["sources"])
        + lga_map_legend(ctx["lga_rows"]) + "</div>"
        '<div class="lga-panel">'
        '<div class="lga-detail" id="lga-detail">'
        '<div class="lga-detail-head">'
        f'<div class="detail-label">{copy("Selected area", "Wanda za zaɓi")}</div>'
        '<h3 id="selected-lga"></h3>'
        '<p id="selected-hint" data-en="Select an area on the map to read what is recorded for it. The first public records are tracked as statewide progress while LGA-specific project evidence is verified." '
        'data-ha="Zaɓi wani area a taswirar don karanta abin da aka record shi. Bayanan farko ana sune a matsayin ci gaban jihada yayin da ake tabbatar da bayanan LGA.">Select an area on the map to read what is recorded for it. The first public records are tracked as statewide progress while LGA-specific project evidence is verified.</p>'
        "</div>"
        '<dl class="evidence-rows" id="selected-rows" hidden>'
        '<div class="evidence-row"><dt>' + copy("Recorded evidence", "Bayanai da aka tabbata") + '</dt>'
        '<dd id="selected-evidence"></dd></div>'
        '<div class="evidence-row"><dt>' + copy("APM commitment", "Alkawarin APM") + '</dt>'
        '<dd id="selected-promise"></dd></div>'
        '<div class="evidence-row"><dt>' + copy("Next result to measure", "Sami na gaba za auna") + '</dt>'
        '<dd id="selected-result"></dd></div>'
        "</dl>"
        f'<span class="detail-label" {attr("20 LGAs · 1 evidence model", "LGA 20 · 1 tsarin tabbaci")}>20 LGAs · 1 evidence model</span>'
        '</div>'
        + lga_ra_list(ctx["ward_rows"]) +
        '</div></div>'
        '</div></section>'
    )
    return (header + page_hero("LGA atlas", "Taswirar LGA",
                      "Twenty local government areas.", "LGA ashirin.",
                      "Every Bauchi LGA with its source-backed evidence row. Select an area on the map to read what is recorded for it.",
                      "Kowane LGA na Bauchi tare da jimayin bayanai mai goyon bayan sauro. Zaɓi wani area a taswirar don karanta abin da aka record shi.",
                      "LGA atlas", "Taswirar LGA")
            + '<main id="main">' + section + "</main>")


def body_poll(ctx):
    """The poll, its results, and the request form.

    Two distinct things share this page, so the headings and the disclosure have to
    keep them apart: the poll records an anonymous sector preference, while the
    request form opens a follow-up channel that can collect contact details. A visitor
    must never read one as the other.
    """
    header = subpage_open("poll")
    note = (
        '<section class="section" id="how"><div class="shell"><div class="section-head"><div>'
        f'<div class="eyebrow">{copy("Before you send", "Kafin ka aika")}</div>'
        f'<h2>{copy("What happens to this form.", "Abin da zai faru da wannan fom.")}</h2></div>'
        f'<p>{copy("The poll and the request form below are both not connected to a public endpoint yet, so nothing is sent from this build.", "Hawsar da fom na buƙatar da ke ƙasa duk ba a haɗa su da wata adireshin da za a iya amfani ba tukuna, don haka ba a tura komai daga wannan gina.")}</p>'
        '</div><div class="note-box">' + copy(
            "The poll asks for no name, phone number, email, address, exact age or voter ID. It "
            "records one sector choice, the area you live in, optional age group and gender, "
            "and an optional comment that goes with it. Areas and groups with "
            "very few answers are never published. The request form below is separate and can "
            "ask for contact details if you choose to give them. Any confirmation reference on "
            "either form is a generated tracking reference, not a voter ID.",
            "Hawsar ba ta nemi suna, l waya, imel, adireshi, shekaru kuma daidai ko ID na zabb'ar masu "
            "zayyawa ba. Tana yin rikodin zaɓi na sector daya, wurin da kake, shekaru da "
            "jinsi da za ka zaɓi, da sharhi na zaɓi da ke tare da ita. Wurare da "
            "mukulli da ke da amsa kaɗan ba a wallafa su ba. Fom na buƙatar da ke ƙasa shi dabewa "
            "ne, yana iya nemi bayanan hulɗe idan ka zaɓi su bayar. Kowane ID na tabbaci a "
            "koɗa cikin sunu ID na bin ne, ba ID na zabb'ar masu zayyawa ba.")
        + '</div></div></section>')
    return (header + page_hero("Speak to us", "Yi magana da mu",
                      "One question, and one way to ask for something.", "Ƙa tambaya daya, da hanya daya ka nemi abin da kake buƙata.",
                      "The poll records an anonymous sector priority. The request form below opens a follow-up channel for a specific need in your area. Contact details there are optional and are never shown publicly.",
                      "Hawsar tana yin rikodin fihimmanci na sector a banda su sani. Fom na buƙatar da ke ƙasa yana buɗe hanya ta binfollow-up don buƙatar daya cikin wurin da kake. Bayanan hulɗe a nan zaɓi ne kuma ba a nuna su a fili ba.",
                      "Speak to us", "Yi magana da mu")
            + '<main id="main">' + ctx["poll_section"] + ctx["poll_results"]
            + ctx["request_section"] + note + "</main>")


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
            f'<article class="agenda-card" id="promise-{esc(sector)}"><div><span class="agenda-no">0{idx}</span>'
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


def body_about(ctx):
    """The About page.

    Prose, not data: every sentence here is the owner's, drafted with them and confirmed
    by them, and the source register carries the campaign materials it comes from. It states
    nothing that is not on a registered source, and it links to the agenda rather than
    repeating it -- `agenda.html` is where the five commitments live, with their source
    links, and a second copy would be a second thing to drift.
    """
    header = subpage_open("about")
    hero = page_hero(
        "About the candidate", "Game da mai tambaya",
        "The man behind the movement.", "Mutumin da ke bayan aikin ci gabansu.",
        "Dr. Yakubu Adamu has spent his working life inside Bauchi\u2019s economy \u2014 "
        "first in the banks, then in the state treasury, now in the service of all twenty "
        "local government areas.",
        "Dr. Yakubu Adamu ya yi rayuwar aiki cikin sauro Bauchi \u2014 farkon da bangare, "
        "sannan da kaban kasa, yanzu da hidima ga duk lga ashiru.",
        "About", "Game da shi")

    story = (
        '<section class="section" id="who"><div class="shell">'
        '<div class="about-grid">'
        '<figure class="about-figure">'
        '<img class="about-portrait" src="assets/brand/yakubu-adamu-single.png" '
        'alt="Portrait of Dr. Yakubu Adamu" '
        'data-alt-en="Portrait of Dr. Yakubu Adamu" '
        'data-alt-ha="Hotun na Dr. Yakubu Adamu" '
        'width="720" height="600" loading="eager" decoding="async">'
        '<figcaption>' + copy(
            "Dr. Yakubu Adamu, APM candidate for Bauchi State Governor.",
            "Dr. Yakubu Adamu, mai neman mukamu na APM don Babban Sarkin Bauchi.")
        + '</figcaption></figure>'
        '<div class="about-copy">'
        + f'<div class="eyebrow">{copy("Who he is", "Yawan shi")}</div>'
        + f'<h2>{copy("A career built inside the Bauchi economy.", "Karautu da aka gina a cikin sauro Bauchi.")}</h2>'
        + '<p>' + copy(
            "Born and raised in Bauchi, Dr. Yakubu Adamu built his career in financial "
            "services before he entered public office. He held senior roles at City "
            "Monument Bank and Skye Bank, led the public sector team for the North-East at "
            "Polaris Bank, and served as Commissioner for Finance and Economic Development "
            "in Bauchi State \u2014 the office that touches every naira the state collects "
            "and every naira it spends.",
            "An girmama shi a Bauchi kuma ya girma a nan, Dr. Yakubu Adamu ya gina karautinsa a "
            "fihirar hankali kafin ya shiga aiki a sectorar hukumu. Ya riƙe muhimman riga a "
            "City Monument Bank da Skye Bank, ya jagoranta karkashin ruwa na ƙasa da Arewa "
            "a Polaris Bank, kuma ya yi aiki a matsayin Sarkin Kudi da Ci gabar Hasken "
            "Bauchi \u2014 kantin da ke tare da kowane kudi da jihar ke tara da kowane kudi "
            "da ke yi amfani.")
        + '</p><p>' + copy(
            "He was affirmed as the Allied Peoples Movement\u2019s candidate for the 2027 "
            "Bauchi governorship at Government House in May 2026, with Mahmood Babamaji "
            "Abubakar as his running mate, on a platform of continuity, internal party "
            "democracy and an issue-based campaign.",
            "An tabbatar da shi a matsayin mai neman mukamu na Allied Peoples Movement na "
            "2027 a Government House a cikin Mayu 2026, tare da Mahmood Babamaji Abubakar a "
            "matsayin abokin harkinsa, kan wanda ke ciki ci gaba da kowane, democracyar "
            "cikin bangare da gaggawa da ke mayar da hankali a kan batun.")
        + '</p></div></div>'
        '<blockquote class="about-quote"><p>'
        + copy(
            "Good people of Bauchi, I stand before you not just as a candidate, but as a "
            "partner in our shared journey toward a more prosperous future.",
            "Mutane masu ardata na Bauchi, ina tsaye a gabanku ba don ina mai neman "
            "mukamu kawai ba, amma don ina kashewa da ku a cikin tafiarmu na zuciya zuwa "
            "ci gabar da rayuwa mai kyau.")
        + '</p><cite>' + copy("Dr. Yakubu Adamu", "Dr. Yakubu Adamu")
        + '</cite></blockquote>'
        '<p class="about-source">' + copy(
            "Words published by the candidate. The full campaign position is on the agenda "
            "page, and every commitment there carries its own source.",
            "Kalmar da aka wallafa da Dr. Yakubu Adamu. Matsayin gaggawa cikinsa yana kan "
            "shafin bayan-APM, kuma kowane alkawari a nan yana da saurinsa.")
        + '</p></div></section>')

    chips = []
    for promise in ctx["promise_rows"]:
        sector = promise.get("sector", "")
        if not sector:
            continue
        label = SECTOR_LABELS.get(sector, sector.title())
        chips.append(
            f'<li><a class="about-chip" href="agenda.html#promise-{esc(sector)}">'
            + copy(label, SECTOR_HA.get(sector, label)) + '</a></li>')

    # The count is read from the data, never written by hand. The page previously said
    # "Five commitments" over an eight-row promises file and enumerated five sectors that
    # were not the five in it -- a wrong number on the candidate's own agenda page, which is
    # the one page a voter would fact-check.
    count = len(chips)
    heading = copy(*ABOUT_COMMITMENT_COUNT.get(
        count, (f"{count} commitments.", f"{count} alkawari.")))
    commitments = (
        '<section class="section" id="commitments"><div class="shell"><div class="section-head"><div>'
        + f'<div class="eyebrow">{copy("What he is standing for", "Abin da yake tsayawa da shi")}</div>'
        + f'<h2>{heading}</h2></div>'
        + '<p>' + copy(
            "Every commitment is published in full on the agenda page, with the measure "
            "that would show whether it was delivered and the source it came from. "
            "Selecting one takes you straight to it.",
            "Kowane alkawari yana wallafa shi gaba a cikin shafin bayan-APM, tare da "
            "matakan aunawa da zai nuna ko an iska shi da kuma tushen da ya fito. "
            "Zaɓi ɗaya zai kai ka kai tsaye a kai shi.")
        + '</p></div>'
        '<ul class="about-chips">' + "".join(chips) + '</ul>'
        '<p class="about-cta"><a class="btn btn-primary" href="agenda.html">'
        + copy("Read the full agenda", "Karanta cikakken bayan-APM")
        + '</a></p></div></section>')

    contributor = (
        '<section class="section" id="contributor"><div class="shell"><div class="about-grid about-grid--credit">'
        '<figure class="about-figure about-figure--credit">'
        '<img class="about-portrait about-portrait--credit" '
        'src="assets/brand/abdulkadir-ahmad-hammayo.png" '
        'alt="Portrait of Abdulkadir Ahmad (Hammayo)" '
        'data-alt-en="Portrait of Abdulkadir Ahmad (Hammayo)" '
        'data-alt-ha="Hotun na Abdulkadir Ahmad (Hammayo)" '
        'width="512" height="512" loading="lazy" decoding="async">'
        '<figcaption>' + copy(
            "Abdulkadir Ahmad (Hammayo), contributor.",
            "Abdulkadir Ahmad (Hammayo), mai ba da da\u0199i.")
        + '</figcaption></figure>'
        '<div class="about-copy">'
        + f'<div class="eyebrow">{copy("Contributor", "Mai ba da da\u0199i")}</div>'
        + f'<h2>{copy("Built with people, not just published by them.", "An gina shi da mutane, ba da kayan da aka wallafa shi kawai ba.")}</h2>'
        + '<p>' + copy(
            "This site was built by Abdulkadir Ahmad (Hammayo) \u2014 a dedicated member of "
            "his campaign team.",
            "Wannan shafi an gina shi da Abdulkadir Ahmad (Hammayo) \u2014 memba mai \u0199aukar "
            "hankali na hukumar sa.")
        + '</p></div></div></div></section>')

    return (header + hero + story + commitments + contributor
            + '<section class="section" id="about-source-note"><div class="shell">'
            + '<p class="note-box">' + copy(
        "Sources: the candidate\u2019s own published campaign materials and Bauchi State "
        "reporting, listed on the sources page. Photographs are used with the owner\u2019s "
        "permission.",
        "Bayanan: kayan gaggawa da aka wallafa da Dr. Yakubu Adamu da kayan manyautar "
        "Bauchi, da aka lissafi a kan shafin bayane. Hotuna an yi amfani da su tare da "
        "permission daga mai shi.")
        + '</p></div></section>')

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
    "about": (body_about, "About · APM Bauchi",
             "Dr. Yakubu Adamu: career, published commitments, and who built this site."),
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
        "poll_section": poll_section(ward_rows),
        "poll_results": poll_results_section(load_poll_snapshot()),
        "ward_rows": ward_rows,
        "achievement_count": len(achievement_rows),
        "promise_count": len(promise_rows),
        "built": datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y · %H:%M UTC"),
    }


# Page scripts take the render context. The poll's script needs the registration-area
# names so a reader recognises their own area rather than seeing a bare code, and those
# rows are loaded by `load_context`, not at import time.
PAGE_SCRIPTS = {
    "index": lambda ctx: SCRIPT_INDEX,
    "achievements": lambda ctx: FEATURED_SCRIPT,
    # poll.html carries both intake forms, so it needs both scripts. A duplicate `const`
    # across two script blocks is still a single parse unit in the browser, so the
    # blocks are concatenated into one inline <script> and their top-level names are
    # kept distinct.
    "poll": lambda ctx: poll_script(ctx["ward_rows"]) + "\n" + REQUEST_SCRIPT,
    "atlas": lambda ctx: ATLAS_SCRIPT,
}


def render():
    validate_data()
    prepare_assets()
    ctx = load_context()

    written = []
    for slug, (builder, title, description) in PAGE_BUILDERS.items():
        scripts = PAGE_SCRIPTS.get(slug, lambda ctx: "")(ctx)
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
