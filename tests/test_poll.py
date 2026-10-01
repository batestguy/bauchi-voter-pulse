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
import csv
import json
import re
import shutil
import subprocess
import tempfile
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


# The published demographic vocabularies, as snapshot keys. A declined value is stored as
# an empty string and therefore never appears in a published map, so a decline cannot be
# mistaken for a group here.
DEMOGRAPHIC_KEYS = frozenset({
    "age_18_25", "age_26_35", "age_36_45", "age_46_55", "age_56_65", "age_66_plus",
    "woman", "man",
})
AREA_PREFIX = "RA-"


def leaf_paths(tree, prefix=()):
    """Yield the key path leading to every count leaf in a nested count map.

    A snapshot map is `key -> key -> ... -> count`, so a path is the full chain of
    dimensions a reader would have to select to reach that number. Asserting on paths
    rather than on individual maps is what makes "a registration area and a demographic
    never appear together" checkable at all: it is a statement about the whole tree.
    """
    if isinstance(tree, dict):
        for key, value in tree.items():
            yield from leaf_paths(value, prefix + (key,))
    else:
        yield prefix


def inner_maps(tree):
    """Yield ``(key_path, innermost_count_map)`` for every nesting level of a count map."""
    if isinstance(tree, dict):
        values = list(tree.values())
        if values and all(isinstance(v, dict) for v in values):
            for key, value in tree.items():
                yield from inner_maps(value)
            return
        yield (), tree



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

    def test_a_demographic_is_never_published_below_lga_level(self):
        # Two rules, asserted as one walk over every cross the module builds rather than
        # by naming maps, so a cross added later cannot quietly breach either:
        #   1. a registration area and a demographic never appear in the same key path;
        #   2. a demographic is only ever scoped by an LGA or by the whole state -- the
        #      level above it is never anything finer than an LGA.
        # Rule 2 permits "nothing above it" on purpose: `by_gender_sector` is statewide,
        # which is a coarser scope than an LGA and therefore not a breach. What it forbids
        # is a demographic hanging off a registration area, which rule 1 already catches.
        #
        # Both the raw tally and the published snapshot are walked. The tally is where a
        # forbidden cross would actually be *built*, and building one is the privacy
        # decision -- publishing it is only a later, separate mistake. Checking only the
        # snapshot would let a forbidden cross sit in the tally indefinitely, one forgotten
        # return-dict edit away from publication.
        rows = repeated("water", n=8) + repeated("roads", n=7)
        for row in rows:
            row["ward_code"] = "RA-001"
            row["age_band"] = "age_26_35"
            row["gender"] = "woman"
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)
        lgas = set(validation.BAUCHI_LGAS)

        trees = dict(snapshot)
        trees.update(aggregate.tally_poll_responses(rows))
        checked = 0
        for map_name, tree in sorted(trees.items()):
            if not map_name.startswith("by_"):
                continue
            for path in leaf_paths(tree):
                checked += 1
                has_area = any(str(k).startswith(AREA_PREFIX) for k in path)
                has_demo = any(k in DEMOGRAPHIC_KEYS for k in path)
                with self.subTest(map=map_name, path=path):
                    self.assertFalse(
                        has_area and has_demo,
                        f"{map_name} reaches a number through both a registration area "
                        f"and a demographic: {path}")
                    if not has_demo or not path:
                        continue
                    index = min(
                        i for i, k in enumerate(path) if k in DEMOGRAPHIC_KEYS)
                    if index == 0:
                        continue  # statewide, which is coarser than an LGA
                    self.assertIn(
                        path[index - 1], lgas,
                        f"{map_name} scopes a demographic by {path[index-1]!r}, which is "
                        f"finer than an LGA")
        self.assertGreater(checked, 0, "the walk checked nothing at all")

    def test_the_forbidden_crosses_are_named_and_absent(self):
        # The refusal lives in data, not only in prose, so a test can assert against it and
        # a future cross has to be added deliberately rather than by accident.
        self.assertIn("ward_x_gender", aggregate.FORBIDDEN_CROSSINGS)
        self.assertIn("ward_x_age_band", aggregate.FORBIDDEN_CROSSINGS)
        self.assertIn("ward_x_sector_x_gender", aggregate.FORBIDDEN_CROSSINGS)
        for crossing in aggregate.FORBIDDEN_CROSSINGS:
            with self.subTest(crossing=crossing):
                self.assertTrue(crossing.startswith("ward_"))
                self.assertNotIn(crossing, aggregate.PUBLIC_SNAPSHOT_FIELDS)

    def test_the_area_and_demographic_crosses_are_built(self):
        # The three grains the dashboard reads: area x sector, LGA x demographic x sector,
        # and demographic x sector statewide. Each answers a different planning question
        # and each is a different size, which is why all three exist.
        rows = (repeated("water", n=8, ward_code="RA-001", age_band="age_26_35",
                         gender="woman")
                + repeated("roads", n=7, ward_code="RA-001", age_band="age_26_35",
                           gender="woman")
                + repeated("education", n=6, lga="Bogoro", age_band="age_18_25",
                           gender="man"))
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)

        # Area x sector: an area cross, stopped at area.
        self.assertEqual(snapshot["by_ward_sector"]["RA-001"],
                         {"roads": 7, "water": 8})
        # LGA x gender x sector.
        self.assertEqual(
            snapshot["by_lga_gender_sector"]["Bauchi"]["woman"],
            {"roads": 7, "water": 8})
        # LGA x age x sector.
        self.assertEqual(
            snapshot["by_lga_age_band_sector"]["Bauchi"]["age_26_35"],
            {"roads": 7, "water": 8})
        # Demographic x sector statewide, which is the view most likely to publish.
        self.assertEqual(snapshot["by_gender_sector"]["woman"],
                         {"roads": 7, "water": 8})
        self.assertEqual(snapshot["by_age_band_sector"]["age_18_25"],
                         {"education": 6})

    def test_every_new_cross_honours_the_suppression_floor(self):
        # Adding a dimension to the UI must not lower the privacy bar. Each new map is
        # checked cell by cell against the floor the snapshot declares.
        rows = (repeated("water", n=8, ward_code="RA-001", age_band="age_26_35",
                         gender="woman")
                + repeated("roads", n=2, ward_code="RA-001", age_band="age_26_35",
                           gender="woman")
                + repeated("education", n=2, ward_code="RA-002", age_band="age_26_35",
                           gender="woman"))
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)
        floor = snapshot["small_count_threshold"]
        for map_name in ("by_ward_sector", "by_lga_age_band_sector",
                         "by_lga_gender_sector", "by_age_band_sector",
                         "by_gender_sector"):
            with self.subTest(map=map_name):
                self.assertIn(map_name, snapshot)
                for _path, counts in inner_maps(snapshot[map_name]):
                    for value in counts.values():
                        if value is not None:
                            self.assertGreaterEqual(value, floor)
        # The two small cells are withheld, in every map they appear in.
        self.assertIsNone(snapshot["by_ward_sector"]["RA-001"]["roads"])
        self.assertIsNone(snapshot["by_lga_gender_sector"]["Bauchi"]["woman"]["roads"])
        self.assertIsNone(snapshot["by_gender_sector"]["woman"]["roads"])
        # The large sibling still publishes, so suppression is not blanking the whole group.
        self.assertEqual(snapshot["by_ward_sector"]["RA-001"]["water"], 8)

    def test_a_suppressed_cell_keeps_its_key(self):
        # "This group answered, but too few to publish" and "this group never existed" are
        # different facts. Dropping the key would collapse them, and the dashboard renders
        # a withheld cell differently from an absent one.
        rows = repeated("water", n=8) + repeated("roads", n=2)
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)
        self.assertIn("roads", snapshot["by_sector"])
        self.assertIsNone(snapshot["by_sector"]["roads"])
        self.assertEqual(snapshot["by_sector"]["water"], 8)

    def test_nested_suppression_matches_the_flat_rule_exactly(self):
        # `suppress_nested` is a second implementation of a privacy floor, and a second
        # implementation is exactly the kind of thing that drifts from the first.
        for threshold in (2, 5, 9):
            with self.subTest(threshold=threshold):
                flat = {str(n): n for n in range(0, 12)}
                expected, expected_n = aggregate.suppress(flat, threshold)
                actual, actual_n = aggregate.suppress_nested(flat, threshold)
                self.assertEqual(actual, expected)
                self.assertEqual(actual_n, expected_n)

    def test_nested_suppression_keeps_a_zero_published(self):
        # A zero identifies nobody. Suppressing it would read as "too few to say", which is
        # a different and weaker statement.
        actual, suppressed = aggregate.suppress_nested({"a": {"water": 0}}, 5)
        self.assertEqual(actual, {"a": {"water": 0}})
        self.assertEqual(suppressed, 0)

    def test_publishable_cells_sum_to_their_own_marginal(self):
        # The dashboard divides a cell by the group's own total. When nothing was withheld
        # the parts must add up to the whole, or every percentage on the page is wrong.
        rows = (repeated("water", n=8, age_band="age_26_35")
                + repeated("roads", n=7, age_band="age_26_35")
                + repeated("security", n=6, age_band="age_18_25"))
        snapshot = aggregate.build_public_snapshot(rows, generated_at=NOW)
        wide = snapshot["by_age_band_sector"]["age_26_35"]
        per_lga = snapshot["by_lga_age_band_sector"]["Bauchi"]["age_26_35"]
        self.assertEqual(sum(wide.values()), sum(per_lga.values()))
        self.assertEqual(sum(wide.values()),
                         snapshot["by_lga_age_band"]["Bauchi"]["age_26_35"])
        self.assertEqual(sum(wide.values()) + 6, snapshot["by_lga"]["Bauchi"])


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


