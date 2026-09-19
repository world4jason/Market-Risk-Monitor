import unittest
from datetime import date, timedelta

from pipeline.ma_breadth_self_compute import (
    PointInTimeBreadthError,
    above_ma_flags,
    compute_point_in_time_breadth,
    parse_historical_membership_csv,
    parse_price_csv,
    to_import_csv,
)
from pipeline.ma_breadth import build_ma_breadth_metrics, parse_ma_breadth_csv


def daily_dates(start: str, count: int):
    d = date.fromisoformat(start)
    return [(d + timedelta(days=i)).isoformat() for i in range(count)]


class PointInTimeSelfComputeTests(unittest.TestCase):
    def test_membership_parser(self):
        text = """date,tickers
2025-01-01,"A,B"
2025-01-02,"A,C"
"""
        rows = parse_historical_membership_csv(text)
        self.assertEqual(rows[0]["tickers"], ["A", "B"])
        self.assertEqual(rows[1]["tickers"], ["A", "C"])

    def test_adjusted_close_required_when_requested(self):
        text = """Date,Close
2025-01-01,100
"""
        with self.assertRaises(PointInTimeBreadthError):
            parse_price_csv(text, price_adjustment="adjusted_close")

    def test_above_ma_flags_include_current_observation(self):
        rows = [
            {"date": d, "price": float(i + 1)}
            for i, d in enumerate(daily_dates("2025-01-01", 20))
        ]
        flags = above_ma_flags(rows, horizons=(20,))
        self.assertNotIn("2025-01-19", flags[20])
        self.assertTrue(flags[20]["2025-01-20"])

    def test_point_in_time_membership_switch_changes_denominator(self):
        dates = daily_dates("2025-01-01", 205)
        membership = []
        for i, d in enumerate(dates):
            tickers = ["A", "B"] if i < 202 else ["A", "C"]
            membership.append({"date": d, "tickers": tickers})

        prices = {
            "A": [{"date": d, "price": 100 + i} for i, d in enumerate(dates)],
            "B": [{"date": d, "price": 300 - i * 0.5} for i, d in enumerate(dates)],
            "C": [{"date": d, "price": 50 + i * 0.8} for i, d in enumerate(dates)],
        }

        rows = compute_point_in_time_breadth(
            membership,
            prices,
            membership_snapshot="fixture-pit",
            price_adjustment="adjusted_close",
        )

        before = rows[201]
        after = rows[203]

        self.assertEqual(before["eligible_200d"], 2)
        self.assertEqual(after["eligible_200d"], 2)
        # B is trending down; C is trending up. The membership switch must
        # alter the actual numerator rather than keep today's/current basket.
        self.assertEqual(before["above_200d_count"], 1)
        self.assertEqual(after["above_200d_count"], 2)

        canonical = parse_ma_breadth_csv(to_import_csv(rows))
        metrics = build_ma_breadth_metrics(canonical)
        self.assertTrue(
            metrics["sp500_above_50dma_pct"]["source"]["point_in_time_membership"]
        )

    def test_missing_price_is_counted_not_assumed_below(self):
        dates = daily_dates("2025-01-01", 60)
        membership = [{"date": d, "tickers": ["A", "MISSING"]} for d in dates]
        prices = {
            "A": [{"date": d, "price": 100 + i} for i, d in enumerate(dates)]
        }
        rows = compute_point_in_time_breadth(
            membership,
            prices,
            membership_snapshot="fixture-pit",
            price_adjustment="adjusted_close",
        )
        last = rows[-1]
        self.assertEqual(last["eligible_50d"], 1)
        self.assertEqual(last["missing_50d"], 1)
        self.assertEqual(last["above_50d_count"], 1)
        self.assertEqual(last["above_50dma_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
