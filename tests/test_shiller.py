import unittest
from datetime import datetime, timezone

from pipeline.shiller import build_shiller_metrics, parse_shiller_rows
from pipeline.validate import validate_metric


def make_rows(months=122):
    rows = [["header"]]
    for i in range(months):
        year = 1871 + i // 12
        month = i % 12 + 1
        # Date is deliberately ambiguous for October: 1871.1 can mean Jan or Oct
        date_cell = float(f"{year}.{month:02d}")
        date_fraction = year + (month - 0.5) / 12
        row = [None] * 13
        row[0] = date_cell
        row[1] = 100 + i
        row[5] = date_fraction
        row[7] = 110 + i
        row[9] = 120 + i
        row[12] = 10 + i / 10
        rows.append(row)
    return rows


class ShillerTests(unittest.TestCase):
    def test_date_fraction_drives_month_sequence(self):
        parsed = parse_shiller_rows(make_rows())
        # final partial/revisable month is intentionally dropped
        self.assertEqual(len(parsed), 121)
        self.assertEqual(parsed[0]["date"], "1871-01-01")
        self.assertEqual(parsed[9]["date"], "1871-10-01")
        self.assertEqual(parsed[-1]["date"], "1881-01-01")

    def test_build_shiller_metrics(self):
        rows = parse_shiller_rows(make_rows())
        metrics = build_shiller_metrics(rows, datetime(1881, 2, 20, tzinfo=timezone.utc))
        self.assertIn("shiller_price", metrics)
        self.assertIn("shiller_cape", metrics)
        self.assertIn("shiller_real_tr_price", metrics)

        for metric in metrics.values():
            self.assertEqual(metric["coverage"]["history_start"], "1871-01-01")
            self.assertEqual(metric["latest"]["as_of"], "1881-01-01")
            validate_metric(metric)


if __name__ == "__main__":
    unittest.main()
