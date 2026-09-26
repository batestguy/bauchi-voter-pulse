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


class BilingualRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text(encoding="utf-8")

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
        # A null write here throws inside setLanguage and kills the whole toggle.
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn("if(!titleEl||!copyEl)return;", html.replace(" ", ""))
        self.assertNotIn("document.getElementById('selected-lga').textContent", html)


if __name__ == "__main__":
    unittest.main()
