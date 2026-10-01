"""Pure validation for the public opinion poll endpoint.

This module has no Google dependencies and performs no logging, exactly like
`src/requests/validation.py`. It is intended to be called by a server adapter and is
safe to exercise directly from unit tests.

Three properties are the reason this is a separate package, and all three are
load-bearing:

1. **The poll collects no direct identity.** No name, no phone, no email, no address, no
   NIN, no BVN, no official voter ID. `FORBIDDEN_IDENTITY_FIELDS` is a strict allowlist of
   refusal, and `validate_poll_response` rejects a payload carrying one of those rather
   than storing and ignoring it. An identity field the validator silently drops is still
   an identity field on the wire and in the access log of whatever sits in front of the
   endpoint.

2. **Geography is accepted, and that is a weaker guarantee than it looks.** `lga` and an
   optional `ward_code` were added on 29 September 2026 so the results could be broken
   down by area. `lga` is 20 broad buckets and is defensible. `ward_code` is a provisional
   INEC registration area out of 212, which is **not** a council ward and is **not**
   geo-located, and it is *optional* precisely so that a respondent who does not want to
   narrow themselves further is not forced to.

   The reason this needs saying plainly: an area plus a sector plus a date is closer to a
   person than a sector alone. This is why the published snapshot must suppress small
   cells, which is the sole thing that makes public ward-level output defensible. See
   `src/poll/aggregate.py`.

3. **Q2 is a comment attached to the vote, not a second question.** It is validated,
   length-capped and stored, but `tally_poll_responses` never reads it. Only `sector` can
   move a number. A test asserts that property directly.

4. **A stored comment is kept, but it is kept apart and it is not kept forever.** The
   owner wants the complaints, because that is the part of the poll no tally can replace.
   So the comment is stored — on its own tab, in its own projection
   (:func:`comment_record`), which carries the text, the sector, the LGA and the
   timestamp and **nothing else**: no registration area, no age band, no gender, and no
   ``response_id`` to join it back to the row that does carry them. Free text sitting on a
   row that also holds an area and two demographics is close to naming a person, and the
   whole design rests on the comment being unattributable.

   The retention ceiling (:func:`validate_comment_retention_days`) is what makes keeping
   it defensible rather than merely convenient. It is a **ceiling, not a floor** — the
   privacy risk of free text grows with time, so the value that must be refused is the
   long one. A poll that promises its respondents their words are kept, and then keeps
   them for a decade, has told them something false.
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

BAUCHI_LGAS = (
    "Alkaleri", "Bauchi", "Bogoro", "Dambam", "Darazo", "Dass", "Gamawa",
    "Ganjuwa", "Giade", "Itas-Gadau", "Jamaare", "Katagum", "Kirfi", "Misau",
    "Ningi", "Shira", "Tafawa-Balewa", "Toro", "Warji", "Zaki",
)

REQUIRED_FIELDS = ("sector", "lga", "consent")
OPTIONAL_FIELDS = ("ward_code", "comment", "age_band", "gender")
# Deliberately exhaustive. If a future field is wanted, it must be added here and
# reasoned about, not appended to the form and picked up automatically.
ALLOWED_PAYLOAD_FIELDS = frozenset(
    REQUIRED_FIELDS + OPTIONAL_FIELDS + ("website", "submitted_at")
)

# Age is collected as BANDS, never as a number. Bands are optional and answered from a
# closed list, so the form cannot leak an exact age even by accident, and no respondent
# is forced to narrow themselves further than they want to. Age plus LGA plus ward is
# already a lot of dimensions; an exact age on top of that is the thing that turns an
# aggregate into a person.
AGE_BANDS = (
    "age_18_25",
    "age_26_35",
    "age_36_45",
    "age_46_55",
    "age_56_65",
    "age_66_plus",
    "age_unspecified",
)

# Closed set with a decline option. Free text here would be a re-identification channel
# and an abuse target, so the field is a choice, never a sentence.
GENDER_OPTIONS = (
    "woman",
    "man",
    "gender_unspecified",
)

DECLINE = "unspecified"

MAX_LENGTHS = {
    "sector": 32,
    "lga": 80,
    "ward_code": 40,
    "comment": 300,
    "age_band": 32,
    "gender": 32,
}
MAX_RESPONSE_ID_LENGTH = 40
HONEYPOT_FIELDS = ("website",)

# Q2 is capped hard because it is the field most likely to be abused and the field most
# likely to capture an identifying detail a respondent typed unprompted.
MAX_COMMENT_LENGTH = MAX_LENGTHS["comment"]

# How long a stored comment is kept before it is deleted, in days. 180 is chosen because
# it covers a whole reporting cycle plus a re-run of the analysis, and it is short enough
# that a sheet nobody is actively curating is not also a growing archive of things people
# typed in anger about a specific tap.
DEFAULT_COMMENT_RETENTION_DAYS = 180

# The hard ceiling. 365 is the most a free-text field can be held and still be called
# temporary, and it exists so the retention setting cannot be raised to "forever" by
# editing one number. Below 1 day is also refused: a comment deleted on arrival is not a
# retained comment, and silently storing it forever under a 0-day setting would invert
# the guarantee.
MIN_COMMENT_RETENTION_DAYS = 1
MAX_COMMENT_RETENTION_DAYS = 365

MAX_SUBMITTED_AGE = timedelta(hours=24)
MAX_SUBMITTED_CLOCK_SKEW = timedelta(minutes=5)

MIN_PERCENTAGE_FLOOR = 0
DEFAULT_PERCENTAGE_FLOOR = 10

# Small-cell suppression is mandatory for published geographic output. A cell below this
# count is withheld rather than shown, because "1 response from this registration area"
# is one person's registration area.
DEFAULT_SMALL_COUNT_THRESHOLD = 5

_RESPONSE_ID_SHAPE = re.compile(r"^APM-POLL-[0-9]{4}-[0-9]{4,12}$")

# Fields that must never appear in a poll payload. `lga`, `ward_code`, `age_band` and
# `gender` are NOT here: they are the approved area/demographic breakdown, and the
# snapshot's small-cell suppression is what keeps them safe to publish. Everything below
# names a person or a credential directly, or is an alias that would smuggle an exact age
# past the band list.
FORBIDDEN_IDENTITY_FIELDS = (
    "name",
    "full_name",
    "phone",
    "phone_number",
    "email",
    "address",
    "voter_id",
    "voterid",
    "registered_voter_number",
    "nin",
    "bvn",
    "date_of_birth",
    "dob",
    # Exact-age aliases. The form collects bands; these are the keys someone would reach
    # for to defeat that, so they are refused by name rather than by accident.
    "age",
    "age_years",
    "exact_age",
    "years_old",
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


def _comparison_key(value: str) -> str:
    return " ".join(value.split()).casefold()


def canonical_lga_lookup(lgas: Iterable[str] | None = None) -> dict[str, str]:
    """Map a case-insensitive LGA key to its canonical spelling."""
    source = BAUCHI_LGAS if lgas is None else tuple(lgas)
    if isinstance(source, (str, bytes)) or not isinstance(source, Iterable):
        raise PollValidationError("invalid_lga_configuration")
    lookup: dict[str, str] = {}
    for value in source:
        if not isinstance(value, str) or not value.strip():
            raise PollValidationError("invalid_lga_configuration")
        if any(unicodedata.category(c) in {"Cc", "Cf"} for c in value):
            raise PollValidationError("invalid_lga_configuration")
        if len(value.strip()) > MAX_LENGTHS["lga"]:
            raise PollValidationError("invalid_lga_configuration")
        canonical = " ".join(value.split())
        key = _comparison_key(canonical)
        if key in lookup:
            raise PollValidationError("invalid_lga_configuration")
        lookup[key] = canonical
    if not lookup:
        raise PollValidationError("invalid_lga_configuration")
    return lookup


def validate_lga(value: Any, lgas: Iterable[str] | None = None) -> str:
    """Normalize and validate the respondent's LGA, returning the configured spelling."""
    lookup = canonical_lga_lookup(lgas)
    cleaned = validate_text_length(value, "lga")
    key = _comparison_key(cleaned)
    if key not in lookup:
        raise PollValidationError("invalid_lga", field="lga")
    return lookup[key]


