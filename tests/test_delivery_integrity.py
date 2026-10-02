import csv
import hashlib
import re
import subprocess
import unittest
from copy import deepcopy
from pathlib import Path

from src.dashboard import render


DATA = Path("data/delivery")
DOCS_ASSETS = Path("docs/assets/brand")


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
    def test_the_weekly_sync_cannot_drop_a_column_from_the_source_register(self):
        """The cron rewrites this file every week, so a lossy rewrite is silent damage.

        `sync_source_register` once hardcoded eleven column names and left out
        `usage_note_ha`. The weekly job therefore rewrote the register without the
        Hausa column, deleting 28 hand-reviewed translations and breaking the build --
        and the cron reported success, because from its point of view nothing failed.
        It committed on 2 October 2026 and had to be restored by hand.

        So this runs the real function against a temporary copy of the committed file
        and asserts that every column and every translated cell survives. The point is
        the round trip, not the individual column: a future column must survive too,
        which is why the assertion is made against the header rather than a list.
        """
        import shutil
        import tempfile

        from src.ingestion import delivery_sources

        register = DATA / "source_register.csv"
        before_header = register.open(encoding="utf-8").readline().strip().split(",")
        before = rows("source_register.csv")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source_register.csv").write_bytes(register.read_bytes())
            original_data = delivery_sources.DATA
            delivery_sources.DATA = root
            try:
                delivery_sources.sync_source_register(
                    [
                        {
                            "source_id": before[0]["source_id"],
                            "content_hash": "0" * 64,
                            "retrieved_date": "2026-10-02",
                            "publication_date": "2026-09-01",
                        }
                    ]
                )
            finally:
                delivery_sources.DATA = original_data

            after_path = root / "source_register.csv"
            after_header = after_path.open(encoding="utf-8").readline().strip().split(",")
            with after_path.open(newline="", encoding="utf-8") as handle:
                after = list(csv.DictReader(handle))

        self.assertEqual(after_header, before_header,
                         "the sync changed the register's columns")
        self.assertEqual(len(after), len(before), "the sync changed the register's row count")
        self.assertIn("usage_note_ha", after_header, "the Hausa usage note column is gone again")
        for old, new in zip(before, after):
            with self.subTest(source_id=old["source_id"]):
                self.assertEqual(new["usage_note_ha"], old["usage_note_ha"],
                                 "the sync rewrote a hand-reviewed Hausa translation")
        self.assertEqual(after[0]["content_hash"], "0" * 64,
                         "the sync did not apply the hash it was given, so the test proves nothing")

    def test_the_sync_refuses_to_write_a_register_missing_a_required_column(self):
        """Losing a column must stop the run, not produce a shorter file.

        The failure above was silent because nothing in the sync path could fail. A
        register arriving without `usage_note_ha` is now refused outright.
        """
        import tempfile

        from src.ingestion import delivery_sources

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source_register.csv"
            stub = (
                "source_id,publisher,title,content_hash,retrieved_date\n"
                "s-1,P,T,abc,2026-01-01\n"
            )
            path.write_text(stub, encoding="utf-8")
            original = delivery_sources.DATA
            delivery_sources.DATA = root
            try:
                with self.assertRaises(ValueError):
                    delivery_sources.sync_source_register(
                        [{"source_id": "s-1", "content_hash": "x", "retrieved_date": "y"}]
                    )
            finally:
                delivery_sources.DATA = original
            # The refusal must leave the file byte-for-byte as it was. Asserting the
            # column is still absent reads as a contradiction unless the intent is
            # spelled out, which is why it is spelled out here.
            self.assertEqual(path.read_text(encoding="utf-8"), stub,
                             "the file was rewritten despite the refusal")

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


