from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")

    def test_decision_first_overview_precedes_market_detail(self) -> None:
        overview = self.html.index('id="overview"')
        us_detail = self.html.index('id="us-detail"')
        taiwan_detail = self.html.index('id="taiwan-detail"')
        research = self.html.index('id="research"')
        data_health = self.html.index('id="data-health-details"')

        self.assertLess(overview, us_detail)
        self.assertLess(overview, taiwan_detail)
        self.assertLess(research, data_health)
        self.assertIn("What the available evidence says now", self.html)

    def test_every_overview_lead_metric_has_central_beginner_context(self) -> None:
        required_metrics = (
            "nfci",
            "vix",
            "finra_margin_debt",
            "finra_margin_debt_yoy_pct",
            "tw_taiex",
            "tw_advance_decline_pct",
            "tw_cbc_rate",
        )
        required_fields = (
            "plain_name",
            "what_it_measures",
            "why_it_matters",
            "how_to_read",
            "higher_lower_or_contextual",
            "important_reference_level",
            "important_caveat",
        )

        registry_start = self.app.index("const beginnerContext = {")
        registry_end = self.app.index("const signalBeginnerContext = {")
        registry = self.app[registry_start:registry_end]

        for metric_id in required_metrics:
            with self.subTest(metric_id=metric_id):
                self.assertIn(f"{metric_id}: {{", registry)

        for field in required_fields:
            with self.subTest(field=field):
                self.assertGreaterEqual(
                    len(re.findall(rf"\b{re.escape(field)}\s*:", registry)),
                    len(required_metrics),
                )

    def test_percentiles_name_their_comparison_window_and_use_real_ordinals(self) -> None:
        self.assertIn("function ordinal(", self.app)
        self.assertIn("function rollingWindowLabel(", self.app)
        self.assertIn("percentile vs", self.app)
        self.assertNotIn("rolling history percentile", self.app)

    def test_finra_and_cbc_wording_preserves_semantics(self) -> None:
        self.assertIn("Margin leverage momentum slowing", self.app)
        self.assertIn("growth momentum is slowing", self.app)
        self.assertIn("effective since", self.app)
        self.assertIn("source verified", self.app)
        self.assertIn("effective_vs_verified", self.app)

    def test_optional_unavailable_modules_are_compact_and_public_safe(self) -> None:
        combined = self.html + "\n" + self.app
        self.assertIn('id="trend-participation-section"', self.html)
        self.assertIn("compact-optional", self.app)
        self.assertIn("Trend Participation — unavailable in the public release", self.app)
        self.assertIn("Taiwan macro/regime family is not included in this public release", self.app)
        self.assertNotIn("python scripts/", combined)
        self.assertIn(".optional-state", self.styles)

    def test_taiwan_one_session_breadth_is_not_presented_as_a_trend(self) -> None:
        self.assertIn("one-session participation snapshot", self.app)
        self.assertIn("no trend inference", self.app)
        self.assertIn("cannot yet support a trend or percentile conclusion", self.app)

    def test_deleveraging_coverage_keeps_unknown_distinct(self) -> None:
        self.assertIn("unavailable/unknown", self.app)
        self.assertIn("unknown is not inactive", self.app)
        self.assertIn("they are not counted as inactive or safe", self.app)

    def test_public_language_strategy_is_consistently_english(self) -> None:
        self.assertNotIn("古往今來", self.html)
        self.assertIn("RESEARCH HISTORY", self.html)


if __name__ == "__main__":
    unittest.main()
