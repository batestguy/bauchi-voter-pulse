"""The human-review database: what a review is allowed to say, and what counts as one.

The confidence routing rule says a row with a confidence below 0.80 waits for a human. It
does not say the human's answer then gets thrown away. This module is the part that keeps
a completed review usable, and its reason for existing is a defect that was found by
looking rather than by reading:

**160 reviews had been completed and were invisible to the pipeline.** The work sat in
`data/human_review/filled/`, `load_reviewed()` read `data/human_review/queue_*.csv`, and
every queue file was unlabelled. The feature looked finished, the tests passed, the
docstring described a merge step that did not exist, and 13 rows asserting the candidate
*was* mentioned were being discarded on every run. Nothing errored: human labour, spent,
thrown away quietly.

So three properties are enforced here, and each is a rule that used to be prose:

1. **A label outside the schema's vocabulary is refused, not written.** The reviewer can
   change what a post is, but not invent a category. A typo in `lga` used to create a
   phantom LGA row in `lga_daily.csv` and a risk band in `risk.csv` for a place that does
   not exist -- and because the aggregator groups on whatever string it is handed, nothing
   downstream would notice.

2. **`mentions` and `opposition` must be actual booleans.** The old code did
   ``str(value).lower() in ("true", "1", "yes")``, so a missing key, a typo, or the string
   ``"yes"`` silently became ``0.0``. A reviewer asserting the candidate *is* mentioned
   could therefore be read as "not mentioned" with no error anywhere -- the single worst
   failure available in this pipeline, because it removes a true positive from the counts.

3. **A review without a signature is not a review.** `data/human_review/README.md` requires
   `reviewer_label`, `reviewer_reasoning`, `reviewed_by` and `reviewed_at`, and states that
   vague reasoning is rejected. That was a document nobody could enforce. It is now a
   precondition, so an unsigned or unreasoned row stays in the queue instead of quietly
   moving a published number.

Rejected rows are never dropped silently: every one is returned as a :class:`Problem` with
its ``raw_id`` and the reason, and `aggregate.py` writes them to
`data/aggregates/review_problems.csv` so the reason a review did not land is visible.
"""

from __future__ import annotations

import csv
import json
import pathlib
from typing import Any, NamedTuple


ROOT = pathlib.Path(__file__).resolve().parents[2]
REVIEW_DIR = ROOT / "data" / "human_review"
FILLED_SUBDIR = "filled"

QUEUE_GLOB = "queue_*.csv"

# --------------------------------------------------------------------------- vocabularies
#
# These are the schema's closed lists, not free text. They mirror what the model emits in
# data/classified/*.csv and what `src/schema/jev_pulse_v3.json` declares; a review that
# disagrees with them is not a review of the same question.

SENTIMENT_LABELS = ("positive", "neutral", "negative", "not_about_candidate")
LANGUAGE_LABELS = ("english", "hausa", "mixed", "other")

# Intensity is ORDINAL. The README calls it "ordinal noise (+1 level): correct only clear
# misses, don't fine-tune levels", so the levels are kept as an ordered scale rather than
# a set, and a review may only name one of them.
INTENSITY_LEVELS = ("calm", "mild", "moderate", "strong", "very_strong")

BAUCHI_LGAS = (
    "Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
    "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi", "Misau",
    "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki",
)

# `unclear` is the fallback the schema uses when a post does not name an LGA. It is a
# legitimate label and a reviewer may assign it -- but it is not a place, so the per-LGA
# outputs must never present it as one. See `is_assigned_lga`.
UNASSIGNED_LGA = "unclear"
REVIEWED_LGA_LABELS = BAUCHI_LGAS + (UNASSIGNED_LGA,)

# The six keys a `final_label` object must carry. Exactly the six the review sheets have
# been using; anything else is a schema change that belongs in the JSON schema, not in a
# spreadsheet column.
REVIEWED_FIELDS = (
    "sentiment", "intensity", "lga", "mentions", "opposition", "language",
)

# The README's required signature. `reviewer_label` records whether the reviewer confirmed
# or overrode the model, which is the thing the weekly eval reads to tell a schema problem
# from a one-off.
SIGNATURE_FIELDS = ("reviewer_label", "reviewer_reasoning", "reviewed_by", "reviewed_at")

# "Vague reasoning ('looks wrong') is rejected." A length floor is a crude instrument, but
# it is the only checkable form of that rule, and the shortest thing that satisfies the
# rule's intent is far longer than this.
MIN_REASONING_CHARACTERS = 20


class Problem(NamedTuple):
    """One review that could not be used, and why.

    Carries no submitted text. `raw_id` is already a stable, non-identifying reference and
    the reason is a vocabulary or shape name, so this is safe to write to a CSV.
    """

    raw_id: str
    source: str
    reason: str


