"""Bauchi State budget documents (bauchistate.gov.ng) — MONTHLY, not daily.
Lists budget PDFs, downloads new ones to data/budgets/, records a manifest CSV.
Text extraction is out of scope here (tables need manual review); the manifest's
`topics` column flags revenue/sector keywords from link titles for analysts.
Run: python -m src.ingestion.budgets
"""
import csv
import datetime
import pathlib
import re

from .common import polite_get

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUDGET_DIR = ROOT / "data" / "budgets"
MANIFEST = BUDGET_DIR / "manifest.csv"
INDEX_PAGES = ["https://bauchistate.gov.ng/budget/", "https://bauchistate.gov.ng/"]
TOPIC_HINT = re.compile(r"budget|revenue|appropriation|expenditure|sector|audit|finance",
                        re.IGNORECASE)


def main():
    BUDGET_DIR.mkdir(parents=True, exist_ok=True)
    seen = set()
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as f:
            seen = {r["url"] for r in csv.DictReader(f)}
    new = []
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("budgets: beautifulsoup4 required")
        return
    for page in INDEX_PAGES:
        try:
            soup = BeautifulSoup(polite_get(page).text, "html.parser")
        except Exception as exc:
            print(f"budgets: skip {page}: {exc}")
            continue
        for a in soup.select("a[href$='.pdf'], a[href*='.pdf']"):
            url = str(a.get("href") or "")
            if url.startswith("/"):
                url = f"https://bauchistate.gov.ng{url}"
            title = a.get_text(" ", strip=True)
            if not url.startswith("http") or url in seen:
                continue
            if not TOPIC_HINT.search(f"{title} {url}"):
                continue
            fname = re.sub(r"[^a-z0-9]+", "_", title.lower())[:60] + ".pdf"
            try:
                pdf = polite_get(url)
                (BUDGET_DIR / fname).write_bytes(pdf.content)
                new.append({"date_scraped": datetime.date.today().isoformat(),
                            "title": title, "url": url, "file": fname})
                seen.add(url)
                print(f"budgets: downloaded {fname}")
            except Exception as exc:
                print(f"budgets: skip file {url}: {exc}")
    if new:
        write_header = not MANIFEST.exists()
        with MANIFEST.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date_scraped", "title", "url", "file"])
            if write_header:
                w.writeheader()
            w.writerows(new)
    print(f"budgets: {len(new)} new documents")


if __name__ == "__main__":
    main()
