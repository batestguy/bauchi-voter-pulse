"""News ingestion via RSS (the polite path: one request per outlet, no article crawling).
Outlets: Punch, Vanguard, Daily Post, The Cable, Tribune.
Keeps items matching Bauchi/politics filters; text = title + description, stored verbatim.
"""
import re
import xml.etree.ElementTree as ET

from .common import make_row, polite_get

SLUG = "news"
FEEDS = {
    "punch": "https://punchng.com/feed/",
    "vanguard": "https://www.vanguardngr.com/feed/",
    "dailypost": "https://dailypost.ng/feed/",
    "thecable": "https://www.thecable.ng/feed",
    "tribune": "https://tribuneonlineng.com/feed/",
}
KEEP = re.compile(r"bauchi|yakubu\s+adamu|\bapm\b|\bpdp\b|\bapc\b|governor|election|"
                  r"lga|senator|assembly|presidency|tinubu|atiku|obi\b", re.IGNORECASE)


def feed_items(xml_bytes):
    root = ET.fromstring(xml_bytes)
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title:
            yield title, desc, link


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
            text = f"{title}. {desc}" if desc else title
            if not KEEP.search(text):
                continue
            row = make_row(f"{SLUG}_{outlet}", text, link, date_scraped)
            if row:
                rows.append(row)
        print(f"news: {outlet}: {len(items)} items scanned")
    return rows
