import json
import unittest

from pipeline.methodology import point_in_time_percentiles
from pipeline.taiwan_macro import (
    build_macro_metrics,
    build_macro_regime,
    monitoring_light,
    parse_taiwan_macro_csv,
)
from pipeline.validate import validate_metric


CONFIG = {
    "ndc_monitoring_bands": [
        {"min": 38, "max": 45, "label": "red"},
        {"min": 32, "max": 37, "label": "yellow-red"},
        {"min": 23, "max": 31, "label": "green"},
        {"min": 17, "max": 22, "label": "yellow-blue"},
        {"min": 9, "max": 16, "label": "blue"},
    ],
    "mrm_regime": {
        "min_known_components": 2,
        "momentum_periods": 3,
        "components": {
            "tw_manufacturing_pmi": {
                "type": "level",
                "threshold": 50,
                "higher_is_positive": True,
            },
            "tw_ndc_leading_index": {
                "type": "delta",
                "periods": 3,
                "threshold": 0,
                "higher_is_positive": True,
            },
            "tw_ndc_coincident_index": {
                "type": "delta",
                "periods": 3,
                "threshold": 0,
                "higher_is_positive": True,
            },
            "tw_manufacturing_production": {
                "type": "return",
                "periods": 3,
                "threshold": 0,
                "higher_is_positive": True,
            },
        },
        "labels": {
            "positive_rising": "expansion",
            "positive_falling": "deceleration",
            "negative_rising": "recovery",
            "negative_falling": "contraction",
        },
    },
}


def csv_fixture():
    header = "date,provider,series_id,value,unit,release_date,source_url"
    rows = [header]
    months = [
        ("2026-01-01", "2026-03-09"),
        ("2026-02-01", "2026-03-30"),
        ("2026-03-01", "2026-04-27"),
        ("2026-04-01", "2026-05-28"),
        ("2026-05-01", "2026-06-26"),
        ("2026-06-01", "2026-07-27"),
        ("2026-07-01", "2026-08-27"),
    ]
    pmi = [57.2, 58.5, 55.4, 60.3, 61.4, 60.7, 61.5]
    leading = [101, 100.5, 100, 101.5, 102, 103, 104]
    coincident = [100, 100.2, 100.4, 101, 102, 103, 104]
    production = [100, 99, 98, 101, 103, 105, 108]
    score = [39, 40, 39, 39, 39, 41, 41]

    for i, (obs, release) in enumerate(months):
        rows.extend(
            [
                f"{obs},CIER,tw_manufacturing_pmi,{pmi[i]},index,{release},https://www.cier.edu.tw/pmi-trend/",
                f"{obs},NDC,tw_ndc_leading_index,{leading[i]},index,{release},https://www.ndc.gov.tw/en/",
                f"{obs},NDC,tw_ndc_coincident_index,{coincident[i]},index,{release},https://www.ndc.gov.tw/en/",
                f"{obs},MOEA,tw_manufacturing_production,{production[i]},index,{release},https://www.moea.gov.tw/",
                f"{obs},NDC,tw_ndc_monitoring_score,{score[i]},score,{release},https://www.ndc.gov.tw/en/",
            ]
        )
    return "\n".join(rows) + "\n"


class TaiwanMacroTests(unittest.TestCase):
    def test_monitoring_light_official_bands(self):
        self.assertEqual(monitoring_light(41, CONFIG), "red")
        self.assertEqual(monitoring_light(35, CONFIG), "yellow-red")
        self.assertEqual(monitoring_light(30, CONFIG), "green")
        self.assertEqual(monitoring_light(18, CONFIG), "yellow-blue")
        self.assertEqual(monitoring_light(12, CONFIG), "blue")

    def test_parse_build_metrics_and_regime(self):
        rows = parse_taiwan_macro_csv(csv_fixture())
        metrics = build_macro_metrics(rows)
        self.assertIn("tw_manufacturing_pmi", metrics)
        self.assertEqual(
            metrics["tw_manufacturing_pmi"]["latest"]["value"],
            61.5,
        )
        for metric in metrics.values():
            validate_metric(metric)

        regime = build_macro_regime(rows, CONFIG)
        current = regime["current"]
        self.assertEqual(current["date"], "2026-07-01")
        self.assertEqual(current["ndc_monitoring_light"], "red")
        self.assertEqual(current["regime"], "expansion")
        self.assertGreaterEqual(current["known_components"], 3)
        self.assertEqual(current["available_on"], "2026-08-27")

    def test_cier_first_ingest_retains_release_date_without_fake_arrivals(self):
        months = [
            "2025-09-01", "2025-10-01", "2025-11-01", "2025-12-01",
            "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01",
            "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01",
        ]
        lines = [
            "date,provider,series_id,value,unit,release_date,source_url"
        ]
        lines.extend(
            (
                f"{obs_date},CIER,tw_manufacturing_pmi,{48 + index / 10},"
                "index,2026-09-21,https://www.cier.edu.tw/pmi-trend/"
            )
            for index, obs_date in enumerate(months)
        )
        rows = parse_taiwan_macro_csv("\n".join(lines) + "\n")
        metric = build_macro_metrics(rows)["tw_manufacturing_pmi"]

        self.assertEqual(metric["source"]["availability_basis"], "release_date")
        self.assertEqual(
            {item["release_date"] for item in metric["observations"]},
            {"2026-09-21"},
        )
        validate_metric(metric)

        pit = point_in_time_percentiles(
            metric["observations"],
            min_observations=2,
            availability_basis="release_date",
        )
        self.assertTrue(
            all(item["percentile"] is None for item in pit)
        )

    def test_duplicate_series_date_rejected(self):
        text = """date,provider,series_id,value,unit,release_date,source_url
2026-01-01,NDC,tw_ndc_leading_index,100,index,2026-02-01,https://example.com
2026-01-01,NDC,tw_ndc_leading_index,101,index,2026-02-02,https://example.com
"""
        with self.assertRaises(ValueError):
            parse_taiwan_macro_csv(text)

    def test_unknown_when_too_few_components(self):
        text = """date,provider,series_id,value,unit,release_date,source_url
2026-01-01,CIER,tw_manufacturing_pmi,49,index,2026-02-01,https://example.com
"""
        rows = parse_taiwan_macro_csv(text)
        regime = build_macro_regime(rows, CONFIG)
        self.assertIsNone(regime["current"])


if __name__ == "__main__":
    unittest.main()
