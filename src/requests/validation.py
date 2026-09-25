"""Pure validation for the future public request intake endpoint.

The module has no Google dependencies and performs no logging.  It is intended to
be called by a server adapter and is safe to exercise directly from unit tests.
A server adapter must allocate request IDs and provide the approved LGA and ward
configuration.  A request ID is not an official voter ID.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any


SCHEMA_VERSION = "request-v1"

ALLOWED_CATEGORIES = (
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

REQUIRED_FIELDS = (
    "lga",
    "ward_code",
    "address",
    "category",
    "details",
    "consent",
)
OPTIONAL_PRIVATE_FIELDS = ("name", "phone", "email")
ALLOWED_PAYLOAD_FIELDS = frozenset(
    REQUIRED_FIELDS + OPTIONAL_PRIVATE_FIELDS + ("website", "submitted_at")
)

MAX_LENGTHS = {
    "lga": 80,
    "ward_code": 40,
    "category": 32,
    "address": 300,
    "details": 1000,
    "name": 120,
    "phone": 40,
    "email": 254,
}
MAX_REQUEST_ID_LENGTH = 40
HONEYPOT_FIELDS = ("website",)
PUBLIC_PROJECTION_FIELDS = ("lga", "category", "created_at")

WARD_MAP_REQUIRED_WARNING = "ward_map_required_before_production"
MAX_SUBMITTED_AGE = timedelta(hours=24)
MAX_SUBMITTED_CLOCK_SKEW = timedelta(minutes=5)

_PHONE_SHAPE = re.compile(r"^\+?[0-9](?:[0-9 ().-]*[0-9])?$")
_EMAIL_LOCAL = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
_EMAIL_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_EMAIL_SHAPE = re.compile(
    rf"^{_EMAIL_LOCAL}@{_EMAIL_LABEL}(?:\.{_EMAIL_LABEL})*\.[A-Za-z]{{2,63}}$"
)
_REQUEST_ID_SHAPE = re.compile(r"^APM-[0-9]{4}-[0-9]{4,12}$")


class RequestValidationError(ValueError):
    """A request or validation configuration error safe to surface to an adapter.

    Error text contains only a stable code and a contract field name.  Submitted
    values are never included.
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

    Surrounding whitespace is removed.  Internal text is otherwise preserved so
    submitted details and location wording are not rewritten.
    """

    max_length = MAX_LENGTHS.get(field)
    if max_length is None:
        raise RequestValidationError("unsupported_validation_field", field=field)

    if value is None:
        if required:
            raise RequestValidationError("invalid_type", field=field)
        return ""

    if not isinstance(value, str):
        raise RequestValidationError("invalid_type", field=field)

    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise RequestValidationError("control_character_rejected", field=field)

    cleaned = value.strip()
    if required and not cleaned:
        raise RequestValidationError("required", field=field)
    if len(cleaned) > max_length:
        raise RequestValidationError("too_long", field=field)
    return cleaned


def _configured_category_set(categories: Iterable[str] | None) -> frozenset[str]:
    if categories is None:
        return frozenset(ALLOWED_CATEGORIES)
    if isinstance(categories, (str, bytes)) or not isinstance(categories, Iterable):
        raise RequestValidationError("invalid_category_configuration")

    configured: set[str] = set()
    for category in categories:
        if not isinstance(category, str) or category != category.strip():
            raise RequestValidationError("invalid_category_configuration")
        if any(unicodedata.category(character) in {"Cc", "Cf"} for character in category):
            raise RequestValidationError("invalid_category_configuration")
        normalized = category.casefold()
        if normalized not in ALLOWED_CATEGORIES or normalized in configured:
            raise RequestValidationError("invalid_category_configuration")
        configured.add(normalized)

    if not configured:
        raise RequestValidationError("invalid_category_configuration")
    return frozenset(configured)


def is_allowed_category(
    value: Any, categories: Iterable[str] | None = None
) -> bool:
    """Return whether a value is in the exact, configured category vocabulary."""

    try:
        configured = _configured_category_set(categories)
    except RequestValidationError:
        return False
    if not isinstance(value, str):
        return False
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        return False
    return value.strip().casefold() in configured


def validate_category(
    value: Any, categories: Iterable[str] | None = None
) -> str:
    """Normalize and validate the request's single primary category."""

    configured = _configured_category_set(categories)
    cleaned = validate_text_length(value, "category")
    normalized = cleaned.casefold()
    if normalized not in configured:
        raise RequestValidationError("invalid_category", field="category")
    return normalized


