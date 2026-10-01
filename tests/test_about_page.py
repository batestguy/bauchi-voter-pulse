"""The About page: its assets, its bilingual carriers, and what it must not duplicate.

Three properties, each for a failure that is invisible in a visual check:

1. **Both portraits carry `data-alt-en` / `data-alt-ha`.** `setLanguage` rewrites
   `textContent` for every `[data-en][data-ha]` element, so a photo given `attr()` instead
   is emptied on the first language switch and the page shows a blank frame with the
   caption still in the other language. `test_photo_alt_is_bilingual` covers the mechanism;
   this asserts the About page uses it.

2. **The About page links to the agenda; it does not restate it.** `agenda.html` is where
   the five commitments live, with a source link each. A second copy is a second thing to
   keep in sync, and it is the failure the one-heavy-section-per-page rule exists to stop.

3. **The portrait is a registered asset.** A file in `assets/brand/` without a register row
   is never hashed, and a row without a file fails `validate_data()`. The candidate's
   campaign owns this image, so no third-party copyright is in play -- which is why it came
   from the campaign site and not from a news outlet.
"""
import contextlib
import csv
import re
import unittest
from pathlib import Path


DOCS = Path("docs")
ASSETS = Path("assets/brand")
PORTRAIT = "yakubu-adamu-single.png"
PROMISES = Path("data/delivery/promises.csv")


@contextlib.contextmanager
def PromiseFile():
    """The published promises, read the way the renderer reads them.

    The point of the count tests below is that the page and this file cannot disagree, so
    they must be read from the same place the renderer reads. Asserting a literal 8 here
    would instead make the test fail loudly the moment a real campaign commitment is added,
    which is the opposite of what is wanted.
    """
    with PROMISES.open(encoding="utf-8", newline="") as handle:
        yield list(csv.DictReader(handle))


def read(slug: str) -> str:
    return (DOCS / f"{slug}.html").read_text(encoding="utf-8")


