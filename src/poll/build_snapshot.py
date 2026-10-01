"""Build data/delivery/poll_snapshot.json from an exported Responses CSV.

The published dashboard is static: it reads a committed snapshot rather than calling the
endpoint, which is what keeps comments, response ids and timestamps off the public site.
That means something has to read the Sheet and write the file, and until this script
existed nothing did -- votes arrived and were stored correctly while the dashboard stayed
permanently empty.

Deliberately not automated. Reading the Sheet from a workflow needs a Google service
account committed as a repository secret, which is a real increase in attack surface on a
public repository, and the alternative -- a person exporting the tab and running this --
keeps every credential out of git entirely. At campaign volumes that is the right trade.

Usage:
    python src/poll/build_snapshot.py responses_export.csv
    python src/poll/build_snapshot.py responses_export.csv --threshold 5

The input is whatever Sheets gives you: File > Download > Comma-separated values on the
Responses tab. Header row expected, one row per accepted response.

Refuses to write a snapshot for an empty input. An empty poll is already rendered by the
page's empty state, and committing a snapshot saying zero responses would replace an
honest message with a chart of nothing.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.poll.aggregate import (  # noqa: E402
    DEFAULT_PERCENTAGE_FLOOR,
    DEFAULT_SMALL_COUNT_THRESHOLD,
    build_public_snapshot,
)

OUTPUT = ROOT / "data" / "delivery" / "poll_snapshot.json"

# The header the endpoint writes. A CSV exported from Sheets carries these names, but a
# hand-edited file may not, so they are checked before anything is counted rather than
# producing a snapshot full of zeroes that looks like a real result.
REQUIRED_COLUMNS = (
    "response_id",
    "received_at",
    "sector",
    "lga",
    "consent",
    "validation_status",
)

# The aggregator reads `created_at`, not `received_at`. The endpoint's tab header says
# `received_at` (Code.gs.template:578), so the two names differ by one letter and nothing
# upstream checks it. Passing the Sheet's column name straight through silently tallied
# zero responses and reported "counted 0" -- a snapshot of nothing, from real data. The
# rename is done here, explicitly, and asserted in the tests.
SHEET_NAME_TO_TALLY = {"received_at": "created_at"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit(f"{path} has no header row.")
        present = {name.strip() for name in reader.fieldnames if name}
        missing = [name for name in REQUIRED_COLUMNS if name not in present]
        if missing:
            raise SystemExit(
                f"{path} is missing required column(s): {', '.join(missing)}. "
                f"Found: {', '.join(sorted(present))}. Export the Responses tab itself."
            )
        rows = []
        for raw in reader:
            # Sheets pads short rows with None; normalise so the aggregator sees "".
            rows.append({(k or "").strip(): (v or "").strip() for k, v in raw.items()})
        return rows


def accepted_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep only rows the endpoint accepted, and rename the timestamp column.

    The Responses tab can also hold rows whose validation failed -- an invalid ward, a
    missing category -- because the endpoint writes the audit outcome alongside. Counting
    those would publish preferences nobody cast. The comments column is never read here,
    and never leaves this process.

    ``consent`` arrives as the Sheet's boolean or as the string "TRUE"; the aggregator
    requires the JSON boolean `True` exactly, so a CSV string would make every row look
    non-consented. Converting here is what makes the export readable at all.
    """
    kept = []
    for row in rows:
        status = row.get("validation_status", "").strip().lower()
        if status and status not in ("validated", "accepted"):
            continue
        if row.get("consent", "").strip().lower() not in ("true", "1", "yes"):
            continue
        tally_row = dict(row)
        for sheet_name, tally_name in SHEET_NAME_TO_TALLY.items():
            if sheet_name in tally_row:
                tally_row[tally_name] = tally_row.pop(sheet_name)
        kept.append(tally_row)
        kept[-1]["consent"] = True
    return kept


def main() -> int:
    # argparse expands %(...)s in help strings, so any literal % in the docstring would abort
    # argument parsing before the script ever looked at a file.
    # RawDescription keeps the usage block readable.
    parser = argparse.ArgumentParser(
        description=__doc__.replace("%", "%%"),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", type=Path,
                        help="CSV exported from the poll Responses tab")
    parser.add_argument("--threshold", type=int, default=DEFAULT_SMALL_COUNT_THRESHOLD,
                        help="small-count suppression floor (minimum 2)")
    parser.add_argument("--floor", type=int, default=DEFAULT_PERCENTAGE_FLOOR,
                        help="percentage floor, so one response is never full")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()

    if not args.csv_path.exists():
        raise SystemExit(f"{args.csv_path} does not exist.")

    raw = read_rows(args.csv_path)
    rows = accepted_rows(raw)
    skipped = len(raw) - len(rows)

    if not rows:
        print(f"no accepted responses in {args.csv_path} "
              f"({len(raw)} row(s) read, all rejected or non-consenting).")
        print("Nothing written: an empty poll renders as the page's own empty state, "
              "and a committed snapshot of zeroes would replace that with a chart of "
              "nothing.")
        return 1

    snapshot = build_public_snapshot(
        rows,
        generated_at=datetime.now(timezone.utc),
        percentage_floor=args.floor,
        small_count_threshold=args.threshold,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")

    print(f"read {len(raw)} row(s), counted {snapshot['total_responses']}"
          + (f", skipped {skipped} rejected/non-consenting" if skipped else ""))
    print(f"sectors: {len(snapshot['by_sector'])}, "
          f"LGAs: {len(snapshot['by_lga'])}, "
          f"suppressed cells: {snapshot['suppressed_cell_count']}")
    # relative_to only works for paths inside the repo, and --out is allowed anywhere.
    try:
        shown = args.out.relative_to(ROOT)
    except ValueError:
        shown = args.out
    print(f"wrote {shown}")
    print("Comments were not read and are not in the snapshot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())