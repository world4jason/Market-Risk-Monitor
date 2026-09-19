import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline.ma_breadth import (
    MovingAverageBreadthError,
    assert_history_not_truncated,
    audit_rows,
    build_ma_breadth_metrics,
    cross_check_reference,
    parse_ma_breadth_csv,
)
from pipeline.validate import validate_metric


FIXTURE = Path(__file__).parent / "fixtures" / "ma_breadth_sp500.csv"


class MovingAverageBreadthTests(unittest.TestCase):
    def test_parse_and_build_all_horizons(self):
        rows = parse_ma_breadth_csv(FIXTURE.read_text())
        self.assertEqual(rows[0]["market_scope"], "S&P 500")
        self.assertEqual(rows[0]["membership_mode"], "point_in_time")

        metrics = build_ma_breadth_metrics(
            rows,
            datetime(2026, 2, 15, tzinfo=timezone.utc),
        )
        for metric_id in [
            "sp500_above_20dma_pct",
            "sp500_above_50dma_pct",
            "sp500_above_200dma_pct",
        ]:
            self.assertIn(metric_id, metrics)
            self.assertEqual(metrics[metric_id]["source"]["market_scope"], "S&P 500")
            self.assertTrue(metrics[metric_id]["source"]["point_in_time_membership"])
            validate_metric(metrics[metric_id])

    def test_out_of_bounds_rejected(self):
        text = """date,market_scope,provider,above_50dma_pct
2026-01-02,S&P 500,test,101
"""
        with self.assertRaises(MovingAverageBreadthError):
            parse_ma_breadth_csv(text)

    def test_numerator_exceeds_denominator_rejected(self):
        text = """date,market_scope,provider,above_50dma_pct,eligible_50d,above_50d_count
2026-01-02,S&P 500,test,50,500,501
"""
        with self.assertRaises(MovingAverageBreadthError):
            parse_ma_breadth_csv(text)

    def test_count_percentage_mismatch_rejected(self):
        text = """date,market_scope,provider,above_50dma_pct,eligible_50d,above_50d_count
2026-01-02,S&P 500,test,25,500,300
"""
        with self.assertRaises(MovingAverageBreadthError):
            parse_ma_breadth_csv(text)

    def test_non_monotonic_dates_rejected(self):
        text = """date,market_scope,provider,above_50dma_pct
2026-01-05,S&P 500,test,30
2026-01-02,S&P 500,test,25
"""
        with self.assertRaises(MovingAverageBreadthError):
            parse_ma_breadth_csv(text)

    def test_duplicate_dates_rejected(self):
        text = """date,market_scope,provider,above_50dma_pct
2026-01-02,S&P 500,test,30
2026-01-02,S&P 500,test,25
"""
        with self.assertRaises(MovingAverageBreadthError):
            parse_ma_breadth_csv(text)

    def test_wrong_scope_rejected(self):
        text = """date,market_scope,provider,above_50dma_pct
2026-01-02,NYSE,test,25
"""
        with self.assertRaises(MovingAverageBreadthError):
            parse_ma_breadth_csv(text)

    def test_audit_records_survivorship_mode(self):
        rows = parse_ma_breadth_csv(FIXTURE.read_text())
        audit = audit_rows(rows)
        self.assertTrue(audit["point_in_time_membership"])
        self.assertEqual(audit["market_scope"], "S&P 500")
        self.assertGreater(audit["horizons"]["50"]["observations"], 250)

    def test_current_constituent_backfill_is_marked_non_point_in_time(self):
        text = """date,market_scope,provider,above_50dma_pct,membership_mode
2025-01-02,S&P 500,test,50,current_constituents_retroactive
2025-01-03,S&P 500,test,40,current_constituents_retroactive
"""
        rows = parse_ma_breadth_csv(text)
        metric = build_ma_breadth_metrics(rows)["sp500_above_50dma_pct"]
        self.assertFalse(metric["source"]["point_in_time_membership"])

    def test_history_truncation_guard(self):
        rows = parse_ma_breadth_csv(FIXTURE.read_text())
        metrics = build_ma_breadth_metrics(rows)
        previous = metrics["sp500_above_50dma_pct"]
        newer = dict(previous)
        newer["metric"] = dict(previous["metric"])
        newer["coverage"] = dict(previous["coverage"])
        newer["coverage"]["history_start"] = "2025-06-01"
        with self.assertRaises(MovingAverageBreadthError):
            assert_history_not_truncated(previous, newer)

    def test_latest_cross_provider_reference(self):
        import json
        ref = json.loads(
            (Path(__file__).parent / "fixtures" / "ma_breadth_reference_latest.json").read_text()
        )
        imported = parse_ma_breadth_csv(
            """date,market_scope,provider,above_50dma_pct,membership_mode
2026-09-18,S&P 500,Investing-EOD-crosscheck,27.83,provider_point_in_time
"""
        )
        metric = build_ma_breadth_metrics(imported)["sp500_above_50dma_pct"]
        check = cross_check_reference(
            metric["latest"]["value"],
            ref["reference_value"],
            tolerance_pp=ref["tolerance_pp"],
        )
        self.assertTrue(check["within_tolerance"])

    def test_fixed_external_reference_tolerance(self):
        import json
        ref = json.loads(
            (Path(__file__).parent / "fixtures" / "ma_breadth_reference.json").read_text()
        )
        imported = parse_ma_breadth_csv(
            """date,market_scope,provider,above_50dma_pct,membership_mode
2026-09-01,S&P 500,Barchart-reference,45.52,provider_point_in_time
"""
        )
        metric = build_ma_breadth_metrics(imported)["sp500_above_50dma_pct"]
        check = cross_check_reference(
            metric["latest"]["value"],
            ref["reference_value"],
            tolerance_pp=ref["tolerance_pp"],
        )
        self.assertTrue(check["within_tolerance"])
        self.assertAlmostEqual(check["absolute_difference_pp"], 0.0)


if __name__ == "__main__":
    unittest.main()
