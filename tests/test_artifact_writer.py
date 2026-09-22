"""
Every canonical metric producer must write artifacts the release validator
accepts.

metric.comparison is required by schemas/metric-series.schema.json but is
stamped at write time, not by the builders. So a producer that writes JSON
through its own helper instead of the shared one succeeds, passes
validate_metric(), and then fails scripts/validate_data.py -- the artifact is
only invalid once the release tries to validate it.

These tests drive real producers and validate their output against the full
JSON Schema, which is what scripts/validate_data.py applies.
"""
import copy
import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from pipeline.artifacts import write_json_artifact
from pipeline.presentation import comparison_for
from pipeline.taiwan_trend_breadth import MARKET_SCOPE, compute_from_panel


ROOT = Path(__file__).resolve().parents[1]
SPECIAL_ARTIFACTS = {
    "catalog.json",
    "coverage.json",
    "refresh-report.json",
    "signals.json",
    "ma-breadth-audit.json",
    "ma-breadth-event-study.json",
    "taiwan-macro-regime.json",
    "taiwan-macro-audit.json",
    "taiwan-cbc-rate-regime.json",
    "fed-rate-regime.json",
    "taiwan-trend-breadth-audit.json",
}

METRIC_SCHEMA = Draft202012Validator(
    json.loads(
        (ROOT / "schemas" / "metric-series.schema.json").read_text(encoding="utf-8")
    ),
    format_checker=FormatChecker(),
)


def assert_schema_valid(test, payload, context):
    errors = sorted(
        METRIC_SCHEMA.iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(p) for p in first.absolute_path) or "<root>"
        test.fail(f"{context}: schema error at {location}: {first.message}")


class SharedWriterTests(unittest.TestCase):
    def test_writer_finalizes_a_builder_metric_into_a_schema_valid_artifact(self):
        # Builders do not set comparison; the writer does.
        metric = {
            "schema_version": "1.0.0",
            "environment": "production",
            "metric": {
                "id": "tw_taiex",
                "name": "TAIEX",
                "description": "fixture",
                "pillar": "market",
                "units": "index",
                "frequency": "daily",
                "polarity": "contextual",
            },
            "source": {
                "provider": "TWSE",
                "dataset": "fixture",
                "series_id": "tw_taiex",
                "url": "https://example.com",
                "license_note": "fixture",
                "redistribution": "unknown",
            },
            "coverage": {
                "history_start": "2026-01-01",
                "history_end": "2026-01-02",
                "timezone": "Asia/Taipei",
                "expected_observation_lag_days": 1,
            },
            "freshness": {
                "state": "fresh",
                "max_age_days": 5,
                "age_days": 1,
                "evaluated_at": "2026-01-03T00:00:00Z",
                "reason": None,
            },
            "lineage": {
                "kind": "raw",
                "inputs": [],
                "formula": None,
                "transform_version": "twse-raw-v1",
            },
            "baselines": [],
            "latest": {
                "as_of": "2026-01-02",
                "fetched_at": "2026-01-03T00:00:00Z",
                "value": 2.0,
                "revision_tag": None,
            },
            "observations": [
                {"date": "2026-01-01", "value": 1.0, "status": "observed"},
                {"date": "2026-01-02", "value": 2.0, "status": "observed"},
            ],
        }
        self.assertNotIn("comparison", metric["metric"])

        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "tw_taiex.json"
            write_json_artifact(dest, metric)
            written = json.loads(dest.read_text(encoding="utf-8"))

        self.assertEqual(written["metric"]["comparison"], "percent_change")
        assert_schema_valid(self, written, "tw_taiex")

    def test_no_producer_writes_artifacts_outside_the_shared_path(self):
        # Supplementary guard. Six copies of this helper existed, and only the
        # copy in refresh_data learned to stamp comparison; the rest silently
        # produced schema-invalid artifacts. A module may still define an
        # atomic_json wrapper -- refresh_data adds the release ledger to it --
        # but it has to delegate rather than reimplement the write.
        offenders = []
        for path in sorted(
            list((ROOT / "scripts").glob("*.py"))
            + list((ROOT / "pipeline").glob("*.py"))
        ):
            if path.name == "artifacts.py":
                continue
            text = path.read_text(encoding="utf-8")
            if "def atomic_json(" not in text:
                continue
            body = text.split("def atomic_json(", 1)[1].split("\ndef ", 1)[0]
            if "write_json_artifact(" not in body:
                offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])


