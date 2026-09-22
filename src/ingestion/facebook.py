"""Public Facebook pages — TOKEN-GATED. Without FB_PAGE_TOKEN in the environment this
module logs a skip and returns []. Public pages only; never private groups or DMs.
To enable: set FB_PAGE_TOKEN (a valid Graph API token with pages_read_engagement) and
list page IDs in FB_PAGES (comma-separated). Usernames are never stored.
"""
import os

import requests

SLUG = "facebook"


def scrape(date_scraped):
    token = os.environ.get("FB_PAGE_TOKEN", "")
    pages = [p.strip() for p in os.environ.get("FB_PAGES", "").split(",") if p.strip()]
    if not token or not pages:
        print("facebook: skipped (FB_PAGE_TOKEN/FB_PAGES not set)")
        return []
    from .common import TIMEOUT, USER_AGENT, lga_keyword_match, make_raw_id
    rows = []
    for page in pages:
        try:
            resp = requests.get(
                f"https://graph.facebook.com/v19.0/{page}/posts",
                params={"fields": "message,created_time,permalink_url",
                        "limit": 25, "access_token": token},
                headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT)
            resp.raise_for_status()
            for post in resp.json().get("data", []):
                text = (post.get("message") or "").strip()
                if not text:
                    continue
                url = post.get("permalink_url", "")
                rows.append({
                    "raw_id": make_raw_id(f"{SLUG}_{page}", url or text,
                                          text),
                    "source": f"{SLUG}_{page}", "date_scraped": date_scraped,
                    "text": text, "url": url,
                    "lga_keyword_match": lga_keyword_match(text)})
        except Exception as exc:
            print(f"facebook: skip page {page}: {exc}")
    return rows
