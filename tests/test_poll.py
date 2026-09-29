"""S5 poll contract, validation and tally tests.

The properties these defend are the ones that would make a published poll dishonest:

1. **The poll collects no PII.** A name, phone, email, ward or voter ID in a payload is
   rejected, not silently dropped. An identity field the validator quietly ignores is
   still on the wire and in any intermediate log.
2. **Q2 never moves a number.** The comment is stored but never counted, so a long
   persuasive comment cannot change the published result.
3. **One vote is never "100%".** The percentage floor exists so a single response
   cannot render as a unanimous mandate.
4. **An empty poll is empty**, never a chart of zeros that reads as data.
5. **A build with no endpoint cannot send anything.** The disabled state is asserted in
   the HTML, in the JavaScript, and in the tests.
"""
import json
import re
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.dashboard import render
from src.poll import aggregate, validation


NOW = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


WARDS = {"Bauchi": ("RA-001", "RA-002"), "Bogoro": ("RA-101",)}


def response(sector="water", **overrides):
    record = {
        "sector": sector,
        "lga": "Bauchi",
        "ward_code": "",
        "comment": "",
        "age_band": "",
        "gender": "",
        "consent": True,
        "created_at": "2026-09-29T10:00:00Z",
    }
    record.update(overrides)
    return record


def payload(**overrides):
    body = {"sector": "water", "lga": "Bauchi", "consent": True}
    body.update(overrides)
    return body


def repeated(sector, lga="Bauchi", n=6, **overrides):
    """`n` responses for one sector/LGA, enough to clear the suppression floor."""
    return [response(sector, lga=lga, **overrides) for _ in range(n)]


class PollSchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(
            Path("src/poll/poll_schema.json").read_text(encoding="utf-8"))

    def test_schema_is_valid_json_and_forbids_extra_fields(self):
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(sorted(self.schema["required"]), ["consent", "lga", "sector"])

    def test_sector_vocabulary_matches_the_request_categories(self):
        # Direct comparability with the request queue is the reason for reusing the
        # vocabulary, so the two must not be allowed to drift apart.
        from src.poll.validation import ALLOWED_SECTORS
        self.assertEqual(tuple(self.schema["properties"]["sector"]["enum"]), ALLOWED_SECTORS)
        request_keys = tuple(key for key, _, _ in render.REQUEST_CATEGORIES)
        self.assertEqual(ALLOWED_SECTORS, request_keys)

    def test_schema_declares_every_forbidden_identity_field(self):
        declared = tuple(self.schema["x-forbidden-fields"]["fields"])
        self.assertEqual(declared, validation.FORBIDDEN_IDENTITY_FIELDS)

    def test_approved_geography_is_not_also_forbidden(self):
        # A field in both lists would be accepted and rejected at once, which is how a
        # contract quietly stops meaning anything.
        declared = set(self.schema["x-forbidden-fields"]["fields"])
        for approved in ("lga", "ward_code", "age_band", "gender"):
            with self.subTest(field=approved):
                self.assertNotIn(approved, declared)

    def test_schema_requires_an_lga(self):
        self.assertIn("lga", self.schema["required"])

    def test_schema_makes_suppression_mandatory(self):
        public = self.schema["x-public-snapshot"]
        self.assertIn("small_count_threshold", public["required"])
        self.assertIn("suppressed_cell_count", public["required"])
        self.assertEqual(public["properties"]["small_count_threshold"]["minimum"], 2)

    def test_schema_forbids_ward_by_demographic_crossings(self):
        rules = " ".join(self.schema["x-safety-rules"]).lower()
        self.assertIn("never crossed with registration areas", rules)
        self.assertIn("sequential", rules)
        self.assertIn("ip addresses", rules)

    def test_comment_is_optional_and_capped(self):
        comment = self.schema["properties"]["comment"]
        self.assertNotIn("comment", self.schema["required"])
        self.assertEqual(comment["maxLength"], validation.MAX_COMMENT_LENGTH)
        self.assertIn("not a second poll question", comment["description"].lower())

    def test_public_snapshot_excludes_the_comment(self):
        excluded = self.schema["x-public-snapshot"]["excluded-fields"]
        self.assertIn("comment", excluded)
        self.assertIn("response_id", excluded)

    def test_schema_records_the_publication_safety_rules(self):
        rules = " ".join(self.schema["x-safety-rules"]).lower()
        self.assertIn("self-selected", rules)
        self.assertIn("not a vote", rules)
        self.assertIn("representative", rules)
        self.assertIn("not verified needs", rules)
        self.assertIn("never be counted", rules)