class CommentStorageTests(unittest.TestCase):
    """Where a stored complaint is kept, and for how long.

    The owner wants the comments kept — they are the part of the poll no tally can replace.
    So these tests do not argue for deleting them. They pin down the two things that make
    keeping them defensible: the stored row cannot be joined back to the respondent, and it
    cannot accumulate forever without something deleting it.
    """

    def _record(self, **overrides):
        record = response(
            comment="Our borehole has been dry since March",
            ward_code="RA-001",
            age_band="age_26_35",
            gender="woman",
            **overrides,
        )
        return record

    def test_a_stored_comment_keeps_what_the_study_needs(self):
        stored = validation.comment_record(self._record())
        self.assertEqual(stored["comment"], "Our borehole has been dry since March")
        self.assertEqual(stored["sector"], "water")
        self.assertEqual(stored["lga"], "Bauchi")
        self.assertEqual(stored["created_at"], "2026-09-29T10:00:00Z")

    def test_a_stored_comment_carries_no_area_no_demographics_and_no_join_key(self):
        # The whole rule, in one assertion. A distinctive complaint plus a registration
        # area plus an age band plus a gender is a person, and the response_id is the key
        # that would let the two tabs be re-joined by anyone who can read both.
        stored = validation.comment_record(self._record())
        self.assertEqual(set(stored), set(validation.COMMENT_RECORD_FIELDS))
        flat = json.dumps(stored)
        for forbidden in ("RA-001", "age_26_35", "woman", "ward", "gender", "response_id"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, flat)

    def test_the_projection_cannot_grow_a_field_without_a_deliberate_change(self):
        # COMMENT_RECORD_FIELDS is exported as data, so adding a column to the stored
        # comment is a change to a tuple a reviewer can see rather than a silent extra key.
        self.assertEqual(
            validation.COMMENT_RECORD_FIELDS,
            ("sector", "lga", "comment", "created_at"))

    def test_a_vote_with_no_comment_stores_no_comment(self):
        # Otherwise the Comments tab becomes a second copy of the vote count.
        self.assertEqual(validation.comment_record(response(comment="")), {})
        self.assertEqual(validation.comment_record(response(comment="   ")), {})
        self.assertEqual(validation.comment_record(response()), {})

    def test_stored_comments_are_not_quoted_anywhere_on_the_public_page(self):
        # The two projections are opposite directions. A comment may be STORED and must
        # still never be PUBLISHED, so the public path is checked to still exclude it.
        stored = validation.comment_record(self._record())
        self.assertNotIn("comment", validation.public_projection(self._record()))
        self.assertNotIn("ward_code", stored)

    def test_the_retention_ceiling_is_refused_rather_than_honoured(self):
        # The direction is the point. Holding free text gets riskier the longer it is
        # held, so the value that must be refused is the LARGE one -- the mirror image of
        # the small-cell floor, which refuses small values.
        self.assertEqual(
            validation.validate_comment_retention_days(365),
            validation.MAX_COMMENT_RETENTION_DAYS)
        for too_long in (366, 1000, 10_000, 365 * 10):
            with self.subTest(days=too_long):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_comment_retention_days(too_long)
                self.assertEqual(caught.exception.code,
                                 "invalid_comment_retention_days")

    def test_zero_retention_is_refused_because_it_is_a_permissive_lie(self):
        # "Keep for 0 days" reads as "do not keep these". If the implementation then failed
        # to delete anything, the setting would be false in the direction that matters.
        for zeroish in (0, -1, -365):
            with self.subTest(days=zeroish):
                with self.assertRaises(validation.PollValidationError):
                    validation.validate_comment_retention_days(zeroish)

    def test_the_default_retention_is_inside_the_bounds(self):
        self.assertEqual(
            validation.validate_comment_retention_days(
                validation.DEFAULT_COMMENT_RETENTION_DAYS),
            validation.DEFAULT_COMMENT_RETENTION_DAYS)
        self.assertGreater(validation.DEFAULT_COMMENT_RETENTION_DAYS,
                           validation.MIN_COMMENT_RETENTION_DAYS)
        self.assertLessEqual(validation.DEFAULT_COMMENT_RETENTION_DAYS,
                             validation.MAX_COMMENT_RETENTION_DAYS)

    def test_a_non_integer_retention_is_refused(self):
        # A float of 2.5 days cannot be honoured by a daily trigger, so it is a
        # misconfiguration rather than a rounding question.
        for bad in ("180", 180.5, None, True):
            with self.subTest(value=bad):
                with self.assertRaises(validation.PollValidationError):
                    validation.validate_comment_retention_days(bad)


