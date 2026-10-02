"""S3 contract tests for the six-page split.

Two release-breaking traps motivated this file:

1. The weekly cron used to stage only `docs/index.html`. It now stages
   `docs/*.html`, and a missing page fails the build rather than shipping stale.
2. A duplicate `const` in a page's inline script is a SyntaxError that disables
   every handler on that page while the HTML still renders. Each generated page
   is parsed with `node --check`.
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from src.dashboard import render

DOCS = Path("docs")

# Re-exported for the type checker: these are defined at import time in render.py.
PAGE_BUILDERS = render.PAGE_BUILDERS
PAGE_NAV = render.PAGE_NAV
SHELL_CSS = render.SHELL_CSS

PAGE_SLUGS = ("index", "achievements", "atlas", "poll", "agenda", "about", "sources")


def read(slug):
    return (DOCS / f"{slug}.html").read_text(encoding="utf-8")


class GeneratedPageTests(unittest.TestCase):
    def test_every_page_is_generated(self):
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertTrue((DOCS / f"{slug}.html").exists())
                self.assertGreater((DOCS / f"{slug}.html").stat().st_size, 10_000)

    def test_render_lists_exactly_the_seven_pages(self):
        self.assertEqual(tuple(PAGE_BUILDERS), PAGE_SLUGS)

    def test_every_page_has_its_own_title_and_description(self):
        titles, descriptions = set(), set()
        for slug in PAGE_SLUGS:
            html = read(slug)
            # Scope to <head>. The atlas map carries SVG <title> elements so each outline
            # has a native hover tooltip, and that is a different element from the
            # document title -- counting them as titles made this guard fire on correct
            # markup.
            head = re.search(r"<head>(.*?)</head>", html, re.S)
            if head is None:
                self.fail(f"{slug} must have a <head>")
            titles_found = re.findall(r"<title>(.*?)</title>", head.group(1))
            descs_found = re.findall(r'<meta name="description" content="(.*?)">', head.group(1))
            self.assertEqual(len(titles_found), 1, f"{slug} must have exactly one title")
            self.assertEqual(len(descs_found), 1, f"{slug} must have exactly one description")
            self.assertGreater(len(titles_found[0]), 5)
            self.assertGreater(len(descs_found[0]), 20)
            # A second document title outside <head> would silently override the first.
            outside_svg = re.sub(r"<svg\b.*?</svg>", "", html[head.end():], flags=re.S)
            self.assertNotIn(
                "<title>", outside_svg,
                f"{slug} has a <title> outside <head> that is not inside an <svg>",
            )
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
            'id="demo-video"': ("about",),
        }
        for needle, expected in expectations.items():
            with self.subTest(needle=needle):
                carriers = [s for s in PAGE_SLUGS if needle in read(s)]
                self.assertEqual(carriers, list(expected),
                                 f"{needle} should be on {expected}, found on {carriers}")

    def test_a_download_link_points_at_a_file_that_exists_and_is_registered(self):
        """A link to a missing file is a 404 that no test would ever see.

        The demo video is offered as two downloads from the About page. Nothing else
        on the site links to a binary, so this is the only place a stale path can hide:
        the renderer writes the href from a filename, the register holds a hash, and
        nothing in the ordinary build compares the three. `ASSET_FILES` copies the file
        into `docs/assets/brand/`, so the href, the copy and the register row have to
        agree -- which is exactly what this asserts, and what the repository keeps
        rediscovering the hard way elsewhere.
        """
        html = read("about")
        hrefs = re.findall(r'href="(assets/brand/[^"]+\.(?:mp4|webm|gif))"', html)
        self.assertTrue(hrefs, "the About page should offer at least one download")

        with open("data/delivery/asset_register.csv", encoding="utf-8", newline="") as fh:
            registered = {row["file"] for row in csv.DictReader(fh)}

        for href in hrefs:
            with self.subTest(href=href):
                published = DOCS / href
                source = Path("assets/brand") / Path(href).name
                self.assertTrue(source.exists(), f"{href} has nothing in assets/brand/")
                self.assertTrue(published.exists(),
                                f"{href} was never copied into docs/, so the link 404s")
                self.assertEqual(source.read_bytes(), published.read_bytes(),
                                 "the published copy differs from the registered source")
                self.assertIn(source.name, registered,
                              f"{source.name} is published but absent from asset_register.csv")
                self.assertIn(source.name, render.ASSET_FILES,
                              f"{source.name} is registered but would never be published")

    def test_the_demo_video_states_when_it_was_recorded(self):
        """The caption says "nobody has answered yet". That is a claim with an expiry.

        Once the poll has responses the video is asserting something false, on the
        owner's behalf, in every feed it is shared into. The page carries the recording
        date and the state of the poll at that moment, so the claim is bounded on the
        page rather than only in a commit message nobody rereads.
        """
        html = read("about")
        self.assertIn('id="demo-video"', html)
        section = html.split('id="demo-video"', 1)[1].split("</section>", 1)[0]
        self.assertIn("2 October 2026", section)
        self.assertIn("before any poll response", section)


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

    def test_lga_binding_ships_everywhere_but_is_inert_off_atlas(self):
        # renderLgaDetail is on the core script and null-guarded, so it is safe on
        # pages with no [data-lga] elements.
        for slug in PAGE_SLUGS:
            js = "\n".join(re.findall(r"<script>(.*?)</script>", read(slug), re.S))
            with self.subTest(page=slug):
                self.assertIn("if(!titleEl)return;", js)
                self.assertIn("if(!evidenceEl||!promiseEl||!resultEl)return;", js)

    def test_stylesheet_braces_balance(self):
        # A missing `}` inside a single-line @media block does not fail loudly: the rest
        # of the stylesheet is silently swallowed into the media query, so the rules stop
        # applying at desktop widths. The page still renders, which is what makes it
        # expensive -- it cost a broken hero and topbar on every page before this test
        # existed. CSS in render.py is hand-edited, so check it on every run.
        from src.dashboard import render

        for name, css in (("SITE_CSS", render.SITE_CSS),
                          ("SHELL_CSS", render.SHELL_CSS)):
            with self.subTest(stylesheet=name):
                self.assertEqual(
                    css.count("{"), css.count("}"),
                    f"{name} has unbalanced braces: "
                    f"{css.count('{')} open, {css.count('}')} close. Everything after the "
                    "missing brace is being parsed inside the wrong at-rule.",
                )

    def test_every_media_query_starts_at_the_top_level(self):
        """A missing `}` in one at-rule must not swallow the rules that follow it.

        The real defect this guards: a single-line `@media (max-width:1050px){...}` lost the
        brace closing its first rule, so the rest of the stylesheet was parsed *inside* that
        media query and stopped applying at desktop widths. Total brace count stayed
        plausible and the pages still rendered, just wrong.
        """
        from src.dashboard import render

        for name, css in (("SITE_CSS", render.SITE_CSS),
                          ("SHELL_CSS", render.SHELL_CSS)):
            depth = 0
            for match in re.finditer(r"@media|(\{)|(\})", css):
                if match.group(0) == "@media":
                    with self.subTest(stylesheet=name, at_rule=css[match.start():match.start() + 40]):
                        self.assertEqual(
                            depth, 0,
                            "an @media query began while a previous rule or at-rule was "
                            f"still open (depth {depth}); its contents have swallowed the "
                            f"stylesheet from here: {css[match.start():match.start() + 60]!r}",
                        )
                elif match.group(0) == "{":
                    depth += 1
                else:
                    depth -= 1
            with self.subTest(stylesheet=name):
                self.assertEqual(depth, 0, f"{name} ends inside an unclosed block")

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
    """The traps that failed silently. These assert the fixes stay in place.

    Trap 3 was found on 29 September 2026: the asset-authorization gate parsed
    `asset_register.csv` with `awk -F,`, so any row whose quoted `description` or
    `approval_note` contains a comma was read as unapproved. The derived
    `apm-emblem.png` row is exactly such a row, so the first scheduled run of the
    weekly cron failed and the site had never been regenerated automatically.
    """

    def test_workflow_stages_every_generated_page(self):
        workflow = Path(".github/workflows/rebuild-pages.yml").read_text(encoding="utf-8")
        self.assertIn("git add docs/*.html", workflow)
        self.assertNotIn("git add docs/index.html", workflow)

    def test_workflow_fails_when_a_page_is_missing(self):
        workflow = Path(".github/workflows/rebuild-pages.yml").read_text(encoding="utf-8")
        self.assertIn("Verify every generated page exists", workflow)
        for slug in PAGE_SLUGS:
            self.assertIn(slug, workflow)

    def _asset_gate_script(self):
        """The exact check body from rebuild-pages.yml, dedented and runnable."""
        gate = Path(".github/workflows/rebuild-pages.yml").read_text(encoding="utf-8")
        self.assertIn("python -c '", gate, "asset gate no longer runs a Python check")
        body = gate.split("python -c '", 1)[1].split("';", 1)[0]
        return textwrap.dedent(body)

    def test_asset_gate_parses_the_register_as_csv_not_awk(self):
        # `awk -F,` reads field 6 as the sha256 on any row whose quoted description or
        # approval_note contains a comma, so the gate rejected approved assets and the
        # first scheduled run failed on the derived apm-emblem row. The gate must parse
        # with the csv module and look `usage_status` up by name.
        workflow = Path(".github/workflows/rebuild-pages.yml").read_text(encoding="utf-8")
        commands = "\n".join(line for line in workflow.splitlines()
                             if not line.lstrip().startswith("#"))
        self.assertNotIn("awk", commands)
        self.assertIn("csv.DictReader", commands)
        self.assertIn("usage_status", commands)

    def test_asset_gate_passes_on_the_real_register(self):
        result = subprocess.run([sys.executable, "-c", self._asset_gate_script()],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr.strip())

    def test_asset_gate_rejects_an_unapproved_row(self):
        # Break-test the check: a row that is genuinely unapproved must fail, so the pass
        # above is not a gate that never fires. Approved status is set by column name via
        # the csv module, so the substitution is on a whole parsed row.
        script = self._asset_gate_script()
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "asset_register.csv"
            rows = Path("data/delivery/asset_register.csv").read_text(encoding="utf-8")
            broken = rows.replace("campaign approved", "not approved", 1)
            self.assertNotEqual(broken, rows, "fixture no longer contains an approved row")
            register.write_text(broken, encoding="utf-8")
            probe = script.replace("data/delivery/asset_register.csv",
                                   str(register).replace("\\", "\\\\"))
            result = subprocess.run([sys.executable, "-c", probe],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, "gate passed an unapproved asset")
            self.assertIn("Unapproved campaign assets", result.stderr)

    def test_asset_gate_still_passes_without_the_newest_row(self):
        # Guards the other direction: the gate must not start rejecting a register that
        # is entirely approved, which is how the old version failed on a clean file.
        script = self._asset_gate_script()
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "asset_register.csv"
            lines = Path("data/delivery/asset_register.csv").read_text(
                encoding="utf-8").splitlines(True)
            register.write_text("".join(lines[:-1]), encoding="utf-8")
            probe = script.replace("data/delivery/asset_register.csv",
                                   str(register).replace("\\", "\\\\"))
            result = subprocess.run([sys.executable, "-c", probe],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr.strip())

    def test_asset_gate_rejects_an_approved_row_missing_its_date(self):
        # usage_status alone is not enough: an undated approval is not an approval.
        script = self._asset_gate_script()
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "asset_register.csv"
            rows = Path("data/delivery/asset_register.csv").read_text(encoding="utf-8")
            broken = rows.replace("campaign approved,campaign team,2026-09-24",
                                  "campaign approved,campaign team,", 1)
            self.assertNotEqual(broken, rows, "fixture no longer contains a dated row")
            register.write_text(broken, encoding="utf-8")
            probe = script.replace("data/delivery/asset_register.csv",
                                   str(register).replace("\\", "\\\\"))
            result = subprocess.run([sys.executable, "-c", probe],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, "gate passed an undated approval")
            self.assertIn("Unapproved campaign assets", result.stderr)

    def test_every_page_appears_in_the_handoff_allowlist(self):
        handoff = Path("HANDOFF.md").read_text(encoding="utf-8")
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertIn(f"docs/{slug}.html", handoff)

    def test_the_page_cards_list_every_subpage(self):
        # The home page advertises the site with a row of cards. About was added to
        # PAGE_NAV and to PAGE_BUILDERS but not to that list, so the landing page listed
        # five pages while the nav linked to six and the site shipped seven -- and the
        # heading beside them read "Five pages, one record." None of that broke a link or
        # failed a test, because nothing compared the cards against the pages.
        cards = re.findall(r'<a class="nav-card" href="([a-z]+)\.html"', read("index"))
        expected = [slug for slug in PAGE_SLUGS if slug != "index"]
        self.assertEqual(cards, expected,
                         "the landing-page cards and the generated pages disagree")

    def test_the_page_count_in_the_heading_matches_the_cards(self):
        html = read("index")
        cards = re.findall(r'<a class="nav-card" href="[a-z]+\.html"', html)
        section = re.search(r'id="pages".*?</section>', html, re.S)
        self.assertIsNotNone(section)
        heading = re.search(r'<h2><span data-en="([^"]*)"', section.group(0))
        self.assertIsNotNone(heading)
        for word, number in (("Two", 2), ("Three", 3), ("Four", 4), ("Five", 5),
                             ("Six", 6), ("Seven", 7), ("Eight", 8), ("Nine", 9),
                             ("Ten", 10)):
            if heading.group(1).startswith(word):
                self.assertEqual(
                    number, len(cards),
                    f"heading says {heading.group(1)!r} but there are {len(cards)} cards")
                break
        else:
            self.fail(f"unrecognised page-count heading: {heading.group(1)!r}")

    def test_readme_lists_every_page(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        for slug in PAGE_SLUGS:
            with self.subTest(page=slug):
                self.assertIn(f"{slug}.html", readme)


if __name__ == "__main__":
    unittest.main()
