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
            phone="+234 800 000 0000",
            email="Test@Example.COM",
        )
        record = validation.validate_request(payload, LGAS, WARDS)

        self.assertEqual(record["lga"], "Bauchi")
        self.assertEqual(record["category"], "water")
        self.assertEqual(record["phone"], "+2348000000000")
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
            ("phone", f"+{'1' * 41}"),
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
        for field, value in (("phone", "not-a-phone"), ("email", "bad-email")):
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
                phone="+234 800 000 0000",
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


if __name__ == "__main__":
    unittest.main()
