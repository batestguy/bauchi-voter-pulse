import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.requests import validation


LGAS = (
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
WARDS = {"Bauchi": ("B-001", "B-002")}


def valid_payload(**overrides):
    payload = {
        "lga": "Bauchi",
        "ward_code": "B-001",
        "address": "Test Road, Bauchi",
        "category": "water",
        "details": "The test standpipe has no water.",
        "consent": True,
        "website": "",
    }
    payload.update(overrides)
    return payload


class RequestValidationTests(unittest.TestCase):
    def test_valid_payload_is_normalized(self):
        payload = valid_payload(
            lga="  bauchi ",
            category=" WATER ",
            name=" Test User ",
            email="Test@Example.COM",
        )
        record = validation.validate_request(payload, LGAS, WARDS)

        self.assertEqual(record["lga"], "Bauchi")
        self.assertEqual(record["category"], "water")
        self.assertEqual(record["email"], "Test@example.com")
        self.assertEqual(record["validation_status"], "validated")
        self.assertEqual(record["validation_warnings"], [])
        self.assertNotIn("request_id", record)

    def test_missing_ward_map_returns_production_warning(self):
        record = validation.validate_request(valid_payload(), LGAS)

        self.assertEqual(record["ward_code"], "B-001")
        self.assertEqual(record["validation_status"], "ward_map_missing")
        self.assertEqual(
            record["validation_warnings"],
            [validation.WARD_MAP_REQUIRED_WARNING],
        )

    def test_invalid_lga_is_rejected(self):
        with self.assertRaises(validation.RequestValidationError) as raised:
            validation.validate_request(valid_payload(lga="Unknown"), LGAS, WARDS)

        self.assertEqual(raised.exception.field, "lga")
        self.assertNotIn("Unknown", str(raised.exception))

    def test_ward_must_belong_to_selected_lga(self):
        with self.assertRaises(validation.RequestValidationError) as raised:
            validation.validate_request(
                valid_payload(ward_code="B-999"), LGAS, WARDS
            )

        self.assertEqual(raised.exception.field, "ward_code")
        self.assertEqual(raised.exception.code, "invalid_ward")

    def test_invalid_category_is_rejected(self):
        with self.assertRaises(validation.RequestValidationError) as raised:
            validation.validate_request(
                valid_payload(category="transport"), LGAS, WARDS
            )

        self.assertEqual(raised.exception.code, "invalid_category")

    def test_consent_must_be_boolean_true(self):
        for consent in (None, False, "true", 1):
            with self.subTest(consent=consent):
                payload = valid_payload()
                if consent is None:
                    del payload["consent"]
                else:
                    payload["consent"] = consent
                with self.assertRaises(
                    validation.RequestValidationError
                ) as raised:
                    validation.validate_request(payload, LGAS, WARDS)
                expected_code = "required" if consent is None else "consent_required"
                self.assertEqual(raised.exception.code, expected_code)

    def test_field_length_limits_are_enforced(self):
        cases = (
            ("lga", "B" * 81),
            ("ward_code", "W" * 41),
            ("address", "a" * 301),
            ("details", "d" * 1001),
            ("name", "n" * 121),
            ("email", f"{'e' * 245}@example.com"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                with self.assertRaises(
                    validation.RequestValidationError
                ) as raised:
                    validation.validate_request(
                        valid_payload(**{field: value}), LGAS, WARDS
                    )
                self.assertEqual(raised.exception.field, field)
                self.assertEqual(raised.exception.code, "too_long")

    def test_control_characters_are_rejected(self):
        with self.assertRaises(validation.RequestValidationError) as raised:
            validation.validate_request(
                valid_payload(details="unsafe\u0000text"), LGAS, WARDS
            )

        self.assertEqual(raised.exception.code, "control_character_rejected")

    def test_populated_honeypot_is_rejected(self):
        with self.assertRaises(validation.RequestValidationError) as raised:
            validation.validate_request(
                valid_payload(website="https://spam.invalid"), LGAS, WARDS
            )

        self.assertEqual(raised.exception.field, "website")
        self.assertEqual(raised.exception.code, "honeypot_rejected")

    def test_invalid_contact_shapes_do_not_echo_values(self):
        for field, value in (("email", "bad-email"),):
            with self.subTest(field=field):
                with self.assertRaises(
                    validation.RequestValidationError
                ) as raised:
                    validation.validate_request(
                        valid_payload(**{field: value}), LGAS, WARDS
                    )
                self.assertEqual(raised.exception.field, field)
                self.assertNotIn(value, str(raised.exception))

    def test_request_id_is_server_supplied_and_not_official(self):
        now = datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc)
        record = validation.validate_request(
            valid_payload(submitted_at="2026-09-25T10:29:30Z"),
            LGAS,
            WARDS,
            now=now,
            request_id="apm-2026-0001",
        )

        self.assertEqual(record["request_id"], "APM-2026-0001")
        self.assertEqual(record["created_at"], "2026-09-25T10:30:00Z")

    def test_implausible_submitted_at_is_rejected(self):
        now = datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc)
        cases = (
            ("2026-09-24T09:00:00Z", "submitted_at_too_old"),
            ("2026-09-25T10:40:00Z", "submitted_at_in_future"),
        )
        for submitted_at, expected_code in cases:
            with self.subTest(submitted_at=submitted_at):
                with self.assertRaises(
                    validation.RequestValidationError
                ) as raised:
                    validation.validate_request(
                        valid_payload(submitted_at=submitted_at),
                        LGAS,
                        WARDS,
                        now=now,
                    )
                self.assertEqual(raised.exception.code, expected_code)

    def test_public_projection_excludes_all_private_fields(self):
        now = datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc)
        private_record = validation.validate_request(
            valid_payload(
                name="Test User",
                    email="test@example.com",
            ),
            LGAS,
            WARDS,
            now=now,
            request_id="APM-2026-0001",
        )
        private_record["unexpected_private_value"] = "must not escape"
        public_record = validation.public_projection(private_record)

        self.assertEqual(
            public_record,
            {
                "lga": "Bauchi",
                "category": "water",
                "created_at": "2026-09-25T10:30:00Z",
            },
        )
        serialized = json.dumps(public_record, sort_keys=True)
        for private_value in (
            "APM-2026-0001",
            "Test Road",
            "standpipe",
            "Test User",
            "8000000000",
            "test@example.com",
            "B-001",
            "must not escape",
        ):
            self.assertNotIn(private_value, serialized)

    def test_request_schema_documents_server_only_id_and_categories(self):
        contract = json.loads(
            Path("src/requests/request_schema.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            tuple(contract["properties"]["category"]["enum"]),
            validation.ALLOWED_CATEGORIES,
        )
        self.assertNotIn("request_id", contract["properties"])
        self.assertFalse(
            contract["x-server-allocated-fields"]["request_id"][
                "client-submission-allowed"
            ]
        )



class PhoneRemovalTests(unittest.TestCase):
    """The phone number is refused, not dropped.

    The owner removed the phone field from the request form on the reading that it is about
    one need, not about building a contact list. Removing the INPUT alone would have left
    the endpoint still accepting and storing a number, which is the opposite of what was
    asked -- so `phone` left `ALLOWED_PAYLOAD_FIELDS` and a payload carrying one is now an
    `unsupported_field`.

    "Refused" rather than "ignored" is the whole distinction. A silently dropped field is
    still on the wire, in the access log, and in whatever sits in front of the endpoint, so
    dropping it is not a privacy control and never was.
    """

    BASE = {
        "lga": "Bauchi",
        "ward_code": "RA-001",
        "address": "Behind the primary school",
        "category": "water",
        "details": "The borehole is dry.",
        "consent": True,
    }
    LGAS = ("Bauchi",)
    WARDS = {"Bauchi": ("RA-001",)}

    def _reject(self, payload):
        with self.assertRaises(validation.RequestValidationError) as caught:
            validation.validate_request(
                payload, self.LGAS, self.WARDS,
                now=datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc))
        return caught.exception.code

    def test_a_phone_number_is_refused(self):
        self.assertEqual(self._reject({**self.BASE, "phone": "08012345678"}),
                         "unsupported_field")

    def test_a_phone_number_is_refused_in_its_international_form(self):
        self.assertEqual(self._reject({**self.BASE, "phone": "+234 801 234 5678"}),
                         "unsupported_field")

    def test_an_empty_phone_field_is_refused_too(self):
        # Tolerating an empty value is the first half of accepting a populated one. A field
        # the form no longer renders should not be a field the contract quietly permits.
        self.assertEqual(self._reject({**self.BASE, "phone": ""}), "unsupported_field")

    def test_phone_is_not_an_optional_private_field(self):
        self.assertNotIn("phone", validation.OPTIONAL_PRIVATE_FIELDS)

    def test_phone_is_not_in_the_allowed_payload(self):
        self.assertNotIn("phone", validation.ALLOWED_PAYLOAD_FIELDS)

    def test_phone_has_no_length_budget(self):
        # A length limit for a field that cannot be sent is a contradiction, and it is the
        # kind that survives unnoticed because nothing ever exercises it.
        self.assertNotIn("phone", validation.MAX_LENGTHS)

    def test_email_is_still_collected_for_correspondence(self):
        record = validation.validate_request(
            {**self.BASE, "email": "aminu.bala@example.com"},
            self.LGAS, self.WARDS, now=datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc))
        self.assertEqual(record["email"], "aminu.bala@example.com")
        self.assertIn("email", validation.OPTIONAL_PRIVATE_FIELDS)

    def test_name_is_still_collected(self):
        # Not asked to be removed, and it is the one field that makes a reply personal
        # rather than anonymous.
        record = validation.validate_request(
            {**self.BASE, "name": "Aminu Bala"},
            self.LGAS, self.WARDS, now=datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc))
        self.assertEqual(record["name"], "Aminu Bala")

    def test_a_request_without_any_contact_detail_still_validates(self):
        record = validation.validate_request(
            dict(self.BASE), self.LGAS, self.WARDS,
            now=datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc))
        self.assertNotIn("phone", record)
        self.assertNotIn("email", record)

    def test_the_published_schema_no_longer_offers_a_phone(self):
        # The schema is the document a reader trusts to describe what the form collects.
        # It kept offering a phone for a full session after the code, the form and the
        # endpoint had all stopped accepting one, so the documented contract and the real
        # one disagreed and nothing noticed -- the one place a phone was still described
        # as collectable.
        raw = Path("src/requests/request_schema.json").read_text(encoding="utf-8")
        self.assertNotIn("phone", raw)
        contract = json.loads(raw)
        self.assertNotIn("phone", contract["properties"])
        self.assertNotIn("phone", contract["x-normalized-private-record"]["properties"])

    def test_the_schema_and_the_validator_agree_on_the_optional_private_fields(self):
        # The two descriptions of the same rule drift unless something compares them, and
        # this is the only check that would have caught the drift above.
        contract = json.loads(
            Path("src/requests/request_schema.json").read_text(encoding="utf-8"))
        documented = set(contract["properties"]) & set(validation.OPTIONAL_PRIVATE_FIELDS)
        self.assertEqual(documented, set(validation.OPTIONAL_PRIVATE_FIELDS))

if __name__ == "__main__":
    unittest.main()
