import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline.ma_breadth import (
    MovingAverageBreadthError,
    audit_rows,
    build_ma_breadth_metrics,
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


if __name__ == "__main__":
    unittest.main()
