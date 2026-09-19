import unittest

from pipeline.tradermonty_ma_breadth import (
    build_tradermonty_metrics,
    convert_tradermonty_csv,
)
from pipeline.ma_breadth import parse_ma_breadth_csv
from pipeline.validate import validate_metric


FIXTURE = """Date,S&P500_Price,Breadth_Index_Raw,Breadth_Index_200MA,Breadth_Index_8MA,Breadth_200MA_Trend,Bearish_Signal,Is_Peak,Is_Trough,Is_Trough_8MA_Below_04,Breadth_50_Index_Raw,Breadth_50_Index_50MA,Breadth_50_Index_8MA,Breadth_50_MA_Trend,Bearish_Signal_50,Is_Peak_50,Is_Trough_50
2026-09-01,6500,0.7020,0.6810,0.6950,1,False,False,False,False,0.4552,0.5000,0.4800,-1,True,False,False
2026-09-02,6520,0.7100,0.6820,0.6970,1,False,False,False,False,0.4751,0.4980,0.4820,-1,True,False,False
"""


class TraderMontyMABreadthTests(unittest.TestCase):
    def test_convert_public_csv_to_mrm_contract(self):
        converted = convert_tradermonty_csv(FIXTURE)
        rows = parse_ma_breadth_csv(converted)
        self.assertEqual(rows[0]["above_50dma_pct"], 45.52)
        self.assertEqual(rows[0]["above_200dma_pct"], 70.20)
        self.assertEqual(rows[0]["membership_mode"], "current_constituents_retroactive")

    def test_metrics_are_non_point_in_time_and_20dma_missing(self):
        metrics = build_tradermonty_metrics(FIXTURE)
        self.assertNotIn("sp500_above_20dma_pct", metrics)
        self.assertIn("sp500_above_50dma_pct", metrics)
        self.assertIn("sp500_above_200dma_pct", metrics)

        for metric in metrics.values():
            self.assertFalse(metric["source"]["point_in_time_membership"])
            self.assertIn("TraderMonty", metric["source"]["provider"])
            validate_metric(metric)


if __name__ == "__main__":
    unittest.main()