def validate_consent(value: Any) -> bool:
    """Require the JSON boolean ``true``; strings and numbers are not consent."""

    if value is not True:
        raise RequestValidationError("consent_required", field="consent")
    return True


def is_honeypot_empty(value: Any) -> bool:
    """Return whether a supplied honeypot value is an empty string."""

    return isinstance(value, str) and not value.strip()


def validate_honeypot(value: Any) -> bool:
    """Reject a populated honeypot field without echoing its value."""

    if not is_honeypot_empty(value):
        raise RequestValidationError("honeypot_rejected", field="website")
    return True


def validate_request_id(value: Any) -> str:
    """Validate a server-allocated, non-official tracking ID."""

    if not isinstance(value, str):
        raise RequestValidationError("invalid_request_id", field="request_id")
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise RequestValidationError("invalid_request_id", field="request_id")

    normalized = value.strip().upper()
    if (
        len(normalized) > MAX_REQUEST_ID_LENGTH
        or not _REQUEST_ID_SHAPE.fullmatch(normalized)
    ):
        raise RequestValidationError("invalid_request_id", field="request_id")
    return normalized


def normalize_phone(value: Any) -> str:
    """Validate a contact phone and remove formatting without inferring country."""

    cleaned = validate_text_length(value, "phone", required=False)
    if not cleaned:
        return ""
    if (
        not _PHONE_SHAPE.fullmatch(cleaned)
        or cleaned.count("(") != cleaned.count(")")
        or "()" in cleaned
    ):
        raise RequestValidationError("invalid_phone", field="phone")

    digits = "".join(character for character in cleaned if character.isdigit())
    if not 7 <= len(digits) <= 15:
        raise RequestValidationError("invalid_phone", field="phone")
    return f"+{digits}" if cleaned.startswith("+") else digits


def normalize_email(value: Any) -> str:
    """Validate an email conservatively and lowercase only its domain."""

    cleaned = validate_text_length(value, "email", required=False)
    if not cleaned:
        return ""
    if ".." in cleaned or not _EMAIL_SHAPE.fullmatch(cleaned):
        raise RequestValidationError("invalid_email", field="email")

    local_part, domain = cleaned.rsplit("@", 1)
    if len(local_part) > 64 or any(
        len(label) > 63 for label in domain.split(".")
    ):
        raise RequestValidationError("invalid_email", field="email")
    return f"{local_part}@{domain.lower()}"


def _comparison_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def _canonical_lga_lookup(lgas: Iterable[str]) -> dict[str, str]:
    if isinstance(lgas, (str, bytes)) or not isinstance(lgas, Iterable):
        raise RequestValidationError("invalid_lga_configuration")

    lookup: dict[str, str] = {}
    for value in lgas:
        if not isinstance(value, str) or not value.strip():
            raise RequestValidationError("invalid_lga_configuration")
        if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
            raise RequestValidationError("invalid_lga_configuration")
        if len(value.strip()) > MAX_LENGTHS["lga"]:
            raise RequestValidationError("invalid_lga_configuration")
        canonical = " ".join(value.split())
        key = canonical.casefold()
        if key in lookup:
            raise RequestValidationError("invalid_lga_configuration")
        lookup[key] = canonical
    if not lookup:
        raise RequestValidationError("invalid_lga_configuration")
    return lookup


def _canonical_ward_lookup(
    wards_by_lga: Mapping[str, Iterable[str]], lga_lookup: Mapping[str, str]
) -> dict[str, dict[str, str]]:
    if not isinstance(wards_by_lga, Mapping):
        raise RequestValidationError("invalid_ward_configuration")

    lookup: dict[str, dict[str, str]] = {}
    for lga, raw_codes in wards_by_lga.items():
        if not isinstance(lga, str) or not lga.strip():
            raise RequestValidationError("invalid_ward_configuration")
        if any(unicodedata.category(character) in {"Cc", "Cf"} for character in lga):
            raise RequestValidationError("invalid_ward_configuration")
        lga_key = _comparison_key(lga)
        if lga_key not in lga_lookup or lga_key in lookup:
            raise RequestValidationError("invalid_ward_configuration")
        if isinstance(raw_codes, (str, bytes)) or not isinstance(raw_codes, Iterable):
            raise RequestValidationError("invalid_ward_configuration")

        ward_lookup: dict[str, str] = {}
        for raw_code in raw_codes:
            if not isinstance(raw_code, str) or not raw_code.strip():
                raise RequestValidationError("invalid_ward_configuration")
            if any(
                unicodedata.category(character) in {"Cc", "Cf"}
                for character in raw_code
            ):
                raise RequestValidationError("invalid_ward_configuration")
            if len(raw_code.strip()) > MAX_LENGTHS["ward_code"]:
                raise RequestValidationError("invalid_ward_configuration")
            canonical = " ".join(raw_code.split())
            ward_key = canonical.casefold()
            if ward_key in ward_lookup:
                raise RequestValidationError("invalid_ward_configuration")
            ward_lookup[ward_key] = canonical

        if not ward_lookup:
            raise RequestValidationError("invalid_ward_configuration")
        lookup[lga_key] = ward_lookup
    return lookup