class PollPrivacyTests(unittest.TestCase):
    def test_no_direct_identity_field_is_collectable(self):
        for field in validation.FORBIDDEN_IDENTITY_FIELDS:
            with self.subTest(field=field):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_poll_response(payload(**{field: "anything"}))
                self.assertEqual(caught.exception.code, "identity_field_forbidden")
                self.assertEqual(caught.exception.field, field)

    def test_exact_age_cannot_smuggle_past_the_band_list(self):
        # The form collects bands. These are the keys someone would reach for to defeat
        # that, so they are refused by name rather than by accident.
        for field in ("age", "age_years", "exact_age", "years_old", "date_of_birth"):
            with self.subTest(field=field):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_poll_response(payload(**{field: 34}))
                self.assertEqual(caught.exception.code, "identity_field_forbidden")

    def test_identity_fields_are_not_merely_silently_ignored(self):
        with self.assertRaises(validation.PollValidationError):
            validation.validate_poll_response(
                {"sector": "water", "lga": "Bauchi", "consent": True, "email": "a@b.com"})

    def test_normalized_record_carries_no_direct_identity_key(self):
        record = validation.validate_poll_response(
            payload(), NOW, response_id_generator=lambda: "APM-POLL-2026-00000001")
        for forbidden in validation.FORBIDDEN_IDENTITY_FIELDS:
            self.assertNotIn(forbidden, record)
        self.assertEqual(
            set(record),
            {"sector", "lga", "ward_code", "comment", "age_band", "gender",
             "consent", "created_at", "response_id"})


class PollGeographyTests(unittest.TestCase):
    """Geography was added on 29 September 2026 so results could be broken down."""

    def test_lga_is_required_and_must_be_a_bauchi_lga(self):
        for bad in ("Kano", "Bauchi South", "Atlantis", 7, ""):
            with self.subTest(bad=bad):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_poll_response(payload(lga=bad), NOW)
                self.assertIn(caught.exception.code, {"required", "invalid_lga", "invalid_type"})

    def test_lga_is_returned_in_the_configured_spelling(self):
        record = validation.validate_poll_response(payload(lga="  bauchi "), NOW)
        self.assertEqual(record["lga"], "Bauchi")

    def test_ward_is_optional(self):
        record = validation.validate_poll_response(payload(), NOW)
        self.assertEqual(record["ward_code"], "")
        record = validation.validate_poll_response(payload(ward_code="  "), NOW)
        self.assertEqual(record["ward_code"], "")

    def test_ward_must_belong_to_the_selected_lga(self):
        ok = validation.validate_poll_response(
            payload(lga="Bauchi", ward_code="RA-001"), NOW, wards_by_lga=WARDS)
        self.assertEqual(ok["ward_code"], "RA-001")
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(
                payload(lga="Bauchi", ward_code="RA-101"), NOW, wards_by_lga=WARDS)
        self.assertEqual(caught.exception.code, "invalid_ward")

    def test_ward_is_refused_rather_than_accepted_unverified(self):
        # No ward map configured means an area cannot be checked, and an unchecked area
        # is a misattributed one.
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(ward_code="RA-001"), NOW)
        self.assertEqual(caught.exception.code, "ward_map_required_for_ward_code")


