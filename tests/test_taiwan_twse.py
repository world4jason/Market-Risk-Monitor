import json
import unittest
from datetime import datetime, timezone

from pipeline.taiwan_twse import (
    TaiwanTwseError,
    build_taiex_metrics,
    build_taiwan_breadth_metrics,
    merge_metric_history,
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

    def test_parse_mi_index_current_tables_shape(self):
        # TWSE now returns a `tables` list instead of flat data1..data9 keys.
        # The breadth table is NOT at a stable index -- here it is tables[1]
        # and tables[2] is empty, mirroring the live 2026-09-18 response where
        # it sat at index 7 with index 8 empty. Matching on the field
        # signature is what keeps this from silently reading the wrong table.
        payload = {
            "stat": "OK",
            "date": "20260918",
            "type": "MS",
            "tables": [
                {
                    "title": "115年09月18日 大盤統計資訊",
                    "fields": ["成交統計", "成交金額(元)", "成交股數(股)", "成交筆數"],
                    "data": [
                        ["1.一般股票", "1,060,401,174,750", "5,860,392,347", "3,610,593"],
                        ["4.ETF", "72,666,060,556", "3,152,113,663", "950,024"],
                    ],
                },
                {
                    "title": "漲跌證券數合計",
                    "fields": ["類型", "整體市場", "股票"],
                    "data": [
                        ["上漲(漲停)", "9,531(119)", "748(32)"],
                        ["下跌(跌停)", "4,331(55)", "251(0)"],
                        ["持平", "968", "78"],
                        ["未成交", "16,946", "1"],
                        ["無比價", "3,432", "0"],
                    ],
                },
                {},
            ],
        }
        row = parse_mi_index_market_summary_json(
            json.dumps(payload, ensure_ascii=False)
        )
        self.assertEqual(row["date"], "2026-09-18")
        # Stocks column, not the 9,531 / 4,331 overall-market column.
        self.assertEqual(row["advancing"], 748)
        self.assertEqual(row["declining"], 251)
        self.assertEqual(row["limit_up"], 32)
        self.assertEqual(row["limit_down"], 0)
        self.assertEqual(row["unchanged"], 78)
        self.assertEqual(row["unmatched"], 1)

    def test_mi_index_missing_breadth_table_is_rejected(self):
        payload = {
            "stat": "OK",
            "date": "20260918",
            "type": "MS",
            "tables": [
                {
                    "title": "115年09月18日 大盤統計資訊",
                    "fields": ["成交統計", "成交金額(元)"],
                    "data": [["1.一般股票", "1,060,401,174,750"]],
                },
                {},
            ],
        }
        with self.assertRaises(TaiwanTwseError):
            parse_mi_index_market_summary_json(
                json.dumps(payload, ensure_ascii=False)
            )

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

    def test_metric_history_merge_preserves_start(self):
        old_rows = [
            {"date": "2020-01-02", "close": 12000.0},
            {"date": "2020-01-03", "close": 12100.0},
        ]
        new_rows = [
            {"date": "2026-09-18", "close": 47180.75},
        ]
        old_metric = build_taiex_metrics(
            old_rows,
            datetime(2020, 1, 4, tzinfo=timezone.utc),
        )["tw_taiex"]
        new_metric = build_taiex_metrics(
            new_rows,
            datetime(2026, 9, 19, tzinfo=timezone.utc),
        )["tw_taiex"]
        merged = merge_metric_history(old_metric, new_metric)
        self.assertEqual(merged["coverage"]["history_start"], "2020-01-02")
        self.assertEqual(merged["coverage"]["history_end"], "2026-09-18")
        self.assertEqual(merged["latest"]["value"], 47180.75)
        self.assertEqual(len(merged["observations"]), 3)
        validate_metric(merged)


if __name__ == "__main__":
    unittest.main()
