"""S2 header, emblem, sponsor slot and language-control tests.

The emblem regression is the reason most of this exists: `filter:brightness(0) invert(1)`
on an opaque-white logo collapsed the white page and the whitened artwork into a single
solid block, so the header rendered a white rectangle at 116x26.
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.dashboard import render

PAGE = Path("docs/index.html")
ASSETS = Path("assets/brand")
DOCS_ASSETS = Path("docs/assets/brand")


class EmblemAssetTests(unittest.TestCase):
    def test_emblem_exists_and_is_registered(self):
        rows = {r["file"]: r for r in render.read_csv("asset_register.csv")}
        self.assertIn("apm-emblem.png", rows)
        row = rows["apm-emblem.png"]
        self.assertTrue((ASSETS / "apm-emblem.png").exists())
        self.assertEqual(
            hashlib.sha256((ASSETS / "apm-emblem.png").read_bytes()).hexdigest(), row["sha256"])
        self.assertEqual(row["usage_status"], "campaign approved")
        self.assertTrue(row["approved_at"])
        # rebuild-pages.yml checks usage_status by column position, not by name.
        self.assertEqual(list(row.values())[5], "campaign approved")

    def test_emblem_is_copied_to_the_published_tree(self):
        self.assertTrue((DOCS_ASSETS / "apm-emblem.png").exists())
        self.assertEqual(
            hashlib.sha256((DOCS_ASSETS / "apm-emblem.png").read_bytes()).hexdigest(),
            hashlib.sha256((ASSETS / "apm-emblem.png").read_bytes()).hexdigest())

    def test_emblem_has_a_transparent_background(self):
        # A white-background emblem would reintroduce the original solid-block bug.
        from PIL import Image
        image = Image.open(ASSETS / "apm-emblem.png")
        self.assertEqual(image.mode, "RGBA")
        alpha = image.getchannel("A")
        self.assertEqual(alpha.getextrema()[0], 0, "emblem has no transparent pixels")

    def test_emblem_is_in_the_copied_asset_list(self):
        self.assertIn("apm-emblem.png", render.ASSET_FILES)

    def test_original_logo_is_retained(self):
        self.assertTrue((ASSETS / "apm-logo.png").exists())
        self.assertIn("apm-logo.png", render.ASSET_FILES)


class HeaderBrandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_header_uses_the_emblem_with_explicit_dimensions(self):
        self.assertIn('src="assets/brand/apm-emblem.png"', self.html)
        self.assertIn('width="38"', self.html)
        self.assertIn('height="44"', self.html)
        self.assertIn('class="brand"', self.html)

    def test_wordmark_remains_as_text_next_to_the_emblem(self):
        self.assertIn("Allied Peoples' Movement", self.html)
        self.assertIn("Allied Peoples Movement emblem", self.html)

    def test_no_invert_filter_on_the_header_image(self):
        style = self.html.split("</style>")[0]
        rules = re.findall(r"\.brand img\{[^}]*\}", style)
        self.assertEqual(len(rules), 1, f"expected one .brand img rule, got {rules}")
        for rule in rules:
            self.assertNotIn("invert(", rule)
            self.assertNotIn("brightness(", rule)

    def test_favicon_points_at_the_emblem(self):
        hrefs = re.findall(r'<link rel="icon"[^>]*href="([^"]+)"', self.html)
        self.assertEqual(hrefs, ["assets/brand/apm-emblem.png"])
        for href in hrefs:
            self.assertTrue((Path("docs") / href).exists())

    def test_referenced_assets_all_exist(self):
        for src in set(re.findall(r'src="(assets/[^"]+)"', self.html)):
            with self.subTest(src=src):
                self.assertTrue((Path("docs") / src).exists(), f"missing {src}")


class LanguageControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_control_is_labelled_as_a_language_selector(self):
        self.assertIn("Language", self.html)
        self.assertIn("Harshe", self.html)
        self.assertIn('class="lang-label"', self.html)
        self.assertIn('id="lang-label"', self.html)

    def test_buttons_are_grouped_and_labelled(self):
        self.assertIn('class="lang-toggle"', self.html)
        self.assertIn('role="group"', self.html)
        self.assertIn('aria-labelledby="lang-label"', self.html)
        self.assertIn('data-lang="en"', self.html)
        self.assertIn('data-lang="ha"', self.html)

    def test_choice_persists_across_navigation(self):
        flat = self.html.replace(" ", "")
        self.assertIn("constLANGUAGE_KEY='apm-lang'", flat)
        self.assertIn("window.localStorage.getItem(LANGUAGE_KEY)", flat)
        self.assertIn("window.localStorage.setItem(LANGUAGE_KEY,lang)", flat)
        # the stored value must be re-applied on load
        self.assertIn("conststoredLanguage=readStoredLanguage()", flat)
        self.assertIn("if(storedLanguage)setLanguage(storedLanguage,false)", flat)

    def test_storage_failures_are_contained(self):
        flat = self.html.replace(" ", "")
        # a blocked localStorage must not throw out of the toggle
        self.assertGreaterEqual(flat.count("try{"), 2)
        self.assertIn("catch(error)", flat)

    def test_only_valid_language_values_are_restored(self):
        flat = self.html.replace(" ", "")
        self.assertIn("stored==='ha'||stored==='en'", flat)


class SponsorSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_slot_renders_with_photo_name_and_contribution(self):
        self.assertIn('class="sponsor"', self.html)
        self.assertIn('class="sponsor-photo"', self.html)
        self.assertIn('class="sponsor-name"', self.html)
        self.assertIn('class="sponsor-contribution"', self.html)

    def test_contribution_is_visually_prominent(self):
        self.assertIn(".sponsor-contribution b{color:#fff;font-weight:700}", self.html)

    def test_every_field_is_bilingual(self):
        for en, ha in (("Sponsor", "Mai tallafi"),
                       ("Contribution:", "Zuciya:"),
                       ("Sponsor photo", "Hotun mai tallafi")):
            with self.subTest(label=en):
                self.assertIn(en, self.html)
                self.assertIn(ha, self.html)

    def test_slot_ships_as_an_obvious_placeholder(self):
        self.assertIn("[ Sponsor name ]", self.html)
        self.assertIn("[ Suna na mai tallafi ]", self.html)
        self.assertIn("to be completed by the campaign team", self.html)

    def test_no_invented_sponsor_content(self):
        # No amount, no organisation, no role may be fabricated into the slot.
        blocks = re.findall(r'<div class="sponsor">.*?</div></div>(?=<a class="deerflow")',
                            self.html, re.S)
        self.assertEqual(len(blocks), 1, "expected exactly one sponsor slot")
        text = blocks[0] if blocks else ""
        self.assertNotRegex(text, r"[₦$]\s?[\d,]+")
        self.assertNotRegex(text, r"\b\d{4,}\b")
        for invented in ("Dr. Yakubu Adamu", "APM", "Bauchi State Government"):
            self.assertNotIn(invented, text)

    def test_slot_is_visually_a_placeholder(self):
        style = self.html.split("</style>")[0]
        rules = re.findall(r"\.sponsor\{[^}]*\}", style)
        self.assertEqual(len(rules), 1, f"expected one .sponsor rule, got {rules}")
        for rule in rules:
            self.assertIn("border:1px dashed", rule)
        photo = re.findall(r"\.sponsor-photo\{[^}]*\}", style)
        for rule in photo:
            self.assertIn("border:1px dashed", rule)

    def test_footer_wraps_on_narrow_screens(self):
        # The tile is a third flex child; without wrapping it would squeeze the brand.
        # Two rules are expected: the flex base and the 760px display:block override.
        style = self.html.split("</style>")[0]
        rules = re.findall(r"\.footer-inner\{[^}]*\}", style)
        self.assertGreaterEqual(len(rules), 2)
        self.assertTrue(any("flex-wrap:wrap" in r for r in rules),
                        "base .footer-inner must wrap")
        self.assertTrue(any("display:block" in r for r in rules),
                        "narrow-screen override must stack the footer")


class PromiseIntegrityTests(unittest.TestCase):
    def test_no_two_promises_share_text(self):
        render.validate_unique_promises()

    def test_wash_promise_is_labelled_as_a_clause(self):
        rows = {r["promise_id"]: r for r in render.read_csv("promises.csv")}
        wash = rows["promise-wash"]
        self.assertEqual(wash["promise_type"], "Published commitment clause")
        self.assertIn("Infrastructure", wash["approval_status"])
        self.assertNotEqual(wash["promise_text"], rows["promise-infrastructure"]["promise_text"])

    def test_agenda_renders_each_promise_once(self):
        html = PAGE.read_text(encoding="utf-8")
        cards = re.findall(r'<article class="agenda-card">', html)
        self.assertEqual(len(cards), len(render.read_csv("promises.csv")))

    def test_validator_catches_a_reintroduced_duplicate(self):
        import csv
        import pathlib
        import shutil
        import tempfile

        target = pathlib.Path(render.DATA) / "promises.csv"
        with tempfile.TemporaryDirectory() as tmp:
            backup = pathlib.Path(tmp) / "promises.csv"
            shutil.copy(target, backup)
            try:
                with target.open(encoding="utf-8", newline="") as fh:
                    reader = csv.DictReader(fh)
                    fields = list(reader.fieldnames or [])
                    rows = list(reader)
                infra = next(r["promise_text"] for r in rows
                             if r["promise_id"] == "promise-infrastructure")
                for row in rows:
                    if row["promise_id"] == "promise-wash":
                        row["promise_text"] = infra
                with target.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
                    writer.writeheader()
                    writer.writerows(rows)
                with self.assertRaises(ValueError) as caught:
                    render.validate_unique_promises()
                self.assertIn("duplicate promise_text", str(caught.exception))
            finally:
                shutil.copy(backup, target)
        render.validate_unique_promises()


class ScriptIntegrityTests(unittest.TestCase):
    """The page ships as one inline <script>. A duplicate `const` declaration is a
    SyntaxError that silently disables every handler on the page, and the HTML still
    renders, so only a real parse catches it."""

    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")
        blocks = re.findall(r"<script>(.*?)</script>", cls.html, re.S)
        cls.js = "\n".join(blocks)

    def test_inline_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node is unavailable; duplicate-declaration guard inactive")
        handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
        try:
            handle.write(self.js)
            handle.close()
            result = subprocess.run([node, "--check", handle.name],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[:2000])
        finally:
            os.unlink(handle.name)

    def test_no_duplicate_top_level_const_declarations(self):
        names = re.findall(r"^const\s+([A-Za-z_$][\w$]*)\s*=", self.js, re.M)
        duplicates = {n for n in names if names.count(n) > 1}
        self.assertEqual(duplicates, set(), f"duplicate const declarations: {duplicates}")

    def test_set_language_is_defined_exactly_once(self):
        self.assertEqual(len(re.findall(r"const setLanguage=", self.js)), 1)

    def test_language_persistence_wired_into_the_single_definition(self):
        self.assertIn("if(persist)storeLanguage(lang);", self.js)


if __name__ == "__main__":
    unittest.main()