class ContractFixtureTests(unittest.TestCase):
    """
    docs/data-contract.md points at these files as the contract examples, so
    they have to satisfy the contract. When metric.comparison became required
    they did not, and the repository's own examples violated its own schema.
    """

    def fixtures(self):
        paths = sorted((ROOT / "data" / "fixtures").glob("metric-*.json"))
        self.assertTrue(paths, "no contract fixtures found")
        return paths

    def test_every_contract_fixture_passes_the_release_validator(self):
        for path in self.fixtures():
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert_schema_valid(self, payload, path.name)

    def test_no_metric_shaped_json_in_the_repo_violates_the_schema(self):
        # Broader than the three fixtures: any example, fixture or checked-in
        # artifact outside data/generated must satisfy the same contract, so a
        # future one cannot be added and quietly left behind.
        skip_parts = {".venv", ".cache", ".git", "node_modules"}
        checked = 0
        for path in sorted(ROOT.rglob("*.json")):
            relative = path.relative_to(ROOT)
            if set(relative.parts) & skip_parts:
                continue
            if relative.parts[:2] == ("data", "generated"):
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if not (
                isinstance(payload, dict)
                and isinstance(payload.get("metric"), dict)
                and "observations" in payload
            ):
                continue
            assert_schema_valid(self, payload, relative.as_posix())
            checked += 1
        self.assertGreaterEqual(checked, 3)

    def test_the_zero_centred_fixture_declares_an_absolute_comparison(self):
        # nfci_fixture holds negative values, so a relative change has no
        # stable sign. Its id is deliberately not in
        # ZERO_CENTRED_INDEX_METRIC_IDS -- fixture ids do not belong in
        # production config -- so the fixture declares the comparison itself.
        # This guards against someone "correcting" it to match the derivation.
        payload = json.loads(
            (ROOT / "data" / "fixtures" / "metric-weekly.json").read_text(
                encoding="utf-8"
            )
        )
        values = [
            obs["value"]
            for obs in payload["observations"]
            if obs["value"] is not None
        ]
        self.assertLess(min(values), 0, "fixture no longer crosses/sits below zero")
        self.assertEqual(payload["metric"]["comparison"], "absolute")

    def test_derived_fixtures_agree_with_the_production_derivation(self):
        # The claim was that fixture comparisons are derived rather than hand
        # picked. That only holds if it is enforced: otherwise a later change
        # to comparison_for() leaves the contract examples quietly drifted from
        # what producers actually emit.
        for name in ["metric-daily.json", "metric-monthly.json"]:
            payload = json.loads(
                (ROOT / "data" / "fixtures" / name).read_text(encoding="utf-8")
            )
            declared = payload["metric"]["comparison"]
            stripped = copy.deepcopy(payload)
            del stripped["metric"]["comparison"]
            self.assertEqual(
                declared,
                comparison_for(stripped),
                f"{name} no longer matches the production derivation",
            )

    def test_the_weekly_fixture_is_an_intentional_override(self):
        # Deliberately exempt from the rule above. nfci_fixture is a
        # zero-centred series whose id is not, and should not be, in
        # ZERO_CENTRED_INDEX_METRIC_IDS, so the derivation gets it wrong and
        # the fixture overrides it. Asserting the disagreement keeps the
        # exemption honest: if the derivation ever learns to handle this case,
        # this test fails and the override can be removed.
        payload = json.loads(
            (ROOT / "data" / "fixtures" / "metric-weekly.json").read_text(
                encoding="utf-8"
            )
        )
        stripped = copy.deepcopy(payload)
        del stripped["metric"]["comparison"]

        self.assertEqual(comparison_for(stripped), "percent_change")
        self.assertEqual(payload["metric"]["comparison"], "absolute")

    def test_a_declared_comparison_survives_the_writer(self):
        payload = json.loads(
            (ROOT / "data" / "fixtures" / "metric-weekly.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "metric-weekly.json"
            write_json_artifact(dest, payload)
            written = json.loads(dest.read_text(encoding="utf-8"))
        self.assertEqual(written["metric"]["comparison"], "absolute")


class DirectProducerSchemaTests(unittest.TestCase):
    def write_panel(self, path):
        start = date(2020, 1, 1)
        fields = [
            "date", "symbol", "high", "low", "close",
            "market_scope", "provider", "membership_mode", "price_adjustment",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for i in range(300):
                obs_date = (start + timedelta(days=i)).isoformat()
                for symbol, close in (("AAA", 100 + i), ("BBB", 500 - i)):
                    writer.writerow(
                        {
                            "date": obs_date,
                            "symbol": symbol,
                            "high": close + 1,
                            "low": close - 1,
                            "close": close,
                            "market_scope": MARKET_SCOPE,
                            "provider": "fixture official panel",
                            "membership_mode": "point_in_time",
                            "price_adjustment": "unadjusted_close",
                        }
                    )

    def test_taiwan_trend_breadth_output_passes_the_release_validator(self):
        # compute_from_panel() writes canonical metrics without going through
        # scripts/refresh_data.py, so it is one of the producers that used to
        # emit artifacts the release validator rejects.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            panel = root / "panel.csv"
            output = root / "out"
            self.write_panel(panel)

            report = compute_from_panel(panel, output)
            self.assertTrue(report["metrics"], "producer emitted no metrics")

            validated = 0
            for path in sorted(output.glob("*.json")):
                if path.name in SPECIAL_ARTIFACTS:
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn(
                    "comparison",
                    payload["metric"],
                    f"{path.name} was written without comparison",
                )
                assert_schema_valid(self, payload, path.name)
                validated += 1

            self.assertEqual(validated, len(report["metrics"]))


if __name__ == "__main__":
    unittest.main()