def validate_ward_code(
    value: Any,
    lga: str,
    wards_by_lga: Mapping[str, Iterable[str]],
    lgas: Iterable[str] | None = None,
) -> str:
    """Validate an optional registration-area code against the respondent's own LGA.

    The code must belong to the LGA the respondent selected. Accepting a ward that
    belongs to a different LGA would let a cell be misattributed, which is a correctness
    bug as well as a privacy one.
    """
    cleaned = validate_text_length(value, "ward_code", required=False)
    if not cleaned:
        return ""
    if not isinstance(wards_by_lga, Mapping):
        raise PollValidationError("invalid_ward_configuration")
    lga_lookup = canonical_lga_lookup(lgas)
    lga_key = _comparison_key(lga)
    if lga_key not in lga_lookup:
        raise PollValidationError("invalid_lga", field="lga")
    codes = wards_by_lga.get(lga_lookup[lga_key])
    if not codes:
        raise PollValidationError("ward_not_configured_for_lga", field="ward_code")
    if isinstance(codes, (str, bytes)) or not isinstance(codes, Iterable):
        raise PollValidationError("invalid_ward_configuration")
    for code in codes:
        if not isinstance(code, str) or not code.strip():
            raise PollValidationError("invalid_ward_configuration")
        if any(unicodedata.category(c) in {"Cc", "Cf"} for c in code):
            raise PollValidationError("invalid_ward_configuration")
        if _comparison_key(code) == _comparison_key(cleaned):
            return " ".join(code.split())
    raise PollValidationError("invalid_ward", field="ward_code")


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


