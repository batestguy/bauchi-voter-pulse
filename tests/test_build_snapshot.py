"""Exercise the snapshot builder against a synthetic export.

Runs in a temp directory with an explicit --out, so it never writes
data/delivery/poll_snapshot.json. That path is the live artefact and a test must not be
able to create or destroy it.
"""
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "poll" / "build_snapshot.py"
sys.path.insert(0, str(ROOT))

HEADER = [
    "response_id", "received_at", "sector", "lga", "ward_code",
    "age_band", "gender", "consent", "validation_status",
]


def write_csv(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in HEADER})


def accepted(i, sector="water", lga="Bauchi", **extra):
    row = {
        "response_id": f"APM-POLL-2026-{i:06d}",
        "received_at": f"2026-10-01T10:{i % 60:02d}:00Z",
        "sector": sector,
        "lga": lga,
        "consent": "TRUE",
        "validation_status": "validated",
    }
    row.update(extra)
    return row


def run(csv_path, out_path, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(csv_path), "--out", str(out_path), *args],
        capture_output=True, text=True, cwd=ROOT)


class SnapshotBuilderTests(unittest.TestCase):
    def test_a_real_export_produces_a_valid_snapshot(self):
        import json
        from src.poll import aggregate

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path = tmp / "responses.csv"
            out = tmp / "snapshot.json"
            write_csv(csv_path, [accepted(i) for i in range(1, 13)])
            result = run(csv_path, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            snapshot = json.loads(out.read_text(encoding="utf-8"))
            # The field set is the contract, and it is asserted exactly: a snapshot that
            # quietly grew or lost a key would change what the page can publish. Sorted
            # because the file is written with sort_keys for a stable diff.
            self.assertEqual(tuple(sorted(snapshot)),
                             tuple(sorted(aggregate.PUBLIC_SNAPSHOT_FIELDS)))
            self.assertEqual(snapshot["total_responses"], 12)
            self.assertEqual(snapshot["by_sector"]["water"], 12)

    def test_rejected_and_non_consenting_rows_are_not_counted(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path = tmp / "responses.csv"
            out = tmp / "snapshot.json"
            rows = [accepted(i) for i in range(1, 13)]
            # An invalid ward and a missing consent are stored in the same tab. Counting
            # either would publish a preference nobody cast.
            rows.append(accepted(99, ward_code="RA-999", validation_status="ward_map_missing"))
            rows.append(accepted(98, consent="FALSE"))
            rows.append(accepted(97, validation_status="rejected"))
            write_csv(csv_path, rows)
            result = run(csv_path, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            snapshot = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["total_responses"], 12)

    def test_an_empty_export_writes_nothing(self):
        # The page renders its own honest empty state. A committed snapshot of zeroes would
        # replace that with a chart of nothing.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path = tmp / "responses.csv"
            out = tmp / "snapshot.json"
            write_csv(csv_path, [])
            result = run(csv_path, out)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(out.exists(), "an empty poll must not produce a snapshot")

    def test_a_wrong_csv_is_refused_with_a_useful_message(self):
        # A hand-picked file of the wrong shape must fail loudly. Silently producing a
        # snapshot full of zeroes is the failure mode this guards.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path = tmp / "wrong.csv"
            csv_path.write_text("name,email\nAminu,a@b.c\n", encoding="utf-8")
            result = run(csv_path, tmp / "snapshot.json")
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing required column", result.stdout + result.stderr)
            self.assertFalse((tmp / "snapshot.json").exists())

    def test_it_never_writes_comments_into_the_snapshot(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path = tmp / "responses.csv"
            out = tmp / "snapshot.json"
            rows = [accepted(i, comment="a private free-text comment") for i in range(1, 13)]
            write_csv(csv_path, rows)
            result = run(csv_path, out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            body = out.read_text(encoding="utf-8")
            self.assertNotIn("private free-text comment", body)
            # No response id may be published either: it is a receipt, not a count.
            self.assertNotIn("APM-POLL-2026-000001", body)

    def test_the_sheets_timestamp_column_is_mapped_to_the_name_the_tally_reads(self):
        # The Responses tab header says `received_at` (Code.gs.template:578) and the
        # aggregator reads `created_at` (aggregate.py:277). Passing the Sheet's own column
        # name straight through tallied zero responses from twelve perfectly good rows and
        # reported "counted 0" -- a snapshot of nothing, built from real data, with no error
        # anywhere. A CSV has no booleans, so consent is mapped too. Both mappings are
        # asserted here because both fail silently and identically.
        import json
        from src.poll import aggregate

        rows = [{"response_id": "APM-POLL-2026-000001",
                 "received_at": "2026-10-01T10:00:00Z",   # Sheet's name
                 "sector": "water", "lga": "Bauchi",
                 "consent": "TRUE",                         # Sheet's string boolean
                 "validation_status": "validated"}]
        # Unmapped: the tally sees no timestamp and no consent, and rejects everything.
        naive = aggregate.tally_poll_responses(rows)
        self.assertEqual(naive["total_responses"], 0,
                         "expected the name mismatch to be real, not theoretical")

        mapped = [dict(rows[0], created_at=rows[0]["received_at"], consent=True)]
        fixed = aggregate.tally_poll_responses(mapped)
        self.assertEqual(fixed["total_responses"], 1)

        # And the builder itself performs both mappings. Loaded by path because
        # src/poll/build_snapshot.py is a script, not part of the src.poll package.
        import importlib.util
        spec = importlib.util.spec_from_file_location("_bs", SCRIPT)
        self.assertIsNotNone(spec, "could not load the builder script")
        build_snapshot = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(build_snapshot)  # type: ignore[union-attr]
        out = build_snapshot.accepted_rows(rows)
        self.assertEqual(out[0]["created_at"], "2026-10-01T10:00:00Z")
        self.assertNotIn("received_at", out[0])
        self.assertIs(out[0]["consent"], True)

    def test_it_never_writes_the_live_artefact_accidentally(self):
        live = ROOT / "data" / "delivery" / "poll_snapshot.json"
        before = live.exists()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            csv_path = tmp / "responses.csv"
            write_csv(csv_path, [accepted(i) for i in range(1, 13)])
            run(csv_path, tmp / "snapshot.json")
        self.assertEqual(live.exists(), before,
                         "the test run wrote to the committed snapshot path")


if __name__ == "__main__":
    unittest.main()