def is_assigned_lga(value: Any) -> bool:
    """Whether a label names one of the 20 LGAs, as opposed to the `unclear` fallback.

    `unclear` is a real label and its rows still count towards statewide figures. What it
    is not is a place, so `risk.csv`, `lga_daily.csv`, `lga_weekly.csv` and `lga_topics.csv`
    must not carry a row for it. Published alongside, an `unclear` row reads as "somewhere
    in Bauchi State is safe", which is a claim about a location made from posts that
    deliberately did not name one.
    """
    return isinstance(value, str) and value.strip() in BAUCHI_LGAS


def _review_sources() -> list[pathlib.Path]:
    """Every CSV that may hold review rows: the queues and the completed `filled/` parts.

    Both, deliberately. The queues are authoritative once a review has been merged into
    them, but until then the completed work lives in `filled/` and reading only the queues
    is precisely the defect this module exists to fix. Reading only one of the two is not a
    stricter stance, it is the bug.
    """
    sources = sorted(REVIEW_DIR.glob(QUEUE_GLOB))
    filled = REVIEW_DIR / FILLED_SUBDIR
    if filled.is_dir():
        sources.extend(sorted(filled.glob(QUEUE_GLOB)))
    return sources


def _coerce_boolean(value: Any, field: str) -> bool:
    """Require a real JSON boolean.

    Not `str(value).lower() in (...)`. That conversion is what let a typo, a missing key
    or the string "yes" read as `False`, which for `mentions` means a reviewed post that
    does reference the candidate is discarded from the counts with nothing logged.
    """
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field}_must_be_a_json_boolean")


def parse_review(
    row: dict[str, str], source: str
) -> tuple[dict[str, Any] | None, list[Problem]]:
    """Validate one queue row's `final_label` and signature.

    Returns ``(review, problems)``. ``review`` is None when the row carries no review at
    all, which is the normal state of an unfilled queue and is not a problem.
    """
    raw_id = (row.get("raw_id") or "").strip()
    if not raw_id:
        return None, []

    raw_label = (row.get("final_label") or "").strip()
    if not raw_label:
        return None, []

    def reject(reason: str) -> tuple[None, list[Problem]]:
        return None, [Problem(raw_id, source, reason)]

    try:
        parsed = json.loads(raw_label)
    except json.JSONDecodeError:
        return reject("final_label_is_not_json")
    if not isinstance(parsed, dict):
        return reject("final_label_is_not_an_object")

    missing = [field for field in REVIEWED_FIELDS if field not in parsed]
    if missing:
        return reject("final_label_missing:" + ",".join(sorted(missing)))
    unexpected = sorted(set(parsed) - set(REVIEWED_FIELDS))
    if unexpected:
        return reject("final_label_unexpected:" + ",".join(unexpected))

    problems: list[Problem] = []

    # The signature, before the values. A row nobody signed is not evidence, whatever it
    # says, so it is not worth validating the rest of.
    for field in SIGNATURE_FIELDS:
        if not (row.get(field) or "").strip():
            problems.append(Problem(raw_id, source, f"missing_signature:{field}"))
    reasoning = (row.get("reviewer_reasoning") or "").strip()
    if reasoning and len(reasoning) < MIN_REASONING_CHARACTERS:
        problems.append(Problem(
            raw_id, source, f"reasoning_too_short:{len(reasoning)}"))
    if problems:
        return None, problems

    sentiment = parsed["sentiment"]
    if sentiment not in SENTIMENT_LABELS:
        return reject(f"sentiment_not_in_vocabulary:{sentiment!r}")

    intensity = parsed["intensity"]
    if intensity not in INTENSITY_LEVELS:
        return reject(f"intensity_not_in_vocabulary:{intensity!r}")

    lga = parsed["lga"]
    if lga not in REVIEWED_LGA_LABELS:
        return reject(f"lga_not_in_vocabulary:{lga!r}")

    language = parsed["language"]
    if language not in LANGUAGE_LABELS:
        return reject(f"language_not_in_vocabulary:{language!r}")

    try:
        mentions = _coerce_boolean(parsed["mentions"], "mentions")
        opposition = _coerce_boolean(parsed["opposition"], "opposition")
    except ValueError as error:
        return reject(str(error))

    return (
        {
            "sentiment": sentiment,
            "intensity": intensity,
            "lga": lga,
            "mentions": mentions,
            "opposition": opposition,
            "language": language,
            # Carried through so a cleared row is traceable back to who decided it and why,
            # which is the whole point of the queue being a record rather than a scratchpad.
            "reviewer_label": (row.get("reviewer_label") or "").strip(),
            "reviewer_reasoning": reasoning,
            "reviewed_by": (row.get("reviewed_by") or "").strip(),
            "reviewed_at": (row.get("reviewed_at") or "").strip(),
        },
        [],
    )


