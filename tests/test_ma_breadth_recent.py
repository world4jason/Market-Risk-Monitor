import csv
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from pipeline.ma_breadth_pit import (
    MembershipSnapshot,
    compute_from_price_files,
)
from pipeline.ma_breadth_recent import tickers_for_window


class RecentMovingAverageBreadthTests(unittest.TestCase):
    def test_recent_universe_includes_pre_window_members_and_changes(self):
        snapshots = [
            MembershipSnapshot("2024-01-01", frozenset({"AAA", "BBB"})),
            MembershipSnapshot("2025-03-01", frozenset({"AAA", "CCC"})),
            MembershipSnapshot("2025-06-01", frozenset({"DDD", "CCC"})),
        ]
        tickers = tickers_for_window(
            snapshots,
            "2025-01-01",
            "2025-12-31",
        )
        self.assertEqual(tickers, ["AAA", "BBB", "CCC", "DDD"])

    def test_recent_price_file_wins_overlap_without_erasing_history(self):
        start = date(2024, 1, 1)
        dates = [start + timedelta(days=i) for i in range(30)]

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            membership = root / "membership.csv"
            historical = root / "historical.csv"
            recent = root / "recent.csv"
            output = root / "breadth.csv"
            db = root / "work.sqlite3"

            membership.write_text(
                f'date,tickers\n{dates[0].isoformat()},"AAA"\n',
                encoding="utf-8",
            )

            with historical.open("w", encoding="utf-8", newline="") as handle:
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

            with recent.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["date", "symbol", "adjusted_close"],
                )
                writer.writeheader()
                for i, obs_date in enumerate(dates[-5:]):
                    writer.writerow(
                        {
                            "date": obs_date.isoformat(),
                            "symbol": "AAA",
                            "adjusted_close": 1000 + i,
                        }
                    )

            report = compute_from_price_files(
                membership,
                [historical, recent],
                output,
                provider="historical + recent fixture",
                min_coverage=1.0,
                work_db=db,
                source_labels=["historical", "recent"],
            )

            self.assertEqual(len(report["price_sources"]), 2)
            self.assertEqual(
                report["price_conflict_precedence"],
                "files are ingested in listed order; later file wins for identical symbol/date",
            )

            conn = sqlite3.connect(db)
            oldest = conn.execute(
                "SELECT adjusted_close FROM prices WHERE symbol='AAA' AND date=?",
                (dates[0].isoformat(),),
            ).fetchone()[0]
            overlap = conn.execute(
                "SELECT adjusted_close FROM prices WHERE symbol='AAA' AND date=?",
                (dates[-1].isoformat(),),
            ).fetchone()[0]
            conn.close()

            self.assertEqual(oldest, 100)
            self.assertEqual(overlap, 1004)
            self.assertGreater(report["output_rows"], 0)


if __name__ == "__main__":
    unittest.main()