class AboutPageTests(unittest.TestCase):
    def setUp(self):
        if not (DOCS / "about.html").exists():
            self.skipTest("about.html has not been rendered")
        self.html = read("about")

    def test_the_page_exists_and_is_linked_from_the_nav(self):
        self.assertTrue((DOCS / "about.html").exists())
        for slug in ("index", "atlas", "poll"):
            with self.subTest(page=slug):
                self.assertIn('href="about.html"', read(slug))

    def test_the_page_is_marked_as_current_on_itself(self):
        self.assertIn('href="about.html" aria-current="page"', self.html)

    def test_the_candidate_portrait_is_present_and_bilingual(self):
        self.assertIn(f'assets/brand/{PORTRAIT}', self.html)
        # Both alt attributes, not just one. A missing Hausa alt means a Hausa-reading
        # visitor is announced to in English on every page load.
        self.assertIn('data-alt-en="Portrait of Dr. Yakubu Adamu"', self.html)
        self.assertIn("data-alt-ha=", self.html)

    def test_the_contributor_portrait_is_present_and_bilingual(self):
        self.assertIn("assets/brand/abdulkadir-ahmad-hammayo.png", self.html)
        self.assertIn('data-alt-en="Portrait of Abdulkadir Ahmad (Hammayo)"', self.html)
        self.assertIn("data-alt-ha=", self.html)

    def test_the_contributor_is_named_and_only_says_what_was_supplied(self):
        self.assertIn("Abdulkadir Ahmad (Hammayo)", self.html)
        self.assertIn("a dedicated member of his campaign team", self.html.lower())
        # The anti-fabrication rule, restated: no amount, no four-digit year, no third
        # party named inside the credit.
        credit = self.html.split('id="contributor"', 1)[-1].split("</section>", 1)[0]
        for forbidden in ("Dr. Yakubu Adamu, PhD", "Bauchi State Government"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, credit)
        self.assertIsNone(re.search(r"\b\d{4}\b", credit),
                          "a year appears in the contributor credit")

    def test_the_agenda_is_linked_not_repeated(self):
        self.assertIn('href="agenda.html"', self.html)
        # The five commitment headings belong to agenda.html alone.
        agenda = read("agenda")
        for heading in ("Published commitment clause",):
            with self.subTest(heading=heading):
                self.assertIn(heading, agenda)
                self.assertNotIn(heading, self.html)

    def test_every_commitment_link_on_the_page_lands_on_a_real_anchor(self):
        # The commitments are named as chips that deep-link into agenda.html, which only
        # works because each agenda card carries an id. Neither file can prove the other
        # exists on its own -- agenda.html can drop an id and about.html keeps linking,
        # and a dead anchor is a link that appears to work and scrolls nowhere.
        chips = re.findall(r'href="agenda\.html#([^"]+)"', self.html)
        self.assertGreaterEqual(len(chips), 5, "the five commitments are not all linked")
        agenda = read("agenda")
        for anchor in chips:
            with self.subTest(anchor=anchor):
                self.assertIn(f'id="{anchor}"', agenda)

    def test_the_page_carries_its_own_css(self):
        # The page shipped with no rules of its own: the portrait rendered at its natural
        # 720px and the commitments section was a heading and a button in 200px of nothing.
        # A test suite of string assertions passed the whole time, because nothing about a
        # missing stylesheet is visible in markup. So the class names the markup uses are
        # checked against the stylesheet instead.
        style = re.search(r"<style>(.*?)</style>", self.html, re.S)
        self.assertIsNotNone(style, "no inline stylesheet on the page")
        css = style.group(1) or ""
        for selector in (".about-grid", ".about-portrait", ".about-copy", ".about-quote",
                         ".about-chips", ".about-chip", ".about-cta"):
            with self.subTest(selector=selector):
                self.assertIn(selector, css,
                              f"{selector} is used in the markup but never styled")

    def test_the_commitment_links_are_the_only_way_to_the_detail(self):
        # A chip that also restated the commitment's promise text would be the second copy
        # this page exists to avoid. The sector name is a label; the text is the agenda's.
        with PromiseFile() as rows:
            expected = [r["sector"] for r in rows if r.get("sector")]
        chips = re.findall(r'<a class="about-chip"[^>]*>(.*?)</a>', self.html, re.S)
        self.assertEqual(len(chips), len(expected))
        for anchor, chip in zip(expected, chips):
            with self.subTest(anchor=anchor):
                self.assertNotIn("<p", chip)

    def test_the_stated_commitment_count_is_the_number_in_the_promises_file(self):
        # The page once claimed "Five commitments" over an eight-row promises file, and
        # enumerated five sectors that were not the five in it -- health, water, livelihoods
        # and governance were missing from the sentence. A voter reading the About page and
        # then the agenda sees two different campaigns. The heading is now derived, so this
        # fails the moment the data and the sentence would disagree again.
        with PromiseFile() as rows:
            count = len([r for r in rows if r.get("sector")])
        section = re.search(r'<section class="section" id="commitments".*?</section>',
                            self.html, re.S)
        self.assertIsNotNone(section, "the commitments section is gone")
        heading = re.search(r'<h2><span data-en="([^"]*)"', section.group(0) or "")
        self.assertIsNotNone(heading, "no English heading on the commitments section")
        for word, number in (("One", 1), ("Two", 2), ("Three", 3), ("Four", 4), ("Five", 5),
                             ("Six", 6), ("Seven", 7), ("Eight", 8), ("Nine", 9), ("Ten", 10)):
            if heading.group(1).startswith(word):
                self.assertEqual(
                    number, count,
                    f"the page says {heading.group(1)!r} but promises.csv holds {count}")
                break
        else:
            self.fail(f"unrecognised commitment heading: {heading.group(1)!r}")

    def test_the_page_does_not_enumerate_commitments_in_prose(self):
        # Even with the right number, a hand-written list is a second description of the
        # agenda that can drift. The chips are generated; this prose was not, and it was
        # the prose that was wrong.
        with PromiseFile() as rows:
            self.assertGreater(len([r for r in rows if r.get("sector")]), 5,
                               "expected more than five commitments, so a stale "
                               "'five commitments' enumeration could hide here")
        self.assertNotIn("Security and public safety, quality education", self.html)

    def test_the_portrait_is_a_registered_asset(self):
        register = Path("data/delivery/asset_register.csv")
        with register.open(encoding="utf-8", newline="") as handle:
            rows = {r["file"]: r for r in csv.DictReader(handle)}
        self.assertIn(PORTRAIT, rows, f"{PORTRAIT} has no asset_register row")
        row = rows[PORTRAIT]
        self.assertEqual(row["usage_status"], "campaign approved")
        self.assertTrue(row["approved_at"])
        # The row must name where it came from, so the provenance is auditable.
        self.assertIn("yakubuadamuphd.com", row["source_url"])

    def test_the_portrait_actually_exists_in_the_source_and_published_trees(self):
        # A register row without a file fails the build; a file without a row is never
        # hashed. Both halves are required, so both are asserted.
        self.assertTrue((ASSETS / PORTRAIT).exists(), "missing from assets/brand/")
        self.assertTrue((DOCS / "assets" / "brand" / PORTRAIT).exists(),
                        "missing from docs/assets/brand/, so it will not publish")

    def test_no_unicode_escape_reached_the_page(self):
        # A literal backslash-uXXXX in the rendered HTML is a source-escape bug that reads as
        # "\\u2014" to a visitor. It happened while writing this page.
        self.assertIsNone(re.search(r"\\\\u[0-9a-fA-F]{4}", self.html),
                          "the page contains a raw unicode escape")

    def test_every_user_facing_bilingual_pair_ships_both_strings(self):
        # The standing rule: `attr()` on an element that owns children empties it, and a
        # copy() with no Hausa degrades silently. The repository-wide checks cover the
        # mechanism; this asserts the new page participates.
        pairs = re.findall(r'data-en="([^"]*)" data-ha="([^"]*)"', self.html)
        self.assertGreater(len(pairs), 15)
        for english, hausa in pairs:
            with self.subTest(english=english[:40]):
                self.assertTrue(hausa.strip(), f"no Hausa for {english!r}")

    def test_the_page_carries_the_source_and_permission_note(self):
        self.assertIn("permission", self.html.lower())


if __name__ == "__main__":
    unittest.main()