def validate_closed_choice(
    value: Any, allowed: Iterable[str], field: str
) -> str:
    """Validate an optional closed-list choice, normalising a decline to ''.

    A closed list, never free text. A declined value is stored as an empty string and so
    is excluded from the demographic breakdowns, rather than becoming a slice of its own
    that would have to be published and suppressed like any other.

    The decline marker is matched by suffix as well as by equality, because the
    vocabulary is namespaced (`age_unspecified`, `gender_unspecified`). Matching on the
    bare word "unspecified" would accept a decline but fail to recognise the actual
    values the form sends.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        raise PollValidationError("invalid_type", field=field)
    if any(unicodedata.category(c) in {"Cc", "Cf"} for c in value):
        raise PollValidationError("control_character_rejected", field=field)
    cleaned = value.strip()
    if not cleaned:
        return ""
    if len(cleaned) > MAX_LENGTHS.get(field, 32):
        raise PollValidationError("too_long", field=field)
    normalized = cleaned.casefold()
    vocabulary = set(allowed)
    if normalized not in vocabulary:
        raise PollValidationError("invalid_choice", field=field)
    if normalized == DECLINE or normalized.endswith(f"_{DECLINE}"):
        return ""
    return normalized


def validate_small_count_threshold(value: Any) -> int:
    """Validate the mandatory small-cell suppression floor.

    This is not a cosmetic setting. Published geographic output without it would render
    "1 response from this registration area", which is one person's registration area.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise PollValidationError(
            "invalid_small_count_threshold", field="small_count_threshold")
    if value < 2:
        # A floor of 0 or 1 would publish single respondents, which is the exact failure
        # the floor exists to prevent.
        raise PollValidationError(
            "invalid_small_count_threshold", field="small_count_threshold")
    return value


def validate_comment_retention_days(value: Any) -> int:
    """Validate the maximum age, in days, of a stored comment.

    This is a **ceiling with a floor under it**, and the direction is the whole point.
    The privacy risk of holding someone's free text grows with how long you hold it, so
    the value that must be refused is the large one: ``MAX_COMMENT_RETENTION_DAYS`` is a
    refusal, not a suggestion, and raising it means editing a bound and re-deriving the
    justification in the docstring rather than changing a config number.

    ``0`` and negatives are refused too, for a different reason. A 0-day setting reads as
    "comments are not kept", and if the implementation then failed to delete anything the
    setting would be a lie in the permissive direction — the worst direction for this
    field. Refusing it means the code and the stated guarantee cannot diverge.
    """

    if isinstance(value, bool) or not isinstance(value, int):
        raise PollValidationError(
            "invalid_comment_retention_days", field="comment_retention_days")
    if not MIN_COMMENT_RETENTION_DAYS <= value <= MAX_COMMENT_RETENTION_DAYS:
        raise PollValidationError(
            "invalid_comment_retention_days", field="comment_retention_days")
    return value