class PollDemographicTests(unittest.TestCase):
    def test_age_is_bands_only_and_optional(self):
        self.assertEqual(validation.validate_poll_response(payload(), NOW)["age_band"], "")
        for band in validation.AGE_BANDS:
            if band == "age_unspecified":
                continue  # the decline option, covered by its own test
            with self.subTest(band=band):
                record = validation.validate_poll_response(payload(age_band=band), NOW)
                self.assertEqual(record["age_band"], band)
        # Every non-decline band is a range, never a number.
        for band in validation.AGE_BANDS:
            if band != "age_unspecified":
                self.assertRegex(band, r"^age_\d+(_\d+|_plus)?$")

    def test_gender_is_a_closed_list_and_optional(self):
        self.assertEqual(validation.validate_poll_response(payload(), NOW)["gender"], "")
        for value in validation.GENDER_OPTIONS:
            if value == "gender_unspecified":
                continue  # the decline option, covered by its own test
            with self.subTest(value=value):
                record = validation.validate_poll_response(payload(gender=value), NOW)
                self.assertEqual(record["gender"], value)

    def test_free_text_demographics_are_rejected(self):
        for payload_field, value in (("gender", "nonbinary trans woman"),
                                     ("age_band", "about 34")):
            with self.subTest(field=payload_field):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_poll_response(payload(**{payload_field: value}), NOW)
                self.assertEqual(caught.exception.code, "invalid_choice")

    def test_an_explicit_decline_is_stored_as_empty(self):
        # The decline option exists in the vocabulary so the form can offer it, and it is
        # normalised to "declined" rather than becoming a demographic slice of its own.
        for band in ("age_unspecified", "AGE_UNSPECIFIED", " age_unspecified "):
            with self.subTest(band=band):
                record = validation.validate_poll_response(payload(age_band=band), NOW)
                self.assertEqual(record["age_band"], "")
        for value in ("gender_unspecified", "GENDER_UNSPECIFIED"):
            with self.subTest(gender=value):
                record = validation.validate_poll_response(payload(gender=value), NOW)
                self.assertEqual(record["gender"], "")

    def test_public_projection_excludes_the_comment(self):
        projected = validation.public_projection(
            response(comment="My name is Aminu Yusuf and I live in Bauchi"))
        self.assertNotIn("comment", projected)
        self.assertEqual(projected["sector"], "water")

    def test_response_id_shape_is_not_a_voter_id(self):
        with self.assertRaises(validation.PollValidationError):
            validation.validate_response_id("VOTER-2026-00000001")
        with self.assertRaises(validation.PollValidationError):
            validation.validate_response_id("APM-2026-00000001")
        self.assertEqual(
            validation.validate_response_id("apm-poll-2026-00000042"),
            "APM-POLL-2026-00000042")


class PollValidationTests(unittest.TestCase):
    def test_minimal_valid_payload(self):
        record = validation.validate_poll_response(payload(), NOW)
        self.assertEqual(record["sector"], "water")
        self.assertEqual(record["comment"], "")
        self.assertEqual(record["created_at"], "2026-09-29T12:00:00Z")

    def test_sector_must_be_in_the_vocabulary(self):
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(sector="aircraft"), NOW)
        self.assertEqual(caught.exception.code, "invalid_sector")

    def test_consent_must_be_the_boolean_true(self):
        for value in ("true", 1, "yes", None):
            with self.subTest(value=value):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_poll_response(payload(consent=value), NOW)
                self.assertEqual(caught.exception.code, "consent_required")

    def test_missing_required_field_is_rejected(self):
        for field in ("sector", "consent"):
            body = payload()
            del body[field]
            with self.subTest(field=field):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_poll_response(body, NOW)
                self.assertEqual(caught.exception.code, "required")

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(referrer="https://x.test"), NOW)
        self.assertEqual(caught.exception.code, "unsupported_field")

    def test_honeypot_must_be_empty_and_its_value_is_never_echoed(self):
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(
                payload(website="http://spam.example"), NOW)
        self.assertEqual(caught.exception.code, "honeypot_rejected")
        self.assertNotIn("spam.example", str(caught.exception))

    def test_comment_length_is_capped(self):
        long_comment = "x" * (validation.MAX_COMMENT_LENGTH + 1)
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(comment=long_comment), NOW)
        self.assertEqual(caught.exception.code, "too_long")
        ok = validation.validate_poll_response(
            payload(comment="y" * validation.MAX_COMMENT_LENGTH), NOW)
        self.assertEqual(len(ok["comment"]), validation.MAX_COMMENT_LENGTH)

    def test_control_characters_are_rejected_in_the_comment(self):
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(comment="a\u0000b"), NOW)
        self.assertEqual(caught.exception.code, "control_character_rejected")

    def test_submitted_at_window_is_enforced(self):
        stale = (NOW - timedelta(hours=25)).isoformat().replace("+00:00", "Z")
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(submitted_at=stale), NOW)
        self.assertEqual(caught.exception.code, "submitted_at_too_old")

        future = (NOW + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(submitted_at=future), NOW)
        self.assertEqual(caught.exception.code, "submitted_at_in_future")

    def test_submitted_at_requires_an_explicit_server_now(self):
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(submitted_at="2026-09-29T11:00:00Z"))
        self.assertEqual(caught.exception.code, "explicit_now_required_for_submitted_at")

    def test_response_id_sources_are_unambiguous(self):
        with self.assertRaises(validation.PollValidationError):
            validation.validate_poll_response(
                payload(), NOW, response_id="APM-POLL-2026-00000001",
                response_id_generator=lambda: "APM-POLL-2026-00000002")

    def test_validator_never_allocates_its_own_reference(self):
        record = validation.validate_poll_response(payload(), NOW)
        self.assertNotIn("response_id", record)

    def test_sector_subset_configuration_is_enforced(self):
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(sector="security"), NOW, sectors=("water", "roads"))
        self.assertEqual(caught.exception.code, "invalid_sector")
        self.assertFalse(validation.is_allowed_sector("security", ("water", "roads")))
        self.assertTrue(validation.is_allowed_sector("water", ("water", "roads")))

    def test_error_text_never_contains_the_submitted_value(self):
        secret = "Aminu Yusuf, 08012345678"
        with self.assertRaises(validation.PollValidationError) as caught:
            validation.validate_poll_response(payload(comment=secret + "\u0007"), NOW)
        self.assertNotIn(secret, str(caught.exception))