def load_reviews(
    sources: list[pathlib.Path] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[Problem]]:
    """Load every usable review, keyed by `raw_id`.

    Returns ``(reviews, problems)``. A `raw_id` that appears twice with **different**
    labels is excluded and reported, rather than one silently winning: which of two
    contradictory human judgements is authoritative is a reviewer's decision, not this
    module's, and guessing would put an unreviewed label into the counts.
    """
    paths = _review_sources() if sources is None else sources
    candidates: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    problems: list[Problem] = []

    for path in paths:
        source = path.name
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                review, row_problems = parse_review(row, source)
                problems.extend(row_problems)
                if review is not None:
                    candidates.setdefault(row["raw_id"].strip(), []).append(
                        (source, review))

    reviews: dict[str, dict[str, Any]] = {}
    for raw_id, entries in candidates.items():
        distinct = {json.dumps(entry, sort_keys=True) for _source, entry in entries}
        if len(distinct) > 1:
            where = ", ".join(sorted({source for source, _ in entries}))
            problems.append(Problem(raw_id, where, "conflicting_reviews_for_same_row"))
            continue
        reviews[raw_id] = entries[-1][1]

    return reviews, problems


def merge_completed_reviews(dry_run: bool = True) -> dict[str, Any]:
    """Copy completed reviews from `filled/` back into the authoritative queue files.

    This is the step `load_reviewed()`'s old docstring promised and no code performed. Its
    purpose is to stop `filled/` from being a second source of truth: while the work sits
    there and the queues stay empty, "where did this review live?" has two answers, and
    the one the pipeline reads is the one with nothing in it.

    Three refusals, all deliberate:

    - **A queue row that already carries a verdict is never overwritten.** Two reviewers
      disagreeing is a queue question, not something a merge should decide.
    - **A signed row with no verdict is counted separately as `incomplete`.** That is a
      review somebody started and abandoned, not one that is finished. Filling in the
      verdict would mean inventing the reviewer's conclusion, and it is a different
      problem from "already done" because it is worth going back and finishing.
    - **A `filled/` row whose `raw_id` is in no queue is reported, not inserted.** It is
      either a typo or a post that was never routed for review; inventing a queue row for
      it would put something in the review record that no one ever asked to review.

    Defaults to a dry run, because this writes to files a human has been editing.
    """
    filled_dir = REVIEW_DIR / FILLED_SUBDIR
    result: dict[str, Any] = {
        "dry_run": dry_run,
        "merged": 0,
        "already_labelled": 0,
        "incomplete": 0,
        "orphaned": 0,
        "problems": [],
    }
    if not filled_dir.is_dir():
        return result

    label_columns = ("reviewer_label", "reviewer_reasoning", "final_label",
                     "reviewed_by", "reviewed_at")

    for queue_path in sorted(REVIEW_DIR.glob(QUEUE_GLOB)):
        with queue_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
        owners = {row["raw_id"].strip(): index for index, row in enumerate(rows)}

        for filled_path in sorted(filled_dir.glob(QUEUE_GLOB)):
            with filled_path.open(encoding="utf-8", newline="") as handle:
                for row in csv.DictReader(handle):
                    raw_id = (row.get("raw_id") or "").strip()
                    if not raw_id or not (row.get("final_label") or "").strip():
                        continue
                    index = owners.get(raw_id)
                    if index is None:
                        result["orphaned"] += 1
                        result["problems"].append(
                            Problem(raw_id, filled_path.name, "not_in_any_queue"))
                        continue
                    existing = rows[index]
                    if (existing.get("final_label") or "").strip():
                        result["already_labelled"] += 1
                        continue
                    if any((existing.get(col) or "").strip() for col in label_columns):
                        result["incomplete"] += 1
                        result["problems"].append(
                            Problem(raw_id, queue_path.name,
                                    "signature_present_but_no_final_label"))
                        continue
                    for col in label_columns:
                        if col in fieldnames:
                            rows[index][col] = row.get(col, "")
                    result["merged"] += 1

        if dry_run or not result["merged"]:
            continue
        with queue_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return result


__all__ = [
    "BAUCHI_LGAS",
    "INTENSITY_LEVELS",
    "LANGUAGE_LABELS",
    "MIN_REASONING_CHARACTERS",
    "REVIEWED_FIELDS",
    "REVIEWED_LGA_LABELS",
    "SENTIMENT_LABELS",
    "SIGNATURE_FIELDS",
    "UNASSIGNED_LGA",
    "Problem",
    "is_assigned_lga",
    "load_reviews",
    "merge_completed_reviews",
    "parse_review",
]
