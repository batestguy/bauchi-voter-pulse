"""S1 bilingual correctness tests.

Three defect classes are guarded here:

1. UI strings shipping with data-ha == data-en (English in both slots).
2. Hausa text pasted into an English content column.
3. Required Hausa columns going missing, so a future edit cannot silently drop them.

The identity check uses an explicit denylist rather than a blanket data-en == data-ha
comparison: 217 identical pairs are legitimate (electoral RA proper nouns, the "LGA"
acronym, the party motto, and numeric values that are identical in both languages).
"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

from src.dashboard import render

PAGE = Path("docs/index.html")

# Strings that must never render English in the Hausa slot. Numeric values and proper
# nouns are deliberately absent.
MUST_TRANSLATE = (
    "Outcome being measured",
    "Progress delivered",
    "Project underway",
    "Approval milestone",
    "Promise to complete",
    "Next priority",
    "Choose a registration area",
    "Baseline pending",
    "Target not set",
    "Tsarin asal",
    "Sami na gaba",
    "Next result",
    "Source",
)


def bilingual_pairs(html):
    return re.findall(r'data-en="(.*?)" data-ha="(.*?)"', html)


class _BilingualTextCollector(HTMLParser):
    """Collect `[data-en][data-ha]` elements that contain no text of their own.

    Built on `html.parser` rather than a regular expression on purpose. A regex for
    "an element with these two attributes, up to its closing tag" is easy to get subtly
    wrong and then match nothing at all, which produces a guard that passes forever while
    checking zero elements. That happened: the first version of this check used
    `\\bdata-en="..."\\b`, and `\\b` after a closing quote requires a WORD character to
    follow, so it never matched a single element and the test was vacuous. A real parser
    cannot fail that way.
    """

    def __init__(self, js_owned):
        super().__init__(convert_charrefs=True)
        self.js_owned = js_owned
        self.offenders = []
        self._open = []          # stack of (tag, has_text, is_candidate, why)
        self._counted = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        candidate = "data-en" in attributes and "data-ha" in attributes
        is_js_owned = any(
            name in attributes for name in self.js_owned
        ) or any(name in attributes for name in JS_OWNED_ATTRS)
        self._open.append((tag, False, candidate, is_js_owned))
        if candidate and not is_js_owned:
            self._counted += 1

    def handle_startendtag(self, tag, attrs):
        attributes = dict(attrs)
        if "data-en" in attributes and "data-ha" in attributes:
            self._counted += 1
            if not any(name in attributes for name in JS_OWNED_ATTRS):
                self.offenders.append((tag, dict(attributes)))

    def handle_data(self, data):
        if self._open and data.strip():
            tag, _, _, _ = self._open[-1]
            self._open[-1] = (tag, True, self._open[-1][2], self._open[-1][3])

    def handle_endtag(self, tag):
        # Close to the matching open tag, tolerating a stray close.
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index][0] == tag:
                _, has_text, candidate, is_js_owned = self._open.pop(index)
                if candidate and not has_text and not is_js_owned:
                    self.offenders.append((tag, {}))
                return


# Nodes the poll script fills in with `textContent` on first paint. They are legitimately
# empty in the source HTML, so a "has no text" assertion about them would be wrong.
JS_OWNED_ATTRS = frozenset({
    "data-poll-scope-summary",
    "data-poll-scope-total",
})


def bilingual_elements_with_no_text(html):
    """Bilingual elements that ship with no visible text of their own.

    `setLanguage` rewrites `textContent` from `data-ha`, so a bilingual element with empty
    content renders as a visible but EMPTY box until someone toggles the language. That is
    worse than an untranslated string, because the box looks deliberate and there is
    nothing to read. It happened here twice: a note explaining why a share was withheld,
    and a note explaining why the demographic filter is switched off, were both written as
    `<p {attr(...)}>` with no inner text.
    """
    collector = _BilingualTextCollector(JS_OWNED_ATTRS)
    collector.feed(html)
    collector.close()
    # A guard that inspects nothing is worse than no guard, because it reads as coverage.
    if collector._counted == 0:
        raise AssertionError("no bilingual elements were inspected; the check is broken")
    return collector.offenders


# HTML void elements: reported by `handle_starttag` but never closed. Any tree walker built
# on `html.parser` has to skip them or its element stack silently desynchronises.
VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
})


class _ElementChildrenCollector(HTMLParser):
    """Find `[data-en][data-ha]` elements whose DIRECT children include an element.

    The paired data attributes are a *text swap* contract, and `setLanguage` implements it
    with `textContent`. On a parent, that is a deletion of the children. This exists because
    the defect is invisible in a flat scan of the markup: the offending page looks correct
    until someone switches language, and it has now happened twice -- once to the whole map,
    once to the Group dropdown's options.

    Each stack entry records the element's own DIRECT child tags, populated as siblings open
    while it is on the stack. Counting the ancestor stack instead would flag every element
    on the page, which is how the first version of this check failed.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parents_with_bilingual_children = []
        self._open = []   # list of [tag, is_bilingual, [direct_child_tags]]

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in VOID_ELEMENTS:
            # A void element has no closing tag, so pushing it would desynchronise the
            # whole stack and make every element below it look like it owns children. That
            # is how the first version of this check reported 379 offenders on a page with
            # two of them.
            if self._open:
                self._open[-1][2].append(tag)
            return
        if self._open:
            self._open[-1][2].append(tag)
        self._open.append([
            tag,
            "data-en" in attributes and "data-ha" in attributes,
            [],
        ])

    def handle_startendtag(self, tag, attrs):
        # A self-closing tag is still an element child of whatever is open.
        if self._open:
            self._open[-1][2].append(tag)

    def handle_endtag(self, tag):
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index][0] == tag:
                entry = self._open.pop(index)
                if entry[1] and entry[2]:
                    attributes = dict()
                    self.parents_with_bilingual_children.append(
                        (entry[0], entry[2], sorted(attributes)))
                return

    def close(self):
        super().close()
        self._open = []


class BilingualRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

    def test_no_bilingual_element_ships_without_text(self):
        # Guards the whole family of defects at once, on every page, rather than one
        # string at a time. A note that explains why a figure is withheld but has no text
        # is a silent lie: the reader sees the withheld numbers and no reason for them.
        for page in sorted(Path("docs").glob("*.html")):
            with self.subTest(page=page.name):
                offenders = bilingual_elements_with_no_text(
                    page.read_text(encoding="utf-8"))
                self.assertEqual(
                    offenders, [],
                    f"{page.name}: bilingual elements with no text: {offenders}")

    def test_setLanguage_can_never_empty_an_element_that_owns_children(self):
        # `setLanguage` rewrites `textContent` for every `[data-en][data-ha]` element, so
        # that pair on a parent DELETES its children. It blanked the whole map once, and it
        # blanked the Group dropdown's options once, each time because the static HTML
        # looked correct and only the live DOM was wrong.
        #
        # This walks the parsed tree rather than the markup, because the defect is about
        # NESTING, which a flat regex over a file cannot see.
        offenders = []
        for page in sorted(Path("docs").glob("*.html")):
            collector = _ElementChildrenCollector()
            collector.feed(page.read_text(encoding="utf-8"))
            collector.close()
            for tag, child_tags, _ in collector.parents_with_bilingual_children:
                # A <script>'s "children" are its source text, which the parser does not
                # report as elements, so nothing here should ever be a script.
                offenders.append((page.name, tag, sorted(set(child_tags))))
        self.assertEqual(
            offenders, [],
            "elements with data-en/data-ha that own element children; setLanguage will "
            f"delete them on a language switch: {offenders}")

    def test_no_known_ui_string_ships_untranslated(self):
        pairs = bilingual_pairs(self.html)
        offenders = sorted({en for en, ha in pairs if en == ha and en in MUST_TRANSLATE})
        self.assertEqual(offenders, [], f"untranslated UI strings: {offenders}")

    def test_status_vocabulary_has_hausain_everywhere(self):
        self.assertEqual(set(render.STATUS_HA), set(render.STATUS_CLASSES))
        for status in render.STATUS_CLASSES:
            with self.subTest(status=status):
                self.assertTrue(render.STATUS_HA[status].strip())
                self.assertNotEqual(render.STATUS_HA[status], status)

    def test_indicator_statuses_are_a_subset_of_the_vocabulary(self):
        self.assertTrue(render.INDICATOR_STATUSES.issubset(render.STATUS_CLASSES))

    def test_every_status_badge_carries_a_distinct_hausain_slot(self):
        badges = re.findall(
            r'<span class="status status-[a-z]+" data-en="([^"]*)" data-ha="([^"]*)"', self.html)
        self.assertGreater(len(badges), 0)
        identical = [en for en, ha in badges if en == ha]
        self.assertEqual(identical, [], f"status badges rendering English in both slots: {identical}")

    def test_integrity_caveats_translate(self):
        # verification_status and usage_note are our own prose, so they must switch.
        for en, ha in bilingual_pairs(self.html):
            if en.startswith("Publicly announced") or en.startswith("Official LGA report"):
                with self.subTest(en=en):
                    self.assertNotEqual(en, ha)

    def test_source_titles_stay_in_the_source_language(self):
        # Titles are citations. They must NOT be wrapped for translation.
        register = {row["title"] for row in render.read_csv("source_register.csv")}
        for title in register:
            with self.subTest(title=title):
                self.assertNotIn(f'data-en="{title}"', self.html)

    def test_language_toggle_covers_the_page(self):
        self.assertIn('data-lang="en"', self.html)
        self.assertIn('data-lang="ha"', self.html)
        self.assertIn("el.dataset[lang]||el.dataset.en", self.html.replace(" ", ""))


