"""Negative control: prove the register round-trip guard actually fails.

Not part of the build. This reinstates the original defect -- `sync_source_register`
with a hardcoded eleven-column list that omits `usage_note_ha` -- runs the real guard
against it, and restores the file. If the guard still passes, it is decorative and
must not be trusted.

The original defect shipped. The weekly cron committed a register without the Hausa
column on 2 October 2026, deleting 28 hand-reviewed translations and breaking the
build, while reporting success.

The file is patched in place rather than in a copy because the guard imports the
module by name, so a copy is never loaded. It is restored in a `finally`, and the
git checkout afterwards is the belt to that braces.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "ingestion" / "delivery_sources.py"
REL = "src/ingestion/delivery_sources.py"

FIXED = "        fields = list(reader.fieldnames or [])"
ORIGINAL = (
    '        fields = ["source_id", "publisher", "source_type", "title", "url", '
    '"publication_date", "retrieved_date", "document_type", "source_grade", '
    '"usage_note", "content_hash"]'
)
GUARD = 'required = {"source_id", "content_hash", "retrieved_date", "usage_note", "usage_note_ha"}'

TEST = (
    "tests.test_delivery_integrity.DeliveryIntegrityTests"
    ".test_the_weekly_sync_cannot_drop_a_column_from_the_source_register"
)


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    if FIXED not in src:
        print("FAILED: the fixed line is not present; this control is out of date")
        return 1

    patched = (
        src.replace(FIXED, ORIGINAL)
        .replace(GUARD, "required = set()")
        .replace("missing = required - set(fields)", "missing = set()")
    )
    if patched == src:
        print("FAILED: could not reinstate the defect")
        return 1

    TARGET.write_text(patched, encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "unittest", TEST],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
    finally:
        # Restore from the in-memory copy only. A `git checkout` here looks like a
        # safer belt to these braces, and it silently threw the fix away while the
        # fix was still uncommitted -- which then read as "the file is intact"
        # because a clean diff against HEAD looks identical either way.
        TARGET.write_text(src, encoding="utf-8")

    tail = [
        line
        for line in output.splitlines()
        if "AssertionError" in line or line.startswith(("OK", "FAILED"))
    ]
    print("\n".join(tail[-2:]))
    print(f"exit code: {result.returncode}")

    # Confirm the fix is back in place. Without this the control happily destroys an
    # uncommitted fix and reports success, which it did once already.
    restored = TARGET.read_text(encoding="utf-8")
    if FIXED not in restored:
        print("FAILED: the control did not restore the fix")
        return 1

    # Require the guard's own complaint, not merely a non-zero exit: an earlier
    # version of this control accepted any failure and so "passed" on an unrelated
    # error, which is the same mistake the brief's guard had already made once.
    fired = result.returncode != 0 and "changed the register" in output
    print("GUARD BITES" if fired else "GUARD DID NOT FIRE -- DO NOT TRUST IT")
    return 0 if fired else 1


if __name__ == "__main__":
    raise SystemExit(main())