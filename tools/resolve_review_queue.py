"""Record the review verdict for the candidate the sources cron left pending.

The weekly `delivery-sources.yml` job appends crawled candidates to
`data/delivery/review_queue.csv` with `review_status = needs_review`, and
`test_no_pending_source_reviews` refuses to let the tree carry one. This fills the
verdict for the row that job added on 2 October 2026.

The evidence, and why the verdict is not_achievement
----------------------------------------------------
`data/delivery/source_snapshots/delivery-81c21bd81b43.html` is 296 KB of HTML that
reduces to 6,490 characters of visible text. It contains **zero** occurrences of
"Naira", "billion", "trillion" or the naira sign. What it does contain is the site's
own navigation chrome and a column of "Download Now!" links to budget documents --
the FY2026 appropriation law, the Q1 budget implementation report, the citizen
budget, and so on. The documents themselves were not captured.

So this is an index, not evidence. Promoting it would publish a source that contains
no figure and no claim, which is the failure this repository keeps guarding against.
The same shape was already reviewed as `not_achievement` on 24 September 2026
(candidate-8d01196b6724, "Navigation page listing reports and services"), and this
row is recorded the same way for consistency.

The underlying budget PDFs remain genuinely useful and are NOT dismissed by this
verdict -- they are simply not this capture. Adding them is a separate, manual step
that needs someone to fetch and read each document.

Run:  python tools/resolve_review_queue.py
"""

from __future__ import annotations

import csv
import datetime as dt
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "delivery" / "review_queue.csv"

CANDIDATE = "candidate-81c21bd81b43"
VERDICT = "not_achievement"
REASON = (
    "Navigation page indexing budget documents; the archived capture holds no "
    "figures, only 'Download Now!' links to PDFs the crawl did not retrieve"
)
REVIEWER = "opencode-review"


def main() -> int:
    # DictReader/DictWriter, never line.split(","): the excerpt column carries commas
    # inside quotes, and positional splitting shifts every column after it.
    with QUEUE.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    pending = [r for r in rows if r["review_status"].strip() == "needs_review"]
    unknown = [r["candidate_id"] for r in pending if r["candidate_id"] != CANDIDATE]
    if unknown:
        print(f"FAILED: unhandled pending candidates {unknown}")
        print("Review each one by hand, then add it here. Do not guess.")
        return 1
    if not pending:
        print("nothing pending")
        return 0

    today = dt.date.today().isoformat()
    for row in pending:
        row["review_status"] = VERDICT
        row["review_reason"] = REASON
        row["reviewed_by"] = REVIEWER
        row["reviewed_at"] = today
        row["review_notes"] = REASON
        print(f"resolved {row['candidate_id']} -> {VERDICT}")

    with QUEUE.open("w", newline="", encoding="utf-8") as handle:
        # lineterminator="\n" on purpose: csv defaults to \r\n, which rewrites all
        # 35 lines of the file on a Linux runner and buries a one-line verdict in a
        # whole-file diff. The committed file is LF apart from one embedded break.
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)

    remaining = sum(1 for r in rows if r["review_status"].strip() == "needs_review")
    print(f"rows: {len(rows)}, still pending: {remaining}")
    return 1 if remaining else 0


if __name__ == "__main__":
    raise SystemExit(main())