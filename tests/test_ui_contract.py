from __future__ import annotations

import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_braced_block(source: str, anchor: str) -> str:
    start = source.index(anchor)
    brace = source.index("{", start)
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False

    i = brace
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
            i += 1
            continue

        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                i += 2
                continue
            i += 1
            continue

        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            i += 1
            continue

        if char == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if char in ("'", '"', "`"):
            quote = char
            i += 1
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace : i + 1]
        i += 1

    raise AssertionError(f"unterminated block for {anchor}")


def extract_function(source: str, name: str) -> str:
    return extract_braced_block(source, f"function {name}(")


def flatten_rules(rule: dict) -> list[dict]:
    if not rule:
        return []
    if rule.get("children"):
        out: list[dict] = []
        for child in rule["children"]:
            out.extend(flatten_rules(child))
        return out
    return [rule]


def reference_taiwan_breadth_state(
    *,
    present: bool,
    observations: int,
    freshness: str,
    percentile_available: bool,
) -> str:
    if not present or observations == 0:
        return "missing"
    if freshness != "fresh":
        return "not_current"
    if observations == 1:
        return "snapshot_only"
    if not percentile_available:
        return "history_building"
    return "context_available"


class IdAttributeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.by_id: dict[str, dict[str, str | None]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        element_id = attr_map.get("id")
        if element_id:
            self.by_id[element_id] = attr_map


class UiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
        cls.signals = json.loads(
            (ROOT / "data" / "generated" / "signals.json").read_text(encoding="utf-8")
        )
        cls.margin_yoy = json.loads(
            (ROOT / "data" / "generated" / "finra_margin_debt_yoy_pct.json").read_text(
                encoding="utf-8"
            )
        )
        cls.margin_level = json.loads(
            (ROOT / "data" / "generated" / "finra_margin_debt.json").read_text(
                encoding="utf-8"
            )
        )
        cls.parser = IdAttributeParser()
        cls.parser.feed(cls.html)

    def test_decision_summary_precedes_explanation_cards_and_market_detail(self) -> None:
        decision = self.html.index('class="decision-summary"')
        cards = self.html.index('class="overview-grid"')
        us_detail = self.html.index('id="us-detail"')
        taiwan_detail = self.html.index('id="taiwan-detail"')

        self.assertLess(decision, cards)
        self.assertLess(decision, us_detail)
        self.assertLess(decision, taiwan_detail)

        for state_id in (
            "decision-stress-state",
            "decision-leverage-state",
            "decision-deleveraging-state",
            "decision-taiwan-state",
            "decision-coverage-state",
        ):
            self.assertIn(state_id, self.parser.by_id)

        mobile_css = self.styles[self.styles.rindex("@media (max-width: 640px)") :]
        self.assertIn(".mode-nav { display: none; }", mobile_css)
        self.assertIn(".decision-summary", mobile_css)
        self.assertIn("grid-template-columns: 1fr;", mobile_css)

    def test_every_lead_metric_has_every_required_beginner_field(self) -> None:
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
        registry = extract_braced_block(self.app, "const beginnerContext =")

        for metric_id in required_metrics:
            metric_block = extract_braced_block(registry, f"{metric_id}:")
            for field in required_fields:
                with self.subTest(metric_id=metric_id, field=field):
                    self.assertRegex(metric_block, rf"\b{re.escape(field)}\s*:")

    def test_taiwan_breadth_state_machine_covers_missing_snapshot_and_history(self) -> None:
        cases = [
            (
                dict(
                    present=False,
                    observations=0,
                    freshness="missing",
                    percentile_available=False,
                ),
                "missing",
            ),
            (
                dict(
                    present=True,
                    observations=0,
                    freshness="fresh",
                    percentile_available=False,
                ),
                "missing",
            ),
            (
                dict(
                    present=True,
                    observations=1,
                    freshness="fresh",
                    percentile_available=False,
                ),
                "snapshot_only",
            ),
            (
                dict(
                    present=True,
                    observations=2,
                    freshness="fresh",
                    percentile_available=False,
                ),
                "history_building",
            ),
            (
                dict(
                    present=True,
                    observations=300,
                    freshness="fresh",
                    percentile_available=True,
                ),
                "context_available",
            ),
            (
                dict(
                    present=True,
                    observations=300,
                    freshness="stale",
                    percentile_available=True,
                ),
                "not_current",
            ),
        ]
        for inputs, expected in cases:
            with self.subTest(inputs=inputs):
                self.assertEqual(reference_taiwan_breadth_state(**inputs), expected)

        classifier = extract_function(self.app, "taiwanBreadthState")
        for state_name in (
            "missing",
            "not_current",
            "snapshot_only",
            "history_building",
            "context_available",
        ):
            self.assertIn(f'state: "{state_name}"', classifier)

        overview = extract_function(self.app, "renderOverview")
        detail = extract_function(self.app, "renderTaiwanMarket")
        self.assertIn("taiwanBreadthState(twBreadth)", overview)
        self.assertIn("taiwanBreadthState(adPct)", detail)
        self.assertIn('breadth.state === "missing"', overview)
        self.assertIn('breadth.state === "snapshot_only"', overview)
        self.assertIn('breadth.state === "history_building"', overview)

    def test_taiex_current_wording_is_guarded_by_effective_freshness(self) -> None:
        overview = extract_function(self.app, "renderOverview")
        self.assertIn(
            "const taiexFreshness = effectiveFreshness(taiex).state;",
            overview,
        )
        freshness_guard = overview.index('taiexFreshness !== "fresh"')
        current_wording = overview.index('"TAIEX is current;')
        self.assertLess(freshness_guard, current_wording)
        self.assertIn("TAIEX data is ${taiexFreshness}", overview)

    def test_missing_expected_stress_condition_cannot_render_reassuring_summary(self) -> None:
        overview = extract_function(self.app, "renderOverview")
        self.assertIn(
            "const expectedStressConditions = [financialCondition, vixStress];",
            overview,
        )
        self.assertIn(
            "expectedStressConditions.some((condition) => !condition)",
            overview,
        )
        self.assertIn('"U.S. stress evidence is incomplete"', overview)
        self.assertIn(
            '"Current U.S. stress checks are not broadly elevated"',
            overview,
        )

    def test_margin_rollover_exposes_the_actual_positive_growth_deceleration_trigger(self) -> None:
        condition = next(
            item
            for item in self.signals["current"]["conditions"]
            if item["id"] == "margin_debt_rollover"
        )
        active_delta = next(
            rule
            for rule in flatten_rules(condition["rules"])
            if rule["type"] == "delta_periods_below" and rule["status"] == "active"
        )

        self.assertEqual(condition["status"], "active")
        self.assertGreater(self.margin_yoy["latest"]["value"], 0)
        self.assertLessEqual(active_delta["value"], active_delta["threshold"])
        self.assertEqual(active_delta["periods"], 3)

        helper = extract_function(self.app, "marginMomentumEvidence")
        overview = extract_function(self.app, "renderOverview")
        signals = extract_function(self.app, "renderSignals")
        rule_detail = extract_function(self.app, "formatRuleDetail")

        self.assertIn('rule.metric === "finra_margin_debt_yoy_pct"', helper)
        self.assertIn('rule.type === "delta_periods_below"', helper)
        self.assertIn("Math.abs(value).toFixed(1)", helper)
        self.assertIn("marginMomentumEvidence(marginSignal)", overview)
        self.assertIn("this is the active rollover evidence", overview)
        self.assertIn("details.map(formatRuleDetail)", signals)
        self.assertIn("detail.reason", rule_detail)

    def test_contextual_percentile_is_labeled_context_only_in_all_surfaces(self) -> None:
        self.assertEqual(self.margin_level["metric"]["polarity"], "contextual")

        suffix = extract_function(self.app, "percentileContextSuffix")
        card = extract_function(self.app, "metricCard")
        overview = extract_function(self.app, "renderOverview")
        dialog = extract_function(self.app, "openMetric")

        self.assertIn('polarity === "contextual"', suffix)
        self.assertIn('" · context only"', suffix)
        self.assertIn("percentileContextSuffix(metric)", card)
        self.assertIn("overviewPercentileText(margin, marginPct)", overview)
        self.assertIn("percentileContextSuffix(metric)", overview)
        self.assertIn("percentileContextSuffix(metric)", dialog)
        self.assertIn("it is not a risk direction", dialog)

    def test_breadth_beginner_copy_is_not_snapshot_specific(self) -> None:
        registry = extract_braced_block(self.app, "const beginnerContext =")
        breadth = extract_braced_block(registry, "tw_advance_decline_pct:")
        self.assertNotIn("current public release has only one breadth session", breadth)
        self.assertNotIn("only one breadth session", breadth)

        dynamic = extract_function(self.app, "dynamicMetricCaveat")
        self.assertIn('breadth.state === "snapshot_only"', dynamic)
        self.assertIn("Only 1 published breadth session", dynamic)
        self.assertIn('breadth.state === "history_building"', dynamic)

    def test_optional_ma_family_is_compact_and_hidden_before_javascript_runs(self) -> None:
        section_attrs = self.parser.by_id["trend-participation-section"]
        self.assertIn("compact-optional", section_attrs.get("class", ""))

        for element_id in (
            "trend-controls",
            "ma-chart",
            "trend-legend",
            "ma-study-block",
        ):
            with self.subTest(element_id=element_id):
                self.assertIn("hidden", self.parser.by_id[element_id])

        summary_start = self.html.index('id="ma-summary"')
        summary_end = self.html.index('id="ma-chart"', summary_start)
        initial_summary = self.html[summary_start:summary_end]
        self.assertIn(
            "Trend Participation — unavailable in the public release",
            initial_summary,
        )

    def test_percentiles_name_comparison_window_and_use_real_ordinals(self) -> None:
        self.assertIn("function ordinal(", self.app)
        self.assertIn("function rollingWindowLabel(", self.app)
        self.assertIn("percentile vs", self.app)
        self.assertNotIn("rolling history percentile", self.app)

    def test_cbc_effective_and_verified_dates_remain_distinct(self) -> None:
        self.assertIn("effective_vs_verified", self.app)
        self.assertIn("effective since", self.app)
        self.assertIn("source verified", self.app)

    def test_deleveraging_unknown_remains_distinct_from_inactive(self) -> None:
        overview = extract_function(self.app, "renderOverview")
        signals = extract_function(self.app, "renderSignals")
        self.assertIn("unavailable/unknown", signals)
        self.assertIn("unknown is not inactive", signals)
        self.assertIn("not counted as inactive or safe", overview)

    def test_public_page_contains_no_operator_cli_recovery_commands(self) -> None:
        self.assertNotIn("python scripts/", self.html + "\n" + self.app)

    def test_public_language_strategy_is_consistently_english(self) -> None:
        self.assertNotIn("古往今來", self.html)
        self.assertIn("RESEARCH HISTORY", self.html)


if __name__ == "__main__":
    unittest.main()
