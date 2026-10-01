import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class OverviewStructureTests(unittest.TestCase):
    def setUp(self):
        self.html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.js = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")

    def test_decision_thesis_has_read_confidence_and_triggers(self):
        for element_id in (
            "decision-thesis",
            "overview-thesis-title",
            "overview-thesis-summary",
            "overview-thesis-confidence",
            "overview-thesis-evidence",
            "overview-thesis-triggers",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("function setDecisionThesis(", self.js)
        self.assertIn('data-i18n="thesis.changes"', self.html)
        self.assertIn('"trigger.margin_rule"', self.js)
        self.assertIn('"trigger.breadth_rule"', self.js)

    def test_first_screen_has_exactly_four_snapshot_cards(self):
        cards = re.findall(r'data-overview-card="([^"]+)"', self.html)
        self.assertEqual(cards, ["stress", "leverage", "deleveraging", "taiwan"])

    def test_old_duplicated_overview_surfaces_are_removed(self):
        self.assertNotIn('class="decision-summary"', self.html)
        self.assertNotIn('class="overview-grid"', self.html)
        self.assertNotIn("overview-evidence", self.html)
        self.assertNotIn("overview-note", self.html)

    def test_data_health_is_separate_from_market_interpretation(self):
        self.assertIn('id="overview-health-strip"', self.html)
        self.assertIn('id="overview-health-state"', self.html)
        self.assertIn('id="overview-health-detail"', self.html)
        self.assertIn('href="#data-health-details"', self.html)

    def test_each_card_has_state_value_and_compact_facts(self):
        for kind in ("stress", "leverage", "deleveraging", "taiwan"):
            self.assertIn(f'id="overview-{kind}-status"', self.html)
            self.assertIn(f'id="overview-{kind}-value"', self.html)
            self.assertIn(f'id="overview-{kind}-sub"', self.html)

    def test_renderer_uses_state_first_contract(self):
        self.assertIn("function setSnapshotCard(", self.js)
        self.assertIn("function setOverviewHealth(", self.js)
        self.assertNotIn("function setOverviewCard(", self.js)


if __name__ == "__main__":
    unittest.main()
