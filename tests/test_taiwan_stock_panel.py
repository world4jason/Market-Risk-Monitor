import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.taiwan_stock_panel import (
    append_snapshot,
    build_daily_panel_rows,
)


class TaiwanStockPanelTests(unittest.TestCase):
    def test_company_master_filters_non_company_securities(self):
        companies = [
            {"公司代號": "2330", "公司簡稱": "台積電"},
            {"公司代號": "2317", "公司簡稱": "鴻海"},
        ]
        stocks = [
            {
                "Date": "1150921",
                "Code": "2330",
                "HighestPrice": "1,500.00",
                "LowestPrice": "1,470.00",
                "ClosingPrice": "1,490.00",
            },
            {
                "Date": "1150921",
                "Code": "2317",
                "HighestPrice": "230.00",
                "LowestPrice": "225.00",
                "ClosingPrice": "228.00",
            },
            {
                "Date": "1150921",
                "Code": "0050",
                "HighestPrice": "70.00",
                "LowestPrice": "69.00",
                "ClosingPrice": "69.50",
            },
        ]
        rows = build_daily_panel_rows(stocks, companies)
        self.assertEqual([row["symbol"] for row in rows], ["2317", "2330"])
        self.assertEqual(rows[0]["date"], "2026-09-21")
        self.assertEqual(
            rows[0]["membership_mode"],
            "official_daily_snapshot",
        )

    def test_recollect_same_date_replaces_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "panel.csv"
            rows = [
                {
                    "date": "2026-09-21",
                    "symbol": "2330",
                    "high": 1500,
                    "low": 1470,
                    "close": 1490,
                    "market_scope": "TWSE listed common stocks",
                    "provider": "Taiwan Stock Exchange (TWSE) OpenAPI",
                    "membership_mode": "official_daily_snapshot",
                    "price_adjustment": "unadjusted_close",
                }
            ]
            append_snapshot(path, rows)
            rows[0]["close"] = 1495
            append_snapshot(path, rows)
            with path.open(encoding="utf-8") as handle:
                parsed = list(csv.DictReader(handle))
            self.assertEqual(len(parsed), 1)
            self.assertEqual(float(parsed[0]["close"]), 1495)


if __name__ == "__main__":
    unittest.main()
