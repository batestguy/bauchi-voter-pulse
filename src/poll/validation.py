"""Pure validation for the public opinion poll endpoint.

This module has no Google dependencies and performs no logging, exactly like
`src/requests/validation.py`. It is intended to be called by a server adapter and is
safe to exercise directly from unit tests.

Two properties are the reason this is a separate package rather than a reuse of the
request validator, and both are load-bearing:

1. **The poll collects no PII at all.** No name, no phone, no email, no address, no ward
   code, no voter ID. `ALLOWED_PAYLOAD_FIELDS` is a strict allowlist that does not
   contain those names, so `validate_poll_response` rejects a payload carrying them
   rather than storing and ignoring them. An identity field that the validator silently
   drops is an identity field that is still on the wire and in the access log of whatever
   sits in front of the endpoint.
2. **Q2 is a comment attached to the vote, not a second question.** It is validated,
   length-capped and stored, but `tally_poll_responses` never reads it. Only `sector`
   (Q1) can move a number. A test asserts that property directly.

A `response_id` is a generated tracking reference. It is not an official voter ID and
must never be described as one.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any


SCHEMA_VERSION = "poll-v1"

# The poll's Q1 vocabulary is the request form's category vocabulary, in the same order,
# so poll results are directly comparable with the request queue instead of inventing a
# second taxonomy that cannot be cross-tabulated against the first.
ALLOWED_SECTORS = (
    "water",
    "electricity",
    "roads",
    "healthcare",
    "education",
    "jobs_agriculture",
    "security",
    "housing_environment",
    "other",
)

REQUIRED_FIELDS = ("sector", "consent")
OPTIONAL_FIELDS = ("comment",)
# Deliberately exhaustive. If a future field is wanted, it must be added here and
# reasoned about, not appended to the form and picked up automatically.
ALLOWED_PAYLOAD_FIELDS = frozenset(
    REQUIRED_FIELDS + OPTIONAL_FIELDS + ("website", "submitted_at")
)

MAX_LENGTHS = {
    "sector": 32,
    "comment": 300,
}
MAX_RESPONSE_ID_LENGTH = 40
HONEYPOT_FIELDS = ("website",)

# Q2 is capped hard because it is the field most likely to be abused and the field most
# likely to capture an identifying detail a respondent typed unprompted.
MAX_COMMENT_LENGTH = MAX_LENGTHS["comment"]

MAX_SUBMITTED_AGE = timedelta(hours=24)
MAX_SUBMITTED_CLOCK_SKEW = timedelta(minutes=5)

MIN_PERCENTAGE_FLOOR = 0
DEFAULT_PERCENTAGE_FLOOR = 10

_RESPONSE_ID_SHAPE = re.compile(r"^APM-POLL-[0-9]{4}-[0-9]{4,12}$")

# Fields that must never appear in a poll payload. Named explicitly so the rejection is
# reportable and testable, and so a future contributor sees why the field is refused.
FORBIDDEN_IDENTITY_FIELDS = (
    "name",
    "phone",
    "email",
    "address",
    "ward_code",
    "voter_id",
    "voterid",
    "registered_voter_number",
    "nin",
    "bvn",
    "phone_number",
    "full_name",
    "lga",
    "date_of_birth",
    "age",
)


class PollValidationError(ValueError):
    """A poll or validation configuration error safe to surface to an adapter.

    Error text contains only a stable code and a contract field name. Submitted values
    are never included, so an error can be logged without writing a respondent's words
    into a log file.
    """

    def __init__(self, code: str, *, field: str | None = None) -> None:
        self.code = code
        self.field = field
        message = code if field is None else f"{code}: {field}"
        super().__init__(message)


def validate_text_length(
    value: Any, field: str, *, required: bool = True
) -> str:
    """Validate one contract field's text shape and length.

    Surrounding whitespace is removed. Internal text is otherwise preserved so a
    respondent's wording is never rewritten.
    """

    max_length = MAX_LENGTHS.get(field)
    if max_length is None:
        raise PollValidationError("unsupported_validation_field", field=field)

    if value is None:
        if required:
            raise PollValidationError("invalid_type", field=field)
        return ""

    if not isinstance(value, str):
        raise PollValidationError("invalid_type", field=field)

    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise PollValidationError("control_character_rejected", field=field)

    cleaned = value.strip()
    if required and not cleaned:
        raise PollValidationError("required", field=field)
    if len(cleaned) > max_length:
        raise PollValidationError("too_long", field=field)
    return cleaned


def _configured_sector_set(sectors: Iterable[str] | None) -> frozenset[str]:
    if sectors is None:
        return frozenset(ALLOWED_SECTORS)
    if isinstance(sectors, (str, bytes)) or not isinstance(sectors, Iterable):
        raise PollValidationError("invalid_sector_configuration")

    configured: set[str] = set()
    for sector in sectors:
        if not isinstance(sector, str) or sector != sector.strip():
            raise PollValidationError("invalid_sector_configuration")
        if any(unicodedata.category(character) in {"Cc", "Cf"} for character in sector):
            raise PollValidationError("invalid_sector_configuration")
        normalized = sector.casefold()
        if normalized not in ALLOWED_SECTORS or normalized in configured:
            raise PollValidationError("invalid_sector_configuration")
        configured.add(normalized)

    if not configured:
        raise PollValidationError("invalid_sector_configuration")
    return frozenset(configured)


def is_allowed_sector(value: Any, sectors: Iterable[str] | None = None) -> bool:
    """Return whether a value is in the exact, configured sector vocabulary."""

    try:
        configured = _configured_sector_set(sectors)
    except PollValidationError:
        return False
    if not isinstance(value, str):
        return False
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        return False
    return value.strip().casefold() in configured


def validate_sector(value: Any, sectors: Iterable[str] | None = None) -> str:
    """Normalize and validate the response's single Q1 sector choice."""

    configured = _configured_sector_set(sectors)
    cleaned = validate_text_length(value, "sector")
    normalized = cleaned.casefold()
    if normalized not in configured:
        raise PollValidationError("invalid_sector", field="sector")
    return normalized


