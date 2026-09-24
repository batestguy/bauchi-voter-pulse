import csv
import unittest
from copy import deepcopy
from pathlib import Path

from src.dashboard import render


DATA = Path("data/delivery")


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class DeliveryIntegrityTests(unittest.TestCase):
    def test_delivery_data_passes_renderer_validation(self):
        render.validate_data()

    def test_indicators_reference_registered_sources(self):
        source_ids = {row["source_id"] for row in rows("source_register.csv")}
        for indicator in rows("indicators.csv"):
            self.assertIn(indicator["source_id"], source_ids)

    def test_indicator_ledger_shape(self):
        indicators = rows("indicators.csv")
        self.assertEqual(len(indicators), 8)
        self.assertEqual(len({row["indicator_id"] for row in indicators}), 8)
        allowed = {"Progress delivered", "Project underway", "Outcome being measured", "Approval milestone"}
        self.assertTrue(all(row["status"] in allowed for row in indicators))

    def test_indicator_rejects_value_without_year(self):
        indicators = deepcopy(rows("indicators.csv"))
        indicators[0]["baseline_value"] = "10"
        indicators[0]["baseline_year"] = ""
        with self.assertRaises(ValueError):
            render.validate_indicator_rows(indicators)

    def test_indicator_rejects_invalid_year(self):
        indicators = deepcopy(rows("indicators.csv"))
        indicators[0]["current_year"] = "20x6"
        with self.assertRaises(ValueError):
            render.validate_indicator_rows(indicators)

    def test_lga_delivery_has_all_twenty_lgas(self):
        self.assertEqual({row["lga"] for row in rows("lga_delivery.csv")}, set(render.LGAS))

    def test_no_pending_source_reviews(self):
        self.assertFalse(
            any(row["review_status"] == "needs_review" for row in rows("review_queue.csv"))
        )


if __name__ == "__main__":
    unittest.main()
