import csv
import datetime
import hashlib
import re
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from .common import LGA_KEYWORDS, polite_get

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "delivery"
SNAPSHOTS = DATA / "source_snapshots"
MANIFEST = DATA / "source_manifest.csv"
REVIEW_QUEUE = DATA / "review_queue.csv"
MAX_PAGES = 80

SEED_PAGES = [
    "https://home.bauchistate.gov.ng/news-room/",
    "https://home.bauchistate.gov.ng/news-room/page/2",
    "https://home.bauchistate.gov.ng/news-room/page/3",
    "https://home.bauchistate.gov.ng/services-dashboard/",
    "https://home.bauchistate.gov.ng/investment/",
    "https://www.bauchistate.gov.ng/financial-reports-2",
    "https://acresal.gov.ng/bauchi-state-governor-launches-acresal-project-plans-to-construct-over-100-earth-dams-across-the-state",
    "https://yakubuadamuphd.com/en",
    "https://yakubuadamuphd.com/en/about",
]

ALLOWED_DOMAINS = {
    "home.bauchistate.gov.ng",
    "www.bauchistate.gov.ng",
    "bauchistate.gov.ng",
    "acresal.gov.ng",
    "yakubuadamuphd.com",
    "apm.org.ng",
    "radionigerianortheast.gov.ng",
    "alkaleri-lga.bauchistate.gov.ng",
    "thisdaylive.com",
    "tribuneonlineng.com",
    "thesun.ng",
    "9newsng.com",
    "fsssolutions.org",
    "fmino.gov.ng",
    "insightnortheastng.net",
    "punchng.com",
    "thegazellenews.com",
    "albarkaradio.com",
    "unicef.org",
    "thenationonlineng.net",
    "fmcmisau.gov.ng",
    "unicef.org",
}

SECTOR_HINTS = {
    "health": ["health", "hospital", "maternal", "child", "malnutrition", "nutrition", "clinic"],
    "education": ["education", "school", "student", "university", "academic", "teacher", "scholarship"],
    "wash": ["water", "sanitation", "hygiene", "reservoir", "dam", "waste", "borehole"],
    "livelihoods": ["youth", "women", "job", "employment", "entrepreneur", "skills", "finance", "market"],
    "security": ["security", "police", "safety", "crime", "peace", "abduction"],
    "agriculture": ["agriculture", "farmer", "farming", "food", "irrigation", "agro", "crops"],
    "infrastructure": ["road", "transport", "power", "electricity", "infrastructure", "market"],
    "governance": ["budget", "revenue", "audit", "governance", "public service", "performance", "transparency"],
}

SKIP_TERMS = {
    "login", "privacy", "contact", "volunteer", "comment", "cookie", "search",
    "advertisement", "share", "facebook", "instagram", "youtube",
}

DATE_RE = re.compile(
    r"\b(20(?:2[3-9]|3[0-6]))[-/](\d{1,2})[-/](\d{1,2})\b|"
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20(?:2[3-9]|3[0-6]))\b|"
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20(?:2[3-9]|3[0-6]))\b",
    re.IGNORECASE,
)


def allowed_url(url):
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc in ALLOWED_DOMAINS


def normalize_url(base, href):
    if not href:
        return ""
    url, _ = urldefrag(urljoin(base, href))
    return url if allowed_url(url) else ""


def lookup_url(url):
    return (url or "").rstrip("/")


def source_seed_urls():
    path = DATA / "source_register.csv"
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return [row["url"] for row in csv.DictReader(f) if row.get("url") and allowed_url(row["url"])]


def source_ids_by_url():
    path = DATA / "source_register.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {lookup_url(row["url"]): row["source_id"] for row in csv.DictReader(f) if row.get("url") and allowed_url(row["url"])}


def existing_urls():
    if not MANIFEST.exists():
        return set()
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        return {lookup_url(row.get("url", "")) for row in csv.DictReader(f)}


def extract_title(soup):
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    title = soup.find("title")
    return title.get_text(" ", strip=True) if title else ""


def extract_text(soup):
    node = None
    for selector in [".jkit-post-content", ".entry-content", "article", "main"]:
        node = soup.select_one(selector)
        if node:
            break
    if not node:
        node = soup.body or soup
    for tag in node.find_all(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = node.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)[:16000]


def extract_date(soup, text):
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        return meta["content"][:10]
    date_node = soup.select_one(".jkit-post-date, .post-date, .entry-date, time")
    date_text = date_node.get("datetime") or date_node.get_text(" ", strip=True) if date_node else ""
    match = DATE_RE.search(date_text) or DATE_RE.search(text)
    if not match:
        return ""
    parts = [part for part in match.groups() if part]
    if len(parts) != 3:
        return ""
    months = {name.lower(): str(index).zfill(2) for index, name in enumerate(
        ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
    if parts[0].isdigit() and len(parts[0]) == 4:
        return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
    if parts[1].isdigit():
        return f"{parts[2]}-{months.get(parts[0].lower(), '00')}-{parts[1].zfill(2)}"
    return ""


def sector_hint(text):
    lowered = text.lower()
    hits = [(sum(1 for key in keys if key in lowered), sector) for sector, keys in SECTOR_HINTS.items()]
    count, sector = max(hits, default=(0, ""))
    return sector if count else ""


def lga_hint(text):
    lowered = text.lower()
    matches = []
    for lga, aliases in LGA_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(alias.lower()) + r"\b", lowered) for alias in aliases):
            matches.append(lga)
    return "|".join(matches)


