import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from pipeline.taiwan_trend_breadth import (
    MARKET_SCOPE,
    TaiwanTrendBreadthError,
    compute_from_panel,
)
from pipeline.validate import validate_metric


class TaiwanTrendBreadthTests(unittest.TestCase):
    def _write_panel(self, path: Path, *, mode="point_in_time"):
        start = date(2020, 1, 1)
        dates = [start + timedelta(days=i) for i in range(300)]
        fields = [
            "date",
            "symbol",
            "high",
            "low",
            "close",
            "market_scope",
            "provider",
            "membership_mode",
            "price_adjustment",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for i, obs_date in enumerate(dates):
                members = ["AAA", "BBB"]
                if i >= 250:
                    members.append("CCC")
                for symbol in members:
                    if symbol == "AAA":
                        close = 100 + i
                    elif symbol == "BBB":
                        close = 500 - i
                    else:
                        close = 50 + (i - 250)
                    writer.writerow(
                        {
                            "date": obs_date.isoformat(),
                            "symbol": symbol,
                            "high": close + 1,
                            "low": close - 1,
                            "close": close,
                            "market_scope": MARKET_SCOPE,
                            "provider": "fixture official panel",
                            "membership_mode": mode,
                            "price_adjustment": "unadjusted_close",
                        }
                    )
        return dates

    def test_point_in_time_ma_and_high_low_breadth(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            panel = root / "panel.csv"
            output = root / "out"
            dates = self._write_panel(panel)
            report = compute_from_panel(panel, output)
            self.assertTrue(report["daily_rows"] >= 252)

            m50 = json.loads(
                (output / "tw_above_50dma_pct.json").read_text()
            )
            m200 = json.loads(
                (output / "tw_above_200dma_pct.json").read_text()
            )
            highs = json.loads(
                (output / "tw_new_52w_highs.json").read_text()
            )
            lows = json.loads(
                (output / "tw_new_52w_lows.json").read_text()
            )
            hl = json.loads(
                (output / "tw_high_low_pct.json").read_text()
            )
            for metric in (m50, m200, highs, lows, hl):
                validate_metric(metric)
                self.assertTrue(
                    metric["source"]["point_in_time_membership"]
                )

            by_date_50 = {
                o["date"]: o["value"] for o in m50["observations"]
            }
            by_date_200 = {
                o["date"]: o["value"] for o in m200["observations"]
            }
            mature = dates[260].isoformat()
            self.assertAlmostEqual(by_date_50[mature], 50.0)
            self.assertAlmostEqual(by_date_200[mature], 50.0)

            high_by_date = {
                o["date"]: o["value"] for o in highs["observations"]
            }
            low_by_date = {
                o["date"]: o["value"] for o in lows["observations"]
            }
            hl_by_date = {
                o["date"]: o["value"] for o in hl["observations"]
            }
            self.assertEqual(high_by_date[mature], 1)
            self.assertEqual(low_by_date[mature], 1)
            self.assertAlmostEqual(hl_by_date[mature], 0.0)

            audit = json.loads(
                (output / "taiwan-trend-breadth-audit.json").read_text()
            )
            day = next(
                x for x in audit["observations"]
                if x["date"] == mature
            )
            self.assertEqual(day["total_members"], 3)
            self.assertEqual(day["eligible_200d"], 2)
            self.assertEqual(day["missing_200d"], 1)

    def test_current_constituent_history_is_marked_non_pit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            panel = root / "panel.csv"
            output = root / "out"
            self._write_panel(
                panel,
                mode="current_constituents_retroactive",
            )
            compute_from_panel(panel, output)
            metric = json.loads(
                (output / "tw_above_50dma_pct.json").read_text()
            )
            self.assertFalse(
                metric["source"]["point_in_time_membership"]
            )

    def test_wrong_market_scope_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            panel = Path(temp) / "bad.csv"
            panel.write_text(
                "date,symbol,high,low,close,market_scope,provider,membership_mode,price_adjustment\n"
                "2026-01-01,2330,100,90,95,TWSE all securities,test,point_in_time,unadjusted_close\n",
                encoding="utf-8",
            )
            with self.assertRaises(TaiwanTrendBreadthError):
                compute_from_panel(panel, Path(temp) / "out")


if __name__ == "__main__":
    unittest.main()
