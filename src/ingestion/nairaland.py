"""Nairaland Politics scraper (public board only — never private groups/DMs).
Polite: robots.txt + delays via common.polite_get, board index + up to 15 topics, page 1 only.
Anonymization: the "Re: ... by USERNAME ... On DATE" byline and the Like/Share chrome are
stripped (usernames are never stored); post bodies are kept verbatim.
"""
import re

from bs4 import BeautifulSoup

from .common import make_row, polite_get

BYLINE = re.compile(r"^Re: .*?\sby\s\S+\s*(\(\s*[mf]\s*\))?:\s*\d{1,2}:\d{2}\s*(am|pm)\s*"
                    r"On\s+\w+\s+\d+\s*", re.IGNORECASE)
CHROME = re.compile(r"\s*(?:\d+\s+Likes?\s*)?(?:\d+\s+Shares?\s*)?Share\s+Copy\s+Post\b.*$",
                    re.IGNORECASE | re.DOTALL)

BOARD = "https://www.nairaland.com/politics"
MAX_TOPICS = 15
SLUG = "nairaland"


def topic_links():
    soup = BeautifulSoup(polite_get(BOARD).text, "html.parser")
    links = []
    for a in soup.select("table a"):
        href = str(a.get("href") or "")
        if "/jobs/" in href or not href.startswith("https://www.nairaland.com/"):
            continue
        if re_topic(href) and href not in links:
            links.append(href)
        if len(links) >= MAX_TOPICS:
            break
    return links


def re_topic(href):
    return bool(__import__("re").match(r"https://www\.nairaland\.com/\d+/", href))


def topic_posts(url):
    soup = BeautifulSoup(polite_get(url).text, "html.parser")
    posts = []
    for td in soup.select("td.l, div.post-body, td.post"):
        text = td.get_text(" ", strip=True)
        if len(text) > 40:
            posts.append(clean(text))
    if not posts:  # fallback: long paragraphs on the page
        for p in soup.select("p"):
            text = p.get_text(" ", strip=True)
            if len(text) > 120:
                posts.append(clean(text))
    return posts


def clean(text):
    text = BYLINE.sub("", text)
    text = CHROME.sub("", text).strip()
    return text


def scrape(date_scraped):
    rows = []
    for link in topic_links():
        try:
            for text in topic_posts(link):
                row = make_row(SLUG, text, link, date_scraped)
                if row:
                    rows.append(row)
        except Exception as exc:
            print(f"nairaland: skip {link}: {exc}")
    return rows
