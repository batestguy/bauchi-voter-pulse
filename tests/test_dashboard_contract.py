import unittest
from pathlib import Path

from src.dashboard import render


class DashboardContractTests(unittest.TestCase):
    def test_language_toggle_preserves_selected_lga(self):
        # S3 moved the LGA atlas onto its own page.
        html = Path("docs/atlas.html").read_text(encoding="utf-8")
        self.assertIn("let selectedLga=''", html)
        self.assertIn("const renderLgaDetail=", html)
        self.assertIn("renderLgaDetail();", html)
        self.assertIn("data-summary-ha", html)

    def test_featured_lga_scope_matches_achievement_geography(self):
        optional = render.read_optional_csv(render.FEATURED_ACHIEVEMENTS_FILE)
        rows = optional[0] if optional else []
        achievements = {row["achievement_id"]: row for row in render.read_csv("achievements.csv")}
        for row in rows:
            names = [name for name in row["lga_names"].split("|") if name]
            if row["lga_scope"] == "lga":
                self.assertEqual(names, [achievements[row["achievement_id"]]["lga"]])
            elif row["lga_scope"] == "multi_lga":
                self.assertGreaterEqual(len(names), 2)
            else:
                self.assertEqual(names, [])

    def test_featured_section_is_rendered_from_current_data(self):
        # S3 moved the featured carousel onto its own page.
        html = Path("docs/achievements.html").read_text(encoding="utf-8")
        optional = render.read_optional_csv(render.FEATURED_ACHIEVEMENTS_FILE)
        if optional is None:
            self.assertNotIn('id="featured"', html)
        else:
            self.assertIn('id="featured"', html)
            self.assertEqual(html.count('data-featured-carousel tabindex'), 1)
            self.assertEqual(html.count('class="featured-slide"'), 5)
            self.assertEqual(html.count("data-featured-state=\"ready\""), 1)
            self.assertGreaterEqual(html.count("Image source"), 5)
            self.assertGreaterEqual(html.count("Featured source"), 5)
            self.assertIn("image_alt_en", optional[0][0])
            self.assertIn("Context image", html)
            self.assertIn("Katagum|Giade|Itas-Gadau|Gamawa|Zaki|Shira|Jamaare", html)
            self.assertIn("data-lga-names=\"Giade\"", html)


if __name__ == "__main__":
    unittest.main()
