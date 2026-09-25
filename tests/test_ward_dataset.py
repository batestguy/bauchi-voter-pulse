import csv
import unittest
from collections import Counter
from pathlib import Path


EXPECTED_COUNTS = {
    "Alkaleri": 11,
    "Bauchi": 12,
    "Bogoro": 10,
    "Dambam": 10,
    "Darazo": 11,
    "Dass": 10,
    "Gamawa": 11,
    "Ganjuwa": 11,
    "Giade": 10,
    "Itas-Gadau": 10,
    "Jamaare": 10,
    "Katagum": 11,
    "Kirfi": 10,
    "Misau": 10,
    "Ningi": 11,
    "Shira": 11,
    "Tafawa-Balewa": 11,
    "Toro": 11,
    "Warji": 10,
    "Zaki": 11,
}


class WardDatasetTests(unittest.TestCase):
    def test_ward_dataset_has_212_unique_ra_records(self):
        with Path("data/delivery/lga_wards.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 212)
        self.assertEqual(len({row["ward_code"] for row in rows}), 212)
        self.assertEqual(Counter(row["lga"] for row in rows), EXPECTED_COUNTS)
        self.assertTrue(all(row["ra_name_source"] == row["ra_name_display"] for row in rows))

    def test_ward_dataset_is_explicitly_provisional(self):
        with Path("data/delivery/lga_wards.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(all(row["source_scope"] == "electoral_registration_area" for row in rows))
        self.assertTrue(all(row["verification_status"] == "provisional_source_not_directly_downloaded" for row in rows))


if __name__ == "__main__":
    unittest.main()