def validate_poll_response(
    payload: Mapping[str, Any],
    now: datetime | None = None,
    *,
    sectors: Iterable[str] | None = None,
    lgas: Iterable[str] | None = None,
    wards_by_lga: Mapping[str, Iterable[str]] | None = None,
    response_id: str | None = None,
    response_id_generator: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Validate and normalize one poll response.

    Args:
        payload: Untrusted form data. Unknown fields are rejected, including every
            direct-identity field named in :data:`FORBIDDEN_IDENTITY_FIELDS`.
        now: Explicit timezone-aware server time. Required when ``submitted_at`` is
            present; when supplied, its normalized value becomes ``created_at``.
        sectors: Optional server-supplied subset of :data:`ALLOWED_SECTORS`. Keyword
            only, so passing server time positionally can never be mistaken for it.
        lgas: Optional server-supplied LGA vocabulary. Defaults to the 20 Bauchi LGAs.
        wards_by_lga: Optional map of LGA to its registration-area codes. Required when a
            ``ward_code`` is supplied; without it a supplied code is rejected rather
            than accepted unverified, because an unverified area is a misattributed one.
        response_id: Tracking reference already allocated by the endpoint. Clients must
            not submit it. It is not a voter ID.
        response_id_generator: Optional zero-argument endpoint-owned generator. This
            module never allocates a sequence and requires either this callable or
            ``response_id`` before adding a reference.

    Returns:
        A new response dictionary. It does not retain the input mapping, and it never
        contains a name, phone, email, address, or voter ID.
    """

    if not isinstance(payload, Mapping):
        raise PollValidationError("invalid_payload")

    # Reject direct-identity fields with a specific, reportable code before the generic
    # unknown field check, so a misconfigured form fails loudly and legibly instead of
    # looking like a typo.
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
    lga = validate_lga(payload["lga"], lgas)

    raw_ward = payload.get("ward_code")
    if raw_ward is not None and str(raw_ward).strip():
        if wards_by_lga is None:
            raise PollValidationError(
                "ward_map_required_for_ward_code", field="ward_code")
        ward_code = validate_ward_code(raw_ward, lga, wards_by_lga, lgas)
    else:
        ward_code = ""

    comment = validate_text_length(payload.get("comment"), "comment", required=False)
    age_band = validate_closed_choice(
        payload.get("age_band"), AGE_BANDS, "age_band")
    gender = validate_closed_choice(
        payload.get("gender"), GENDER_OPTIONS, "gender")

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
        "lga": lga,
        "ward_code": ward_code,
        "comment": comment,
        "age_band": age_band,
        "gender": gender,
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

    projection = {
        "sector": validate_sector(response.get("sector")),
        "lga": validate_lga(response.get("lga")),
    }

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


def comment_record(response: Mapping[str, Any]) -> dict[str, str]:
    """Return the restricted-storage projection for one response's Q2 comment.

    This is the *other* projection from :func:`public_projection`, and it is the one that
    decides what a stored complaint can be joined to. It carries the text, the sector, the
    LGA and the timestamp. It carries **no registration area, no age band, no gender, and
    no ``response_id``**.

    The omissions are the design, not omissions:

    - **No registration area.** 212 areas over 20 LGAs, and the form warns that most will
      be suppressed. One specific area plus a distinctive complaint is a person.
    - **No age band, no gender.** Both are answerable by anyone who knows the respondent,
      and both are published at LGA level and above only. On a row with free text they
      would make the text attributable to a demographic slice of a community.
    - **No ``response_id``.** This is the load-bearing one. The tracking reference is the
      join key back to the ``Responses`` row that *does* carry the area and the
      demographics. Shipping it alongside the text would rebuild the joined row out of
      two tabs, which would make the split decorative. Dropping it means a comment cannot
      be re-attached to its vote even by someone who can read both tabs.

    What is left is what the qualitative study actually needs: what people said, about
    what, in which LGA, and when. Nobody's area, nobody's age, nobody's gender, and no
    thread back to the row that has them.

    Returns an empty dictionary when the response carries no comment, so a vote without
    one costs no row in the restricted tab.
    """

    if not isinstance(response, Mapping):
        raise PollValidationError("invalid_response_record")

    comment = response.get("comment")
    if comment is None:
        return {}
    cleaned = validate_text_length(comment, "comment", required=False)
    if not cleaned:
        return {}

    record = {
        "sector": validate_sector(response.get("sector")),
        "lga": validate_lga(response.get("lga")),
        "comment": cleaned,
    }

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
        record["created_at"] = _format_timestamp(
            _normalize_aware_datetime(parsed, field="created_at")
        )
    return record


# The exact key set a stored comment may have, asserted against a real record in the test
# suite. Exported as data rather than described in prose so that adding a field to this
# projection is a deliberate change to a tuple someone can see, and so the "no area, no
# demographics, no join key" rule is checkable without reading this docstring.
COMMENT_RECORD_FIELDS = ("sector", "lga", "comment", "created_at")


__all__ = [
    "AGE_BANDS",
    "ALLOWED_PAYLOAD_FIELDS",
    "ALLOWED_SECTORS",
    "BAUCHI_LGAS",
    "COMMENT_RECORD_FIELDS",
    "DECLINE",
    "DEFAULT_COMMENT_RETENTION_DAYS",
    "DEFAULT_PERCENTAGE_FLOOR",
    "DEFAULT_SMALL_COUNT_THRESHOLD",
    "FORBIDDEN_IDENTITY_FIELDS",
    "GENDER_OPTIONS",
    "HONEYPOT_FIELDS",
    "MAX_COMMENT_LENGTH",
    "MAX_COMMENT_RETENTION_DAYS",
    "MAX_LENGTHS",
    "MAX_RESPONSE_ID_LENGTH",
    "MIN_COMMENT_RETENTION_DAYS",
    "MIN_PERCENTAGE_FLOOR",
    "OPTIONAL_FIELDS",
    "REQUIRED_FIELDS",
    "SCHEMA_VERSION",
    "PollValidationError",
    "canonical_lga_lookup",
    "comment_record",
    "is_allowed_sector",
    "is_honeypot_empty",
    "public_projection",
    "validate_comment_retention_days",
    "validate_consent",
    "validate_honeypot",
    "validate_lga",
    "validate_percentage_floor",
    "validate_poll_response",
    "validate_response_id",
    "validate_sector",
    "validate_small_count_threshold",
    "validate_text_length",
    "validate_ward_code",
]
