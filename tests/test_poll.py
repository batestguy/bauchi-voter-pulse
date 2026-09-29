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


def response(sector="water", **overrides):
    record = {
        "sector": sector,
        "comment": "",
        "consent": True,
        "created_at": "2026-09-29T10:00:00Z",
    }
    record.update(overrides)
    return record


def payload(**overrides):
    body = {"sector": "water", "consent": True}
    body.update(overrides)
    return body


class PollSchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads(
            Path("src/poll/poll_schema.json").read_text(encoding="utf-8"))

    def test_schema_is_valid_json_and_forbids_extra_fields(self):
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(sorted(self.schema["required"]), ["consent", "sector"])

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
    def test_no_identity_field_is_collectable(self):
        for field in validation.FORBIDDEN_IDENTITY_FIELDS:
            with self.subTest(field=field):
                with self.assertRaises(validation.PollValidationError) as caught:
                    validation.validate_poll_response(payload(**{field: "anything"}))
                self.assertEqual(caught.exception.code, "identity_field_forbidden")
                self.assertEqual(caught.exception.field, field)

    def test_identity_fields_are_not_merely_silently_ignored(self):
        # The dangerous variant is a validator that strips the field and returns 200.
        # Rejecting is the only behaviour that keeps it off the wire.
        with self.assertRaises(validation.PollValidationError):
            validation.validate_poll_response(
                {"sector": "water", "consent": True, "email": "a@b.com"})

    def test_normalized_record_carries_no_identity_key(self):
        record = validation.validate_poll_response(payload(), NOW, response_id_generator=lambda: "APM-POLL-2026-00000001")
        for forbidden in validation.FORBIDDEN_IDENTITY_FIELDS:
            self.assertNotIn(forbidden, record)
        self.assertEqual(set(record), {"sector", "comment", "consent", "created_at", "response_id"})

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

    def test_every_configured_sector_is_present_so_the_axis_is_stable(self):
        tally = aggregate.tally_poll_responses([response("water")])
        self.assertEqual(set(tally["by_sector"]), set(validation.ALLOWED_SECTORS))
        self.assertEqual(tally["by_sector"]["security"], 0)

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
        self.assertTrue(all(v == 0 for v in snapshot["by_sector"].values()))
        self.assertIsNone(snapshot["reporting_period_start"])
        self.assertIsNone(snapshot["reporting_period_end"])

    def test_response_missing_created_at_is_rejected(self):
        row = response("water")
        del row["created_at"]
        tally = aggregate.tally_poll_responses([row])
        self.assertEqual(tally["total_responses"], 0)
        self.assertEqual(tally["_audit"]["invalid_created_at"], 1)

    def test_period_filtering_is_inclusive_at_both_ends(self):
        rows = [
            response("water", created_at="2026-09-01T00:00:00Z"),
            response("roads", created_at="2026-09-15T00:00:00Z"),
            response("education", created_at="2026-09-30T00:00:00Z"),
        ]
        tally = aggregate.tally_poll_responses(
            rows, period_start="2026-09-15T00:00:00Z", period_end="2026-09-30T00:00:00Z")
        self.assertEqual(tally["total_responses"], 2)
        self.assertEqual(tally["by_sector"]["water"], 0)
        self.assertEqual(tally["by_sector"]["roads"], 1)

    def test_inverted_period_is_rejected(self):
        with self.assertRaises(ValueError):
            aggregate.tally_poll_responses(
                [response()], period_start="2026-09-30T00:00:00Z",
                period_end="2026-09-01T00:00:00Z")


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

    def test_the_poll_asks_for_no_identifying_detail(self):
        # Scoped to the poll form: the request form further down this same page does
        # legitimately collect contact details, and asserting against the whole page
        # would fail for the right reason in the wrong place.
        form = self.html.split('id="public-poll-form"', 1)[1].split("</form>", 1)[0]
        for field in ("name", "phone", "email", "address", "ward_code", "voter_id",
                      "lga", "age", "nin", "bvn"):
            with self.subTest(field=field):
                self.assertNotIn(f'name="{field}"', form)
        self.assertIn("No name, phone, email, address, ward or voter ID is requested", self.html)
        self.assertIn("not a voter ID", self.html)

    def test_the_poll_form_only_binds_the_contract_fields(self):
        form = self.html.split('id="public-poll-form"', 1)[1].split("</form>", 1)[0]
        bound = set(re.findall(r'\bname="([a-z_]+)"', form))
        self.assertEqual(bound, {"sector", "comment", "consent", "website"})

    def test_q2_is_labelled_a_comment_and_excluded_from_the_tally(self):
        self.assertIn("Comment (optional, not counted)", self.html)
        self.assertIn("never counted or published", self.html)

    def test_results_state_the_sample_is_not_representative(self):
        self.assertIn("self-selected visitors", self.html)
        self.assertIn("not a representative sample", self.html)
        self.assertIn("It is not a survey, it is not a vote", self.html)

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

    def test_results_render_as_bars_once_a_real_snapshot_exists(self):
        snapshot = aggregate.build_public_snapshot(
            [response("water"), response("water"), response("roads")],
            generated_at=NOW, percentage_floor=10)
        section = render.poll_results_section(snapshot)
        self.assertIn('class="poll-bars"', section)
        self.assertIn("3 responses", section)
        self.assertIn("poll-bar-fill", section)
        # Bars are ranked by count, so water (2) precedes roads (1).
        self.assertLess(section.index("Water"), section.index("Roads"))
        # And the single-vote floor is visible in the rendered width, not only in Python.
        self.assertIn("width:66.7%", section)

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
        self.assertIn("records one sector choice and an optional comment", self.html)

    def test_both_forms_are_bilingual(self):
        for en, ha in (("Which sector should APM prioritise first?",
                        "Wane sector APM ya fi fahimta da farko?"),
                       ("Comment (optional, not counted)", "Sharhi (zaɓi, ba a taƙaita ba)"),
                       ("Cast vote", "Yi amsa"),
                       ("Sector priorities so far.", "Fihimmanci na sectors har yanzu.")):
            with self.subTest(label=en):
                self.assertIn(en, self.html)
                self.assertIn(ha, self.html)

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