class PollEndpointScriptTests(unittest.TestCase):
    """The Apps Script endpoint, which is a paste-and-deploy step on the owner's account.

    An agent cannot reach a Google account, so this file cannot be executed by the agent
    that would otherwise review it. That is exactly why it needs its own harness: the
    endpoint is the one piece of code that decides what a member of the public can write
    into the campaign's records, and "it looked right" is a weak form of evidence for it.

    `docs/apps-script/test_endpoint.mjs` loads the real Code.gs with the Apps Script
    globals stubbed and runs the real doPost. It is not a mock of the endpoint; it is the
    endpoint, with only the platform objects faked.
    """

    APPS = Path("docs/apps-script")

    def setUp(self):
        self.code_path = self.APPS / "Code.gs"
        self.harness = self.APPS / "test_endpoint.mjs"
        if not self.code_path.exists():
            self.skipTest("Code.gs is generated; run build_code_gs.py")

    def _node(self):
        return shutil.which("node") or shutil.which("nodejs")

    def test_the_generated_script_is_valid_javascript(self):
        # A syntax error here is invisible until the owner deploys, at which point the
        # endpoint is dead and the poll silently accepts nothing.
        node = self._node()
        if not node:
            self.skipTest("node not available")
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "code.js"
            probe.write_text(
                self.code_path.read_text(encoding="utf-8"), encoding="utf-8")
            result = subprocess.run([node, "--check", str(probe)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr[-600:])

    def test_the_endpoint_harness_passes(self):
        node = self._node()
        if not node:
            self.skipTest("node not available")
        result = subprocess.run([node, str(self.harness)],
                                capture_output=True, text=True)
        self.assertEqual(
            result.returncode, 0,
            "the endpoint harness failed; it exists to catch validation defects before "
            f"deployment, not after:\n{result.stdout}\n{result.stderr}")

    def test_the_endpoint_vocabularies_have_not_drifted_from_the_contract(self):
        # The endpoint re-implements every rule in src/poll/validation.py, because the
        # browser cannot be trusted. Two implementations of one rule drift unless
        # something asserts they agree, and drift here is silent: a sector accepted by one
        # and refused by the other is not visible until real people are turned away.
        code = self.code_path.read_text(encoding="utf-8")
        vocabularies = (
            ("ALLOWED_SECTORS", validation.ALLOWED_SECTORS),
            ("BAUCHI_LGAS", validation.BAUCHI_LGAS),
            ("AGE_BANDS", validation.AGE_BANDS),
            ("GENDER_OPTIONS", validation.GENDER_OPTIONS),
            ("FORBIDDEN_IDENTITY_FIELDS", validation.FORBIDDEN_IDENTITY_FIELDS),
        )
        for name, expected in vocabularies:
            with self.subTest(vocabulary=name):
                block = _js_array(code, name)
                self.assertIsNotNone(block, f"{name} not found in Code.gs")
                values = _js_string_list(block)
                for value in expected:
                    self.assertIn(
                        value, values,
                        f"{name} in Code.gs is missing {value!r} from the contract")

    def test_the_endpoint_retention_has_not_drifted_from_the_contract(self):
        # The endpoint enforces the purge, so its copy of the retention numbers is the one
        # that decides how long a respondent's words survive. Drift here is silent in the
        # same way vocabulary drift is: the endpoint would quietly delete on a schedule
        # nobody approved, or refuse to delete at all.
        code = self.code_path.read_text(encoding="utf-8")

        def constant(name):
            match = re.search(rf"var\s+{name}\s*=\s*(\d+)\s*;", code)
            self.assertIsNotNone(match, f"{name} not found in Code.gs")
            return int(match.group(1))

        self.assertEqual(constant("COMMENT_RETENTION_DAYS"),
                         validation.DEFAULT_COMMENT_RETENTION_DAYS)
        self.assertEqual(constant("MAX_COMMENT_RETENTION_DAYS"),
                         validation.MAX_COMMENT_RETENTION_DAYS)
        self.assertEqual(constant("MIN_COMMENT_RETENTION_DAYS"),
                         validation.MIN_COMMENT_RETENTION_DAYS)

    def test_the_endpoint_splits_the_comment_onto_its_own_tab(self):
        # The split is the whole privacy argument for keeping comments, so it is asserted
        # against the literal header rows rather than left to a visual read: a header that
        # grew a ward_code, or a Responses header that grew a comment, would be invisible
        # in a diff-sized glance at 400 lines of generated JavaScript.
        code = self.code_path.read_text(encoding="utf-8")
        responses_header = re.search(
            r"responses\.appendRow\(\[(.*?)\]\)", code, re.S)
        self.assertIsNotNone(responses_header, "Responses header not found")
        responses_columns = _js_string_list(responses_header.group(1))
        comments_header = re.search(
            r"comments\.appendRow\(\[(.*?)\]\)", code, re.S)
        self.assertIsNotNone(comments_header, "Comments header not found")
        comments_columns = _js_string_list(comments_header.group(1))

        self.assertNotIn("comment", responses_columns)
        self.assertEqual(comments_columns,
                         ["sector", "lga", "received_at", "comment"])
        for forbidden in ("ward_code", "age_band", "gender", "response_id"):
            with self.subTest(column=forbidden):
                self.assertNotIn(forbidden, comments_columns)

    def test_the_endpoint_actually_purges_rather_than_only_documenting_it(self):
        # "Retained for 180 days" is a sentence. These three names are the mechanism, and
        # each one missing would leave the sentence unenforced in a different way: no purge
        # to call, no ceiling to validate, no trigger to run it.
        code = self.code_path.read_text(encoding="utf-8")
        for function in ("purgeExpiredComments", "validateRetentionDays_",
                         "installRetention"):
            with self.subTest(function=function):
                self.assertIn(f"function {function}(", code)

    def test_the_endpoint_ward_map_matches_the_form(self):
        # The form offers areas from data/delivery/lga_wards.csv. If the endpoint's map
        # disagrees, a respondent can select an area the endpoint then refuses.
        with open("data/delivery/lga_wards.csv", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        code = self.code_path.read_text(encoding="utf-8")
        match = re.search(r"var WARD_MAP_SOURCE = '([^']*)';", code)
        self.assertIsNotNone(match, "WARD_MAP_SOURCE not found in Code.gs")
        pairs = {}
        for group in match.group(1).split(";"):
            lga, _, codes = group.partition(":")
            pairs[lga] = {c for c in codes.split(",") if c}
        expected = {}
        for row in rows:
            expected.setdefault(row["lga"], set()).add(row["ward_code"])
        self.assertEqual(pairs, expected)
        self.assertEqual(
            sum(len(v) for v in pairs.values()), 212,
            "every registration area in lga_wards.csv must be in the endpoint's map")


def _js_array(source, name):
    """Return the body of a `var NAME = [ ... ];` literal in a JS source file."""
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*\[(.*?)\];", source, re.S)
    return match.group(1) if match else None


def _js_string_list(body):
    return re.findall(r"'([^']*)'", body)


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

    def test_the_button_state_and_the_endpoint_agree(self):
        # This used to assert the build ships disabled, which was true and then stopped
        # being true when the endpoint was connected. The invariant worth keeping is not
        # "disabled" -- it is that the button's state is derived from the endpoint, so an
        # empty endpoint can never present a live button. Asserting a fixed state would
        # mean editing this test at the moment of connection, which is exactly when a test
        # is least likely to be read carefully.
        configured = render.POLL_ENDPOINT.strip()
        if configured:
            self.assertTrue(configured.startswith("https://"), "endpoint must be https")
            self.assertIn("/exec", configured)
            self.assertIn('data-poll-configured="true"', self.html)
            self.assertNotIn("data-poll-submit disabled", self.html)
            # A connected poll must still refuse to claim identity.
            self.assertIn("No name, phone, email, address or voter ID is requested", self.html)
        else:
            self.assertIn('data-poll-endpoint=""', self.html)
            self.assertIn('data-poll-configured="false"', self.html)
            self.assertIn("data-poll-submit disabled", self.html)
            self.assertIn("No vote is being recorded", self.html)

    def test_an_empty_endpoint_still_renders_as_closed(self):
        # The disabled path must survive being unused, or it silently rots the next time
        # someone clears the constant. This re-renders the whole site with the endpoint
        # forced empty and asserts nothing can send.
        original = render.POLL_ENDPOINT
        target = Path("docs/poll.html")
        backup = target.read_text(encoding="utf-8")
        try:
            render.POLL_ENDPOINT = ""
            render.render()
            html = target.read_text(encoding="utf-8")
            self.assertIn('data-poll-endpoint=""', html)
            self.assertIn("data-poll-submit disabled", html)
            self.assertIn("No vote is being recorded", html)
            script = render.POLL_SCRIPT
            self.assertIn("if(!pollEndpointReady){", script)
            self.assertLess(script.index("if(!pollEndpointReady){"),
                            script.index("await fetch("))
        finally:
            render.POLL_ENDPOINT = original
            target.write_text(backup, encoding="utf-8")

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

    def test_q2_invites_a_comment_without_announcing_the_tally_rule(self):
        self.assertIn("Say a bit more (optional)", self.html)
        # The privacy warning stays: it is what stops the writer putting their
        # own name, phone and address into a public record.
        self.assertIn("Please do not include your name, phone number, address",
                      self.html)

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
                      "data-poll-table", "data-poll-filter", "data-poll-snapshot",
                      "data-poll-ward-filter", "data-poll-lens-filter",
                      "data-poll-scope-summary", "data-poll-share-note"):
            with self.subTest(mount=mount):
                self.assertIn(mount, section)
        self.assertIn("14 responses", section)
        self.assertIn("LGA", section)
        for lga in render.LGAS:
            self.assertIn(f'<option value="{lga}">', section)

    def test_the_dashboard_offers_area_and_demographic_scopes(self):
        # The three scope controls the reader uses to ask "what does this group want".
        # A missing one is a silently smaller dashboard, so each is asserted by name.
        snapshot = aggregate.build_public_snapshot(
            repeated("water", n=8) + repeated("roads", n=6), generated_at=NOW)
        section = render.poll_results_section(snapshot)
        self.assertIn('data-poll-filter', section)
        self.assertIn('data-poll-ward-filter', section)
        self.assertIn('data-poll-lens-filter', section)
        # The lens offers every gender and every age band, and nothing else.
        for key, _en, _ha in render.POLL_GENDER_OPTIONS:
            self.assertIn(f'value="g:{key}"', section)
        for key, _en, _ha in render.POLL_AGE_BANDS:
            self.assertIn(f'value="a:{key}"', section)

    def test_the_dashboard_cannot_offer_a_registration_area_with_a_demographic(self):
        # The forbidden cross is ward x demographic. Two independent dropdowns plus a ward
        # list would be three clicks from publishing it, so the page must not ship that
        # shape: the lens is reset and disabled when an area is chosen, and the reason is
        # shown rather than left for the reader to work out.
        script = render.POLL_SCRIPT
        self.assertIn("data-poll-lens-filter", script)
        self.assertIn("data-poll-lens-lock", script)
        section = render.poll_results_section(
            aggregate.build_public_snapshot(repeated("water", n=8), generated_at=NOW))
        self.assertIn("data-poll-lens-lock", section)
        self.assertIn("Age group and gender are switched off for a registration area",
                      section)
        # The lock note must be hidden until an area is actually chosen.
        self.assertIn('data-poll-lens-lock hidden', section)
        self.assertIn("if(blocked)pollState.lens='';", script)
        self.assertIn("select.disabled=blocked;", script)

    def test_the_lens_group_headers_can_actually_be_translated(self):
        # An <optgroup>'s visible text is its `label` ATTRIBUTE, and `setLanguage` only
        # rewrites `textContent`. So the header needs its own pass.
        #
        # The pair must NOT be carried as data-en/data-ha. `setLanguage` implements that
        # pair with `textContent`, so on an <optgroup> -- which OWNS the options -- it
        # deleted every option on the first language switch. The Group dropdown went from
        # nine options to one. `data-poll-label-*` names are outside setLanguage's reach.
        section = render.poll_results_section(
            aggregate.build_public_snapshot(repeated("water", n=8), generated_at=NOW))
        for english, hausa in (("Gender", "Jinsi"), ("Age group", "Shekaru")):
            with self.subTest(header=english):
                self.assertIn(f'data-poll-label-en="{english}"', section)
                self.assertIn(f'data-poll-label-ha="{hausa}"', section)
                self.assertIn(f'label="{english}"', section)
        # The forbidden names must not reappear on the optgroup.
        self.assertNotIn('data-en="Gender" data-ha="Jinsi"', section)
        self.assertNotIn('data-en="Age group" data-ha="Shekaru"', section)
        # ...and the script must copy the pair onto the attribute on every render.
        script = render.POLL_SCRIPT
        self.assertIn("const pollSyncLensGroupLabels=()=>", script)
        self.assertIn("group.setAttribute('label',currentLanguage==='ha'&&ha?ha:en);", script)
        self.assertIn("[data-poll-optgroup]", script)
        self.assertIn("pollSyncLensGroupLabels();", script)

    def test_the_dashboard_never_shows_a_share_it_cannot_compute(self):
        # A percentage is a division. If a sibling cell in the same scope was suppressed the
        # true denominator is unknown, so a percentage would understate the group and look
        # precise. The page must gate the share on every cell being publishable.
        script = render.POLL_SCRIPT
        self.assertIn("const pollShareIsExact=scope=>", script)
        self.assertIn("return values.every(value=>typeof value==='number');", script)
        # The gate must be consulted before any share is written to the page.
        self.assertIn("if(exact){", script)
        self.assertIn("data-poll-share-note", script)
        # ...and the table must not fall back to a stale denominator when it is withheld.
        self.assertIn("c2.className='is-share-withheld';", script)

    def test_the_group_size_has_three_distinct_states(self):
        # "487 women answered", "at least 20 answered" and "too few to show" are three
        # different facts. A regression here made the statewide gender lens report "too few
        # to show" for a group of nearly five hundred people, because only the LGA case had
        # a published marginal to divide by. So the states must be asserted by name.
        script = render.POLL_SCRIPT
        # Statewide x demographic has no marginal, so it sums its own publishable cells.
        self.assertIn("allPublishable?visible.reduce((sum,cell)=>sum+cell,0):null", script)
        # When something is withheld the sum becomes an explicit lower bound, not a total.
        self.assertIn("lowerBound:", script)
        self.assertIn("if(scope.lowerBound)return false;", script)
        # And the reader is told which of the three they are looking at.
        self.assertIn("if(typeof scope.total==='number')", script)
        self.assertIn("else if(scope.lowerBound)", script)
        self.assertIn("at least ", script)
        self.assertIn("answers in this group: too few to show", script)

    def test_the_area_scope_uses_a_published_marginal_not_its_own_sum(self):
        # A registration area and an LGA x demographic scope both have a published count of
        # how many people are in the group. Dividing by the sum of the visible cells instead
        # would silently disagree with that published number whenever anything was withheld.
        script = render.POLL_SCRIPT
        self.assertIn("total:totalOf(snap.by_ward,pollState.ward),", script)
        self.assertIn("total:totalOf((margin[pollState.lga]||{}),value),", script)
        self.assertIn("total:totalOf(snap.by_lga,pollState.lga),", script)

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
                        "Wane sector APM ya fi gabanawa da farko?"),
                       ("Say a bit more (optional)", "Kara bayan aƙari (zaɓi)"),
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
                       ("Which sector this group put first",
                        "Wane sector wannan ƙungiya ya farko"),
                       ("Responses by LGA", "Amsa ta LGA"),
                       ("Exact counts", "Adadin daidai"),
                       ("Registration area", "Wurin ƙaura zaye"),
                       ("Group", "ƙungiya"),
                       ("Everyone", "Kowa"),
                       ("Who answered", "Wa suka amsa"),
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


