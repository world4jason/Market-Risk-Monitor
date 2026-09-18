import unittest
from datetime import datetime, timezone

from pipeline.cboe import build_vix_metric, parse_vix_csv
from pipeline.validate import validate_metric


class CboeTests(unittest.TestCase):
    def test_vix_parser_and_contract(self):
        text = """DATE,OPEN,HIGH,LOW,CLOSE
01/02/1990,17.24,17.24,17.24,17.24
01/03/1990,18.19,18.19,18.19,18.19
01/04/1990,19.22,19.22,19.22,19.22
"""
        obs = parse_vix_csv(text)
        self.assertEqual(obs[0]["date"], "1990-01-02")
        self.assertEqual(obs[-1]["value"], 19.22)

        metric = build_vix_metric(obs, datetime(1990, 1, 5, tzinfo=timezone.utc))
        self.assertEqual(metric["source"]["provider"], "Cboe Global Markets")
        self.assertEqual(metric["latest"]["as_of"], "1990-01-04")
        self.assertEqual(metric["freshness"]["state"], "fresh")
        validate_metric(metric)


if __name__ == "__main__":
    unittest.main()
