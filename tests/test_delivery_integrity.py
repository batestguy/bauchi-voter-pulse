import csv
import hashlib
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from src.dashboard import render


DATA = Path("data/delivery")


def rows(name):
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def git_blob(relpath):
    """The bytes git has committed, read from the index.

    Not the same as the file on disk. `validate_data()` hashes the working copy, which
    on a Windows checkout carries CRLF that the committed blob does not. That gap is
    invisible locally and fatal on the Linux runner, so this reads what CI sees.
    """
    result = subprocess.run(["git", "cat-file", "-p", f":{relpath.as_posix()}"],
                            capture_output=True)
    if result.returncode != 0:
        raise unittest.SkipTest(f"not in the git index: {relpath}")
    return result.stdout


class CommittedSnapshotBytesTests(unittest.TestCase):
    """The manifest hash must describe the committed bytes, not the local ones.

    `.gitattributes` marks these snapshots `-text` so their bytes are preserved exactly,
    but the rule was added in `d9cf5f8`, after the snapshots were first committed. Git
    had already normalized the blobs to LF, while `content_hash` was computed from the
    original CRLF bytes. Every local run passed and the weekly cron failed on
    `validate_data()` with "source snapshot hash mismatch". Found 29 September 2026.
    """

    def test_manifest_hashes_match_the_committed_snapshot_bytes(self):
        for row in rows("source_manifest.csv"):
            with self.subTest(document=row["document_id"]):
                blob = git_blob(DATA / row["local_file"])
                self.assertEqual(
                    hashlib.sha256(blob).hexdigest(), row["content_hash"],
                    f"{row['local_file']} hash in source_manifest.csv does not describe "
                    f"the committed bytes")

    def test_snapshots_are_marked_no_text_so_git_cannot_normalize_them(self):
        attributes = Path(".gitattributes")
        self.assertTrue(attributes.exists(), ".gitattributes is gone")
        rules = attributes.read_text(encoding="utf-8")
        for row in rows("source_manifest.csv"):
            name = Path(row["local_file"]).name
            with self.subTest(snapshot=name):
                self.assertIn(name.rsplit(".", 1)[-1], rules,
                              "snapshot extension no longer covered by .gitattributes")
        self.assertIn("source_snapshots", rules)
        self.assertIn("-text", rules)

    def test_a_fresh_checkout_renders(self):
        # The failure this guards is only reproducible from a clean checkout, so the
        # test materialises one from the index and runs the real entry point in it.
        import os
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            checkout = subprocess.run(
                ["git", "checkout-index", "--all",
                 "--prefix=" + os.path.join(tmp, "").replace("\\", "/")],
                capture_output=True)
            if checkout.returncode != 0:
                self.skipTest("git checkout-index unavailable")
            render_dir = Path(tmp) / "src" / "dashboard"
            self.assertTrue((render_dir / "render.py").exists())
            env = dict(os.environ, PYTHONPATH=tmp)
            result = subprocess.run(
                [sys.executable, os.path.join("src", "dashboard", "render.py")],
                cwd=tmp, capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0,
                             result.stderr.strip()[-2000:])
            for slug in ("index", "achievements", "atlas", "poll", "agenda", "sources"):
                self.assertTrue((Path(tmp) / "docs" / f"{slug}.html").exists(),
                                f"docs/{slug}.html missing from a clean checkout")


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
