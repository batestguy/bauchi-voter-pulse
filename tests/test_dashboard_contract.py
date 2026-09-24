import unittest
from pathlib import Path


class DashboardContractTests(unittest.TestCase):
    def test_language_toggle_preserves_selected_lga(self):
        html = Path("docs/index.html").read_text(encoding="utf-8")
        self.assertIn("let selectedLga=''", html)
        self.assertIn("const renderLgaDetail=", html)
        self.assertIn("renderLgaDetail();", html)
        self.assertIn("data-summary-ha", html)


if __name__ == "__main__":
    unittest.main()
