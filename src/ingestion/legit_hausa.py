"""Legit.ng HAUSA via sitemaps (no RSS exists). Index -> last 3 article-shards by
descending shard number (verified: higher shards hold newer URLs — shard -10 is
all-2026 content, shard -0 starts in 2016; the index itself carries no lastmod)
-> keep locs whose slug matches Bauchi/LGA/Yakubu-Adamu/APM keywords (toponyms
are shared between English and Hausa) -> fetch title+body in ONE polite request
per article, hard-capped at 36 articles/day (index + 3 shards + 36 ≈ 40 requests,
robots-clean: legit robots.txt advertises these sitemaps). All locs are
hausa.legit.ng.
"""
import re

from bs4 import BeautifulSoup

from .common import LGA_KEYWORDS, make_row, polite_get

SLUG = "legit_hausa"
INDEX = "https://hausa.legit.ng/legit/sitemap/hausa/sitemap.xml"
SITEMAP_LIMIT = 3
FETCH_CAP = 36
BODY_CHARS = 4000

_aliases = [re.escape(a) for aliases in LGA_KEYWORDS.values() for a in aliases]
KEEP = re.compile(
    r"bauchi|yakubu\s+adamu|\bapm\b|\b(?:" + "|".join(_aliases) + r")\b",
    re.IGNORECASE)


def _locs(xml_text, tag):
    return re.findall(rf"<{tag}>\s*<loc>([^<]+)</loc>(?:\s*<lastmod>([^<]+)</lastmod>)?",
                      xml_text)


def _shard_num(url):
    m = re.search(r"article-sitemap-(\d+)\.xml", url)
    return int(m.group(1)) if m else -1


def fetch_article(url):
    """One request -> title + body text; '' on any failure or thin content."""
    try:
        soup = BeautifulSoup(polite_get(url).text, "html.parser")
    except Exception:
        return ""
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    paras = [p.get_text(" ", strip=True) for p in
             soup.select("article p, .article-body p, .entry-content p, "
                         ".post-content p, #content p")]
    body = " ".join(p for p in paras if len(p) > 40)[:BODY_CHARS]
    text = f"{title}. {body}" if title and body else (title or body)
    return text if len(text) > 40 else ""


def scrape(date_scraped):
    try:
        index_xml = polite_get(INDEX).text
    except Exception as exc:
        print(f"legit_hausa: index failed: {exc}")
        return []
    maps = [loc for loc, _ in _locs(index_xml, "sitemap")]
    if not maps:
        print("legit_hausa: no sitemaps in index")
        return []
    maps.sort(key=_shard_num, reverse=True)  # higher shard = newer content
    chosen = maps[:SITEMAP_LIMIT]
    kept = []
    for sm in chosen:
        try:
            xml = polite_get(sm).text
        except Exception as exc:
            print(f"legit_hausa: skip sitemap {sm}: {exc}")
            continue
        for loc, _lastmod in _locs(xml, "url"):
            slug_text = re.sub(r"[-_/]+", " ", loc)
            if KEEP.search(slug_text):
                kept.append(loc)
    rows, fetched = [], 0
    for url in kept[:FETCH_CAP]:
        text = fetch_article(url)
        fetched += 1
        row = make_row(SLUG, text, url, date_scraped)
        if row:
            rows.append(row)
    print(f"legit_hausa: {len(kept)} slugs matched in {len(chosen)} shards, "
          f"{fetched} fetched -> {len(rows)} rows")
    return rows
