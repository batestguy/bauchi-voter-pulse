"""Shared ingestion helpers. Hard rules enforced here, not by convention:
public sources only, robots.txt respected, rate-limit delays, no usernames stored,
never modify scraped text, stable raw_id for cross-run dedupe.
"""
import hashlib
import re
import time
import urllib.robotparser as robotparser
from urllib.parse import urlparse

import requests

USER_AGENT = "BauchiVoterPulse/0.1 (public-interest research; contact: repo README)"
REQUEST_DELAY = 2.0
TIMEOUT = 20

# LGA -> lowercase aliases. lga_keyword_match is a coarse hint; Jev decides relevance.
LGA_KEYWORDS = {
    "Alkaleri": ["alkaleri", "gwana"],
    "Bauchi": ["bauchi"],
    "Bogoro": ["bogoro"],
    "Dambam": ["dambam"],
    "Darazo": ["darazo"],
    "Dass": ["dass"],
    "Gamawa": ["gamawa"],
    "Ganjuwa": ["ganjuwa", "kafin madaki"],
    "Giade": ["giade"],
    "Itas-Gadau": ["itas-gadau", "itas/gadau", "itas", "gadau"],
    "Jamaare": ["jamaare", "jama'are"],
    "Katagum": ["katagum", "azare"],
    "Kirfi": ["kirfi"],
    "Misau": ["misau"],
    "Ningi": ["ningi"],
    "Shira": ["shira"],
    "Tafawa-Balewa": ["tafawa-balewa", "tafawa balewa", "bununu"],
    "Toro": ["toro"],
    "Warji": ["warji"],
    "Zaki": ["zaki"],
}
_PATTERNS = {lga: re.compile(r"\b(" + "|".join(map(re.escape, aliases)) + r")\b",
                             re.IGNORECASE)
             for lga, aliases in LGA_KEYWORDS.items()}

_RAW_COLUMNS = ["raw_id", "source", "date_scraped", "text", "url", "lga_keyword_match"]

_last_hit = {}
_robots_cache = {}
_host_delay = {}


def _robots_allows(url):
    """Fetch robots.txt with our own UA (urllib's default UA gets WAF-blocked) and
    parse it. Cached per host for the process lifetime. Unverifiable robots.txt
    -> conservative skip. Returns (allowed, delay)."""
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base not in _robots_cache:
        try:
            resp = requests.get(f"{base}/robots.txt", headers={"User-Agent": USER_AGENT},
                                timeout=TIMEOUT)
            if resp.status_code != 200:
                _robots_cache[base] = (False, 0.0)
            else:
                rp = robotparser.RobotFileParser()
                rp.parse(resp.text.splitlines())
                try:
                    delay = rp.crawl_delay(USER_AGENT) or 0
                except Exception:
                    delay = 0
                _robots_cache[base] = (rp, float(delay or 0))
        except Exception:
            _robots_cache[base] = (False, 0.0)
    cached = _robots_cache[base]
    if cached[0] is False:
        return False, 0.0
    rp, delay = cached
    return rp.can_fetch(USER_AGENT, url), delay


def polite_get(url):
    """GET with robots.txt check + per-host rate limit (honoring Crawl-delay).
    Raises on disallow/unverifiable robots/failure."""
    parts = urlparse(url)
    host = parts.netloc
    allowed, site_delay = _robots_allows(url)
    if not allowed:
        raise PermissionError(f"robots.txt disallows or is unverifiable: {url}")
    wait = max(REQUEST_DELAY, site_delay) - (time.time() - _last_hit.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
    _last_hit[host] = time.time()
    resp.raise_for_status()
    try:
        resp.content.decode("utf-8")
        resp.encoding = "utf-8"
    except UnicodeDecodeError:
        resp.encoding = "windows-1252"  # unlabeled cp1252 pages (smart quotes etc.)
    return resp


def lga_keyword_match(text):
    return "|".join(lga for lga, pat in _PATTERNS.items() if pat.search(text))


def make_raw_id(source_slug, url, text):
    basis = f"{source_slug}|{url or ''}|{text}"
    return f"{source_slug}-{hashlib.sha1(basis.encode('utf-8')).hexdigest()[:12]}"


def make_row(source_slug, text, url, date_scraped):
    text = text.strip()
    if not text:
        return None
    return {"raw_id": make_raw_id(source_slug, url, text), "source": source_slug,
            "date_scraped": date_scraped, "text": text, "url": url or "",
            "lga_keyword_match": lga_keyword_match(text)}


def validate_row(row):
    assert list(row.keys()) == _RAW_COLUMNS, f"bad columns: {list(row.keys())}"
    assert all(isinstance(row[c], str) and row[c].strip() for c in
               ["raw_id", "source", "date_scraped", "text"]), f"empty field in {row['raw_id']}"
    # Privacy: no username/author fields may ever enter the raw schema.
    assert "author" not in row and "username" not in row
    return True
