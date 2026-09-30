"""Pure, privacy-safe tallying for poll responses, with mandatory small-cell suppression.

The public snapshot is built from a fixed projection containing only approved counts and
timestamps. ``tally_poll_responses`` keeps minimal counter metadata under ``_audit`` for
operational review; callers must use ``build_public_snapshot`` before serialising.

Four rules, and every one of them exists because a published number is a claim about
people:

1. **Q2 never moves a number.** ``tally_poll_responses`` reads ``sector`` only. The
   ``comment`` field is not consulted, not counted, not bucketed and not exposed in the
   audit counters. A comment is a comment.

2. **Small cells are withheld, not shown.** Every published cell below
   ``small_count_threshold`` is replaced with ``None``. This is not a nicety: the poll now
   records an LGA and an optional registration area, so a cell reading "1 response from
   this registration area" is *one person's registration area*. The threshold has a hard
   lower bound of 2 -- see ``validate_small_count_threshold``.

3. **A demographic is never published below LGA level.** Age band and gender breakdowns
   are computed statewide and per-LGA, never per registration area. Crossing a demographic
   with 212 registration areas would suppress almost everything anyway, and it would
   suppress it in a way that still leaks the shape of a small community.

   Note what this does and does not forbid. ``ward x sector`` is an *area* cross and is
   published, because it is the same shape as ``lga x sector`` one level down. ``lga x
   gender x sector`` and ``lga x age x sector`` are published, because LGA is the floor.
   What is refused is ``ward x gender``, ``ward x age`` and any three-way combination
   containing a registration area and a demographic. That single prohibition is the whole
   of the rule, and it is what keeps the ward-level view honest.

4. **An empty poll renders as empty, never as zeros.** With no responses the snapshot
   carries ``total_responses: 0`` and the page renders "no responses yet" rather than a
   chart of zeros. A chart of zeros reads as data and is not data.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from .validation import (
    AGE_BANDS,
    ALLOWED_SECTORS,
    BAUCHI_LGAS,
    DEFAULT_PERCENTAGE_FLOOR,
    DEFAULT_SMALL_COUNT_THRESHOLD,
    GENDER_OPTIONS,
    PollValidationError,
    validate_lga,
    validate_percentage_floor,
    validate_sector,
    validate_small_count_threshold,
)


PUBLIC_SNAPSHOT_FIELDS = (
    "schema_version",
    "reporting_period_start",
    "reporting_period_end",
    "total_responses",
    "with_area_responses",
    "with_ward_responses",
    "with_age_band",
    "with_gender",
    "by_sector",
    "by_lga",
    "by_lga_sector",
    "by_ward",
    "by_ward_sector",
    "by_lga_ward",
    "by_lga_age_band",
    "by_lga_gender",
    "by_lga_age_band_sector",
    "by_lga_gender_sector",
    "by_age_band_sector",
    "by_gender_sector",
    "percentage_floor",
    "small_count_threshold",
    "suppressed_cell_count",
    "generated_at",
)

# The combinations this module refuses to build. Kept as data rather than as prose so a
# test can assert against the list itself, and so adding a cross later means changing
# this tuple deliberately instead of by accident.
#
# A forbidden cross is any key that carries BOTH a registration area and a demographic.
# Area x sector is fine, lga x demographic x sector is fine, ward x sector is fine.
# ward x gender is not, and neither is anything built on top of it.
FORBIDDEN_CROSSINGS = (
    "ward_x_age_band",
    "ward_x_gender",
    "ward_x_sector_x_age_band",
    "ward_x_sector_x_gender",
)

_SECTOR_LOOKUP = {sector.casefold(): sector for sector in ALLOWED_SECTORS}
_AUDIT_REASONS = (
    "invalid_record",
    "non_consented",
    "invalid_sector",
    "invalid_lga",
    "invalid_ward",
    "invalid_age_band",
    "invalid_gender",
    "invalid_created_at",
)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field}_must_be_timezone_aware")
        return value.astimezone(timezone.utc)

    if not isinstance(value, str) or len(value) > 64:
        raise ValueError(f"invalid_{field}")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"invalid_{field}")
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        raise ValueError(f"invalid_{field}") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field}_must_be_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _canonical_sector(value: Any) -> str | None:
    try:
        return validate_sector(value)
    except PollValidationError:
        return None


def _canonical_lga(value: Any) -> str | None:
    try:
        return validate_lga(value)
    except PollValidationError:
        return None


def _canonical_choice(value: Any, allowed: tuple[str, ...]) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip().casefold()
    return cleaned if cleaned in allowed else ""


def _canonical_ward(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def _new_audit() -> dict[str, int]:
    audit = {
        "input_records": 0,
        "accepted_records": 0,
        "rejected_records": 0,
        "excluded_by_period": 0,
    }
    audit.update({reason: 0 for reason in _AUDIT_REASONS})
    return audit


def _reject(audit: dict[str, int], reason: str) -> None:
    audit[reason] += 1
    audit["rejected_records"] += 1


def suppress(
    counts: Mapping[str, int], threshold: int
) -> tuple[dict[str, int | None], int]:
    """Replace every cell below ``threshold`` with None, and report how many.

    A cell of **zero** is not suppressed. "Nobody in this area chose water" identifies
    nobody, and hiding it would wrongly read as "too few to say" -- which is a different
    and weaker statement. Suppression exists to protect the 1, 2, 3 and 4 cases.

    Reporting the number of suppressed cells is deliberate. Silently dropping them makes
    a sparse dataset look like a complete one, and a reader cannot tell the difference
    between "no responses here" and "too few to publish".
    """
    out: dict[str, int | None] = {}
    suppressed = 0
    for key, count in counts.items():
        if count and count < threshold:
            out[key] = None
            suppressed += 1
        else:
            out[key] = count
    return out, suppressed


def suppress_nested(tree: Any, threshold: int) -> tuple[Any, int]:
    """Recursively apply :func:`suppress`'s rule to every count leaf under ``tree``.

    The deepest map the snapshot publishes is three levels (``lga -> gender -> sector``),
    so the walk is recursive rather than fixed at one level: a cross added tomorrow gets
    the same floor applied to it by construction, instead of needing this function to be
    rewritten and re-reviewed first.

    The leaf rule is identical to :func:`suppress` and is asserted against it in the test
    suite, because a second implementation of a privacy floor is exactly the kind of thing
    that drifts. A cell of zero is published, never suppressed.

    A suppressed leaf stays a present key holding ``None``. That is deliberate and load
    bearing. Dropping the key would make "this group answered, but too few to publish"
    indistinguishable from "this group never existed", and those are different facts: the
    first is a privacy floor, the second is a gap in collection.
    """
    if isinstance(tree, Mapping):
        out: dict[Any, Any] = {}
        suppressed = 0
        for key, value in tree.items():
            child, n = suppress_nested(value, threshold)
            out[key] = child
            suppressed += n
        return out, suppressed
    if isinstance(tree, int) and not isinstance(tree, bool):
        if tree and tree < threshold:
            return None, 1
        return tree, 0
    raise TypeError("suppress_nested_reached_a_non_count_leaf")


def tally_poll_responses(
    responses: Iterable[Mapping[str, Any]],
    period_start: str | datetime | None = None,
    period_end: str | datetime | None = None,
    percentage_floor: int = DEFAULT_PERCENTAGE_FLOOR,
) -> dict[str, Any]:
    """Tally consented poll responses into counts. No suppression applied here.

    Only ``sector``, ``lga``, ``ward_code``, ``age_band``, ``gender`` and ``consent`` are
    read. ``comment`` is never inspected, so it cannot influence a published number even
    when present and non-empty.

    This function returns *raw* counts plus an ``_audit`` block. It is an internal step.
    Callers must use :func:`build_public_snapshot`, which is what applies the mandatory
    small-cell suppression. Keeping the two apart means a raw count cannot reach a
    published page by accident.
    """

    validate_percentage_floor(percentage_floor)

    audit = _new_audit()
    valid: list[tuple[str, str, str, str, str, datetime]] = []
    for response in responses:
        audit["input_records"] += 1
        if not isinstance(response, Mapping):
            _reject(audit, "invalid_record")
            continue
        if response.get("consent") is not True:
            _reject(audit, "non_consented")
            continue
        sector = _canonical_sector(response.get("sector"))
        if sector is None:
            _reject(audit, "invalid_sector")
            continue
        lga = _canonical_lga(response.get("lga"))
        if lga is None:
            _reject(audit, "invalid_lga")
            continue
        try:
            created_at = _parse_timestamp(response.get("created_at"), "created_at")
        except ValueError:
            _reject(audit, "invalid_created_at")
            continue
        ward_code = _canonical_ward(response.get("ward_code"))
        age_band = _canonical_choice(response.get("age_band"), AGE_BANDS)
        gender = _canonical_choice(response.get("gender"), GENDER_OPTIONS)
        valid.append((sector, lga, ward_code, age_band, gender, created_at))
        audit["accepted_records"] += 1

    if period_start is not None and period_end is not None:
        start = _parse_timestamp(period_start, "period_start")
        end = _parse_timestamp(period_end, "period_end")
        if start > end:
            raise ValueError("period_start_after_period_end")
    else:
        start = _parse_timestamp(period_start, "period_start") if period_start is not None else None
        end = _parse_timestamp(period_end, "period_end") if period_end is not None else None

    selected = []
    for row in valid:
        created_at = row[5]
        if start is not None and created_at < start:
            audit["excluded_by_period"] += 1
            continue
        if end is not None and created_at > end:
            audit["excluded_by_period"] += 1
            continue
        selected.append(row)

    effective_start = start or min((row[5] for row in selected), default=None)
    effective_end = end or max((row[5] for row in selected), default=None)

    sector_counts = Counter(row[0] for row in selected)
    lga_counts = Counter(row[1] for row in selected)
    lga_sector = Counter((row[1], row[0]) for row in selected)
    lga_ward = Counter((row[1], row[2]) for row in selected if row[2])
    ward_counts = Counter(row[2] for row in selected if row[2])
    lga_age = Counter((row[1], row[3]) for row in selected if row[3])
    lga_gender = Counter((row[1], row[4]) for row in selected if row[4])

    # A registration area crossed with a sector is an *area* cross, the same shape as
    # `lga_sector` one level down, and it is what makes the ward-level view useful. It
    # stops at area: no demographic is added on top of it, anywhere below.
    ward_sector = Counter((row[2], row[0]) for row in selected if row[2])

    # LGA is the floor for a demographic. These two crosses answer "what does this age
    # group want prioritised in this LGA", which is the planning question, and they are
    # the finest grain a demographic is ever published at.
    lga_age_sector = Counter((row[1], row[3], row[0]) for row in selected if row[3])
    lga_gender_sector = Counter(
        (row[1], row[4], row[0]) for row in selected if row[4]
    )

    # The same two crosses statewide. They are the demographic view most likely to hold a
    # publishable figure, because a statewide cell is 20 times larger than an LGA one, and
    # dropping them would leave the demographic lens with nothing to show until a single
    # LGA collected enough answers to clear the floor on its own.
    age_sector = Counter((row[3], row[0]) for row in selected if row[3])
    gender_sector = Counter((row[4], row[0]) for row in selected if row[4])

    sorted_lgas = sorted(lga_counts, key=str.casefold)
    sorted_sectors = sorted(sector_counts)

    def nest_by_demographic(source):
        """Group a (lga, demographic, sector) counter into lga -> demographic -> sector."""
        out: dict[str, dict[str, dict[str, int]]] = {}
        for (lga, demographic, sector), count in source.items():
            out.setdefault(lga, {}).setdefault(demographic, {})[sector] = count
        for groups in out.values():
            for demographic, sectors in list(groups.items()):
                groups[demographic] = {s: sectors[s] for s in sorted(sectors)}
        return out

    def nest_by_ward(source):
        """Group a (ward, sector) counter into ward -> sector, sectors in sorted order."""
        out: dict[str, dict[str, int]] = {}
        for (ward, sector), count in source.items():
            out.setdefault(ward, {})[sector] = count
        return {ward: {s: sectors[s] for s in sorted(sectors)} for ward, sectors in out.items()}

    def nest_flat(source):
        """Group a (demographic, sector) counter into demographic -> sector."""
        out: dict[str, dict[str, int]] = {}
        for (demographic, sector), count in source.items():
            out.setdefault(demographic, {})[sector] = count
        return {d: {s: rows[s] for s in sorted(rows)} for d, rows in out.items()}

    return {
        "reporting_period_start": (
            _format_timestamp(effective_start) if effective_start else None
        ),
        "reporting_period_end": (
            _format_timestamp(effective_end) if effective_end else None
        ),
        "total_responses": len(selected),
        "by_sector": {s: sector_counts.get(s, 0) for s in sorted_sectors},
        "by_lga": {l: lga_counts[l] for l in sorted_lgas},
        "by_lga_sector": {
            l: {s: lga_sector[(l, s)] for s in sorted_sectors if lga_sector[(l, s)]}
            for l in sorted_lgas
        },
        "by_ward": dict(ward_counts),
        "by_lga_ward": {
            l: {w: c for (lg, w), c in lga_ward.items() if lg == l}
            for l in sorted_lgas
            if any(lg == l for lg, _ in lga_ward)
        },
        "by_lga_age_band": {
            l: {b: c for (lg, b), c in lga_age.items() if lg == l}
            for l in sorted_lgas
            if any(lg == l for lg, _ in lga_age)
        },
        "by_lga_gender": {
            l: {g: c for (lg, g), c in lga_gender.items() if lg == l}
            for l in sorted_lgas
            if any(lg == l for lg, _ in lga_gender)
        },
        "by_ward_sector": nest_by_ward(ward_sector),
        "by_lga_age_band_sector": nest_by_demographic(lga_age_sector),
        "by_lga_gender_sector": nest_by_demographic(lga_gender_sector),
        "by_age_band_sector": nest_flat(age_sector),
        "by_gender_sector": nest_flat(gender_sector),
        "with_area_responses": sum(1 for row in selected if row[1]),
        "with_ward_responses": sum(1 for row in selected if row[2]),
        "with_age_band": sum(1 for row in selected if row[3]),
        "with_gender": sum(1 for row in selected if row[4]),
        "percentage_floor": percentage_floor,
        "_audit": audit,
    }


def build_public_snapshot(
    responses: Iterable[Mapping[str, Any]],
    generated_at: str | datetime | None = None,
    percentage_floor: int = DEFAULT_PERCENTAGE_FLOOR,
    small_count_threshold: int = DEFAULT_SMALL_COUNT_THRESHOLD,
) -> dict[str, Any]:
    """Return the fixed public projection, with small cells withheld.

    ``small_count_threshold`` is validated with a hard floor of 2: a threshold of 0 or 1
    would publish single respondents, which is the exact outcome the suppression exists
    to prevent, so it is refused rather than honoured.
    """
    threshold = validate_small_count_threshold(small_count_threshold)
    tally = tally_poll_responses(responses, percentage_floor=percentage_floor)

    suppressed_total = 0

    by_sector, n = suppress(tally["by_sector"], threshold)
    suppressed_total += n

    by_lga, n = suppress(tally["by_lga"], threshold)
    suppressed_total += n

    # by_ward is keyed by registration area across all LGAs. Areas are small by
    # definition, so this is the map most likely to be mostly suppressed, which is the
    # honest outcome.
    by_ward, n = suppress(tally["by_ward"], threshold)
    suppressed_total += n

    by_lga_sector = {}
    for lga, sectors in tally["by_lga_sector"].items():
        row, n = suppress(sectors, threshold)
        suppressed_total += n
        by_lga_sector[lga] = row

    by_lga_ward = {}
    for lga, wards in tally["by_lga_ward"].items():
        row, n = suppress(wards, threshold)
        suppressed_total += n
        by_lga_ward[lga] = row

    # Demographics are never crossed with registration areas. See the module docstring.
    by_lga_age_band = {}
    for lga, bands in tally["by_lga_age_band"].items():
        row, n = suppress(bands, threshold)
        suppressed_total += n
        by_lga_age_band[lga] = row

    by_lga_gender = {}
    for lga, genders in tally["by_lga_gender"].items():
        row, n = suppress(genders, threshold)
        suppressed_total += n
        by_lga_gender[lga] = row

    # The three crosses the dashboard actually reads. Each is suppressed cell by cell at
    # exactly the same floor as every other map, so adding a dimension to the UI cannot
    # quietly lower the privacy bar -- a ward-level or gender-level cell is exactly as
    # protected as a statewide one.
    by_ward_sector, n = suppress_nested(tally["by_ward_sector"], threshold)
    suppressed_total += n

    by_lga_age_band_sector, n = suppress_nested(tally["by_lga_age_band_sector"], threshold)
    suppressed_total += n

    by_lga_gender_sector, n = suppress_nested(
        tally["by_lga_gender_sector"], threshold)
    suppressed_total += n

    by_age_band_sector, n = suppress_nested(tally["by_age_band_sector"], threshold)
    suppressed_total += n

    by_gender_sector, n = suppress_nested(tally["by_gender_sector"], threshold)
    suppressed_total += n

    generated = (
        _parse_timestamp(generated_at, "generated_at")
        if generated_at is not None
        else datetime.now(timezone.utc)
    )
    return {
        "schema_version": "poll-v1",
        "reporting_period_start": tally["reporting_period_start"],
        "reporting_period_end": tally["reporting_period_end"],
        "total_responses": tally["total_responses"],
        "with_area_responses": tally["with_area_responses"],
        "with_ward_responses": tally["with_ward_responses"],
        "with_age_band": tally["with_age_band"],
        "with_gender": tally["with_gender"],
        "by_sector": by_sector,
        "by_lga": by_lga,
        "by_lga_sector": by_lga_sector,
        "by_ward": by_ward,
        "by_lga_ward": by_lga_ward,
        "by_lga_age_band": by_lga_age_band,
        "by_lga_gender": by_lga_gender,
        "by_ward_sector": by_ward_sector,
        "by_lga_age_band_sector": by_lga_age_band_sector,
        "by_lga_gender_sector": by_lga_gender_sector,
        "by_age_band_sector": by_age_band_sector,
        "by_gender_sector": by_gender_sector,
        "percentage_floor": tally["percentage_floor"],
        "small_count_threshold": threshold,
        "suppressed_cell_count": suppressed_total,
        "generated_at": _format_timestamp(generated),
    }


def share_of_total(count: int, total: int, percentage_floor: int = DEFAULT_PERCENTAGE_FLOOR) -> float:
    """Return a display share for one sector, capped below a full 100%.

    A single response must never render as "100%", because 100% reads as a unanimous
    mandate and a sample of one is not a mandate. The cap is ``100 - floor`` rather than
    a minimum share: raising a small result would invent a share the votes do not
    support, which is the opposite error. The owner can set the floor to 0 to disable it.
    """

    floor = validate_percentage_floor(percentage_floor)
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("total_must_be_a_non_negative_integer")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("count_must_be_a_non_negative_integer")
    if count > total:
        raise ValueError("count_exceeds_total")
    if total == 0:
        return 0.0
    cap = 100.0 - float(floor)
    return min((count / total) * 100.0, cap)


__all__ = [
    "AGE_BANDS",
    "ALLOWED_SECTORS",
    "BAUCHI_LGAS",
    "DEFAULT_PERCENTAGE_FLOOR",
    "DEFAULT_SMALL_COUNT_THRESHOLD",
    "FORBIDDEN_CROSSINGS",
    "GENDER_OPTIONS",
    "PUBLIC_SNAPSHOT_FIELDS",
    "build_public_snapshot",
    "share_of_total",
    "suppress",
    "suppress_nested",
    "tally_poll_responses",
]
