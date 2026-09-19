import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline.breadth import BreadthError, build_breadth_metrics, parse_breadth_csv
from pipeline.validate import validate_metric


FIXTURE = Path(__file__).parent / "fixtures" / "breadth_nyse.csv"


class BreadthTests(unittest.TestCase):
    def test_parse_scope_and_nonnegative_inputs(self):
        rows = parse_breadth_csv(FIXTURE.read_text())
        self.assertEqual(len(rows), 45)
        self.assertEqual(rows[0]["market_scope"], "NYSE")
        self.assertEqual(rows[0]["provider"], "fixture-authorized")

    def test_negative_input_rejected(self):
        text = """date,market_scope,provider,new_52w_highs
2026-01-02,NYSE,test,-1
"""
        with self.assertRaises(BreadthError):
            parse_breadth_csv(text)

    def test_mixed_scope_rejected(self):
        text = """date,market_scope,provider,new_52w_highs
2026-01-02,NYSE,test,1
2026-01-05,NASDAQ,test,2
"""
        with self.assertRaises(BreadthError):
            parse_breadth_csv(text)

    def test_build_high_low_ad_and_volume_metrics(self):
        rows = parse_breadth_csv(FIXTURE.read_text())
        metrics = build_breadth_metrics(
            rows,
            datetime(2026, 3, 10, tzinfo=timezone.utc),
        )

        expected = [
            "nyse_new_52w_highs",
            "nyse_new_52w_lows",
            "nyse_net_new_52w_highs",
            "nyse_high_low_pct",
            "nyse_advance_decline_diff",
            "nyse_advance_decline_pct",
            "nyse_advance_decline_line",
            "nyse_up_volume",
            "nyse_down_volume",
            "nyse_up_down_volume",
            "mrm_mcclellan_volume_oscillator",
            "mrm_mcclellan_volume_summation",
        ]
        for metric_id in expected:
            self.assertIn(metric_id, metrics)
            self.assertEqual(metrics[metric_id]["source"]["market_scope"], "NYSE")
            validate_metric(metrics[metric_id])

        first = rows[0]
        net = first["new_52w_highs"] - first["new_52w_lows"]
        self.assertEqual(
            metrics["nyse_net_new_52w_highs"]["observations"][0]["value"],
            net,
        )
        self.assertAlmostEqual(
            metrics["nyse_high_low_pct"]["observations"][0]["value"],
            100 * net / first["total_issues"],
        )

    def test_mcclellan_warmup_and_hand_computed_recurrence(self):
        rows = parse_breadth_csv(FIXTURE.read_text())
        metrics = build_breadth_metrics(rows)
        osc = metrics["mrm_mcclellan_volume_oscillator"]["observations"]
        summ = metrics["mrm_mcclellan_volume_summation"]["observations"]

        self.assertTrue(all(o["value"] is None for o in osc[:38]))
        self.assertIsNotNone(osc[38]["value"])
        self.assertIsNotNone(summ[38]["value"])

        values = [r["up_volume"] - r["down_volume"] for r in rows]
        t10 = values[0]
        t05 = values[0]
        expected_osc = None
        for i, value in enumerate(values):
            if i > 0:
                t10 = 0.10 * value + 0.90 * t10
                t05 = 0.05 * value + 0.95 * t05
            if i == 38:
                expected_osc = t10 - t05
                break

        self.assertAlmostEqual(osc[38]["value"], expected_osc)
        self.assertAlmostEqual(summ[38]["value"], 1000 + expected_osc)

    def test_missing_volume_resets_warmup(self):
        rows = parse_breadth_csv(FIXTURE.read_text())
        rows[40]["up_volume"] = None
        metrics = build_breadth_metrics(rows)
        osc = metrics["mrm_mcclellan_volume_oscillator"]["observations"]
        self.assertIsNone(osc[40]["value"])
        self.assertIsNone(osc[41]["value"])


if __name__ == "__main__":
    unittest.main()
