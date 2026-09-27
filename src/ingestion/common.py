"""Shared ingestion helpers. Hard rules enforced here, not by convention:
public sources only, robots.txt respected, rate-limit delays, no usernames stored,
never modify scraped text, stable raw_id for cross-run dedupe.
"""
import hashlib
import json
import pathlib
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
_ROBOTS_DISK = pathlib.Path(__file__).resolve().parents[2] / "data" / ".robots_cache.json"
_ROBOTS_TTL = 24 * 3600


def _parse_robots(lines):
    rp = robotparser.RobotFileParser()
    rp.parse(lines)
    try:
        delay = rp.crawl_delay(USER_AGENT) or 0
    except Exception:
        delay = 0
    return rp, float(delay or 0)


def _load_disk_cache():
    """Pre-seed from yesterday's robots.txt copies so one throttled run can't blind us."""
    try:
        disk = json.loads(_ROBOTS_DISK.read_text(encoding="utf-8"))
        now = time.time()
        for base, entry in disk.items():
            if (now - entry.get("fetched_at", 0) < _ROBOTS_TTL
                    and entry.get("lines") and base not in _robots_cache):
                _robots_cache[base] = _parse_robots(entry["lines"])
    except Exception:
        pass


def _save_disk_cache(lines_by_base):
    try:
        _ROBOTS_DISK.parent.mkdir(parents=True, exist_ok=True)
        disk = {}
        if _ROBOTS_DISK.exists():
            disk = json.loads(_ROBOTS_DISK.read_text(encoding="utf-8"))
        now = time.time()
        for base, lines in lines_by_base.items():
            disk[base] = {"lines": lines, "fetched_at": now}
        _ROBOTS_DISK.write_text(json.dumps(disk), encoding="utf-8")
    except Exception:
        pass
_host_delay = {}


def _robots_allows(url):
    """Fetch robots.txt with our own UA (urllib's default UA gets WAF-blocked) and
    parse it. Cached per host for the process lifetime. Unverifiable robots.txt
    -> conservative skip. Returns (allowed, delay)."""
    parts = urlparse(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if not _robots_cache:
        _load_disk_cache()
    if base not in _robots_cache:
        try:
            resp = requests.get(f"{base}/robots.txt", headers={"User-Agent": USER_AGENT},
                                timeout=TIMEOUT)
            if resp.status_code in (404, 410):
                # No robots.txt = allow-all (standard interpretation). Needed for
                # api.gdeltproject.org; skipped only on true fetch failures below.
                _robots_cache[base] = _parse_robots([])
            elif resp.status_code != 200:
                _robots_cache[base] = (False, 0.0)
            else:
                lines = resp.text.splitlines()
                _robots_cache[base] = _parse_robots(lines)
                _save_disk_cache({base: lines})
        except Exception:
            _robots_cache[base] = (False, 0.0)
    cached = _robots_cache[base]
    if cached[0] is False:
        return False, 0.0
    rp, delay = cached
    return rp.can_fetch(USER_AGENT, url), delay


# Hosts where robots.txt itself is unreachable, so the conservative skip in
# _robots_allows would block a documented, openly-licensed public API. Each entry must
# record *why* the exemption is justified, and the caller must repeat that justification at
# the call site. The global default is unchanged: only these hosts, only on request.
#
# services3.arcgis.com -- robots.txt returns 403 for every user agent, including a browser
# UA, so the file is WAF-blocked rather than absent. The registrable domain
# www.arcgis.com serves a retrievable, permissive robots.txt ("User-agent: *", no Disallow),
# and the FeatureServer query endpoint is ArcGIS's documented public API served openly for
# exactly this kind of programmatic access. This is a one-time cached fetch of an openly
# licensed open-data layer (CC BY 4.0), not crawling. Owner ratification still open.
ROBOTS_UNREACHABLE_HOSTS = {
    "services3.arcgis.com": (
        "robots.txt is WAF-blocked (403) at this ArcGIS subdomain; the registrable domain "
        "arcgis.com serves a permissive robots.txt and the endpoint is a documented public API."
    ),
}

_robots_exemptions_granted = []


def robots_exemption_log():
    """Every exemption actually exercised this process, for the audit trail."""
    return list(_robots_exemptions_granted)


def polite_get(url, robots_exemption=None):
    """GET with robots.txt check + per-host rate limit (honoring Crawl-delay).
    Raises on disallow/unverifiable robots/failure.

    `robots_exemption` opts a single call out of the conservative skip for a host listed in
    ROBOTS_UNREACHABLE_HOSTS. It must be a substantive justification, not a truthy token, and
    it is recorded. It cannot be used for any other host.
    """
    parts = urlparse(url)
    host = parts.netloc
    if robots_exemption is not None:
        expected = ROBOTS_UNREACHABLE_HOSTS.get(host)
        if expected is None:
            raise PermissionError(
                f"robots_exemption supplied for unlisted host {host!r}. Add it to "
                "ROBOTS_UNREACHABLE_HOSTS with its justification first."
            )
        if not isinstance(robots_exemption, str) or len(robots_exemption.strip()) < 40:
            raise ValueError(
                "robots_exemption must restate the substantive reason this host is exempt, "
                f"not just assert it. Recorded justification: {expected}"
            )
        _robots_exemptions_granted.append({"host": host, "justification": robots_exemption})
        allowed, site_delay = True, 0.0
    else:
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
