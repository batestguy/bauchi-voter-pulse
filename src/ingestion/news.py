"""News ingestion via RSS (the polite path: one request per outlet, no article crawling).
Outlets: Punch, Vanguard, Daily Post, Tribune, Daily Trust, Premium Times, RFI Hausa,
ArewaEars, Guarantee. Keeps items matching Bauchi/politics filters; text = title +
description, stored verbatim.
"""
import re
import xml.etree.ElementTree as ET

from .common import make_row, polite_get

SLUG = "news"
# thecable: robots allow but server 403s non-browser clients — dropped.
# leadership: feed endpoint times out repeatedly — dropped. bbc hausa: usable feed
# but BBC Terms explicitly forbid datasets/AI use — excluded on purpose.
FEEDS = {
    "punch": "https://punchng.com/feed/",
    "vanguard": "https://www.vanguardngr.com/feed/",
    "dailypost": "https://dailypost.ng/feed/",
    "tribune": "https://tribuneonlineng.com/feed/",
    "dailytrust": "https://dailytrust.com/feed/",
    "premiumtimes": "https://www.premiumtimesng.com/feed/",
    "rfi_hausa": "https://www.rfi.fr/ha/rss",
    # Hausa/Northern politics blogs (Bauchi-2027 coverage). arewaears has been
    # connection-failing from this host; kept so it recovers automatically.
    "arewaears": "https://arewaears.com/feed/",
    "guarantee": "https://guaranteeradio.com/feed/",
}
KEEP = re.compile(r"bauchi|yakubu\s+adamu|\bapm\b|\bpdp\b|\bapc\b|governor|election|"
                  r"lga|senator|assembly|presidency|tinubu|atiku|obi\b|"
                  r"gwamna|zabe|jam['’]?iyya|dan\s+takara|mulki|majalisa|talakawa|"
                  r"sanata|shugaba", re.IGNORECASE)
BODY_CHARS = 4000


def feed_items(xml_bytes):
    root = ET.fromstring(xml_bytes)
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title:
            yield title, desc, link


def article_body(url):
    """Full article text (one polite request). Falls back to '' on any failure —
    caller keeps the RSS title+description instead."""
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(polite_get(url).text, "html.parser")
    except Exception:
        return ""
    for sel in ["article p", ".article-body p", ".entry-content p",
                ".post-content p", "#content p"]:
        paras = [p.get_text(" ", strip=True) for p in soup.select(sel)]
        body = " ".join(p for p in paras if len(p) > 40)
        if len(body) > 300:
            return body[:BODY_CHARS]
    return ""


def scrape(date_scraped):
    rows = []
    for outlet, feed in FEEDS.items():
        try:
            resp = polite_get(feed)
        except Exception as exc:
            print(f"news: skip {outlet}: {exc}")
            continue
        try:
            items = list(feed_items(resp.content))
        except Exception as exc:
            print(f"news: parse failed {outlet}: {exc}")
            continue
        for title, desc, link in items:
            rss_text = f"{title}. {desc}" if desc else title
            if not KEEP.search(rss_text):
                continue
            body = article_body(link) if link else ""
            text = f"{title}. {body}" if body else rss_text
            row = make_row(f"{SLUG}_{outlet}", text, link, date_scraped)
            if row:
                rows.append(row)
        print(f"news: {outlet}: {len(items)} items scanned")
    return rows
