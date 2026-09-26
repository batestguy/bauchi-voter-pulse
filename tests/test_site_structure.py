"""S3 contract tests for the six-page split.

Two release-breaking traps motivated this file:

1. The weekly cron used to stage only `docs/index.html`. It now stages
   `docs/*.html`, and a missing page fails the build rather than shipping stale.
2. A duplicate `const` in a page's inline script is a SyntaxError that disables
   every handler on that page while the HTML still renders. Each generated page
   is parsed with `node --check`.
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.dashboard import render

DOCS = Path("docs")

# Re-exported for the type checker: these are defined at import time in render.py.
PAGE_BUILDERS = render.PAGE_BUILDERS
PAGE_NAV = render.PAGE_NAV
SHELL_CSS = render.SHELL_CSS

PAGE_SLUGS = ("index", "achievements", "atlas", "poll", "agenda", "sources")


def read(slug):
    return (DOCS / f"{slug}.html").read_text(encoding="utf-8")


class GeneratedPageTests(unittest.TestCase):
    def test_every_page_is_generated(self):
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertTrue((DOCS / f"{slug}.html").exists())
                self.assertGreater((DOCS / f"{slug}.html").stat().st_size, 10_000)

    def test_render_lists_exactly_the_six_pages(self):
        self.assertEqual(tuple(PAGE_BUILDERS), PAGE_SLUGS)

    def test_every_page_has_its_own_title_and_description(self):
        titles, descriptions = set(), set()
        for slug in PAGE_SLUGS:
            html = read(slug)
            titles_found = re.findall(r"<title>(.*?)</title>", html)
            descs_found = re.findall(r'<meta name="description" content="(.*?)">', html)
            self.assertEqual(len(titles_found), 1, f"{slug} must have exactly one title")
            self.assertEqual(len(descs_found), 1, f"{slug} must have exactly one description")
            self.assertGreater(len(titles_found[0]), 5)
            self.assertGreater(len(descs_found[0]), 20)
            titles.add(titles_found[0])
            descriptions.add(descs_found[0])
        self.assertEqual(len(titles), len(PAGE_SLUGS), "titles must be unique per page")
        self.assertEqual(len(descriptions), len(PAGE_SLUGS), "descriptions must be unique")

    def test_pages_declare_their_own_body_class(self):
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertIn(f'class="page page--{slug}"', read(slug))

    def test_relative_asset_paths_resolve(self):
        for slug in PAGE_SLUGS:
            html = read(slug)
            for src in set(re.findall(r'src="(assets/[^"]+)"', html)):
                with self.subTest(page=slug, src=src):
                    self.assertTrue((DOCS / src).exists(), f"{slug}: missing {src}")

    def test_no_nested_directory_paths(self):
        # Pages are flat in docs/ so assets/brand/... keeps resolving without "../".
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertNotIn('src="../', read(slug))
                self.assertNotIn('href="../', read(slug))

    def test_heavy_sections_appear_on_exactly_one_page(self):
        expectations = {
            'class="source-list"': ("sources",),
            'id="requests"': ("poll",),
            'id="agenda"': ("agenda",),
            'id="indicators"': ("achievements",),
            'id="atlas"': ("atlas",),
            'data-featured-carousel': ("achievements",),
        }
        for needle, expected in expectations.items():
            with self.subTest(needle=needle):
                carriers = [s for s in PAGE_SLUGS if needle in read(s)]
                self.assertEqual(carriers, list(expected),
                                 f"{needle} should be on {expected}, found on {carriers}")


class NavigationTests(unittest.TestCase):
    def test_every_page_carries_all_navigation_links(self):
        for slug in PAGE_SLUGS:
            html = read(slug)
            for target, _label_en, _label_ha in PAGE_NAV:
                with self.subTest(page=slug, target=target):
                    self.assertIn(f'href="{target}.html"', html)

    def test_exactly_one_page_is_marked_current(self):
        for slug in PAGE_SLUGS:
            html = read(slug).split("</style>")[-1]  # markup only
            with self.subTest(page=slug):
                # one in the desktop nav, one in the mobile panel
                self.assertEqual(html.count('aria-current="page"'), 2)

    def test_aria_label_carries_no_markup(self):
        # aria-label is an attribute; a <span> inside it is invalid.
        for slug in PAGE_SLUGS:
            html = read(slug)
            labels = re.findall(r'aria-label="([^"]*)"', html)
            for label in labels:
                with self.subTest(page=slug, label=label[:30]):
                    self.assertNotIn("<", label)

    def test_current_page_marks_itself(self):
        for slug in PAGE_SLUGS:
            html = read(slug)
            with self.subTest(page=slug):
                self.assertIn(f'<a class="" href="{slug}.html" aria-current="page">', html)

    def test_mobile_menu_exists_because_the_desktop_nav_is_hidden(self):
        # .nav is display:none below 1050px, so the <details> menu is the only
        # phone path to any subpage.
        css = SHELL_CSS
        self.assertIn(".navmenu{display:none}", css)
        self.assertIn("@media (max-width:1050px){", css)
        for slug in PAGE_SLUGS:
            html = read(slug)
            with self.subTest(page=slug):
                self.assertIn('class="navmenu"', html)
                self.assertIn("<summary", html)
                self.assertIn('class="navmenu-panel"', html)

    def test_menu_uses_no_javascript(self):
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertNotIn("navmenu", read(slug).split("<script>")[-1])

    def test_subpages_have_a_solid_header(self):
        # index keeps the dark hero; the rest need an opaque header or the white
        # brand text lands on the cream page background.
        self.assertIn("<header class=\"hero\"", read("index"))
        for slug in PAGE_SLUGS[1:]:
            with self.subTest(page=slug):
                self.assertIn('class="page-head"', read(slug))
                self.assertIn("page-hero", read(slug))
        # The mobile panel is absolutely positioned at top:100% of the bar, so the
        # bar must be its containing block - position:static put it off-screen.
        self.assertIn(".page-head .topbar{position:relative", SHELL_CSS)
        self.assertNotIn(".navmenu .navmenu-panel{position:fixed}", SHELL_CSS)

    def test_home_page_links_out_to_every_subpage(self):
        html = read("index")
        for slug in PAGE_SLUGS[1:]:
            with self.subTest(target=slug):
                self.assertIn(f'href="{slug}.html"', html)
        self.assertIn("nav-cards", html)

    def test_brand_and_language_control_on_every_page(self):
        for slug in PAGE_SLUGS:
            html = read(slug)
            with self.subTest(page=slug):
                self.assertIn('src="assets/brand/apm-emblem.png"', html)
                self.assertIn('class="lang-label"', html)
                self.assertIn('data-lang="en"', html)
                self.assertIn('data-lang="ha"', html)
                self.assertIn('class="sponsor"', html)
                icons = re.findall(r'<link rel="icon"[^>]*href="([^"]+)"', html)
                self.assertEqual(icons, ["assets/brand/apm-emblem.png"])
                self.assertTrue((DOCS / icons[0]).exists())


class ScriptRoutingTests(unittest.TestCase):
    def test_core_script_ships_on_every_page(self):
        for slug in PAGE_SLUGS:
            js = "\n".join(re.findall(r"<script>(.*?)</script>", read(slug), re.S))
            with self.subTest(page=slug):
                self.assertIn("const setLanguage=", js)
                self.assertIn("readStoredLanguage", js)
                self.assertIn("let renderFeatured=()=>{};", js)

    def test_featured_script_only_on_achievements(self):
        for slug in PAGE_SLUGS:
            html = read(slug)
            with self.subTest(page=slug):
                self.assertEqual("moveFeatured" in html, slug == "achievements")

    def test_request_script_only_on_poll(self):
        for slug in PAGE_SLUGS:
            html = read(slug)
            with self.subTest(page=slug):
                self.assertEqual("publicRequestForm" in html, slug == "poll")

    def test_sector_filter_script_only_on_index(self):
        for slug in PAGE_SLUGS:
            html = read(slug)
            with self.subTest(page=slug):
                self.assertEqual("data-filter" in html, slug == "index")

    def test_lga_tile_binding_ships_everywhere_but_is_inert_off_atlas(self):
        # renderLgaDetail is on the core script and null-guarded, so it is safe on
        # pages with no [data-lga] buttons.
        for slug in PAGE_SLUGS:
            js = "\n".join(re.findall(r"<script>(.*?)</script>", read(slug), re.S))
            with self.subTest(page=slug):
                self.assertIn("if(!titleEl||!copyEl)return;", js)

    def test_every_page_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        for slug in PAGE_SLUGS:
            js = "\n".join(re.findall(r"<script>(.*?)</script>", read(slug), re.S))
            with self.subTest(page=slug):
                handle = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                                     encoding="utf-8")
                try:
                    handle.write(js)
                    handle.close()
                    result = subprocess.run([node, "--check", handle.name],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr[:1500])
                finally:
                    os.unlink(handle.name)

    def test_no_duplicate_top_level_declarations_per_page(self):
        for slug in PAGE_SLUGS:
            js = "\n".join(re.findall(r"<script>(.*?)</script>", read(slug), re.S))
            names = re.findall(r"^(?:const|let|var)\s+([A-Za-z_$][\w$]*)", js, re.M)
            duplicates = {n for n in names if names.count(n) > 1}
            with self.subTest(page=slug):
                self.assertEqual(duplicates, set(), f"{slug} duplicates {duplicates}")


class ReleaseTrapTests(unittest.TestCase):
    """Both traps failed silently before. These assert the fixes stay in place."""

    def test_workflow_stages_every_generated_page(self):
        workflow = Path(".github/workflows/rebuild-pages.yml").read_text(encoding="utf-8")
        self.assertIn("git add docs/*.html", workflow)
        self.assertNotIn("git add docs/index.html", workflow)

    def test_workflow_fails_when_a_page_is_missing(self):
        workflow = Path(".github/workflows/rebuild-pages.yml").read_text(encoding="utf-8")
        self.assertIn("Verify every generated page exists", workflow)
        for slug in PAGE_SLUGS:
            self.assertIn(slug, workflow)

    def test_workflow_keeps_the_column_six_asset_gate(self):
        workflow = Path(".github/workflows/rebuild-pages.yml").read_text(encoding="utf-8")
        self.assertIn("$6 != \"campaign approved\"", workflow)

    def test_every_page_appears_in_the_handoff_allowlist(self):
        handoff = Path("HANDOFF.md").read_text(encoding="utf-8")
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertIn(f"docs/{slug}.html", handoff)

    def test_readme_lists_every_page(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertIn(f"{slug}.html", readme)


if __name__ == "__main__":
    unittest.main()