class ReadmeInventoryTests(unittest.TestCase):
    """The README's data table is prose, and prose drifts.

    It said 12 registered assets after two more were registered, and nothing in the build
    compared the two: `validate_data()` hashes each register row, and no check ever asked
    whether the number a reader is shown still matches the register. This walks the table
    and recomputes every figure from the file it names, so the same class of defect cannot
    survive a change to the data again.
    """

    TABLE = re.compile(r"^\|\s*[^|]+?\|\s*(\d[\d,]*)\s*\|\s*`([^`]+)`\s*\|\s*$", re.MULTILINE)

    def test_every_inventory_figure_matches_the_file_it_cites(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        found = self.TABLE.findall(readme)
        self.assertGreaterEqual(len(found), 8, "the README inventory table was not found")

        for printed, cited in found:
            with self.subTest(row=cited):
                path = Path(cited)
                self.assertTrue(path.exists(), f"{cited} is cited in the README but missing")
                with path.open(newline="", encoding="utf-8") as handle:
                    actual = len(list(csv.DictReader(handle)))
                self.assertEqual(int(printed.replace(",", "")), actual,
                                 f"README says {printed} for {cited}, which holds {actual} rows")

    def test_every_download_the_readme_offers_is_a_real_registered_file(self):
        """A download link in the README is the one thing on this page a reader can act on.

        The repo offers two MP4s from the README and the About page. A relative link to a
        binary would land on GitHub's file page rather than the file, so the README uses
        absolute `raw.githubusercontent.com` URLs - which means a rename, a move or a
        deleted asset would leave a 404 in the first screen of the project with no test
        anywhere noticing. This walks the URLs and resolves each one to a file that exists
        on disk and is registered.
        """
        readme = Path("README.md").read_text(encoding="utf-8")
        urls = re.findall(
            r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/(assets/brand/[^\s)\"']+)",
            readme,
        )
        self.assertGreaterEqual(len(urls), 2, "no raw download links found in the README")

        with open("data/delivery/asset_register.csv", encoding="utf-8", newline="") as fh:
            registered = {row["file"] for row in csv.DictReader(fh)}

        for url_path in urls:
            with self.subTest(url=url_path):
                local = Path(url_path)
                self.assertTrue(local.exists(), f"{local} is offered for download but missing")
                self.assertEqual(local.stat().st_size, (DOCS_ASSETS / local.name).stat().st_size,
                                 "the downloadable copy differs from the published one")
                self.assertIn(local.name, registered,
                              f"{local.name} is offered for download but not registered")

    def test_the_brief_is_downloadable_from_the_repo_and_is_not_published_on_the_site(self):
        """The five-page brief is a repository download, and must stay one.

        The README offers it as a raw URL, so the file has to be committed for that link
        to resolve. It was also explicitly NOT to be published on the site, and the only
        thing separating the two states is where the file sits: GitHub Pages serves
        `docs/`, so a copy under `docs/` would put a five-page PDF in front of every
        visitor while looking, in the repository, like nothing had changed. Nothing else
        in the build would notice.

        So both halves are asserted: the README link resolves to a committed file, and
        that file is outside `docs/`.
        """
        readme = Path("README.md").read_text(encoding="utf-8")
        urls = re.findall(
            r"https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/(brief/[^\s)\"']+)", readme
        )
        self.assertTrue(urls, "the README offers no brief download link")

        for url_path in urls:
            with self.subTest(url=url_path):
                local = Path(url_path)
                self.assertTrue(local.is_file(), f"{local} is offered for download but is not committed")
                self.assertGreater(local.stat().st_size, 20_000,
                                   "the committed brief is implausibly small; was it truncated?")

                # The whole point of the rule, asserted rather than assumed.
                self.assertFalse(local.is_relative_to(Path("docs")),
                                 "the brief must not live under docs/, which Pages serves")
                self.assertFalse(
                    list(Path("docs").rglob(local.name)),
                    f"a copy of the brief was published under docs/; it was explicitly not to be")

    def test_the_brief_states_the_contributor_and_offers_the_demo_video(self):
        """The brief is generated, so its content is a build product and not a promise.

        Two things must survive every rebuild, because both are commitments rather than
        layout: the contributor is credited by name with the role the campaign supplied,
        and the recording is downloadable from inside the document -- a brief that says
        "watch it work" and then offers no way to watch it is worse than one that does
        not mention it.
        """
        brief = Path("brief/apm-brief.pdf")
        self.assertTrue(brief.is_file(), "brief/apm-brief.pdf has not been built")

        import pypdf

        reader = pypdf.PdfReader(str(brief))
        raw = "\n".join(page.extract_text() for page in reader.pages)
        # The text layer carries the visual line breaks, so "his campaign team." is
        # split across two lines on the page. Collapsing whitespace asserts the
        # content rather than the wrapping, which is not what this test is about.
        text = " ".join(raw.split())
        links = set()
        for page in reader.pages:
            for annot in page.get("/Annots", []) or []:
                action = annot.get_object().get("/A")
                if action is not None and action.get("/S") == "/URI":
                    links.add(str(action.get("/URI")))

        self.assertEqual(len(reader.pages), 5, "the brief is a five-page document")
        self.assertIn("Abdulkadir Ahmad (Hammayo)", text)
        self.assertIn("A dedicated member of his campaign team.", text)
        self.assertIn(
            "https://raw.githubusercontent.com/batestguy/bauchi-voter-pulse/main/assets/brand/demo-16x9.mp4",
            links,
            "the brief does not offer the widescreen recording for download",
        )
        self.assertIn(
            "https://raw.githubusercontent.com/batestguy/bauchi-voter-pulse/main/assets/brand/demo-9x16.mp4",
            links,
            "the brief does not offer the phone-cut recording for download",
        )
        # Every link must resolve to something, or the document only looks interactive.
        dead = [
            annot
            for page in reader.pages
            for annot in (page.get("/Annots") or [])
            if annot.get_object().get("/Subtype") == "/Link"
            and annot.get_object().get("/A") is None
            and not annot.get_object().get("/Dest")
        ]
        self.assertEqual(dead, [], f"{len(dead)} link annotations resolve nowhere")


if __name__ == "__main__":
    unittest.main()