class PollTallyTests(unittest.TestCase):
    def test_tally_counts_sector_only(self):
        tally = aggregate.tally_poll_responses([
            response("water"), response("water"), response("roads"),
        ])
        self.assertEqual(tally["total_responses"], 3)
        self.assertEqual(tally["by_sector"]["water"], 2)
        self.assertEqual(tally["by_sector"]["roads"], 1)

    def test_the_comment_can_never_change_a_number(self):
        with_comments = [
            response("water", comment="URGENT please fix this everywhere " * 40),
            response("water", comment="I am the only person who voted and I demand action"),
        ]
        without = [response("water"), response("water")]
        self.assertEqual(
            aggregate.tally_poll_responses(with_comments)["by_sector"],
            aggregate.tally_poll_responses(without)["by_sector"],
        )

    def test_tally_groups_by_lga(self):
        tally = aggregate.tally_poll_responses(
            [response("water", lga="Bauchi"), response("roads", lga="Bogoro")])
        self.assertEqual(tally["by_lga"], {"Bauchi": 1, "Bogoro": 1})
        self.assertEqual(tally["by_lga_sector"]["Bauchi"], {"water": 1})

    def test_a_response_without_an_lga_is_rejected(self):
        row = response("water")
        del row["lga"]
        tally = aggregate.tally_poll_responses([row])
        self.assertEqual(tally["total_responses"], 0)
        self.assertEqual(tally["_audit"]["invalid_lga"], 1)

    def test_demographic_coverage_is_counted_separately(self):
        tally = aggregate.tally_poll_responses([
            response("water", age_band="age_26_35", gender="woman"),
            response("water"),
        ])
        self.assertEqual(tally["with_age_band"], 1)
        self.assertEqual(tally["with_gender"], 1)
        self.assertEqual(tally["with_ward_responses"], 0)

    def test_demographics_never_cross_with_registration_areas(self):
        # A ward x age cell is the combination that actually identifies someone, so the
        # tally must not build one. See the module docstring.
        rows = repeated("water", n=6)
        for row in rows:
            row["ward_code"] = "RA-001"
            row["age_band"] = "age_26_35"
        tally = aggregate.tally_poll_responses(rows)
        keys = {key for lga in tally["by_lga_age_band"] for key in tally["by_lga_age_band"][lga]}
        self.assertNotIn("RA-001", keys)
        for lga in tally["by_lga_ward"]:
            self.assertNotIn("age_26_35", tally["by_lga_ward"][lga])

    def test_non_consented_and_invalid_rows_are_rejected_and_counted(self):
        tally = aggregate.tally_poll_responses([
            response("water"),
            response("water", consent=False),
            response("aircraft"),
            response("water", created_at="not-a-date"),
        ])
        self.assertEqual(tally["total_responses"], 1)
        audit = tally["_audit"]
        self.assertEqual(audit["non_consented"], 1)
        self.assertEqual(audit["invalid_sector"], 1)
        self.assertEqual(audit["invalid_created_at"], 1)
        self.assertEqual(audit["rejected_records"], 3)

    def test_audit_counters_are_not_part_of_the_public_snapshot(self):
        snapshot = aggregate.build_public_snapshot(
            [response("water")], generated_at=NOW)
        self.assertNotIn("_audit", snapshot)
        self.assertEqual(set(snapshot), set(aggregate.PUBLIC_SNAPSHOT_FIELDS))

    def test_empty_poll_is_empty_not_a_chart_of_zeros(self):
        snapshot = aggregate.build_public_snapshot([], generated_at=NOW)
        self.assertEqual(snapshot["total_responses"], 0)
        self.assertEqual(snapshot["by_sector"], {})
        self.assertEqual(snapshot["suppressed_cell_count"], 0)
        self.assertIsNone(snapshot["reporting_period_start"])
        self.assertIsNone(snapshot["reporting_period_end"])

    def test_response_missing_created_at_is_rejected(self):
        row = response("water")
        del row["created_at"]
        tally = aggregate.tally_poll_responses([row])
        self.assertEqual(tally["total_responses"], 0)
        self.assertEqual(tally["_audit"]["invalid_created_at"], 1)

    def test_period_filtering_is_inclusive_at_both_ends(self):
        rows = (
            [response("water", created_at="2026-09-01T00:00:00Z")]
            + [response("roads", created_at="2026-09-15T00:00:00Z")]
            + [response("education", created_at="2026-09-30T00:00:00Z")]
        )
        tally = aggregate.tally_poll_responses(
            rows, period_start="2026-09-15T00:00:00Z", period_end="2026-09-30T00:00:00Z")
        self.assertEqual(tally["total_responses"], 2)
        self.assertNotIn("water", tally["by_sector"])
        self.assertEqual(tally["by_sector"]["roads"], 1)

    def test_inverted_period_is_rejected(self):
        with self.assertRaises(ValueError):
            aggregate.tally_poll_responses(
                [response()], period_start="2026-09-30T00:00:00Z",
                period_end="2026-09-01T00:00:00Z")


