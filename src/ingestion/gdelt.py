"""GDELT DOC 2.0 targeted discovery (keyless, free) — the APM/Bauchi precision fix.
Query-driven: pulls articles matching (Bauchi OR "Yakubu Adamu" OR APM) across global
news over a 90-day window, then keeps only Bauchi-centric titles before fetching
bodies. Adaptive date-window pagination: a window returning maxrecords (250, likely
truncated) is split in half and re-queried. >=6.5s pacing between API calls; on 429
back off 30s (rate limit observed: "one every 5 seconds"). Bodies via
common.polite_get + news.article_body; API itself also goes through polite_get.
"""
import datetime as dt
import json
import re
import time
from urllib.parse import urlencode

from requests import HTTPError

from .common import LGA_KEYWORDS, make_row, polite_get
from .news import article_body

SLUG = "gdelt"
API = "https://api.gdeltproject.org/api/v2/doc/doc"
QUERY = '(Bauchi OR "Yakubu Adamu" OR APM)'
MAXRECORDS = 250
# Observed: bursts earn a multi-minute sliding 429 regardless of the documented 5s
# spacing. Space artlist calls widely and back off long; adaptive windows keep the
# total call count low (niche query = typically 1-3 calls per run).
PACE = 90
BACKOFF = 240
LOOKBACK_DAYS = 90
MAX_BODY_FETCHES = 50

_aliases = [re.escape(a) for aliases in LGA_KEYWORDS.values() for a in aliases]
TITLE_KEEP = re.compile(
    r"bauchi|yakubu\s+adamu|\bapm\b|\b(?:" + "|".join(_aliases) + r")\b",
    re.IGNORECASE)
# Standing exclusions enforced at URL level: BBC terms forbid dataset/AI use;
# TheCable is a standing exclusion. (Leadership's exclusion is feed-endpoint-only —
# its articles reached via GDELT are allowed.)
EXCLUDE_URL = re.compile(r"bbc\.co\.uk|bbc\.com|thecable\.ng", re.IGNORECASE)

_last_api = 0.0


def _fmt(t):
    return t.strftime("%Y%m%d%H%M%S")


def _parse(stamp):
    return dt.datetime.strptime(stamp, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)


def _api_get(params):
    global _last_api
    qs = urlencode(params)
    for attempt in range(3):
        wait = PACE - (time.time() - _last_api)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = polite_get(f"{API}?{qs}")
            _last_api = time.time()
            return resp.text
        except HTTPError as exc:
            _last_api = time.time()
            status = exc.response.status_code if exc.response is not None else 0
            if status == 429 and attempt < 2:
                print(f"gdelt: 429, backoff {BACKOFF}s (attempt {attempt + 1})")
                time.sleep(BACKOFF)
                continue
            raise
    raise RuntimeError("gdelt: rate limited after retries")


def artlist(start, end):
    """Articles with seendate in [start, end); [] on empty or non-JSON (GDELT
    sometimes answers plain text, e.g. no results)."""
    text = _api_get({"query": QUERY, "mode": "artlist", "format": "json",
                     "maxrecords": str(MAXRECORDS),
                     "startdatetime": start, "enddatetime": end})
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print(f"gdelt: non-JSON for {start}-{end}: {text[:120]}")
        return []
    return data.get("articles") or []


def windowed_articles(start, end):
    """Adaptive split so no single window can silently truncate at MAXRECORDS."""
    stack = [(start, end)]
    out, seen = [], set()
    while stack:
        s, e = stack.pop()
        arts = artlist(s, e)
        if len(arts) >= MAXRECORDS and (_parse(e) - _parse(s)).total_seconds() > 86400:
            mid = _fmt(_parse(s) + (_parse(e) - _parse(s)) / 2)
            stack.append((s, mid))
            stack.append((mid, e))
            continue
        for a in arts:
            url = a.get("url") or ""
            if url and url not in seen:
                seen.add(url)
                out.append(a)
    return out


def rows_from_articles(arts, date_scraped):
    """Precision gate + body fetch for a list of GDELT article dicts."""
    matched = [a for a in arts if TITLE_KEEP.search(a.get("title") or "")]
    rows, bodies = [], 0
    for a in matched:
        title = (a.get("title") or "").strip()
        url = a.get("url") or ""
        if not url or EXCLUDE_URL.search(url):
            continue
        body = ""
        if url and bodies < MAX_BODY_FETCHES:
            body = article_body(url)
            bodies += 1
        text = f"{title}. {body}" if body else title
        row = make_row(SLUG, text, url, date_scraped)
        if row:
            rows.append(row)
    print(f"gdelt: {len(arts)} listed, {len(matched)} Bauchi-matched, "
          f"{bodies} bodies fetched -> {len(rows)} rows")
    return rows


def scrape(date_scraped):
    now = dt.datetime.now(dt.timezone.utc)
    try:
        arts = windowed_articles(_fmt(now - dt.timedelta(days=LOOKBACK_DAYS)),
                                 _fmt(now))
    except Exception as exc:
        print(f"gdelt: FAILED: {exc}")
        return []
    return rows_from_articles(arts, date_scraped)