def validate_consent(value: Any) -> bool:
    """Require the JSON boolean ``true``; strings and numbers are not consent."""

    if value is not True:
        raise PollValidationError("consent_required", field="consent")
    return True


def is_honeypot_empty(value: Any) -> bool:
    """Return whether a supplied honeypot value is an empty string."""

    return isinstance(value, str) and not value.strip()


def validate_honeypot(value: Any) -> bool:
    """Reject a populated honeypot field without echoing its value."""

    if not is_honeypot_empty(value):
        raise PollValidationError("honeypot_rejected", field="website")
    return True


def validate_response_id(value: Any) -> str:
    """Validate a server-allocated, non-official tracking reference."""

    if not isinstance(value, str):
        raise PollValidationError("invalid_response_id", field="response_id")
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise PollValidationError("invalid_response_id", field="response_id")

    normalized = value.strip().upper()
    if (
        len(normalized) > MAX_RESPONSE_ID_LENGTH
        or not _RESPONSE_ID_SHAPE.fullmatch(normalized)
    ):
        raise PollValidationError("invalid_response_id", field="response_id")
    return normalized


def _normalize_aware_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise PollValidationError("timezone_required", field=field)
    if value.utcoffset() is None:
        raise PollValidationError("timezone_required", field=field)
    return value.astimezone(timezone.utc)


