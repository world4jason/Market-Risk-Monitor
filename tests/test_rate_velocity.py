import copy
import json
import unittest
from datetime import datetime, timezone

from pipeline.rate_velocity import (
    build_rate_metrics,
    build_rate_regime_artifact,
    combine_fed_target_metrics,
    parse_cbc_rate_csv,
    rate_regime,
    rate_velocity_rows,
)
from pipeline.validate import validate_metric, validate_rate_regime


CONFIG = {
    "regimes": {
        "easing_max_6m_bp": -25,
        "stable_abs_6m_bp": 24.999,
        "aggressive_tightening_min_6m_bp": 100,
        "aggressive_single_step_bp": 75,
    }
}


class RateVelocityTests(unittest.TestCase):
    def test_cbc_steps_and_cumulative_changes(self):
        text = """date,discount_rate,collateral_rate,short_term_rate,source_url
2020-03-20,1.125,1.5,3.375,https://www.cbc.gov.tw/en/lp-695-2.html
2022-03-18,1.375,1.75,3.625,https://www.cbc.gov.tw/en/lp-695-2.html
2022-06-17,1.5,1.875,3.75,https://www.cbc.gov.tw/en/lp-695-2.html
2022-09-23,1.625,2.0,3.875,https://www.cbc.gov.tw/en/lp-695-2.html
2022-12-16,1.75,2.125,4.0,https://www.cbc.gov.tw/en/lp-695-2.html
"""
        rows = parse_cbc_rate_csv(text)
        velocity = rate_velocity_rows(
            [{"date": r["date"], "value": r["discount_rate"]} for r in rows]
        )
        self.assertAlmostEqual(velocity[1]["step_bp"], 25.0)
        self.assertAlmostEqual(velocity[2]["step_bp"], 12.5)
        self.assertAlmostEqual(velocity[3]["change_6m_bp"], 25.0)
        self.assertEqual(rate_regime(velocity[3], CONFIG), "gradual_tightening")

        metrics = build_rate_metrics(
            [{"date": r["date"], "value": r["discount_rate"]} for r in rows],
            prefix="tw_cbc",
            name_prefix="Taiwan CBC Discount Rate",
            provider="CBC",
            source_url="https://www.cbc.gov.tw/en/lp-695-2.html",
            market_scope="Taiwan",
            fetched_at=datetime(2026, 9, 21, tzinfo=timezone.utc),
        )
        self.assertIn("tw_cbc_rate", metrics)
        self.assertIn("tw_cbc_change_6m_bp", metrics)
        for metric in metrics.values():
            validate_metric(metric)

    def test_fed_daily_series_is_compressed_to_change_points(self):
        legacy = {
            "observations": [
                {"date": "2008-12-14", "value": 1.0},
                {"date": "2008-12-15", "value": 1.0},
            ]
        }
        upper = {
            "observations": [
                {"date": "2008-12-16", "value": 0.25},
                {"date": "2008-12-17", "value": 0.25},
                {"date": "2015-12-17", "value": 0.50},
                {"date": "2015-12-18", "value": 0.50},
            ]
        }
        combined = combine_fed_target_metrics(legacy, upper)
        self.assertEqual(
            combined,
            [
                {"date": "2008-12-14", "value": 1.0},
                {"date": "2008-12-16", "value": 0.25},
                {"date": "2015-12-17", "value": 0.50},
            ],
        )

    def test_75bp_single_step_is_aggressive(self):
        rows = [
            {"date": "2022-03-17", "value": 0.50},
            {"date": "2022-05-05", "value": 1.00},
            {"date": "2022-06-16", "value": 1.75},
        ]
        velocity = rate_velocity_rows(rows)
        self.assertAlmostEqual(velocity[-1]["step_bp"], 75.0)
        self.assertEqual(
            rate_regime(velocity[-1], CONFIG),
            "aggressive_tightening",
        )

    def test_rate_regime_artifact(self):
        rows = [
            {"date": "2022-03-17", "value": 0.50},
            {"date": "2022-05-05", "value": 1.00},
            {"date": "2022-06-16", "value": 1.75},
        ]
        artifact = build_rate_regime_artifact(
            rows,
            CONFIG,
            name="Fed Policy Rate Regime",
        )
        self.assertEqual(
            artifact["current"]["regime"],
            "aggressive_tightening",
        )
        validate_rate_regime(artifact)
        self.assertEqual(
            artifact["provenance"]["methodology"]["id"],
            "policy-rate-regime",
        )
        self.assertEqual(
            artifact,
            build_rate_regime_artifact(
                copy.deepcopy(rows),
                copy.deepcopy(CONFIG),
                name="Fed Policy Rate Regime",
            ),
        )


if __name__ == "__main__":
    unittest.main()
