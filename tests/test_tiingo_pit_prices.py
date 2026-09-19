import unittest

from scripts.fetch_tiingo_pit_prices import normalize_csv, ticker_candidates


class TiingoPITPriceTests(unittest.TestCase):
    def test_normalize_csv_preserves_close_and_adj_close(self):
        raw = """date,close,adjClose
2026-01-02T00:00:00.000Z,100.0,99.5
2026-01-05T00:00:00.000Z,101.0,100.5
"""
        out = normalize_csv(raw)
        self.assertIn("Date,Close,Adj Close", out)
        self.assertIn("2026-01-02,100.0,99.5", out)
        self.assertIn("2026-01-05,101.0,100.5", out)

    def test_ticker_candidates_are_auditable_variants(self):
        self.assertEqual(ticker_candidates("BRK.B"), ["BRK.B", "BRK-B"])
        self.assertEqual(ticker_candidates("BRK-B"), ["BRK-B", "BRK.B"])


if __name__ == "__main__":
    unittest.main()
