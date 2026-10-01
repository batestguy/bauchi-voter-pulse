"""The request intake endpoint, and the contract it must not drift from.

`docs/requests-script/Code.gs` is generated from `Code.gs.template` plus the real
registration-area map, and pasted into the owner's Sheet by hand. An agent cannot reach a
Google account, so this file cannot be executed by the agent that would otherwise review
it. That is why it has its own harness: `docs/requests-script/test_endpoint.mjs` loads the
real generated Code.gs with the Apps Script globals stubbed and runs the real doPost. It is
not a mock of the endpoint; it is the endpoint, with only the platform objects faked.

This matters more here than for the poll. The poll stores no direct identity. This form
stores a name, an email address for correspondence and a street address, so the endpoint
decides what a member of the public can write into the campaign's private records and what
gets logged about it.

Two rules the tests here exist to enforce:

1. **The endpoint mirrors `src/requests/validation.py`.** The browser cannot be trusted, so
   every rule is implemented twice. Two implementations of one rule drift unless something
   asserts they agree, and drift is silent: an address accepted by one and refused by the
   other is a member of the public turned away with no error shown.

2. **The audit tab cannot hold a contact field.** Three narrow columns, and both the
   harness and this file assert that a rejected request -- which carries a name, an email
   and a street address -- leaves only a stable rejection code behind.
"""
import csv
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.requests import validation


APPS = Path("docs/requests-script")
WARDS_CSV = Path("data/delivery/lga_wards.csv")


def _js_array(source: str, name: str) -> str | None:
    """Return the body of a `var NAME = [ ... ];` literal in a JS source file."""
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*\[(.*?)\];", source, re.S)
    return match.group(1) if match else None


def _js_string_list(block: str | None) -> list[str]:
    """Pull the quoted strings out of a JS array literal, or fail loudly."""
    if block is None:
        raise AssertionError("the array literal was not found in Code.gs")
    return re.findall(r"'([^']*)'", block)


def _function_body(source: str, name: str) -> str:
    """Return the text of one `function NAME(...) { ... }` body.

    Brace-matched rather than non-greedy-to-the-next-`}`, because a regex that stops at
    the first closing brace returns a truncated body for any function containing a nested
    block -- and a truncated body then "passes" an assertion about code further down,
    which is the worst way for a guard to be wrong.
    """
    match = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source)
    if not match:
        raise AssertionError(f"function {name}( not found")
    start = match.end()
    depth = 1
    index = start
    while depth and index < len(source):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    return source[start:index - 1]


def _js_object(source: str, name: str) -> dict[str, int]:
    """Return a flat `var NAME = { key: number, ... };` literal as a dict of ints."""
    match = re.search(rf"var\s+{re.escape(name)}\s*=\s*\{{(.*?)\}};", source, re.S)
    if not match:
        return {}
    return {
        key: int(value)
        for key, value in re.findall(r"([A-Za-z_]+)\s*:\s*(\d+)", match.group(1))
    }


class RequestEmailContractTests(unittest.TestCase):
    """The email rule, because it was wrong and the failure was invisible.

    The local part's character class omitted ".", so the greedy match stopped at the first
    dot and then required an "@" that was not there. Every address shaped
    `first.last@example.com` was refused with a clean `invalid_email` -- no crash, no
    trace, just a member of the public who typed a normal address and was told no.

    The regression tests are here rather than in the validation suite because the defect
    was only ever discovered by probing the real contract rather than reading it.
    """

    def _email(self, value):
        return validation.normalize_email(value)

    def test_a_dotted_local_part_is_accepted(self):
        # The shape that used to be refused outright, and the most common one there is.
        for address in (
            "aminu.bala@example.com",
            "first.last@example.com",
            "a.b.c@example.co.uk",
            "first.last+tag@mail.example.co.uk",
        ):
            with self.subTest(address=address):
                self.assertEqual(self._email(address), address)

    def test_only_the_domain_is_lowercased(self):
        # The local part is case-sensitive per RFC 5321. Rewriting it would change an
        # address the respondent gave us, and one we cannot then write to.
        self.assertEqual(
            self._email("Aminu.Bala@Example.COM"), "Aminu.Bala@example.com")

    def test_a_dot_atom_may_not_begin_or_end_with_a_dot(self):
        # "no .." catches neither of these, which is why they are separate checks.
        for address in (".aminu@example.com", "aminu.@example.com"):
            with self.subTest(address=address):
                with self.assertRaises(validation.RequestValidationError) as caught:
                    self._email(address)
                self.assertEqual(caught.exception.code, "invalid_email")

    def test_still_refuses_what_it_refused_before(self):
        for address in (
            "a..b@example.com",
            "aminu@example",
            "@example.com",
            "aminu.example.com",
            "x" * 65 + "@example.com",
            "aminu@" + ("a" * 64 + ".") * 3 + "com",
        ):
            with self.subTest(address=address):
                with self.assertRaises(validation.RequestValidationError):
                    self._email(address)

    def test_a_blank_email_is_still_optional(self):
        self.assertEqual(self._email(""), "")
        self.assertEqual(self._email(None), "")