class EnglishColumnTests(unittest.TestCase):
    def test_no_hausain_text_in_english_columns(self):
        render.validate_no_hausain_english_columns()

    def test_detector_catches_known_offenders(self):
        for sample in (
            "Jihada ta fara ayyukan hanya na karkara na RAAMP tare da karkashin 115km.",
            "An fara aikin 38km na hanya ta karkara a Kirfi tare da kudin kungiyar kowane.",
            "An fara aikin hanya na ciki ba tare da 2.5km ba a babban makaranta a Gadau.",
        ):
            with self.subTest(sample=sample[:40]):
                self.assertTrue(render.looks_like_hausa(sample))

    def test_detector_does_not_flag_english_prose(self):
        for sample in (
            "The state began developing a sector strategy for education health.",
            "Primary healthcare facilities offering free maternal and child services",
            "Implementing partner reports a 49 percent increase; follow-up required",
            "300 schools; 3000 teachers; 21000 schools mapped",
            "Bauchi Govt Says 300 Schools Renovated 3000 Teachers Recruited in One Year",
        ):
            with self.subTest(sample=sample[:40]):
                self.assertFalse(render.looks_like_hausa(sample))


class RequiredHausainColumnTests(unittest.TestCase):
    REQUIRED = {
        "indicators.csv": ("status_ha", "measurement_note_ha"),
        "achievements.csv": ("verification_status_ha",),
        "source_register.csv": ("usage_note_ha",),
    }

    def test_required_hausain_columns_are_present_and_populated(self):
        for name, columns in self.REQUIRED.items():
            rows = render.read_csv(name)
            with self.subTest(table=name):
                for column in columns:
                    self.assertIn(column, rows[0], f"{name} missing {column}")
                    blank = [r for r in rows if not r.get(column)]
                    self.assertEqual(blank, [], f"{name}.{column} has blank cells")

    def test_validate_data_accepts_current_tables(self):
        render.validate_data()

    def test_indicator_status_pairs_are_distinct(self):
        rows = render.read_csv("indicators.csv")
        for row in rows:
            with self.subTest(indicator=row["indicator_id"]):
                self.assertNotEqual(row["status"], row["status_ha"])


class HardeningTests(unittest.TestCase):
    def test_attr_falls_back_to_english(self):
        self.assertIn('data-ha="Alpha"', render.attr("Alpha", ""))
        self.assertIn('data-ha="Beta"', render.attr("Alpha", "Beta"))

    def test_status_badge_defaults_to_the_vocabulary(self):
        badge = render.status_badge("Outcome being measured")
        self.assertIn('data-ha="Ana aunawa sakamako"', badge)
        self.assertNotIn('data-ha=""', badge)

    def test_status_badge_prefers_an_explicit_override(self):
        badge = render.status_badge("Progress delivered", "Cin galma")
        self.assertIn('data-ha="Cin galma"', badge)

    def test_lga_detail_guards_its_target_elements(self):
        # A null write here throws inside setLanguage and kills the whole toggle. The
        # panel is now three separate value elements, so every one of them must be reached
        # through a guarded reference rather than a bare getElementById(...).textContent.
        html = PAGE.read_text(encoding="utf-8")
        compact = html.replace(" ", "")
        self.assertIn("if(!titleEl)return;", compact)
        self.assertIn("if(!evidenceEl||!promiseEl||!resultEl)return;", compact)
        for target in ("selected-evidence", "selected-promise", "selected-result"):
            with self.subTest(target=target):
                self.assertIn(f"getElementById('{target}')", compact)
                self.assertNotIn(f"getElementById('{target}').textContent", compact)
        self.assertNotIn("getElementById('selected-lga').textContent", compact)


if __name__ == "__main__":
    unittest.main()
