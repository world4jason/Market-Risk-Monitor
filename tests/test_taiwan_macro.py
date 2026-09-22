import json
import unittest

from pipeline.taiwan_macro import (
    build_macro_metrics,
    build_macro_regime,
    monitoring_light,
    parse_taiwan_macro_csv,
)
from pipeline.validate import (
    ValidationError,
    validate_metric,
    validate_taiwan_macro_regime,
)


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
        self.assertIsNone(regime["current"]["score"])
        self.assertEqual(regime["current"]["regime"], "unknown")
        self.assertIsNone(regime["latest_known"])

    def test_current_does_not_carry_forward_a_stale_known_regime(self):
        # A month with a full component set followed by a month where only PMI
        # arrived. The dashboard reads `current` directly, so returning the
        # older month's regime would present a stale benign reading as the
        # present state.
        rows = parse_taiwan_macro_csv(csv_fixture())
        stale = [
            row
            for row in rows
            if not (
                row["date"] == "2026-07-01"
                and row["series_id"] != "tw_manufacturing_pmi"
            )
        ]

        regime = build_macro_regime(stale, CONFIG)

        current = regime["current"]
        self.assertEqual(current["date"], "2026-07-01")
        self.assertEqual(current["regime"], "unknown")
        self.assertIsNone(current["score"])
        self.assertLess(current["known_components"], 2)

        # The earlier reading is still available, but clearly labelled as the
        # last known one rather than as the current state.
        latest_known = regime["latest_known"]
        self.assertIsNotNone(latest_known)
        self.assertLess(latest_known["date"], current["date"])
        self.assertNotEqual(latest_known["regime"], "unknown")


def regime_row(date_, regime, **extra):
    row = {
        "date": date_,
        "score": None if regime == "unknown" else 0.5,
        "known_components": 1 if regime == "unknown" else 4,
        "total_components": 4,
        "confidence": 0.25 if regime == "unknown" else 1.0,
        "available_on": "2026-09-21",
        "components": {},
        "regime": regime,
    }
    row.update(extra)
    return row


def regime_payload(history, *, current=None, latest_known=None):
    payload = {
        "schema_version": "1.0.0",
        "name": "MRM Taiwan Macro Regime",
        "history": history,
        "current": current if current is not None else (history[-1] if history else None),
    }
    payload["latest_known"] = latest_known
    return payload


class TaiwanMacroRegimeValidatorTests(unittest.TestCase):
    def setUp(self):
        self.history = [
            regime_row("2026-05-01", "recovery"),
            regime_row("2026-06-01", "expansion"),
            regime_row("2026-07-01", "unknown"),
        ]

    def test_correct_latest_known_is_accepted(self):
        validate_taiwan_macro_regime(
            regime_payload(self.history, latest_known=self.history[1])
        )

    def test_latest_known_must_be_the_last_known_row_not_an_earlier_one(self):
        # 2026-05 is a genuine known row, but 2026-06 is the last one. Accepting
        # any older known row would let a stale regime be presented as the most
        # recent reading.
        with self.assertRaises(ValidationError):
            validate_taiwan_macro_regime(
                regime_payload(self.history, latest_known=self.history[0])
            )

    def test_latest_known_not_present_in_history_is_rejected(self):
        fabricated = regime_row("2026-06-01", "expansion", score=0.9)
        with self.assertRaises(ValidationError):
            validate_taiwan_macro_regime(
                regime_payload(self.history, latest_known=fabricated)
            )

    def test_latest_known_missing_while_a_known_row_exists_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_taiwan_macro_regime(
                regime_payload(self.history, latest_known=None)
            )

    def test_latest_known_must_be_null_when_no_row_is_known(self):
        history = [regime_row("2026-07-01", "unknown")]
        validate_taiwan_macro_regime(regime_payload(history, latest_known=None))

        with self.assertRaises(ValidationError):
            validate_taiwan_macro_regime(
                regime_payload(
                    history,
                    latest_known=regime_row("2026-06-01", "expansion"),
                )
            )

    def test_generated_regime_passes_its_own_validator(self):
        rows = parse_taiwan_macro_csv(csv_fixture())
        validate_taiwan_macro_regime(build_macro_regime(rows, CONFIG))

        stale = [
            row
            for row in rows
            if not (
                row["date"] == "2026-07-01"
                and row["series_id"] != "tw_manufacturing_pmi"
            )
        ]
        validate_taiwan_macro_regime(build_macro_regime(stale, CONFIG))


if __name__ == "__main__":
    unittest.main()
