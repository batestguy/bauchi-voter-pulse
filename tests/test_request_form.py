import unittest
from pathlib import Path

from src.dashboard import render


class RequestFormContractTests(unittest.TestCase):
    def setUp(self):
        self.html = Path("docs/poll.html").read_text(encoding="utf-8")
        optional = render.read_optional_csv(render.LGA_WARDS_FILE)
        self.ward_rows = optional[0] if optional else []

    def test_request_form_has_approved_location_and_category_options(self):
        self.assertIn('id="requests"', self.html)
        self.assertIn('action="about:blank"', self.html)
        self.assertIn('onsubmit="return false"', self.html)
        self.assertIn('id="public-request-form"', self.html)
        self.assertIn('id="request-lga"', self.html)
        self.assertIn('id="request-ward-code"', self.html)
        self.assertIn('data-request-ra-lga="Bauchi"', self.html)
        self.assertEqual(self.html.count('data-request-ra-lga='), len(self.ward_rows))
        self.assertEqual(len(self.ward_rows), 212)
        for key, _, _ in render.REQUEST_CATEGORIES:
            self.assertIn(f'value="{key}"', self.html)

    def test_the_request_button_state_and_the_endpoint_agree(self):
        # This asserted the build ships disabled, which was true until the endpoint was
        # connected. The invariant worth keeping is not "disabled" -- it is that the state
        # is DERIVED from the endpoint, so an empty endpoint can never present a live
        # button. Hardcoding a state means editing the test at the moment of connection,
        # which is exactly when a test is least likely to be read carefully.
        configured = render.REQUEST_ENDPOINT.strip()
        if configured:
            self.assertTrue(configured.startswith("https://"), "endpoint must be https")
            self.assertIn("/exec", configured)
            self.assertIn('data-request-configured="true"', self.html)
            self.assertNotIn("data-request-submit disabled", self.html)
        else:
            self.assertIn('data-request-endpoint=""', self.html)
            self.assertIn('data-request-configured="false"', self.html)
            self.assertIn("data-request-submit disabled", self.html)
            self.assertIn("No usable request endpoint is configured", self.html)
            self.assertIn("No request is being sent", self.html)
        # These hold either way.
        self.assertIn('data-en="LGA"', self.html)
        self.assertIn('data-ha="Wurin', self.html)
        self.assertIn("not a voter ID", self.html)
        self.assertIn("Do not enter a voter ID", self.html)

    def test_area_options_are_disabled_not_merely_hidden(self):
        # `hidden` on an <option> does nothing in Chromium, so the LGA -> area constraint
        # was not enforced in the UI at all: a visitor could pick Bauchi and then an area
        # belonging to Alkaleri, and the endpoint refused it as invalid_ward, surfacing
        # only as "we could not send your request". Every option outside the chosen LGA has
        # to be disabled, which a native select does honour.
        script = render.REQUEST_SCRIPT
        self.assertIn("option.disabled=!matches", script)
        # And the guard must not be able to be satisfied by hidden alone.
        self.assertIn("option.hidden=!matches", script)

    def test_an_empty_request_endpoint_still_renders_as_closed(self):
        original = render.REQUEST_ENDPOINT
        target = Path("docs/poll.html")
        backup = target.read_text(encoding="utf-8")
        try:
            render.REQUEST_ENDPOINT = ""
            render.render()
            html = target.read_text(encoding="utf-8")
            self.assertIn('data-request-endpoint=""', html)
            self.assertIn("data-request-submit disabled", html)
            self.assertIn("No request is being sent", html)
        finally:
            render.REQUEST_ENDPOINT = original
            target.write_text(backup, encoding="utf-8")

    def test_request_form_does_not_request_official_voter_id(self):
        lower = self.html.lower()
        self.assertNotIn('name="voter_id"', lower)
        self.assertNotIn('name="voterid"', lower)
        self.assertNotIn('name="registered_voter_number"', lower)
        self.assertIn("generated request tracking reference", lower)

    def test_ra_note_is_explicitly_provisional(self):
        self.assertIn("provisional INEC electoral registration areas", self.html)
        self.assertIn("not a current administrative council-ward schedule", self.html)


if __name__ == "__main__":
    unittest.main()
