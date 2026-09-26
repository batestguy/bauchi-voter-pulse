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

    def test_request_form_is_bilingual_and_blocks_unconfigured_submission(self):
        self.assertIn('data-en="LGA"', self.html)
        self.assertIn('data-ha="Wurin', self.html)
        self.assertIn('data-request-endpoint=""', self.html)
        self.assertIn('data-request-configured="false"', self.html)
        self.assertIn('data-request-submit disabled', self.html)
        self.assertIn("No usable request endpoint is configured", self.html)
        self.assertIn("No request is being sent", self.html)
        self.assertIn("not a voter ID", self.html)
        self.assertIn("Do not enter a voter ID", self.html)

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