class ContentTypePreflightTests(unittest.TestCase):
    """The POST must not declare `application/json`.

    This is the one bug in the whole endpoint integration that no test could have caught
    and that a unit test alone would never have found, because the failure only exists in a
    real browser talking to a real Google deployment.

    `application/json` is not a CORS-safelisted request content type, so the browser sends
    an `OPTIONS` preflight before the POST. Google Apps Script answers that preflight with
    `200 OK` and **no `Access-Control-Allow-*` headers at all**, the browser therefore
    blocks the exchange, and `fetch` rejects with a bare `TypeError: Failed to fetch` --
    no console error, no status code, and a user-visible message saying only "we could not
    send your vote". The vote is never recorded and nothing says why.

    `text/plain;charset=utf-8` is safelisted, so no preflight is sent. Both endpoints read
    `e.postData.contents` and never inspect `e.contentType`, so the JSON body still parses
    identically. Measured against the live poll deployment on 1 October 2026:

        Content-Type: application/json       -> TypeError: Failed to fetch
        Content-Type: text/plain;charset=utf-8 -> 200 {"response_id":"APM-POLL-2026-..."}

    Asserted on both scripts, because the request form sends the same way and would fail
    the same way, silently, on the day it was connected.
    """

    def _fetch_calls(self, script):
        return [line for line in script.splitlines() if "fetch(" in line]

    def test_the_poll_does_not_send_a_content_type_that_triggers_a_preflight(self):
        for line in self._fetch_calls(render.POLL_SCRIPT):
            with self.subTest(line=line.strip()[:80]):
                self.assertNotIn("'Content-Type':'application/json'", line)
                self.assertIn("'Content-Type':'text/plain;charset=utf-8'", line)

    def test_the_request_form_does_not_either(self):
        for line in self._fetch_calls(render.REQUEST_SCRIPT):
            with self.subTest(line=line.strip()[:80]):
                self.assertNotIn("'Content-Type':'application/json'", line)
                self.assertIn("'Content-Type':'text/plain;charset=utf-8'", line)

    def test_neither_script_declares_json_as_a_request_content_type(self):
        for name, script in (("poll", render.POLL_SCRIPT),
                             ("request", render.REQUEST_SCRIPT)):
            with self.subTest(script=name):
                self.assertNotIn("'Content-Type': 'application/json'", script)
                self.assertNotIn('"Content-Type": "application/json"', script)

    def test_the_endpoints_do_not_require_a_json_content_type_to_parse(self):
        # The other half of the fix. If either endpoint ever started validating
        # `e.contentType`, the safelisted workaround would stop being safe, so the
        # guarantee has to be asserted on the endpoint rather than assumed.
        for path in ("docs/apps-script/Code.gs",
                     "docs/requests-script/Code.gs"):
            source = Path(path).read_text(encoding="utf-8")
            with self.subTest(endpoint=path):
                self.assertIn("postData.contents", source)
                self.assertNotIn("e.contentType", source)
                self.assertNotIn("contentType ==", source)


if __name__ == "__main__":
    unittest.main()