class RequestEndpointScriptTests(unittest.TestCase):
    def setUp(self):
        self.code_path = APPS / "Code.gs"
        self.harness = APPS / "test_endpoint.mjs"
        if not self.code_path.exists():
            self.skipTest("Code.gs is generated; run build_code_gs.py")
        self.code = self.code_path.read_text(encoding="utf-8")

    def _node(self):
        return shutil.which("node") or shutil.which("nodejs")

    def _function_body(self, name: str) -> str:
        return _function_body(self.code, name)

    def _run(self, *args):
        return subprocess.run(list(args), capture_output=True, text=True)

    def test_the_generated_script_is_valid_javascript(self):
        # A syntax error here is invisible until the owner deploys, at which point the
        # endpoint is dead and the request form silently accepts nothing.
        node = self._node()
        if not node:
            self.skipTest("node not available")
        with tempfile.TemporaryDirectory() as directory:
            probe = Path(directory) / "code.js"
            probe.write_text(self.code, encoding="utf-8")
            result = self._run(node, "--check", str(probe))
        self.assertEqual(result.returncode, 0, result.stderr[-600:])

    def test_the_endpoint_harness_passes(self):
        node = self._node()
        if not node:
            self.skipTest("node not available")
        result = self._run(node, str(self.harness))
        self.assertEqual(
            result.returncode, 0,
            "the endpoint harness exists to catch validation defects before deployment, "
            f"not after:\n{result.stdout}\n{result.stderr}")

    def test_the_endpoint_vocabularies_have_not_drifted_from_the_contract(self):
        # The endpoint re-implements every rule in src/requests/validation.py, because the
        # browser cannot be trusted. Two implementations of one rule drift unless
        # something asserts they agree, and drift here is silent: a category accepted by
        # one and refused by the other is not visible until real people are turned away.
        for name, expected in (
            ("ALLOWED_CATEGORIES", validation.ALLOWED_CATEGORIES),
            ("MAX_LENGTHS", validation.MAX_LENGTHS),
        ):
            with self.subTest(vocabulary=name):
                if name == "MAX_LENGTHS":
                    found = _js_object(self.code, name)
                    self.assertEqual(
                        found, dict(validation.MAX_LENGTHS),
                        f"MAX_LENGTHS in Code.gs is {found}, contract is "
                        f"{dict(validation.MAX_LENGTHS)}")
                    continue
                block = _js_array(self.code, name)
                self.assertIsNotNone(block, f"{name} not found in Code.gs")
                values = _js_string_list(block)
                for value in expected:
                    self.assertIn(value, values)

    def test_the_endpoint_field_lists_match_the_contract(self):
        # The endpoint's allowed-payload list is the whole boundary. A field added to the
        # form and forgotten here is silently dropped; a field removed from the contract
        # and left here is silently accepted.
        block = _js_array(self.code, "ALLOWED_PAYLOAD_FIELDS")
        self.assertIsNotNone(block, "ALLOWED_PAYLOAD_FIELDS not found in Code.gs")
        self.assertEqual(set(_js_string_list(block)),
                         set(validation.ALLOWED_PAYLOAD_FIELDS))
        required = _js_array(self.code, "REQUIRED_FIELDS")
        self.assertEqual(set(_js_string_list(required)),
                         set(validation.REQUIRED_FIELDS))
        private = _js_array(self.code, "OPTIONAL_PRIVATE_FIELDS")
        self.assertEqual(set(_js_string_list(private)),
                         set(validation.OPTIONAL_PRIVATE_FIELDS))

    def test_the_endpoint_ward_map_matches_the_form(self):
        # The form offers areas from data/delivery/lga_wards.csv. If the endpoint's map
        # disagrees, a respondent can select an area the endpoint then refuses.
        with WARDS_CSV.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        match = re.search(r"var WARD_MAP_SOURCE = '([^']*)';", self.code)
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

    def test_the_endpoint_refuses_to_run_without_a_complete_ward_map(self):
        # The contract tolerates a missing map: it stores the ward code as typed and marks
        # the row `ward_map_missing`, on the understanding that a person notices. For an
        # endpoint that warning is invisible, so the endpoint refuses instead. Asserted by
        # name because a renamed guard is a removed guard.
        self.assertIn("function requireWardMap_()", self.code)
        self.assertIn("ward_map_incomplete", self.code)
        # And it must be called on the REQUEST path, not only in setup.
        # validateWardCode_ is the one that turns a submitted area into a stored one, so
        # that is where the guard has to sit. Asserting only in setupSheets would pass
        # while the endpoint accepted any area for any LGA.
        self.assertIn("requireWardMap_()", self._function_body("validateWardCode_"))

    def test_the_audit_tab_cannot_hold_a_contact_field(self):
        # Three narrow columns. A name, a phone, an email, an address or a detail landing
        # in an audit row is the exact leak this endpoint exists to prevent, and it is
        # prevented by the tab's shape rather than by remembering to be careful.
        block = re.search(r"sheet_\(AUDIT_SHEET_NAME\)\.appendRow\(\[(.*?)\]\)", self.code, re.S)
        self.assertIsNotNone(block, "the audit append is not found")
        written = block.group(1)
        self.assertEqual(
            [token.strip() for token in written.split(",") if token.strip()],
            ["formatTimestamp_(receivedAt)", "status", "code"])
        for forbidden in ("name", "phone", "email", "address", "details",
                          "payload", "record"):
            with self.subTest(field=forbidden):
                self.assertNotIn(forbidden, written)

    def test_the_endpoint_returns_only_the_tracking_reference(self):
        # Anything else is private data coming back into the respondent's own browser,
        # where it lands in their history and over their shoulder.
        block = re.search(r"return jsonResponse_\(\{ request_id: requestId \}\);", self.code)
        self.assertIsNotNone(block, "the success response is not the expected shape")
        for forbidden in ("record.", "payload", "name", "phone", "email", "address"):
            with self.subTest(field=forbidden):
                self.assertNotIn(forbidden, block.group(0))

    def test_a_client_cannot_choose_its_own_reference(self):
        # A client-supplied request_id would let anyone pick their own reference,
        # including one that collides with a real request.
        self.assertIn("hasOwnProperty.call(payload, 'request_id')", self.code)
        # And it must be an UNKNOWN field, not something the endpoint honours and then
        # overwrites: a validated-then-ignored request_id would still let a client probe
        # which references exist.
        self.assertNotIn("payload.request_id", self.code)
        self.assertNotIn("record.request_id", self.code)

    def test_the_endpoint_allocates_a_sequential_reference(self):
        # Never derived from the content. This matters more here than for the poll: a hash
        # of a name, a phone number and an address is a stable fingerprint that anyone who
        # can guess the person can confirm -- and the reference is returned to them.
        for token in ("nextRequestId_", "PropertiesService", "SEQUENCE_KEY"):
            with self.subTest(token=token):
                self.assertIn(token, self.code)
        self.assertIn("('000000' + next).slice(-6)", self.code)
        # The absence that matters is the CALL, not the word. This file explains in a
        # comment why hashing must not be used, so a word-level check fails on the
        # explanation and would still pass on a real digest call written the same way.
        body = self._function_body("nextRequestId_")
        for digest in ("computeDigest", "computeHmac", "getUuid"):
            with self.subTest(digest=digest):
                self.assertNotIn(digest, body)

    def test_the_sheet_header_matches_the_owner_guide(self):
        # GOOGLE_SHEETS_SETUP.md section 1 tells the owner to hand-build these columns. If
        # the writer disagrees with the guide, the owner's Sheet and the endpoint's rows
        # diverge silently.
        guide = Path("docs/GOOGLE_SHEETS_SETUP.md").read_text(encoding="utf-8")
        block = re.search(r"requests\.appendRow\(\[(.*?)\]\)", self.code, re.S)
        self.assertIsNotNone(block, "the Requests header is not found")
        columns = _js_string_list(block.group(1))
        for column in columns:
            with self.subTest(column=column):
                self.assertIn(column, guide)
        self.assertEqual(len(columns), 13)


if __name__ == "__main__":
    unittest.main()