def _parse_submitted_at(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise PollValidationError("invalid_submitted_at", field="submitted_at")
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise PollValidationError("invalid_submitted_at", field="submitted_at")
    cleaned = value.strip()
    if not cleaned:
        raise PollValidationError("invalid_submitted_at", field="submitted_at")
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        raise PollValidationError(
            "invalid_submitted_at", field="submitted_at"
        ) from None
    return _normalize_aware_datetime(parsed, field="submitted_at")


def _format_timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def validate_percentage_floor(value: Any) -> int:
    """Validate the configurable floor that stops one vote showing as 100%."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise PollValidationError("invalid_percentage_floor", field="percentage_floor")
    if not MIN_PERCENTAGE_FLOOR <= value <= 100:
        raise PollValidationError("invalid_percentage_floor", field="percentage_floor")
    return value


def validate_poll_response(
    payload: Mapping[str, Any],
    now: datetime | None = None,
    *,
    sectors: Iterable[str] | None = None,
    response_id: str | None = None,
    response_id_generator: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Validate and normalize one anonymous poll response.

    Args:
        payload: Untrusted form data. Unknown fields are rejected, including every
            identity field named in :data:`FORBIDDEN_IDENTITY_FIELDS`.
        now: Explicit timezone-aware server time. Required when ``submitted_at`` is
            present; when supplied, its normalized value becomes ``created_at``.
        sectors: Optional server-supplied subset of :data:`ALLOWED_SECTORS`. Keyword
            only, so passing server time positionally can never be mistaken for it.
        response_id: Tracking reference already allocated by the endpoint. Clients must
            not submit it. It is not an official voter ID.
        response_id_generator: Optional zero-argument endpoint-owned generator. This
            module never allocates a sequence and requires either this callable or
            ``response_id`` before adding a reference.

    Returns:
        A new response dictionary. It does not retain the input mapping, and it never
        contains a name, phone, email, address, ward code, or voter ID.
    """

    if not isinstance(payload, Mapping):
        raise PollValidationError("invalid_payload")

    # Reject identity fields with a specific, reportable code before the generic unknown
    # field check, so a misconfigured form fails loudly and legibly instead of looking
    # like a typo.
    for forbidden in FORBIDDEN_IDENTITY_FIELDS:
        if forbidden in payload:
            raise PollValidationError("identity_field_forbidden", field=forbidden)

    configured = _configured_sector_set(sectors)

    if set(payload) - ALLOWED_PAYLOAD_FIELDS:
        raise PollValidationError("unsupported_field")
    for field in HONEYPOT_FIELDS:
        if field in payload:
            validate_honeypot(payload[field])
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise PollValidationError("required", field=field)

    consent = validate_consent(payload["consent"])
    sector = validate_sector(payload["sector"], configured)
    comment = validate_text_length(payload.get("comment"), "comment", required=False)

    normalized_now = (
        _normalize_aware_datetime(now, field="now") if now is not None else None
    )
    if "submitted_at" in payload:
        if normalized_now is None:
            raise PollValidationError(
                "explicit_now_required_for_submitted_at", field="now"
            )
        submitted_at = _parse_submitted_at(payload["submitted_at"])
        if submitted_at < normalized_now - MAX_SUBMITTED_AGE:
            raise PollValidationError("submitted_at_too_old", field="submitted_at")
        if submitted_at > normalized_now + MAX_SUBMITTED_CLOCK_SKEW:
            raise PollValidationError("submitted_at_in_future", field="submitted_at")

    if response_id is not None and response_id_generator is not None:
        raise PollValidationError("ambiguous_response_id_source", field="response_id")
    if response_id_generator is not None:
        if not callable(response_id_generator):
            raise PollValidationError(
                "invalid_response_id_generator", field="response_id"
            )
        response_id = response_id_generator()

    record: dict[str, Any] = {
        "sector": sector,
        "comment": comment,
        "consent": consent,
    }
    if normalized_now is not None:
        record["created_at"] = _format_timestamp(normalized_now)
    if response_id is not None:
        record["response_id"] = validate_response_id(response_id)
    return record


def public_projection(response: Mapping[str, Any]) -> dict[str, str]:
    """Return the fixed, non-PII projection allowed from one poll response.

    Q2 is deliberately **excluded**. It is a comment attached to a vote, and publishing
    it would turn an anonymous preference count into a public set of attributable
    statements. The public tally reads only ``sector``.
    """

    if not isinstance(response, Mapping):
        raise PollValidationError("invalid_response_record")

    projection = {"sector": validate_sector(response.get("sector"))}

    created_at = response.get("created_at")
    if created_at is not None:
        if not isinstance(created_at, str) or len(created_at) > 64:
            raise PollValidationError("invalid_created_at", field="created_at")
        if any(
            unicodedata.category(character) in {"Cc", "Cf"} for character in created_at
        ):
            raise PollValidationError("invalid_created_at", field="created_at")
        try:
            parsed = datetime.fromisoformat(created_at.strip().replace("Z", "+00:00"))
        except ValueError:
            raise PollValidationError(
                "invalid_created_at", field="created_at"
            ) from None
        projection["created_at"] = _format_timestamp(
            _normalize_aware_datetime(parsed, field="created_at")
        )
    return projection


__all__ = [
    "ALLOWED_PAYLOAD_FIELDS",
    "ALLOWED_SECTORS",
    "DEFAULT_PERCENTAGE_FLOOR",
    "FORBIDDEN_IDENTITY_FIELDS",
    "HONEYPOT_FIELDS",
    "MAX_COMMENT_LENGTH",
    "MAX_LENGTHS",
    "MAX_RESPONSE_ID_LENGTH",
    "MIN_PERCENTAGE_FLOOR",
    "OPTIONAL_FIELDS",
    "REQUIRED_FIELDS",
    "SCHEMA_VERSION",
    "PollValidationError",
    "is_allowed_sector",
    "is_honeypot_empty",
    "public_projection",
    "validate_consent",
    "validate_honeypot",
    "validate_percentage_floor",
    "validate_poll_response",
    "validate_response_id",
    "validate_sector",
    "validate_text_length",
]
