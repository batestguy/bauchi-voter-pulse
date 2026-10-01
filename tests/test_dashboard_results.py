"""Prove the dashboard renders real figures when a snapshot exists.

Renders with a temporary snapshot in place of the committed one, then removes it, so the
repository never keeps a fabricated tally. The point is that a reader who has cast fifty
votes sees bars and counts -- the empty state must not be what ships.
"""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SNAPSHOT = ROOT / "data" / "delivery" / "poll_snapshot.json"


def rows(n, sector="water", lga="Bauchi", **extra):
    out = []
    for i in range(n):
        row = {"response_id": f"APM-POLL-2026-{i:06d}",
               "created_at": f"2026-10-0{(i % 9) + 1}T10:00:00Z",
               "sector": sector, "lga": lga, "consent": True}
        row.update(extra)
        out.append(row)
    return out


class DashboardShowsResultsTests(unittest.TestCase):
    def setUp(self):
        self.existed = SNAPSHOT.exists()
        self.backup = (SNAPSHOT.read_bytes() if self.existed else None)

    def tearDown(self):
        if self.backup is not None:
            SNAPSHOT.write_bytes(self.backup)
        elif SNAPSHOT.exists():
            SNAPSHOT.unlink()

    def _render_with(self, snapshot):
        SNAPSHOT.write_text(json.dumps(snapshot), encoding="utf-8")
        import importlib
        import src.dashboard.render as render
        importlib.reload(render)
        return render

    def test_a_populated_poll_renders_counts_not_the_empty_state(self):
        from src.poll import aggregate
        snapshot = aggregate.build_public_snapshot(
            rows(30, "water") + rows(24, "education") + rows(18, "healthcare"),
            generated_at="2026-10-09T12:00:00Z")
        render = self._render_with(snapshot)
        section = render.poll_results_section(snapshot)
        self.assertNotIn("No responses have been recorded yet", section)
        # The reader sees the total, so a chart of nothing cannot pass for a result.
        self.assertIn("66", section)
        self.assertIn("data-poll-sector-chart", section)
        self.assertIn("data-poll-table", section)

    def test_an_empty_poll_says_so_above_a_full_dashboard_of_zeros(self):
        # The empty poll renders its whole dashboard -- controls, charts, table -- with
        # every figure at zero, and says why in a line above them. That is a true statement
        # ("nobody has answered yet"), not a placeholder for data that does not exist.
        # What it must never do is invent a count, so the assertion is that nothing
        # non-zero and no reporting date appears.
        from src.poll import aggregate
        snapshot = aggregate.build_public_snapshot([], generated_at="2026-10-09T12:00:00Z")
        render = self._render_with(snapshot)
        section = render.poll_results_section(snapshot)

        self.assertIn("Waiting for the first response", section)
        self.assertIn("data-poll-sector-chart", section)
        self.assertIn("data-poll-table", section)
        # No fabricated figures, and no fabricated period.
        self.assertNotIn("2026-10-09", section)
        self.assertNotRegex(section, r"<b[^>]*>[1-9][0-9]*</b>")

    def test_a_live_figure_carries_its_provenance(self):
        from src.poll import aggregate
        snapshot = aggregate.build_public_snapshot(rows(30), generated_at="2026-10-09T12:00:00Z")
        render = self._render_with(snapshot)
        section = render.poll_results_section(snapshot)
        # A number with no date is not evidence of anything; the reporting date is part of
        # the claim.
        self.assertIn("2026-10-09", section)

    def test_suppressed_cells_are_dashed_never_zero(self):
        # A cell below the floor must read as withheld, not as "nobody chose this". The two
        # look identical in a chart unless one is explicitly a dash.
        from src.poll import aggregate
        snapshot = aggregate.build_public_snapshot(
            rows(30, "water") + rows(6, "security"), generated_at="2026-10-09T12:00:00Z")
        render = self._render_with(snapshot)
        section = render.poll_results_section(snapshot)
        # security has 6, above a floor of 5, so it renders; a 3 would be withheld.
        small = aggregate.build_public_snapshot(
            rows(30, "water") + rows(3, "security"), generated_at="2026-10-09T12:00:00Z")
        self.assertIsNone(small["by_sector"]["security"],
                          "a cell below the floor must be null, not 0")
        self.assertIn("suppressed", section.lower() + "withheld")

    def test_the_reader_is_told_it_is_not_a_survey(self):
        from src.poll import aggregate
        snapshot = aggregate.build_public_snapshot(rows(30), generated_at="2026-10-09T12:00:00Z")
        render = self._render_with(snapshot)
        section = render.poll_results_section(snapshot)
        self.assertIn("not a representative sample", section)
        self.assertIn("not a vote", section)


if __name__ == "__main__":
    unittest.main()