def document_id(url, content_hash):
    return "delivery-" + hashlib.sha1(f"{url}|{content_hash}".encode()).hexdigest()[:12]


def make_row(url, soup, text, raw, publisher, source_id=""):
    content_hash = hashlib.sha256(raw).hexdigest()
    doc_id = document_id(url, content_hash)
    title = extract_title(soup)
    date = extract_date(soup, text)
    local_file = f"source_snapshots/{doc_id}.html"
    excerpt = re.sub(r"\s+", " ", text)[:700]
    return {
        "document_id": doc_id,
        "source_id": source_id or f"discovery-{doc_id.split('-')[-1]}",
        "publisher": publisher,
        "title": title,
        "url": url,
        "publication_date": date,
        "retrieved_date": datetime.date.today().isoformat(),
        "document_type": "public_web_page",
        "content_hash": content_hash,
        "local_file": local_file,
        "word_count": len(text.split()),
        "review_status": "needs_review",
    }, excerpt


def published_source_ids():
    path = DATA / "achievements.csv"
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as f:
        return {row.get("source_id") for row in csv.DictReader(f) if row.get("source_id")}


def candidate_row(document, excerpt, published_sources):
    reviewed = document["source_id"] in published_sources
    return {
        "candidate_id": "candidate-" + document["document_id"].split("-")[-1],
        "document_id": document["document_id"],
        "source_id": document["source_id"],
        "title": document["title"],
        "url": document["url"],
        "publication_date": document["publication_date"],
        "sector_hint": sector_hint(excerpt),
        "lga_hint": lga_hint(excerpt),
        "excerpt": excerpt,
        "review_status": "published_source" if reviewed else "needs_review",
        "review_reason": "Source supports a published achievement; verify new claims before promotion" if reviewed else "Candidate evidence record; verify achievement, actor, scale, location and outcome before publication",
        "reviewed_by": "",
        "reviewed_at": "",
        "review_notes": "",
    }


def write_csv(path, rows, fields):
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def verify_manifest():
    if not MANIFEST.exists():
        return
    with MANIFEST.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            path = ROOT / "data" / "delivery" / row["local_file"]
            if not path.exists():
                raise FileNotFoundError(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != row["content_hash"]:
                raise ValueError(f"source snapshot hash mismatch: {row['document_id']}")


def sync_source_register(documents):
    path = DATA / "source_register.csv"
    if not path.exists() or not documents:
        return
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    by_id = {row.get("source_id"): row for row in rows}
    for document in documents:
        row = by_id.get(document.get("source_id"))
        if not row:
            continue
        row["content_hash"] = document["content_hash"]
        row["retrieved_date"] = document["retrieved_date"]
        if document.get("publication_date"):
            row["publication_date"] = document["publication_date"]
    fields = ["source_id", "publisher", "source_type", "title", "url", "publication_date", "retrieved_date", "document_type", "source_grade", "usage_note", "content_hash"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def sync_published_statuses(published_sources):
    for path in [MANIFEST, REVIEW_QUEUE]:
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        changed = False
        for row in rows:
            if row.get("source_id") in published_sources and row.get("review_status") == "needs_review":
                row["review_status"] = "published_source"
                if path == REVIEW_QUEUE:
                    row["review_reason"] = "Source supports a published achievement; verify new claims before promotion"
                changed = True
        if changed:
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)


def run():
    verify_manifest()
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    source_urls = list(dict.fromkeys(source_seed_urls() + SEED_PAGES))
    registered_sources = source_ids_by_url()
    published_sources = published_source_ids()
    seen = existing_urls()
    documents = []
    candidates = []
    for url in source_urls:
        if len(seen) >= MAX_PAGES:
            break
        if lookup_url(url) in seen:
            continue
        try:
            response = polite_get(url)
        except Exception as exc:
            print(f"delivery_sources: skip {url}: {exc}")
            continue
        raw = response.content
        content_hash = hashlib.sha256(raw).hexdigest()
        soup = BeautifulSoup(response.text, "html.parser")
        text = extract_text(soup)
        publisher = urlparse(url).netloc
        document, excerpt = make_row(url, soup, text, raw, publisher, registered_sources.get(lookup_url(url), ""))
        document["review_status"] = "published_source" if document["source_id"] in published_sources else "needs_review"
        file_path = ROOT / "data" / "delivery" / document["local_file"]
        file_path.write_bytes(raw)
        documents.append(document)
        if document["title"] and len(text.split()) >= 35 and not any(term in document["title"].lower() for term in SKIP_TERMS):
            candidates.append(candidate_row(document, excerpt, published_sources))
        seen.add(lookup_url(url))
    if documents:
        write_csv(MANIFEST, documents, list(documents[0]))
    if candidates:
        write_csv(REVIEW_QUEUE, candidates, list(candidates[0]))
    sync_source_register(documents)
    sync_published_statuses(published_sources)
    print(f"delivery_sources: archived {len(documents)} new pages, queued {len(candidates)} review candidates")


if __name__ == "__main__":
    run()
