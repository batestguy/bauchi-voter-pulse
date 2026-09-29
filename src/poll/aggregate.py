"""Pure, privacy-safe tallying for anonymous poll responses.

The public snapshot is built from a fixed projection containing only approved sector
values, counts, and timestamps. ``tally_poll_responses`` keeps minimal counter metadata
under ``_audit`` for operational review; callers must use ``build_public_snapshot``
before serialising a public result.

Two rules here are deliberately conservative, and both exist because a published poll
number is a claim about what people want:

1. **Q2 never moves a number.** ``tally_poll_responses`` reads ``sector`` only. The
   ``comment`` field is not consulted, not counted, not bucketed and not exposed in the
   audit counters. A comment is a comment.
2. **An empty poll renders as empty, never as zeros.** With no responses,
   ``build_public_snapshot`` returns ``total_responses: 0`` and an empty ``by_sector``,
   and the page renders "no responses yet" rather than a bar chart of 0%. A chart of
   zeros reads as data and is not data.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from .validation import (
    ALLOWED_SECTORS,
    DEFAULT_PERCENTAGE_FLOOR,
    PollValidationError,
    validate_percentage_floor,
    validate_sector,
)


PUBLIC_SNAPSHOT_FIELDS = (
    "schema_version",
    "reporting_period_start",
    "reporting_period_end",
    "total_responses",
    "by_sector",
    "percentage_floor",
    "generated_at",
)

_SECTOR_LOOKUP = {sector.casefold(): sector for sector in ALLOWED_SECTORS}
_AUDIT_REASONS = (
    "invalid_record",
    "non_consented",
    "invalid_sector",
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


def tally_poll_responses(
    responses: Iterable[Mapping[str, Any]],
    period_start: str | datetime | None = None,
    period_end: str | datetime | None = None,
    percentage_floor: int = DEFAULT_PERCENTAGE_FLOOR,
) -> dict[str, Any]:
    """Tally consented poll responses into sanitized counts by sector.

    Only ``sector`` and ``consent`` are read. ``comment`` is never inspected, so it
    cannot influence a published number even if it is present and non-empty.

    ``created_at`` values and optional period boundaries must be timezone-aware ISO-8601
    timestamps. A response missing ``created_at`` is rejected, because an undated
    response cannot be placed in a reporting period. An omitted boundary is derived from
    all valid responses. Filtering is inclusive at both ends.

    Returns:
        A count mapping with minimal ``_audit`` counters. ``_audit`` is not part of a
        public snapshot.
    """

    floor = validate_percentage_floor(percentage_floor)

    audit = _new_audit()
    valid: list[tuple[str, datetime]] = []
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
        try:
            created_at = _parse_timestamp(response.get("created_at"), "created_at")
        except ValueError:
            _reject(audit, "invalid_created_at")
            continue
        valid.append((sector, created_at))
        audit["accepted_records"] += 1

    if period_start is not None and period_end is not None:
        start = _parse_timestamp(period_start, "period_start")
        end = _parse_timestamp(period_end, "period_end")
        if start > end:
            raise ValueError("period_start_after_period_end")
    else:
        start = _parse_timestamp(period_start, "period_start") if period_start is not None else None
        end = _parse_timestamp(period_end, "period_end") if period_end is not None else None

    selected: list[tuple[str, datetime]] = []
    for sector, created_at in valid:
        if start is not None and created_at < start:
            audit["excluded_by_period"] += 1
            continue
        if end is not None and created_at > end:
            audit["excluded_by_period"] += 1
            continue
        selected.append((sector, created_at))

    effective_start = start or min((item[1] for item in selected), default=None)
    effective_end = end or max((item[1] for item in selected), default=None)

    counts = Counter(sector for sector, _ in selected)
    # Every configured sector is present, so the chart keeps a stable axis and a sector
    # with zero responses reads as zero rather than vanishing from the list.
    by_sector = {sector: counts.get(sector, 0) for sector in ALLOWED_SECTORS}

    return {
        "reporting_period_start": (
            _format_timestamp(effective_start) if effective_start else None
        ),
        "reporting_period_end": (
            _format_timestamp(effective_end) if effective_end else None
        ),
        "total_responses": len(selected),
        "by_sector": by_sector,
        "percentage_floor": floor,
        "_audit": audit,
    }


def build_public_snapshot(
    responses: Iterable[Mapping[str, Any]],
    generated_at: str | datetime | None = None,
    percentage_floor: int = DEFAULT_PERCENTAGE_FLOOR,
) -> dict[str, Any]:
    """Return the fixed public projection of the poll tally."""

    tally = tally_poll_responses(responses, percentage_floor=percentage_floor)
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
        "by_sector": tally["by_sector"],
        "percentage_floor": tally["percentage_floor"],
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
    "ALLOWED_SECTORS",
    "DEFAULT_PERCENTAGE_FLOOR",
    "PUBLIC_SNAPSHOT_FIELDS",
    "build_public_snapshot",
    "share_of_total",
    "tally_poll_responses",
]
