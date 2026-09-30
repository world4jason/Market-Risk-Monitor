import copy
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from pipeline.cier_pmi import parse_cier_pmi_html, to_macro_rows as cier_to_macro_rows, validate_rolling_window
from pipeline.ndc_business_cycle import (
    NDCBusinessCycleError,
    merge_current_vintage_rows,
    parse_ndc_snapshot_json,
    to_macro_rows,
    validate_ndc_snapshot,
)
from pipeline.taiwan_macro import (
    assemble_taiwan_macro_sources,
    build_macro_audit,
    build_macro_metrics,
    build_macro_regime,
    parse_taiwan_macro_csv,
)
from pipeline.validate import (
    validate_metric,
    validate_taiwan_macro_audit,
    validate_taiwan_macro_regime,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "ndc_business_cycle_snapshot.json"
COMMITTED = ROOT / "data" / "source" / "ndc-business-cycle-2026-09-26.csv"
CIER_FIXTURE = ROOT / "tests" / "fixtures" / "cier_pmi_trend.html"


class NDCBusinessCycleTests(unittest.TestCase):
    def payload(self):
        return parse_ndc_snapshot_json(FIXTURE.read_text(encoding="utf-8"))

    def test_real_snapshot_shape_and_values(self):
        payload = self.payload()
        self.assertEqual(set(payload), {"lightscore", "leading", "coincident", "lagged"})
        self.assertTrue(all(len(payload[key]["line"]) == 12 for key in payload))
        self.assertEqual(payload["lightscore"]["line"][-1], {"x": "202607", "y": 41})
        self.assertAlmostEqual(payload["leading"]["line"][-1]["y"], 104.6337282843642)
        self.assertAlmostEqual(payload["coincident"]["line"][-1]["y"], 106.8049537676424)
        self.assertAlmostEqual(payload["lagged"]["line"][-1]["y"], 104.7914087010663)
        self.assertEqual(
            {payload[key]["next"] for key in payload},
            {"2026-09-29 16:00"},
        )

    def test_normalizes_to_canonical_macro_contract(self):
        rows = to_macro_rows(self.payload(), observed_at=date(2026, 9, 26))
        self.assertEqual(len(rows), 48)
        self.assertEqual(
            {row["series_id"] for row in rows},
            {
                "tw_ndc_monitoring_score",
                "tw_ndc_leading_index",
                "tw_ndc_coincident_index",
                "tw_ndc_lagging_index",
            },
        )
        self.assertEqual({row["provider"] for row in rows}, {"NDC"})
        self.assertEqual({row["release_date"] for row in rows}, {"2026-09-26"})
        self.assertEqual(min(row["date"] for row in rows), "2025-08-01")
        self.assertEqual(max(row["date"] for row in rows), "2026-07-01")

        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "date", "provider", "series_id", "value", "unit", "release_date", "source_url"
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        parsed = parse_taiwan_macro_csv(buffer.getvalue())
        self.assertEqual(len(parsed), 48)

    def test_rejects_missing_partial_or_nonfinite_snapshot(self):
        payload = self.payload()
        missing = copy.deepcopy(payload)
        del missing["lagged"]
        with self.assertRaisesRegex(NDCBusinessCycleError, "missing required series"):
            validate_ndc_snapshot(missing)

        partial = copy.deepcopy(payload)
        partial["leading"]["line"].pop()
        with self.assertRaisesRegex(NDCBusinessCycleError, "exactly 12 monthly"):
            validate_ndc_snapshot(partial)

        nonfinite = copy.deepcopy(payload)
        nonfinite["coincident"]["line"][0]["y"] = float("nan")
        with self.assertRaisesRegex(NDCBusinessCycleError, "non-finite"):
            validate_ndc_snapshot(nonfinite)

    def test_rejects_noncontiguous_or_misaligned_windows(self):
        payload = self.payload()
        gap = copy.deepcopy(payload)
        gap["leading"]["line"][5]["x"] = "202603"
        with self.assertRaisesRegex(NDCBusinessCycleError, "duplicate month|not contiguous"):
            validate_ndc_snapshot(gap)

        misaligned = copy.deepcopy(payload)
        misaligned["lagged"]["line"][0]["x"] = "202507"
        with self.assertRaisesRegex(NDCBusinessCycleError, "not contiguous|differs from other series"):
            validate_ndc_snapshot(misaligned)

    def test_merge_accumulates_old_months_and_blocks_stale_replay(self):
        incoming = to_macro_rows(self.payload(), observed_at=date(2026, 9, 26))
        existing = [
            {
                "date": "2025-07-01",
                "provider": "NDC",
                "series_id": "tw_ndc_leading_index",
                "value": "97.0",
                "unit": "index",
                "release_date": "2026-08-30",
                "source_url": "https://index.ndc.gov.tw/n/zh_tw/leading",
            }
        ]
        merged = merge_current_vintage_rows(existing, incoming)
        self.assertEqual(len(merged), 49)
        self.assertTrue(any(row["date"] == "2025-07-01" for row in merged))

        stale = [dict(row, release_date="2026-08-31") for row in incoming]
        with self.assertRaisesRegex(NDCBusinessCycleError, "stale NDC snapshot replay"):
            merge_current_vintage_rows(merged, stale)


class NDCBootstrapCliTests(unittest.TestCase):
    def test_saved_snapshot_requires_observed_at(self):
        script = ROOT / "scripts" / "bootstrap_ndc_business_cycle.py"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ndc.csv"
            result = subprocess.run(
                [sys.executable, str(script), "--snapshot-file", str(FIXTURE), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--observed-at is required with --snapshot-file", result.stderr)
            self.assertFalse(output.exists())

    def test_saved_snapshot_reproduces_committed_normalized_csv(self):
        script = ROOT / "scripts" / "bootstrap_ndc_business_cycle.py"
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ndc.csv"
            result = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--snapshot-file",
                    str(FIXTURE),
                    "--observed-at",
                    "2026-09-26",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), COMMITTED.read_bytes())


class NDCRealSourceIntegrationTests(unittest.TestCase):
    def test_real_ndc_snapshot_assembles_with_cier_fixture_and_validates(self):
        ndc_rows = parse_taiwan_macro_csv(COMMITTED.read_text(encoding="utf-8"))
        cier_parsed = parse_cier_pmi_html(CIER_FIXTURE.read_text(encoding="utf-8"))
        validate_rolling_window(cier_parsed)
        cier_rows = cier_to_macro_rows(cier_parsed, observed_at=date(2026, 9, 21))

        rows = assemble_taiwan_macro_sources(
            [("ndc-official", ndc_rows), ("cier-official-fixture", cier_rows)]
        )
        metrics = build_macro_metrics(
            rows,
            datetime(2026, 9, 26, tzinfo=timezone.utc),
        )
        self.assertEqual(
            set(metrics),
            {
                "tw_manufacturing_pmi",
                "tw_ndc_monitoring_score",
                "tw_ndc_leading_index",
                "tw_ndc_coincident_index",
                "tw_ndc_lagging_index",
            },
        )
        for metric in metrics.values():
            validate_metric(metric)
        for metric_id in (
            "tw_ndc_monitoring_score",
            "tw_ndc_leading_index",
            "tw_ndc_coincident_index",
            "tw_ndc_lagging_index",
        ):
            self.assertEqual(metrics[metric_id]["freshness"]["state"], "fresh")
            self.assertEqual(metrics[metric_id]["freshness"]["age_days"], 0)
            self.assertEqual(metrics[metric_id]["source"]["availability_basis"], "unknown")
            self.assertFalse(metrics[metric_id]["baselines"][0]["point_in_time"])

        config = json.loads((ROOT / "data" / "config" / "taiwan-macro.json").read_text())
        regime = build_macro_regime(rows, config)
        validate_taiwan_macro_regime(regime)
        self.assertEqual(regime["current"]["date"], "2026-08-01")
        self.assertEqual(regime["current"]["regime"], "unknown")
        self.assertEqual(regime["latest_known"]["date"], "2026-07-01")
        self.assertFalse(regime["methodology"]["historical_point_in_time"])
        self.assertEqual(regime["methodology"]["history_semantics"], "retrospective_current_vintage")

        audit = build_macro_audit(rows)
        validate_taiwan_macro_audit(audit)


if __name__ == "__main__":
    unittest.main()
