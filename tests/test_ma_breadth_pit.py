import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from pipeline.ma_breadth_pit import (
    MembershipSnapshot,
    compute_from_files,
    membership_for_date,
    normalize_ticker,
    parse_membership_csv,
)


def day_series(start: date, count: int):
    return [start + timedelta(days=i) for i in range(count)]


class PointInTimeMovingAverageBreadthTests(unittest.TestCase):
    def test_ticker_normalization(self):
        self.assertEqual(normalize_ticker("BRK.B"), "BRK-B")
        self.assertEqual(normalize_ticker(" bf.b "), "BF-B")

    def test_membership_uses_latest_snapshot_on_or_before_date(self):
        snapshots = parse_membership_csv(
            """date,tickers
2020-01-01,"AAA,BBB"
2020-04-10,"AAA,CCC"
"""
        )
        self.assertEqual(
            membership_for_date(snapshots, "2020-03-01").tickers,
            frozenset({"AAA", "BBB"}),
        )
        self.assertEqual(
            membership_for_date(snapshots, "2020-04-10").tickers,
            frozenset({"AAA", "CCC"}),
        )
        self.assertIsNone(membership_for_date(snapshots, "2019-12-31"))

    def test_membership_parser_rejects_non_monotonic_snapshots(self):
        with self.assertRaises(ValueError):
            parse_membership_csv(
                """date,tickers
2020-04-10,"AAA,CCC"
2020-01-01,"AAA,BBB"
"""
            )

    def test_end_to_end_pit_sma_and_membership_change(self):
        start = date(2020, 1, 1)
        dates = day_series(start, 230)
        switch_date = dates[100]

        membership = (
            "date,tickers\n"
            f'{dates[0].isoformat()},"AAA,BBB"\n'
            f'{switch_date.isoformat()},"AAA,CCC"\n'
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            membership_path = root / "membership.csv"
            price_path = root / "prices.csv"
            output_path = root / "breadth.csv"

            membership_path.write_text(membership, encoding="utf-8")

            with price_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["date", "symbol", "adjusted_close"],
                )
                writer.writeheader()

                # Deliberately write symbol-by-symbol rather than date-sorted to
                # prove the SQLite ORDER BY path is deterministic.
                for symbol in ["AAA", "BBB", "CCC"]:
                    for i, obs_date in enumerate(dates):
                        if symbol == "AAA":
                            price = 100.0 + i
                        elif symbol == "BBB":
                            price = 500.0 - i
                        else:
                            price = 50.0 + 2 * i
                        writer.writerow(
                            {
                                "date": obs_date.isoformat(),
                                "symbol": symbol,
                                "adjusted_close": price,
                            }
                        )

            report = compute_from_files(
                membership_path,
                price_path,
                output_path,
                provider="fixture PIT + delisted-inclusive prices",
                min_coverage=1.0,
            )
            self.assertEqual(report["membership_snapshots"], 2)
            self.assertGreater(report["output_rows"], 0)

            rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
            by_date = {row["date"]: row for row in rows}

            # Before the membership switch: AAA rises (above SMA), BBB falls
            # (below SMA) -> 50% participation after the horizon has matured.
            before = dates[80].isoformat()
            self.assertAlmostEqual(float(by_date[before]["above_20dma_pct"]), 50.0)
            self.assertAlmostEqual(float(by_date[before]["above_50dma_pct"]), 50.0)
            self.assertEqual(by_date[before]["membership_snapshot"], dates[0].isoformat())

            # Long after the switch: AAA and CCC both rise -> 100% participation.
            after = dates[220].isoformat()
            self.assertAlmostEqual(float(by_date[after]["above_20dma_pct"]), 100.0)
            self.assertAlmostEqual(float(by_date[after]["above_50dma_pct"]), 100.0)
            self.assertAlmostEqual(float(by_date[after]["above_200dma_pct"]), 100.0)
            self.assertEqual(by_date[after]["membership_snapshot"], switch_date.isoformat())
            self.assertEqual(int(by_date[after]["missing_200d"]), 0)

    def test_missing_member_price_is_explicit_and_not_counted_as_below_ma(self):
        start = date(2021, 1, 1)
        dates = day_series(start, 60)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            membership_path = root / "membership.csv"
            price_path = root / "prices.csv"
            output_path = root / "breadth.csv"

            membership_path.write_text(
                f'date,tickers\n{dates[0].isoformat()},"AAA,BBB"\n',
                encoding="utf-8",
            )

            with price_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["date", "symbol", "adjusted_close"],
                )
                writer.writeheader()
                for i, obs_date in enumerate(dates):
                    writer.writerow(
                        {
                            "date": obs_date.isoformat(),
                            "symbol": "AAA",
                            "adjusted_close": 100 + i,
                        }
                    )
                # BBB never has price history.

            report = compute_from_files(
                membership_path,
                price_path,
                output_path,
                provider="fixture",
                min_coverage=0.5,
            )
            self.assertGreater(report["output_rows"], 0)
            rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
            latest = rows[-1]
            self.assertEqual(int(latest["eligible_20d"]), 1)
            self.assertEqual(int(latest["missing_20d"]), 1)
            # AAA is above its SMA, so eligible-only breadth is 100%, not 50%.
            self.assertAlmostEqual(float(latest["above_20dma_pct"]), 100.0)


if __name__ == "__main__":
    unittest.main()
