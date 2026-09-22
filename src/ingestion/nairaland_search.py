"""Nairaland targeted search (complements the front-page board sweep).
Runs a fixed query list (Bauchi, candidate, party, LGA names) against Nairaland's
public search, fetches matching topics, and extracts posts. Same rules: public only,
robots + delays via common, bylines stripped, bodies verbatim.
"""
import re
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from .common import make_row, polite_get
from .nairaland import clean, topic_posts

SLUG = "nairaland_search"
QUERIES = ["bauchi", "yakubu adamu", "apm bauchi", "apm", "pdp bauchi", "apc bauchi",
           "ningi", "misau", "azare", "katagum", "toro", "dass", "gamawa", "darazo",
           "jamaare", "kirfi", "shira", "warji", "zaki", "dambam", "bogoro", "giade",
           "ganjuwa", "alkaleri", "tafawa balewa", "itas gadau"]
TOPIC_RE = re.compile(r"https://www\.nairaland\.com/\d+/")


def search_topics(query):
    url = f"https://www.nairaland.com/search?q={quote_plus(query)}"
    soup = BeautifulSoup(polite_get(url).text, "html.parser")
    links = []
    for a in soup.select("a"):
        href = str(a.get("href") or "")
        if TOPIC_RE.match(href) and href not in links:
            links.append(href.split("#")[0])
    return links


def scrape(date_scraped):
    seen_topics = set()
    rows = []
    for query in QUERIES:
        try:
            links = search_topics(query)
        except Exception as exc:
            print(f"nl_search: skip query {query!r}: {exc}")
            continue
        for link in links:
            if link in seen_topics:
                continue
            seen_topics.add(link)
            try:
                for text in topic_posts(link):
                    row = make_row(SLUG, text, link, date_scraped)
                    if row:
                        rows.append(row)
            except Exception as exc:
                print(f"nl_search: skip {link}: {exc}")
    print(f"nl_search: {len(seen_topics)} topics from {len(QUERIES)} queries")
    return rows
