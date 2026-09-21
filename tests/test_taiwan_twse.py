import json
import unittest
from datetime import datetime, timezone

from pipeline.taiwan_twse import (
    build_taiex_metrics,
    build_taiwan_breadth_metrics,
    merge_taiex_rows,
    parse_fmtqik_json,
    parse_mi_index_market_summary_json,
    parse_taiex_month_json,
    parse_taiwan_breadth_csv,
    roc_date_to_iso,
)
from pipeline.validate import validate_metric


class TaiwanTwseTests(unittest.TestCase):
    def test_roc_date_conversion(self):
        self.assertEqual(roc_date_to_iso("1150901"), "2026-09-01")
        self.assertEqual(roc_date_to_iso("111/07/01"), "2022-07-01")
        self.assertEqual(roc_date_to_iso("2026-09-18"), "2026-09-18")

    def test_parse_fmtqik_openapi_shape(self):
        text = json.dumps(
            [
                {
                    "Date": "1150901",
                    "TradeVolume": "13000849196",
                    "TradeValue": "1187571567117",
                    "Transaction": "5301801",
                    "TAIEX": "46948.72",
                    "Change": "820.25",
                },
                {
                    "Date": "1150902",
                    "TradeVolume": "10824863832",
                    "TradeValue": "976499979054",
                    "Transaction": "5093402",
                    "TAIEX": "46164.72",
                    "Change": "-784.00",
                },
            ],
            ensure_ascii=False,
        )
        rows = parse_fmtqik_json(text)
        self.assertEqual(rows[0]["date"], "2026-09-01")
        self.assertEqual(rows[0]["close"], 46948.72)
        self.assertEqual(rows[0]["trade_volume"], 13000849196)

        metrics = build_taiex_metrics(
            rows,
            datetime(2026, 9, 3, tzinfo=timezone.utc),
        )
        self.assertIn("tw_taiex", metrics)
        self.assertIn("tw_market_trade_value", metrics)
        for metric in metrics.values():
            validate_metric(metric)

    def test_parse_taiex_month_and_merge_ohlc(self):
        month = json.dumps(
            {
                "stat": "OK",
                "data": [
                    [
                        "115/09/01",
                        "46,177.11",
                        "46,948.72",
                        "46,081.11",
                        "46,948.72",
                    ],
                    [
                        "115/09/02",
                        "46,901.32",
                        "46,946.60",
                        "46,164.72",
                        "46,164.72",
                    ],
                ],
            },
            ensure_ascii=False,
        )
        fmt = json.dumps(
            [
                {
                    "Date": "1150901",
                    "TradeVolume": "1000",
                    "TradeValue": "2000",
                    "Transaction": "30",
                    "TAIEX": "46948.72",
                    "Change": "820.25",
                }
            ]
        )
        merged = merge_taiex_rows(
            parse_taiex_month_json(month),
            parse_fmtqik_json(fmt),
        )
        self.assertEqual(merged[0]["open"], 46177.11)
        self.assertEqual(merged[0]["trade_value"], 2000.0)

    def test_parse_mi_index_uses_stocks_not_overall_market(self):
        payload = {
            "stat": "OK",
            "date": "20260918",
            "data8": [
                ["Up (Limit Up)", "9,531(119)", "748(32)"],
                ["Down (Limit Down)", "4,331(55)", "251(0)"],
                ["Unchanged", "968", "78"],
                ["Unmatched", "16,946", "1"],
                ["N/A", "3,432", "0"],
            ],
        }
        row = parse_mi_index_market_summary_json(
            json.dumps(payload, ensure_ascii=False)
        )
        self.assertEqual(row["advancing"], 748)
        self.assertEqual(row["declining"], 251)
        self.assertEqual(row["limit_up"], 32)
        self.assertEqual(row["unmatched"], 1)

    def test_2022_weak_breadth_fixture_and_current_positive_fixture(self):
        text = """date,advancing,declining,unchanged,limit_up,limit_down,unmatched
2022-07-01,58,873,22,1,15,12
2026-09-18,748,251,78,32,0,1
"""
        rows = parse_taiwan_breadth_csv(text)
        metrics = build_taiwan_breadth_metrics(
            rows,
            datetime(2026, 9, 19, tzinfo=timezone.utc),
        )
        ad = metrics["tw_advance_decline_diff"]["observations"]
        pct = metrics["tw_advance_decline_pct"]["observations"]
        self.assertEqual(ad[0]["value"], -815)
        self.assertEqual(ad[1]["value"], 497)
        self.assertLess(pct[0]["value"], -80)
        self.assertGreater(pct[1]["value"], 40)
        for metric in metrics.values():
            validate_metric(metric)

    def test_non_monotonic_breadth_csv_rejected(self):
        text = """date,advancing,declining
2026-09-18,748,251
2026-09-17,600,400
"""
        with self.assertRaises(ValueError):
            parse_taiwan_breadth_csv(text)


if __name__ == "__main__":
    unittest.main()
