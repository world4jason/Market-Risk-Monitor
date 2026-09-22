import json
import unittest
from pathlib import Path

from pipeline.presentation import (
    COMPARISONS,
    apply_presentation,
    comparison_for,
)


def metric(metric_id, units, *, transform="raw-v1", kind="raw"):
    return {
        "metric": {
            "id": metric_id,
            "name": metric_id,
            "pillar": "context",
            "units": units,
            "frequency": "monthly",
            "polarity": "contextual",
        },
        "lineage": {
            "kind": kind,
            "inputs": [],
            "formula": None,
            "transform_version": transform,
        },
        "observations": [],
    }


class ComparisonSemanticsTests(unittest.TestCase):
    def test_policy_rate_levels_compare_in_basis_points(self):
        # 1.75% -> 2.00% is +25 bp, never +14.29%.
        for metric_id, transform in [
            ("us_fed_policy_rate", "rate-velocity-v1"),
            ("tw_cbc_rate", "rate-velocity-v1"),
            ("fed_target_legacy", "fred-raw-v1"),
            ("fed_target_upper", "fred-raw-v1"),
        ]:
            self.assertEqual(
                comparison_for(metric(metric_id, "percent", transform=transform)),
                "basis_points",
                metric_id,
            )

    def test_other_percent_metrics_compare_in_percentage_points(self):
        self.assertEqual(
            comparison_for(metric("tw_advance_decline_pct", "percent", transform="tw-ad-v1")),
            "percentage_points",
        )

    def test_an_unrecognised_percent_metric_still_never_uses_relative_percent(self):
        # The safety property: percentage points and basis points are the same
        # dimension, so a metric we have not classified is displayed in a
        # different unit, never with the wrong meaning.
        result = comparison_for(metric("some_future_percent_metric", "percent"))
        self.assertIn(result, {"percentage_points", "basis_points"})

    def test_derived_percent_change_metrics_have_no_further_comparison(self):
        for metric_id in ["finra_margin_debt_mom_pct", "finra_margin_debt_yoy_pct"]:
            self.assertEqual(
                comparison_for(
                    metric(metric_id, "percent", transform="pct-change-v1", kind="derived")
                ),
                "none",
                metric_id,
            )

    def test_basis_point_metrics_are_already_changes(self):
        for metric_id in ["us_fed_policy_step_bp", "tw_cbc_change_6m_bp"]:
            self.assertEqual(
                comparison_for(
                    metric(metric_id, "basis points", transform="rate-velocity-v1")
                ),
                "none",
                metric_id,
            )

    def test_binary_metrics_have_no_comparison(self):
        self.assertEqual(comparison_for(metric("us_recession", "binary")), "none")

    def test_balances_and_index_levels_use_relative_percent(self):
        self.assertEqual(
            comparison_for(metric("finra_margin_debt", "USD millions", transform="finra-raw-v2")),
            "percent_change",
        )
        self.assertEqual(
            comparison_for(metric("tw_taiex", "index", transform="twse-raw-v1")),
            "percent_change",
        )
        self.assertEqual(
            comparison_for(metric("vix", "index", transform="cboe-vix-raw-v1")),
            "percent_change",
        )
        self.assertEqual(
            comparison_for(metric("shiller_cape", "ratio", transform="shiller-raw-v1")),
            "percent_change",
        )

    def test_zero_centred_indices_use_absolute_change(self):
        # NFCI sits around zero and goes negative, so a relative change has no
        # stable sign and is not meaningful.
        for metric_id in [
            "nfci",
            "nfci_risk",
            "nfci_credit",
            "nfci_nonfinancial_leverage",
            "tw_advance_decline_line",
        ]:
            self.assertEqual(
                comparison_for(metric(metric_id, "index")),
                "absolute",
                metric_id,
            )

    def test_counts_use_absolute_change(self):
        # A net advance-decline difference crosses zero.
        self.assertEqual(
            comparison_for(metric("tw_advance_decline_diff", "count", transform="tw-ad-v1")),
            "absolute",
        )
        self.assertEqual(
            comparison_for(metric("tw_advancing_stocks", "count", transform="twse-raw-v1")),
            "absolute",
        )

    def test_percentile_metrics_compare_in_percentage_points(self):
        self.assertEqual(
            comparison_for(metric("some_percentile", "percentile")),
            "percentage_points",
        )

    def test_every_result_is_in_the_declared_vocabulary(self):
        for units in [
            "percent",
            "percentile",
            "basis points",
            "binary",
            "count",
            "index",
            "ratio",
            "USD millions",
            "TWD",
            "shares",
            "score",
            "something_unheard_of",
        ]:
            self.assertIn(comparison_for(metric("x", units)), COMPARISONS)


class ApplyPresentationTests(unittest.TestCase):
    def test_stamps_comparison_without_mutating_the_input(self):
        original = metric("tw_taiex", "index", transform="twse-raw-v1")
        stamped = apply_presentation(original)

        self.assertEqual(stamped["metric"]["comparison"], "percent_change")
        self.assertNotIn("comparison", original["metric"])

    def test_an_existing_comparison_is_preserved(self):
        original = metric("tw_taiex", "index", transform="twse-raw-v1")
        original["metric"]["comparison"] = "absolute"
        self.assertEqual(
            apply_presentation(original)["metric"]["comparison"],
            "absolute",
        )

    def test_non_metric_payloads_pass_through_untouched(self):
        for payload in [
            {"schema_version": "1.0.0", "metrics": []},
            {"schema_version": "1.0.0", "current": None, "history": []},
            {"not": "a metric"},
        ]:
            self.assertEqual(apply_presentation(payload), payload)

    def test_validator_vocabulary_matches(self):
        from pipeline.validate import ALLOWED_COMPARISONS

        self.assertEqual(set(ALLOWED_COMPARISONS), set(COMPARISONS))

    def test_schema_enum_matches_the_python_vocabulary(self):
        schema = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "schemas"
                / "metric-series.schema.json"
            ).read_text(encoding="utf-8")
        )
        enum = schema["properties"]["metric"]["properties"]["comparison"]["enum"]
        self.assertEqual(set(enum), set(COMPARISONS))


if __name__ == "__main__":
    unittest.main()
