"""Guards that need a real browser.

The rest of the suite is static string checks against the generated HTML. Two classes of
defect cannot be seen that way and are checked here instead:

1. **Horizontal overflow at 375px.** The topbar row is brand + language control + menu
   button. Those three overflowed the shell by 27px on a phone and forced the whole page to
   scroll sideways, on *every* page. The handoff claimed zero overflow had been verified;
   it had not been measured at exactly 375px, so nothing caught it.
2. **The mobile `<details>` menu actually opens.** `.nav` is `display:none` below 1050px, so
   this is the only route to any subpage from a phone.

Skipped, not failed, when Playwright is unavailable, so the suite still runs on a machine
without browsers installed. Playwright is deliberately *not* in requirements.txt -- it
would make every CI run download Chromium for one layout guard -- so to run these:

    pip install playwright && python -m playwright install chromium

`tests/test_site_structure.py::ResponsiveTests` carries a static guard for the same
regression that needs no browser, so the defect cannot return unnoticed in CI.
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE_SLUGS = ("index", "achievements", "atlas", "poll", "agenda", "sources")
MOBILE_WIDTH = 375
DESKTOP_WIDTH = 1440


class MobileTopbarGuardTests(unittest.TestCase):
    """Static counterpart to the browser checks: runs everywhere, no browser needed."""

    def test_small_screen_block_tightens_the_topbar(self):
        # The topbar row is brand + language control + menu button. At 375px those three
        # overflowed the shell by 27px and forced the whole page to scroll sideways. The
        # fix tightens the gaps and type rather than dropping the "Language" label, which
        # is what makes the control self-describing.
        css = (ROOT / "src" / "dashboard" / "render.py").read_text(encoding="utf-8")
        blocks = re.findall(r"@media \(max-width:760px\)\{(.*?)\n\}", css, re.S)
        self.assertTrue(blocks, "expected a max-width:760px block in the stylesheet")
        combined = "\n".join(blocks)
        for rule in (".topbar-inner{gap:", ".lang-label{font-size:",
                     ".lang button{padding:", ".navmenu-toggle{"):
            with self.subTest(rule=rule):
                self.assertIn(rule, combined)

    def test_language_label_is_never_display_none(self):
        """The label is what makes the EN/HA control self-describing; it may shrink, not vanish."""
        css = (ROOT / "src" / "dashboard" / "render.py").read_text(encoding="utf-8")
        self.assertNotIn(".lang-label{display:none", css.replace(" ", ""))
        html = (ROOT / "docs" / "atlas.html").read_text(encoding="utf-8")
        self.assertIn("Language", html)
        self.assertIn("Harshe", html)


def _sync_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    return sync_playwright


class BrowserLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sync_playwright = _sync_playwright()
        if sync_playwright is None:
            raise unittest.SkipTest("playwright is not installed")
        try:
            cls._playwright = sync_playwright().start()
            cls._browser = cls._playwright.chromium.launch()
        except Exception as exc:  # browser binary missing
            cls._playwright.stop()
            raise unittest.SkipTest(f"chromium unavailable: {exc}") from exc
        cls.base = (ROOT / "docs").as_uri()

    @classmethod
    def tearDownClass(cls):
        browser = getattr(cls, "_browser", None)
        if browser is not None:
            browser.close()
        playwright = getattr(cls, "_playwright", None)
        if playwright is not None:
            playwright.stop()

    def test_no_horizontal_overflow_at_mobile_width(self):
        page = self._browser.new_page(viewport={"width": MOBILE_WIDTH, "height": 760})
        try:
            for slug in PAGE_SLUGS:
                with self.subTest(page=slug):
                    page.goto(f"{self.base}/{slug}.html")
                    report = page.evaluate(
                        """() => {
                        const limit = document.documentElement.clientWidth;
                        const over = document.documentElement.scrollWidth - limit;
                        const culprits = [...document.querySelectorAll('*')]
                          .filter(el => el.getBoundingClientRect().right > limit + 1)
                          .map(el => (el.className.baseVal ?? el.className ?? el.tagName).toString());
                        return {over, culprits: [...new Set(culprits)]};
                        }"""
                    )
                    self.assertEqual(
                        report["over"], 0,
                        f"{slug}.html scrolls sideways by {report['over']}px at "
                        f"{MOBILE_WIDTH}px; culprits: {report['culprits']}",
                    )
        finally:
            page.close()

    def test_mobile_details_menu_opens_and_reaches_every_page(self):
        page = self._browser.new_page(viewport={"width": MOBILE_WIDTH, "height": 760})
        try:
            page.goto(f"{self.base}/atlas.html")
            self.assertTrue(page.is_visible(".navmenu"), "the mobile menu must be visible")
            self.assertEqual(page.is_visible(".nav"), False,
                             ".nav is display:none below 1050px, so the details menu "
                             "is the only phone route to a subpage")
            page.click(".navmenu-toggle")
            page.wait_for_selector(".navmenu-panel a", state="visible")
            targets = page.eval_on_selector_all(
                ".navmenu-panel a", "els => els.map(e => e.getAttribute('href'))"
            )
            for slug in PAGE_SLUGS:
                with self.subTest(target=slug):
                    self.assertIn(f"{slug}.html", targets)
        finally:
            page.close()

    def test_map_survives_a_language_switch(self):
        """The bug that motivated the aria()/attr() split in render.py.

        `setLanguage` rewrites textContent for every `[data-en][data-ha]` element, so an
        attr()-bearing <svg> lost all 20 outlines on the first switch to Hausa.
        """
        page = self._browser.new_page(viewport={"width": DESKTOP_WIDTH, "height": 1000})
        try:
            page.goto(f"{self.base}/atlas.html")
            before = page.eval_on_selector_all(".lga-shape", "els => els.length")
            self.assertEqual(before, 20)
            page.click('[data-lang="ha"]')
            self.assertEqual(
                page.eval_on_selector_all(".lga-shape", "els => els.length"), 20,
                "switching to Hausa emptied the map",
            )
            self.assertEqual(page.get_attribute(".lga-map", "aria-label")[0], "T")
            page.click('[data-lang="en"]')
            self.assertEqual(
                page.eval_on_selector_all(".lga-shape", "els => els.length"), 20
            )
        finally:
            page.close()

    def test_map_and_evidence_panel_stay_in_step(self):
        page = self._browser.new_page(viewport={"width": DESKTOP_WIDTH, "height": 1000})
        try:
            page.goto(f"{self.base}/atlas.html")
            page.click('[data-lga="Dambam"]')
            self.assertEqual(page.inner_text("#selected-lga"), "Dambam")
            evidence = page.inner_text("#selected-evidence")
            promise = page.inner_text("#selected-promise")
            result = page.inner_text("#selected-result")
            # Three distinct values in three labelled sections, not one concatenated
            # sentence. The Dambam case is the one that motivated this.
            self.assertIn("49 beds", evidence)
            self.assertIn("maternal outcomes", promise)
            self.assertIn("Measure patient reach", result)
            self.assertNotIn("APM:", evidence)
            self.assertNotIn("Next result:", evidence)
            self.assertEqual(
                page.eval_on_selector_all(".lga-shape.active", "els => els.map(e => e.dataset.lga)"),
                ["Dambam"],
            )
            visible = page.eval_on_selector_all(
                "[data-ra-lga]", "els => els.filter(e => !e.hidden).map(e => e.dataset.raLga)"
            )
            self.assertEqual(visible, ["Dambam"], "the not-geo-located RA list must follow")

            # Switching language re-renders the panel from the Hausa attributes.
            page.click('[data-lang="ha"]')
            self.assertNotEqual(page.inner_text("#selected-evidence"), evidence)
            self.assertNotEqual(page.inner_text("#selected-promise"), promise)
        finally:
            page.close()

    def test_a_map_shape_is_operable_from_the_keyboard(self):
        page = self._browser.new_page(viewport={"width": DESKTOP_WIDTH, "height": 1000})
        try:
            page.goto(f"{self.base}/atlas.html")
            page.focus('[data-lga="Kirfi"]')
            page.keyboard.press("Enter")
            self.assertEqual(page.inner_text("#selected-lga"), "Kirfi")
            page.focus('[data-lga="Zaki"]')
            page.keyboard.press(" ")
            self.assertEqual(page.inner_text("#selected-lga"), "Zaki")
        finally:
            page.close()

    def test_watermark_is_decorative_and_never_intercepts_a_click(self):
        page = self._browser.new_page(viewport={"width": DESKTOP_WIDTH, "height": 1000})
        try:
            for slug in PAGE_SLUGS:
                with self.subTest(page=slug):
                    page.goto(f"{self.base}/{slug}.html")
                    self.assertEqual(page.locator(".watermark").count(), 1)
                    self.assertEqual(
                        page.get_attribute(".watermark", "aria-hidden"), "true",
                        "a decorative watermark must be hidden from assistive technology",
                    )
                    self.assertEqual(page.get_attribute(".watermark img", "alt"), "")
                    self.assertEqual(
                        page.evaluate(
                            "() => getComputedStyle(document.querySelector('.watermark')).pointerEvents"
                        ),
                        "none",
                    )
            # ... and the map still receives its click through the watermark layer.
            page.goto(f"{self.base}/atlas.html")
            page.click('[data-lga="Ganjuwa"]')
            self.assertEqual(page.inner_text("#selected-lga"), "Ganjuwa")
        finally:
            page.close()

    def test_no_console_errors_on_the_atlas(self):
        page = self._browser.new_page(viewport={"width": DESKTOP_WIDTH, "height": 1000})
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(f"{self.base}/atlas.html")
            page.click('[data-map-lga="Kirfi"]')
            page.click('[data-lang="ha"]')
            page.click('[data-lang="en"]')
            page.wait_for_timeout(150)
        finally:
            page.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
