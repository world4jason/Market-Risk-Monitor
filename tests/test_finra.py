import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline.finra import build_finra_metrics, parse_finra_csv
from pipeline.validate import validate_metric


FIXTURE = Path(__file__).parent / "fixtures" / "finra_margin.csv"


class FinraTests(unittest.TestCase):
    def test_parse_finra_csv(self):
        rows=parse_finra_csv(FIXTURE.read_text())
        self.assertEqual(len(rows),14)
        self.assertEqual(rows[0]["date"],"2025-01-31")
        self.assertEqual(rows[-1]["date"],"2026-02-27")
        self.assertEqual(rows[-1]["margin_debt"],2300.0)

    def test_build_raw_and_derived_metrics(self):
        rows=parse_finra_csv(FIXTURE.read_text())
        metrics=build_finra_metrics(rows,datetime(2026,3,20,tzinfo=timezone.utc))
        self.assertIn("finra_margin_debt",metrics)
        self.assertIn("finra_margin_debt_mom_pct",metrics)
        self.assertIn("finra_margin_debt_yoy_pct",metrics)
        self.assertIn("margin_debt_to_free_credit",metrics)

        yoy=metrics["finra_margin_debt_yoy_pct"]
        self.assertAlmostEqual(yoy["latest"]["value"],(2300/1100-1)*100)
        self.assertEqual(yoy["latest"]["as_of"],"2026-02-27")

        ratio=metrics["margin_debt_to_free_credit"]
        expected=2300/(265+315)
        self.assertAlmostEqual(ratio["latest"]["value"],expected)

        for metric in metrics.values():
            validate_metric(metric)


if __name__=="__main__":
    unittest.main()