class SmallCellSuppressionTests(unittest.TestCase):
    """Published geographic output without suppression is not publishable.

    The poll records an LGA and an optional registration area, so a cell of 1 or 2 is a
    cell of identifiable people. These tests are the only thing standing between the
    dataset and a page that names a person by their sector and their area.
    """

    def test_a_small_cell_is_withheld_not_published(self):
        snapshot = aggregate.build_public_snapshot(
            repeated("water", n=4) + repeated("roads", n=6), generated_at=NOW)
        self.assertIsNone(snapshot["by_sector"]["water"])
        self.assertEqual(snapshot["by_sector"]["roads"], 6)
        self.assertGreaterEqual(snapshot["suppressed_cell_count"], 1)

    def test_the_threshold_has_a_hard_lower_bound(self):
        # A floor of 0 or 1 would publish single respondents, which is the exact outcome
        # the floor exists to prevent. It is refused rather than honoured.
        for bad in (0, 1, -1, 2.5, True, "5"):
            with self.subTest(bad=bad):
                with self.assertRaises(validation.PollValidationError):
                    aggregate.build_public_snapshot(
                        [], small_count_threshold=bad)  # type: ignore[arg-type]
        self.assertEqual(
            aggregate.build_public_snapshot([], small_count_threshold=2)["small_count_threshold"], 2)

    def test_a_zero_cell_is_published_because_it_identifies_nobody(self):
        # Suppressing a zero would say "too few to publish" where the truth is
        # "nobody chose this", which is a different and weaker statement. Zero is
        # exercised directly because the tally omits sectors with no responses at all.
        self.assertEqual(aggregate.suppress({"sector": 0}, 5), ({"sector": 0}, 0))
        snapshot = aggregate.build_public_snapshot(
            repeated("water", n=6) + repeated("roads", n=6), generated_at=NOW)
        self.assertEqual(snapshot["by_sector"]["water"], 6)

    def test_suppress_preserves_zero_and_withholds_the_small(self):
        out, suppressed = aggregate.suppress({"a": 0, "b": 1, "c": 4, "d": 5}, 5)
        self.assertEqual(out, {"a": 0, "b": None, "c": None, "d": 5})
        self.assertEqual(suppressed, 2)

    def test_demographics_are_suppressed_too(self):
        rows = repeated("water", n=6)
        for row in rows:
            row["age_band"] = "age_26_35"
        rows += repeated("roads", n=6)
        for row in rows[6:]:
            row["age_band"] = "age_46_55"
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)
        self.assertEqual(snapshot["by_lga_age_band"]["Bauchi"]["age_26_35"], 6)
        self.assertEqual(snapshot["by_lga_age_band"]["Bauchi"]["age_46_55"], 6)

    def test_the_snapshot_never_contains_a_raw_count_below_the_floor(self):
        rows = []
        for sector in ("water", "roads", "education"):
            rows += repeated(sector, n=3 + len(rows))
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)
        floor = snapshot["small_count_threshold"]

        def walk(node):
            if isinstance(node, dict):
                for value in node.values():
                    yield from walk(value)
            elif isinstance(node, int) and not isinstance(node, bool):
                yield node

        for value in walk(snapshot["by_sector"]):
            if value is not None:
                self.assertGreaterEqual(value, floor)
        self.assertIsNone(snapshot["by_sector"]["water"])

    def test_the_published_snapshot_never_carries_a_comment(self):
        rows = repeated("water", n=6)
        for row in rows:
            row["comment"] = "My name is Aminu Yusuf, 08012345678"
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)
        self.assertNotIn("Aminu", repr(snapshot))
        self.assertNotIn("0801", repr(snapshot))
        self.assertNotIn("comment", snapshot)


