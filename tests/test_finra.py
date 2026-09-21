import unittest
from datetime import datetime, timezone
from pathlib import Path

from pipeline.finra import build_finra_metrics, parse_finra_csv
from pipeline.validate import validate_metric


FIXTURE = Path(__file__).parent / "fixtures" / "finra_margin.csv"


class FinraTests(unittest.TestCase):
    def test_parse_finra_csv(self):
        rows = parse_finra_csv(FIXTURE.read_text())
        self.assertEqual(len(rows), 14)
        self.assertEqual(rows[0]["date"], "2025-01-31")
        self.assertEqual(rows[-1]["date"], "2026-02-27")
        self.assertEqual(rows[-1]["margin_debt"], 2300.0)
        self.assertEqual(rows[-1]["total_free_credit"], 265 + 315)

    def test_legacy_combined_free_credit_is_not_mislabeled(self):
        text = """Month,Debit Balances in Customers' Securities Margin Accounts,Free Credit Balances
Dec-09,400,150
Jan-10,420,160
"""
        rows = parse_finra_csv(text)
        self.assertEqual(rows[0]["date"], "2009-12-31")
        self.assertEqual(rows[0]["combined_free_credit"], 150.0)
        self.assertEqual(rows[0]["total_free_credit"], 150.0)
        self.assertIsNone(rows[0]["cash_free_credit"])
        self.assertIsNone(rows[0]["margin_free_credit"])

        metrics = build_finra_metrics(rows, datetime(2010, 2, 20, tzinfo=timezone.utc))
        self.assertEqual(metrics["finra_total_free_credit"]["latest"]["value"], 160.0)
        self.assertAlmostEqual(metrics["margin_debt_to_free_credit"]["latest"]["value"], 420 / 160)

    def test_legacy_single_component_is_reclassified_as_combined(self):
        text = """Month,Debit Balances in Customers' Securities Margin Accounts,Free Credit Balances in Customers' Cash Accounts,Free Credit Balances in Customers' Securities Margin Accounts
Jan-10,420,160,
Feb-10,430,90,80
"""
        rows = parse_finra_csv(text)
        self.assertEqual(rows[0]["combined_free_credit"], 160.0)
        self.assertIsNone(rows[0]["cash_free_credit"])
        self.assertIsNone(rows[0]["margin_free_credit"])
        self.assertEqual(rows[1]["total_free_credit"], 170.0)

    def test_build_raw_and_derived_metrics(self):
        rows = parse_finra_csv(FIXTURE.read_text())
        metrics = build_finra_metrics(rows, datetime(2026, 3, 20, tzinfo=timezone.utc))

        for metric_id in [
            "finra_margin_debt",
            "finra_total_free_credit",
            "finra_cash_free_credit",
            "finra_margin_free_credit",
            "finra_margin_debt_mom_pct",
            "finra_margin_debt_yoy_pct",
            "margin_debt_to_free_credit",
        ]:
            self.assertIn(metric_id, metrics)

        yoy = metrics["finra_margin_debt_yoy_pct"]
        self.assertAlmostEqual(yoy["latest"]["value"], (2300 / 1100 - 1) * 100)
        self.assertEqual(yoy["latest"]["as_of"], "2026-02-27")

        ratio = metrics["margin_debt_to_free_credit"]
        expected = 2300 / (265 + 315)
        self.assertAlmostEqual(ratio["latest"]["value"], expected)

        for metric in metrics.values():
            validate_metric(metric)

    def test_derived_pct_change_uses_contract_observation_statuses(self):
        rows = parse_finra_csv(FIXTURE.read_text())
        metrics = build_finra_metrics(rows, datetime(2026, 3, 20, tzinfo=timezone.utc))
        mom = metrics["finra_margin_debt_mom_pct"]

        # The first month has no prior month to compare against. That is
        # "insufficient_data", not a missing source observation, and it must be
        # expressed in the canonical observation vocabulary rather than the
        # methodology-transform one.
        self.assertIsNone(mom["observations"][0]["value"])
        self.assertEqual(mom["observations"][0]["status"], "insufficient_data")
        self.assertEqual(mom["observations"][1]["status"], "observed")
        self.assertNotIn(
            "ok",
            {obs["status"] for obs in mom["observations"]},
        )


if __name__ == "__main__":
    unittest.main()
