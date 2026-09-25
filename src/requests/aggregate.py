"""Pure, privacy-safe aggregation for private request records.

    The public snapshot is built from a fixed projection containing only approved
    LGA and category values, counts, and timestamps. ``aggregate_requests`` keeps
    minimal counter metadata under ``_audit`` for operational review; callers must
    use ``build_public_snapshot`` before serialising a public result. The current
    small-count threshold applies only to hypothetical ward-level output; no ward
    cells are published.

"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from .validation import ALLOWED_CATEGORIES, RequestValidationError, validate_category


BAUCHI_LGAS = (
    "Alkaleri",
    "Bauchi",
    "Bogoro",
    "Dambam",
    "Darazo",
    "Dass",
    "Gamawa",
    "Ganjuwa",
    "Giade",
    "Itas-Gadau",
    "Jamaare",
    "Katagum",
    "Kirfi",
    "Misau",
    "Ningi",
    "Shira",
    "Tafawa-Balewa",
    "Toro",
    "Warji",
    "Zaki",
)
ALLOWED_LGAS = BAUCHI_LGAS
PUBLIC_SNAPSHOT_FIELDS = (
    "reporting_period_start",
    "reporting_period_end",
    "total_requests",
    "by_lga",
    "by_category",
    "by_lga_category",
    "generated_at",
    "small_count_threshold",
    "suppressed_ward_count",
)

_LGA_LOOKUP = {lga.casefold(): lga for lga in BAUCHI_LGAS}
_AUDIT_REASONS = (
    "invalid_record",
    "non_consented",
    "invalid_status",
    "invalid_lga",
    "invalid_category",
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


def _canonical_lga(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = " ".join(value.split())
    return _LGA_LOOKUP.get(normalized.casefold())


def _canonical_category(value: Any) -> str | None:
    try:
        return validate_category(value, ALLOWED_CATEGORIES)
    except RequestValidationError:
        return None


def _new_audit() -> dict[str, int]:
    audit = {"input_records": 0, "accepted_records": 0, "rejected_records": 0, "excluded_by_period": 0}
    audit.update({reason: 0 for reason in _AUDIT_REASONS})
    return audit


def _reject(audit: dict[str, int], reason: str) -> None:
    audit[reason] += 1
    audit["rejected_records"] += 1


def _validated_projection(record: Mapping[str, Any]) -> tuple[str, str, datetime]:
    lga = _canonical_lga(record.get("lga"))
    if lga is None:
        raise ValueError("invalid_lga")
    category = _canonical_category(record.get("category"))
    if category is None:
        raise ValueError("invalid_category")
    try:
        created_at = _parse_timestamp(record.get("created_at"), "created_at")
    except ValueError:
        raise ValueError("invalid_created_at") from None
    return lga, category, created_at


def _public_aggregate(
    *,
    valid_records: list[tuple[str, str, datetime, str | None]],
    period_start: datetime | None,
    period_end: datetime | None,
    small_count_threshold: int,
    audit: dict[str, int],
) -> dict[str, Any]:
    if period_start is not None and period_end is not None and period_start > period_end:
        raise ValueError("period_start_after_period_end")

    selected: list[tuple[str, str, datetime, str | None]] = []
    for lga, category, created_at, ward_code in valid_records:
        if period_start is not None and created_at < period_start:
            audit["excluded_by_period"] += 1
            continue
        if period_end is not None and created_at > period_end:
            audit["excluded_by_period"] += 1
            continue
        selected.append((lga, category, created_at, ward_code))

    effective_start = period_start or (
        min((item[2] for item in selected), default=None)
    )
    effective_end = period_end or (
        max((item[2] for item in selected), default=None)
    )

    lga_counts = Counter(item[0] for item in selected)
    category_counts = Counter(item[1] for item in selected)
    lga_category_counts = Counter((item[0], item[1]) for item in selected)
    ward_counts = Counter(
        (item[0], item[3])
        for item in selected
        if item[3] is not None
    )

    sorted_lgas = sorted(lga_counts, key=str.casefold)
    sorted_categories = sorted(category_counts)
    by_lga = {lga: lga_counts[lga] for lga in sorted_lgas}
    by_category = {category: category_counts[category] for category in sorted_categories}
    by_lga_category = {
        lga: {
            category: lga_category_counts[(lga, category)]
            for category in sorted_categories
            if lga_category_counts[(lga, category)]
        }
        for lga in sorted_lgas
    }

    return {
        "reporting_period_start": _format_timestamp(effective_start) if effective_start else None,
        "reporting_period_end": _format_timestamp(effective_end) if effective_end else None,
        "total_requests": len(selected),
        "by_lga": by_lga,
        "by_category": by_category,
        "by_lga_category": by_lga_category,
        "small_count_threshold": small_count_threshold,
        "suppressed_ward_count": sum(
            count < small_count_threshold for count in ward_counts.values()
        ),
        "_audit": audit,
    }


def aggregate_requests(
    records: Iterable[Mapping[str, Any]],
    period_start: str | datetime | None = None,
    period_end: str | datetime | None = None,
    small_count_threshold: int = 5,
) -> dict[str, Any]:
    """Aggregate consented, validated private records into sanitized counts.

    ``created_at`` values and optional period boundaries must be timezone-aware
    ISO-8601 timestamps.  An omitted boundary is derived from all valid records;
    when one boundary is supplied, only the other boundary is derived.  Filtering
    is inclusive at both ends.  A record missing ``created_at`` is rejected.
    Missing optional contact fields do not affect aggregation.

    Records with ``validation_status`` present must use the validated status.
    Missing ``validation_status`` is tolerated for private adapters that have
    already performed equivalent validation.  The returned ``_audit`` mapping
    contains counters only and is not part of a public snapshot.
    """

    if isinstance(small_count_threshold, bool) or not isinstance(small_count_threshold, int):
        raise ValueError("small_count_threshold_must_be_a_positive_integer")
    if small_count_threshold < 1:
        raise ValueError("small_count_threshold_must_be_a_positive_integer")

    audit = _new_audit()
    valid_records: list[tuple[str, str, datetime, str | None]] = []
    for record in records:
        audit["input_records"] += 1
        if not isinstance(record, Mapping):
            _reject(audit, "invalid_record")
            continue
        if record.get("consent") is not True:
            _reject(audit, "non_consented")
            continue
        status = record.get("validation_status")
        if status is not None and status != "validated":
            _reject(audit, "invalid_status")
            continue
        try:
            lga, category, created_at = _validated_projection(record)
        except ValueError as error:
            reason = str(error)
            if reason in _AUDIT_REASONS:
                _reject(audit, reason)
            else:
                _reject(audit, "invalid_record")
            continue

        ward_code = record.get("ward_code")
        if not isinstance(ward_code, str):
            ward_code = None
        else:
            ward_code = " ".join(ward_code.split()) or None
        valid_records.append((lga, category, created_at, ward_code))
        audit["accepted_records"] += 1

    derived_start = min((item[2] for item in valid_records), default=None)
    derived_end = max((item[2] for item in valid_records), default=None)
    normalized_start = _parse_timestamp(period_start, "period_start") if period_start is not None else derived_start
    normalized_end = _parse_timestamp(period_end, "period_end") if period_end is not None else derived_end

    return _public_aggregate(
        valid_records=valid_records,
        period_start=normalized_start,
        period_end=normalized_end,
        small_count_threshold=small_count_threshold,
        audit=audit,
    )


def build_public_snapshot(
    records: Iterable[Mapping[str, Any]],
    generated_at: str | datetime | None = None,
    small_count_threshold: int = 5,
) -> dict[str, Any]:
    """Return the fixed public projection of the request aggregate."""

    aggregate = aggregate_requests(
        records,
        small_count_threshold=small_count_threshold,
    )
    generated = _parse_timestamp(generated_at, "generated_at") if generated_at is not None else datetime.now(timezone.utc)
    return {
        "reporting_period_start": aggregate["reporting_period_start"],
        "reporting_period_end": aggregate["reporting_period_end"],
        "total_requests": aggregate["total_requests"],
        "by_lga": aggregate["by_lga"],
        "by_category": aggregate["by_category"],
        "by_lga_category": aggregate["by_lga_category"],
        "generated_at": _format_timestamp(generated),
        "small_count_threshold": aggregate["small_count_threshold"],
        "suppressed_ward_count": aggregate["suppressed_ward_count"],
    }


__all__ = [
    "ALLOWED_CATEGORIES",
    "ALLOWED_LGAS",
    "BAUCHI_LGAS",
    "PUBLIC_SNAPSHOT_FIELDS",
    "aggregate_requests",
    "build_public_snapshot",
]