def _normalize_aware_datetime(value: Any, *, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise RequestValidationError("timezone_required", field=field)
    if value.utcoffset() is None:
        raise RequestValidationError("timezone_required", field=field)
    return value.astimezone(timezone.utc)


def _parse_submitted_at(value: Any) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise RequestValidationError("invalid_submitted_at", field="submitted_at")
    if any(unicodedata.category(character) in {"Cc", "Cf"} for character in value):
        raise RequestValidationError("invalid_submitted_at", field="submitted_at")
    cleaned = value.strip()
    if not cleaned:
        raise RequestValidationError("invalid_submitted_at", field="submitted_at")
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        raise RequestValidationError(
            "invalid_submitted_at", field="submitted_at"
        ) from None
    return _normalize_aware_datetime(parsed, field="submitted_at")


def _format_timestamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def validate_request(
    payload: Mapping[str, Any],
    lgas: Iterable[str],
    wards_by_lga: Mapping[str, Iterable[str]] | None = None,
    categories: Iterable[str] | None = None,
    now: datetime | None = None,
    *,
    request_id: str | None = None,
    request_id_generator: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Validate and normalize one private request record.

    Args:
        payload: Untrusted form data.  Unknown fields are rejected.
        lgas: Server-supplied authoritative LGA names.  Matching is case-insensitive,
            while the configured spelling is returned.
        wards_by_lga: Optional approved map from each LGA to its ward codes.  When
            omitted, a nonblank ward code is accepted but the returned warning
            requires the endpoint to block production use.
        categories: Optional server-supplied subset of :data:`ALLOWED_CATEGORIES`.
        now: Explicit timezone-aware server time.  Required when ``submitted_at``
            is present; when supplied, its normalized value becomes ``created_at``.
        request_id: Tracking ID already allocated by the endpoint.  Clients must not
            submit it.  It is not an official voter ID.
        request_id_generator: Optional zero-argument endpoint-owned generator.  This
            module never allocates a sequence and requires either this callable or
            ``request_id`` before adding an ID.

    Returns:
        A new private record dictionary.  It does not retain the input mapping.
    """

    if not isinstance(payload, Mapping):
        raise RequestValidationError("invalid_payload")

    lga_lookup = _canonical_lga_lookup(lgas)
    allowed_categories = _configured_category_set(categories)

    if set(payload) - ALLOWED_PAYLOAD_FIELDS:
        raise RequestValidationError("unsupported_field")
    for field in HONEYPOT_FIELDS:
        if field in payload:
            validate_honeypot(payload[field])
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise RequestValidationError("required", field=field)

    consent = validate_consent(payload["consent"])

    lga_input = validate_text_length(payload["lga"], "lga")
    lga_key = _comparison_key(lga_input)
    if lga_key not in lga_lookup:
        raise RequestValidationError("invalid_lga", field="lga")
    normalized_lga = lga_lookup[lga_key]

    ward_input = validate_text_length(payload["ward_code"], "ward_code")
    validation_status = "validated"
    validation_warnings: list[str] = []
    if wards_by_lga is None:
        normalized_ward = " ".join(ward_input.split())
        validation_status = "ward_map_missing"
        validation_warnings.append(WARD_MAP_REQUIRED_WARNING)
    else:
        ward_lookup = _canonical_ward_lookup(wards_by_lga, lga_lookup)
        selected_ward_lookup = ward_lookup.get(lga_key)
        if selected_ward_lookup is None:
            raise RequestValidationError(
                "ward_not_configured_for_lga", field="ward_code"
            )
        ward_key = _comparison_key(ward_input)
        if ward_key not in selected_ward_lookup:
            raise RequestValidationError("invalid_ward", field="ward_code")
        normalized_ward = selected_ward_lookup[ward_key]

    category = validate_category(payload["category"], allowed_categories)
    address = validate_text_length(payload["address"], "address")
    details = validate_text_length(payload["details"], "details")

    private_fields: dict[str, str] = {}
    for field in OPTIONAL_PRIVATE_FIELDS:
        cleaned = validate_text_length(payload.get(field), field, required=False)
        if not cleaned:
            continue
        if field == "phone":
            cleaned = normalize_phone(cleaned)
        elif field == "email":
            cleaned = normalize_email(cleaned)
        private_fields[field] = cleaned

    normalized_now = (
        _normalize_aware_datetime(now, field="now") if now is not None else None
    )
    if "submitted_at" in payload:
        if normalized_now is None:
            raise RequestValidationError(
                "explicit_now_required_for_submitted_at", field="now"
            )
        submitted_at = _parse_submitted_at(payload["submitted_at"])
        if submitted_at < normalized_now - MAX_SUBMITTED_AGE:
            raise RequestValidationError("submitted_at_too_old", field="submitted_at")
        if submitted_at > normalized_now + MAX_SUBMITTED_CLOCK_SKEW:
            raise RequestValidationError("submitted_at_in_future", field="submitted_at")

    if request_id is not None and request_id_generator is not None:
        raise RequestValidationError("ambiguous_request_id_source", field="request_id")
    if request_id_generator is not None:
        if not callable(request_id_generator):
            raise RequestValidationError(
                "invalid_request_id_generator", field="request_id"
            )
        request_id = request_id_generator()

    record: dict[str, Any] = {
        "lga": normalized_lga,
        "ward_code": normalized_ward,
        "address": address,
        "category": category,
        "details": details,
        "consent": consent,
        "validation_status": validation_status,
        "validation_warnings": validation_warnings,
    }
    record.update(private_fields)
    if normalized_now is not None:
        record["created_at"] = _format_timestamp(normalized_now)
    if request_id is not None:
        record["request_id"] = validate_request_id(request_id)
    return record


def public_projection(private_record: Mapping[str, Any]) -> dict[str, str]:
    """Return the fixed, non-PII projection allowed from one private record.

    This function constructs a fresh dictionary from an allowlist. It never
    copies address, free text, optional contacts, ward codes, validation
    metadata, or request IDs. The aggregation layer publishes no ward-level
    cells; any future ward-level output must apply the approved small-count rule.
    """

    if not isinstance(private_record, Mapping):
        raise RequestValidationError("invalid_private_record")

    lga = validate_text_length(private_record.get("lga"), "lga")
    normalized_lga = " ".join(lga.split())
    category = validate_category(private_record.get("category"))
    projection = {"lga": normalized_lga, "category": category}

    created_at = private_record.get("created_at")
    if created_at is not None:
        if not isinstance(created_at, str) or len(created_at) > 64:
            raise RequestValidationError("invalid_created_at", field="created_at")
        if any(
            unicodedata.category(character) in {"Cc", "Cf"}
            for character in created_at
        ):
            raise RequestValidationError("invalid_created_at", field="created_at")
        try:
            parsed_created_at = datetime.fromisoformat(
                created_at.strip().replace("Z", "+00:00")
            )
        except ValueError:
            raise RequestValidationError(
                "invalid_created_at", field="created_at"
            ) from None
        projection["created_at"] = _format_timestamp(
            _normalize_aware_datetime(parsed_created_at, field="created_at")
        )
    return projection


__all__ = [
    "ALLOWED_CATEGORIES",
    "ALLOWED_PAYLOAD_FIELDS",
    "HONEYPOT_FIELDS",
    "MAX_LENGTHS",
    "MAX_REQUEST_ID_LENGTH",
    "OPTIONAL_PRIVATE_FIELDS",
    "PUBLIC_PROJECTION_FIELDS",
    "REQUIRED_FIELDS",
    "SCHEMA_VERSION",
    "WARD_MAP_REQUIRED_WARNING",
    "RequestValidationError",
    "is_allowed_category",
    "is_honeypot_empty",
    "normalize_email",
    "normalize_phone",
    "public_projection",
    "validate_category",
    "validate_consent",
    "validate_honeypot",
    "validate_request",
    "validate_request_id",
    "validate_text_length",
]
