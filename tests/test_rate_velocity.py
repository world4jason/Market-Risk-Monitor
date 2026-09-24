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
            artifact["provenance"]["required_inputs"],
            ["rate_rows"],
        )
        self.assertIsNone(
            artifact["provenance"]["inputs"][0]["snapshot_at"]
        )
        self.assertEqual(
            artifact,
            build_rate_regime_artifact(
                copy.deepcopy(rows),
                copy.deepcopy(CONFIG),
                name="Fed Policy Rate Regime",
            ),
        )

    def test_empty_history_requires_null_current(self):
        artifact = build_rate_regime_artifact(
            [],
            CONFIG,
            name="Empty Rate Regime",
        )
        # Empty record inputs have no natural as_of/snapshot timestamp; add a
        # valid synthetic snapshot only to exercise the specialized current
        # invariant rather than failing earlier in generic provenance shape.
        artifact["provenance"]["inputs"][0]["snapshot_at"] = (
            "2026-01-01T00:00:00Z"
        )
        artifact["current"] = {
            "date": "2026-01-01",
            "rate": 1.0,
            "step_bp": None,
            "change_3m_bp": None,
            "change_6m_bp": None,
            "change_12m_bp": None,
            "regime": "unknown",
        }
        with self.assertRaisesRegex(
            Exception,
            "current must equal latest history row or null when empty",
        ):
            validate_rate_regime(artifact)

    def test_rate_regime_builder_canonical_sorts_input_rows(self):
        unsorted_rows = [
            {"date": "2022-06-16", "value": 1.75},
            {"date": "2022-03-17", "value": 0.50},
            {"date": "2022-05-05", "value": 1.00},
        ]
        artifact = build_rate_regime_artifact(
            unsorted_rows,
            CONFIG,
            name="Sorted Rate Regime",
        )
        self.assertEqual(
            [row["date"] for row in artifact["history"]],
            ["2022-03-17", "2022-05-05", "2022-06-16"],
        )
        rate_rows = next(
            item
            for item in artifact["provenance"]["inputs"]
            if item["id"] == "rate_rows"
        )
        self.assertEqual(rate_rows["as_of"], "2022-06-16")
        validate_rate_regime(artifact)

    def test_rate_regime_validator_enforces_rate_rows_contract(self):
        rows = [
            {"date": "2022-03-17", "value": 0.50},
            {"date": "2022-05-05", "value": 1.00},
            {"date": "2022-06-16", "value": 1.75},
        ]
        artifact = build_rate_regime_artifact(
            rows,
            CONFIG,
            name="Rate Regime",
        )
        validate_rate_regime(artifact)

        broken = copy.deepcopy(artifact)
        broken["provenance"]["required_inputs"] = ["other"]
        with self.assertRaisesRegex(
            Exception,
            "required_inputs must be exactly",
        ):
            validate_rate_regime(broken)

        broken = copy.deepcopy(artifact)
        broken["provenance"]["inputs"] = []
        with self.assertRaisesRegex(Exception, "rate_rows provenance input missing"):
            validate_rate_regime(broken)

        broken = copy.deepcopy(artifact)
        broken["provenance"]["inputs"][0]["content_digest"] = (
            "sha256:" + "0" * 64
        )
        with self.assertRaisesRegex(Exception, "digest does not match history"):
            validate_rate_regime(broken)

    def test_rate_regime_name_is_part_of_provenance_parameters(self):
        rows = [
            {"date": "2022-03-17", "value": 0.50},
            {"date": "2022-06-16", "value": 1.75},
        ]
        first = build_rate_regime_artifact(
            rows,
            CONFIG,
            name="Fed Policy Rate Regime",
        )
        second = build_rate_regime_artifact(
            rows,
            CONFIG,
            name="Something Else",
        )

        self.assertEqual(
            first["provenance"]["parameters"],
            {"name": "Fed Policy Rate Regime"},
        )
        self.assertEqual(
            second["provenance"]["parameters"],
            {"name": "Something Else"},
        )
        self.assertNotEqual(first["provenance"], second["provenance"])

        broken = copy.deepcopy(first)
        broken["name"] = "Tampered"
        with self.assertRaisesRegex(Exception, "name parameter mismatch"):
            validate_rate_regime(broken)

    def test_rate_rows_are_fingerprinted_with_upstream_metrics(self):
        upstream = {
            "metric": {"id": "raw_rate"},
            "latest": {
                "as_of": "2022-06-16",
                "fetched_at": "2026-01-01T00:00:00Z",
            },
            "observations": [
                {"date": "2022-06-16", "value": 1.75},
            ],
        }
        first_rows = [
            {"date": "2022-03-17", "value": 0.50},
            {"date": "2022-06-16", "value": 1.75},
        ]
        second_rows = [
            {"date": "2022-03-17", "value": 0.50},
            {"date": "2022-06-16", "value": 2.00},
        ]

        first = build_rate_regime_artifact(
            first_rows,
            CONFIG,
            name="Rate Regime",
            input_metrics=[upstream],
        )
        second = build_rate_regime_artifact(
            second_rows,
            CONFIG,
            name="Rate Regime",
            input_metrics=[upstream],
        )

        self.assertEqual(first["provenance"]["required_inputs"], ["rate_rows"])
        first_inputs = {item["id"]: item for item in first["provenance"]["inputs"]}
        second_inputs = {item["id"]: item for item in second["provenance"]["inputs"]}
        self.assertEqual(
            first_inputs["raw_rate"]["content_digest"],
            second_inputs["raw_rate"]["content_digest"],
        )
        self.assertNotEqual(
            first_inputs["rate_rows"]["content_digest"],
            second_inputs["rate_rows"]["content_digest"],
        )
        self.assertIsNone(first_inputs["rate_rows"]["snapshot_at"])



if __name__ == "__main__":
    unittest.main()