class PercentageFloorTests(unittest.TestCase):
    def test_a_single_vote_never_shows_as_one_hundred_percent(self):
        share = aggregate.share_of_total(1, 1, percentage_floor=10)
        self.assertEqual(share, 90.0)
        self.assertLess(share, 100.0)

    def test_a_real_majority_still_shows_its_true_share(self):
        # The cap only bites near 100%. A 75% majority must not be inflated or deflated.
        self.assertEqual(aggregate.share_of_total(3, 4, percentage_floor=10), 75.0)
        self.assertEqual(aggregate.share_of_total(9, 10, percentage_floor=10), 90.0)

    def test_the_cap_never_invents_a_share_the_votes_do_not_support(self):
        # A small minority must render low, not be lifted up to the floor. Raising it
        # would be the more dangerous version of this feature.
        self.assertEqual(aggregate.share_of_total(1, 9, percentage_floor=10), 11.11111111111111)

    def test_owner_can_disable_the_cap(self):
        self.assertEqual(aggregate.share_of_total(1, 1, percentage_floor=0), 100.0)

    def test_zero_total_is_zero_share(self):
        self.assertEqual(aggregate.share_of_total(0, 0, percentage_floor=10), 0.0)

    def test_floor_is_validated(self):
        for bad in (-1, 101, "10", True, 1.5):
            with self.subTest(bad=bad):
                with self.assertRaises(validation.PollValidationError):
                    aggregate.share_of_total(1, 1, percentage_floor=bad)  # type: ignore[arg-type]

    def test_count_cannot_exceed_total(self):
        with self.assertRaises(ValueError):
            aggregate.share_of_total(5, 3, percentage_floor=0)


class PollPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = Path("docs/poll.html").read_text(encoding="utf-8")

    def test_the_poll_form_is_present_and_shares_the_request_categories(self):
        self.assertIn('id="poll"', self.html)
        self.assertIn('id="public-poll-form"', self.html)
        self.assertIn('id="poll-sector"', self.html)
        self.assertIn('id="poll-comment"', self.html)
        for key, _, _ in render.REQUEST_CATEGORIES:
            self.assertIn(f'value="{key}"', self.html)

    def test_the_build_ships_disabled_and_says_nothing_is_sent(self):
        # The disabled state is the safety property, so it is asserted in the markup.
        self.assertIn('data-poll-endpoint=""', self.html)
        self.assertIn('data-poll-configured="false"', self.html)
        self.assertIn("data-poll-submit disabled", self.html)
        self.assertIn("No vote is being recorded", self.html)
        self.assertEqual(render.POLL_ENDPOINT, "")

    def test_a_disabled_build_contains_no_code_path_that_can_send(self):
        script = render.POLL_SCRIPT
        # The fetch is guarded by the same endpoint check that disables the button, and
        # that check must come first in the source so the guard is visible.
        self.assertIn("if(!pollEndpointReady){", script)
        self.assertLess(script.index("if(!pollEndpointReady){"), script.index("await fetch("))
        self.assertIn("return;", script)
        # And an unconfigured endpoint must not even parse into a URL.
        self.assertIn("pollEndpointUrl=null", script)

    def test_the_poll_asks_for_no_direct_identity(self):
        # Scoped to the poll form: the request form further down this same page does
        # legitimately collect contact details, and asserting against the whole page
        # would fail for the right reason in the wrong place.
        form = self.html.split('id="public-poll-form"', 1)[1].split("</form>", 1)[0]
        for field in ("name", "phone", "email", "address", "voter_id",
                      "age", "age_years", "nin", "bvn", "date_of_birth"):
            with self.subTest(field=field):
                self.assertNotIn(f'name="{field}"', form)
        self.assertIn("No name, phone, email, address or voter ID is requested", self.html)
        self.assertIn("not a voter ID", self.html)

    def test_the_poll_form_only_binds_the_contract_fields(self):
        form = self.html.split('id="public-poll-form"', 1)[1].split("</form>", 1)[0]
        bound = set(re.findall(r'\bname="([a-z_]+)"', form))
        self.assertEqual(
            bound,
            {"sector", "lga", "ward_code", "comment", "age_band", "gender", "consent", "website"})

    def test_the_poll_offers_area_and_optional_demographics(self):
        self.assertIn('id="poll-lga"', self.html)
        self.assertIn('id="poll-ward"', self.html)
        self.assertIn('id="poll-age-band"', self.html)
        self.assertIn('id="poll-gender"', self.html)
        for lga in render.LGAS:
            self.assertIn(f'<option value="{lga}">', self.html)

    def test_the_poll_asks_for_a_group_never_an_exact_age(self):
        self.assertIn("Age group", self.html)
        self.assertIn("never an exact age", self.html)
        # No numeric age input exists at all, so there is nothing to leak an exact age.
        form = self.html.split('id="public-poll-form"', 1)[1].split("</form>", 1)[0]
        self.assertNotIn('type="number"', form)
        for label in ("18\u201325", "26\u201335", "66 and over"):
            self.assertIn(label, self.html)

    def test_gender_is_a_closed_list_with_a_decline(self):
        form = self.html.split('id="public-poll-form"', 1)[1].split("</form>", 1)[0]
        segment = form.split('id="poll-gender"', 1)[1].split("</select>", 1)[0]
        values = [v for v in re.findall(r'<option value="([^"]*)"', segment) if v]
        # The form sends "" for "Prefer not to say" rather than a namespaced marker; the
        # namespaced value stays in the vocabulary so an API client can send it too, and
        # both normalise to a decline.
        self.assertEqual(sorted(values), ["man", "woman"])
        # Two selects (age, gender), and each decline option carries the label twice: once
        # in data-en/data-ha and once as the element's own text.
        self.assertEqual(self.html.count("Prefer not to say"), 4)
        # The two real options must not share a Hausa label, which would be a silent bug
        # in a list whose whole job is telling two categories apart.
        self.assertNotEqual(render.POLL_GENDER_OPTIONS[0][2], render.POLL_GENDER_OPTIONS[1][2])
        self.assertEqual(len(render.POLL_GENDER_OPTIONS), 2)
        self.assertIn("gender_unspecified", validation.GENDER_OPTIONS)
        self.assertEqual(
            validation.validate_poll_response(payload(gender="gender_unspecified"), NOW)["gender"],
            "")

    def test_the_registration_area_is_optional_and_warns_about_suppression(self):
        self.assertIn("Registration area (optional)", self.html)
        self.assertIn("Leave this blank if you would rather not say", self.html)
        # The form must not promise a per-area result it may not be allowed to publish.
        self.assertIn("areas with very few answers are never published", self.html)

    def test_q2_is_labelled_a_comment_and_excluded_from_the_tally(self):
        self.assertIn("Comment (optional, not counted)", self.html)
        self.assertIn("never counted or published", self.html)

    def test_results_state_the_sample_is_not_representative(self):
        self.assertIn("self-selected visitors", self.html)
        self.assertIn("not a representative sample", self.html)
        self.assertIn("It is not a survey and not a vote", self.html)

    def test_an_unconnected_poll_renders_an_empty_state_not_zeros(self):
        # No snapshot file exists, so the page must say so. Seeding placeholder results
        # would be the worst possible failure here.
        self.assertIsNone(render.load_poll_snapshot())
        self.assertIn("No responses have been recorded yet.", self.html)
        self.assertNotIn('class="poll-bar-fill"', self.html)
        self.assertNotIn('class="poll-bars"', self.html)

    def test_no_placeholder_tally_is_committed_anywhere(self):
        path = render.DATA / render.POLL_SNAPSHOT_FILE
        self.assertFalse(path.exists(), "a poll snapshot was committed with no poll")
        self.assertFalse(
            any("poll_snapshot" in str(p) for p in Path("data").rglob("*.json")),
            "a poll snapshot exists but the poll is not connected")

    def test_the_dashboard_mounts_two_charts_a_dropdown_and_a_table(self):
        snapshot = aggregate.build_public_snapshot(
            repeated("water", n=8) + repeated("roads", n=6), generated_at=NOW)
        section = render.poll_results_section(snapshot)
        for mount in ("data-poll-sector-chart", "data-poll-lga-chart",
                      "data-poll-table", "data-poll-filter", "data-poll-snapshot"):
            with self.subTest(mount=mount):
                self.assertIn(mount, section)
        self.assertIn("14 responses", section)
        self.assertIn("Filter by LGA", section)
        for lga in render.LGAS:
            self.assertIn(f'<option value="{lga}">', section)

    def test_a_suppressed_cell_is_carried_as_null_into_the_page(self):
        # The page must be able to tell "too few to publish" from "nobody chose this",
        # which means the null has to survive into the embedded snapshot untouched.
        snapshot = aggregate.build_public_snapshot(
            repeated("water", n=3) + repeated("roads", n=8), generated_at=NOW)
        self.assertIsNone(snapshot["by_sector"]["water"])
        self.assertEqual(snapshot["by_sector"]["roads"], 8)
        section = render.poll_results_section(snapshot)
        self.assertIn('"water": null', section)
        self.assertIn('"roads": 8', section)
        self.assertIn("withheld", section)

    def test_the_snapshot_embedded_in_the_page_carries_no_comment(self):
        rows = repeated("water", n=8)
        for row in rows:
            row["comment"] = "Aminu Yusuf 08012345678"
        section = render.poll_results_section(
            aggregate.build_public_snapshot(rows, generated_at=NOW))
        self.assertNotIn("Aminu", section)
        self.assertNotIn("0801", section)

    def test_the_empty_snapshot_renders_the_empty_state(self):
        section = render.poll_results_section(
            aggregate.build_public_snapshot([], generated_at=NOW))
        self.assertIn("No responses have been recorded yet.", section)
        self.assertNotIn("poll-bars", section)

    def test_the_poll_lives_on_exactly_one_page(self):
        for slug in ("index", "achievements", "atlas", "agenda", "sources"):
            with self.subTest(page=slug):
                other = Path(f"docs/{slug}.html").read_text(encoding="utf-8")
                self.assertNotIn('id="public-poll-form"', other)
                self.assertNotIn('data-poll-endpoint', other)

    def test_the_poll_and_the_request_form_are_distinguishable(self):
        # They share a page, so the headings and the note have to keep them apart.
        self.assertIn("id=\"poll\"", self.html)
        self.assertIn("id=\"requests\"", self.html)
        self.assertIn("The request form below is separate", self.html)
        self.assertIn("very few answers are never published", self.html)

    def test_the_form_is_bilingual(self):
        for en, ha in (("Which sector should APM prioritise first?",
                        "Wane sector APM ya fi fahimta da farko?"),
                       ("Comment (optional, not counted)", "Sharhi (zaɓi, ba a taƙaita ba)"),
                       ("Cast vote", "Yi amsa"),
                       ("Woman", "Mace"),
                       ("Man", "Miji"),
                       ("Your LGA", "LGA da kake"),
                       ("Age group", "Shekaru"),
                       ("Gender", "Jinsi"),
                       ("Registration area (optional)", "Wurin ƙaura zaye (zaɓi)")):
            with self.subTest(label=en):
                self.assertIn(en, self.html)
                self.assertIn(ha, self.html)

    def test_the_dashboard_is_bilingual(self):
        # Asserted against the section builder, because the current build ships without a
        # snapshot and so renders the empty state instead of the charts.
        section = render.poll_results_section(
            aggregate.build_public_snapshot(repeated("water", n=8), generated_at=NOW))
        for en, ha in (("Sector priorities so far.", "Gabanawa na sectors har yanzu."),
                       ("Which sector comes first", "Wane sector ya farko"),
                       ("Responses by LGA", "Amsa ta LGA"),
                       ("Exact counts", "Adadin daidai"),
                       ("Filter by LGA", "Zaɓi ta LGA"),
                       ("Responses", "Amsa"),
                       ("Share", "Raba")):
            with self.subTest(label=en):
                self.assertIn(en, section)
                self.assertIn(ha, section)

    def test_the_poll_script_never_defines_a_name_the_request_script_defines(self):
        # Both blocks land in one inline <script>, so a repeated top-level `const` is a
        # SyntaxError that would disable every handler on the page.
        def top_level(script):
            import re
            return set(re.findall(r"^(?:const|let|var)\s+([A-Za-z_$][\w$]*)", script, re.M))
        overlap = top_level(render.POLL_SCRIPT) & top_level(render.REQUEST_SCRIPT)
        self.assertEqual(overlap, set(), f"poll and request scripts collide on {overlap}")


if __name__ == "__main__":
    unittest.main()
