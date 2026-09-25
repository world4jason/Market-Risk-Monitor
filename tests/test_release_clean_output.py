"""
Behavioural coverage for the release build's output semantics.

A source-code grep cannot show that an allowlist actually produces an exact
release set. These tests pre-seed artifacts an earlier run would have left
behind, drive the real prune path, and assert they are gone from both the
directory and the catalog.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_refresh_module():
    spec = importlib.util.spec_from_file_location(
        "refresh_data_under_test",
        ROOT / "scripts" / "refresh_data.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metric_artifact(metric_id, *, units="index", value=1.0):
    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": metric_id,
            "name": metric_id,
            "description": "fixture",
            "pillar": "market",
            "units": units,
            "frequency": "daily",
            "polarity": "contextual",
            "comparison": "percent_change",
        },
        "source": {
            "provider": "fixture",
            "dataset": "fixture",
            "series_id": metric_id,
            "url": "https://example.com",
            "license_note": "fixture",
            "redistribution": "restricted",
        },
        "coverage": {
            "history_start": "2026-01-01",
            "history_end": "2026-01-02",
            "timezone": "UTC",
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
            "transform_version": "fixture-v1",
        },
        "baselines": [],
        "latest": {
            "as_of": "2026-01-02",
            "fetched_at": "2026-01-03T00:00:00Z",
            "value": value,
            "revision_tag": None,
        },
        "observations": [
            {"date": "2026-01-01", "value": value, "status": "observed"},
            {"date": "2026-01-02", "value": value, "status": "observed"},
        ],
    }


class FredAllowlistGatingTests(unittest.TestCase):
    """--fred-id on its own must actually refresh FRED."""

    class Args:
        def __init__(self, fred=False, public=False, fred_id=()):
            self.fred = fred
            self.public = public
            self.fred_id = list(fred_id)

    def setUp(self):
        self.module = load_refresh_module()

    def test_fred_id_alone_activates_the_refresh(self):
        self.assertTrue(
            self.module.should_run_fred(self.Args(fred_id=["nfci"]))
        )

    def test_explicit_flags_still_activate_it(self):
        self.assertTrue(self.module.should_run_fred(self.Args(fred=True)))
        self.assertTrue(self.module.should_run_fred(self.Args(public=True)))

    def test_no_fred_selection_does_not_activate_it(self):
        self.assertFalse(self.module.should_run_fred(self.Args()))


class GroupedSourceFailureTests(unittest.TestCase):
    """
    A single fetch can produce several metrics.

    When a grouped source fails it names one representative metric in the
    report, so --clean-output must be told the whole group it speaks for.
    Inferring the preserved set from that one name would prune the siblings the
    failed refresh was meant to preserve, breaking the contract in docs/qa.md
    that a failed refresh never deletes a prior real metric file.
    """

    def setUp(self):
        self.module = load_refresh_module()
        self.module.WRITTEN_ARTIFACTS.clear()
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.out = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def seed_group(self, metric_ids):
        for metric_id in metric_ids:
            (self.out / f"{metric_id}.json").write_text(
                json.dumps(metric_artifact(metric_id)), encoding="utf-8"
            )

    def test_failed_taiex_refresh_keeps_every_sibling_snapshot(self):
        group = self.module.TAIEX_GROUP_METRIC_IDS
        self.seed_group(group)
        # Something unrelated did succeed this run.
        self.module.atomic_json(self.out / "vix.json", metric_artifact("vix"))

        report = [
            {
                "metric": "tw_taiex",
                "status": "error",
                "error": "TWSE fetch failed",
                "preserved_previous": True,
                "preserved_metric_ids": group,
            }
        ]

        removed = self.module.prune_unwritten_artifacts(
            self.out,
            preserved_metric_ids=self.module.preserved_ids_from_report(report),
        )

        self.assertEqual(removed, [])
        for metric_id in group:
            self.assertTrue(
                (self.out / f"{metric_id}.json").exists(),
                f"{metric_id} was pruned despite a preserved failure",
            )

    def test_failed_breadth_refresh_keeps_every_sibling_snapshot(self):
        group = self.module.TAIWAN_BREADTH_GROUP_METRIC_IDS
        self.seed_group(group)

        report = [
            {
                "metric": "tw_advance_decline_diff",
                "status": "error",
                "error": "MI_INDEX fetch failed",
                "preserved_previous": True,
                "preserved_metric_ids": group,
            }
        ]

        removed = self.module.prune_unwritten_artifacts(
            self.out,
            preserved_metric_ids=self.module.preserved_ids_from_report(report),
        )

        self.assertEqual(removed, [])
        self.assertEqual(len(list(self.out.glob("*.json"))), len(group))

    def test_inferring_the_group_from_the_reported_name_would_lose_siblings(self):
        # Guards the regression directly: with only the representative id
        # preserved, the siblings are pruned.
        group = self.module.TAIEX_GROUP_METRIC_IDS
        self.seed_group(group)

        removed = self.module.prune_unwritten_artifacts(
            self.out,
            preserved_metric_ids={"tw_taiex"},
        )

        self.assertNotIn("tw_taiex.json", removed)
        self.assertEqual(len(removed), len(group) - 1)

    def test_an_entry_without_a_declared_group_speaks_only_for_itself(self):
        report = [
            {
                "metric": "vix",
                "status": "error",
                "error": "Cboe fetch failed",
                "preserved_previous": True,
            }
        ]
        self.assertEqual(
            self.module.preserved_ids_from_report(report),
            {"vix"},
        )

    def test_a_failure_that_preserved_nothing_contributes_nothing(self):
        report = [
            {
                "metric": "vix",
                "status": "error",
                "error": "Cboe fetch failed",
                "preserved_previous": False,
            },
            {"metric": "nfci", "status": "updated"},
        ]
        self.assertEqual(self.module.preserved_ids_from_report(report), set())

    def test_a_real_twse_outage_preserves_both_groups(self):
        # Drives refresh_twse_current() itself rather than a hand-written
        # report. That distinction matters: a hand-written report hid the fact
        # that a TAIEX failure returns early, so the breadth group was never
        # attempted, never reported, and therefore never preserved -- a failure
        # in one group silently deleted the other group's snapshots.
        group = (
            self.module.TAIEX_GROUP_METRIC_IDS
            + self.module.TAIWAN_BREADTH_GROUP_METRIC_IDS
        )
        self.seed_group(group)

        def outage(*args, **kwargs):
            raise RuntimeError("simulated TWSE outage")

        self.module.fetch_fmtqik_current = outage
        self.module.fetch_market_breadth_day = outage

        report = self.module.refresh_twse_current(self.out)

        self.assertTrue(all(item["status"] == "error" for item in report))
        self.assertEqual(
            {item["metric"] for item in report},
            {"tw_taiex", "tw_advance_decline_diff"},
            "both groups must report, so both can be preserved",
        )

        removed = self.module.prune_unwritten_artifacts(
            self.out,
            preserved_metric_ids=self.module.preserved_ids_from_report(report),
        )

        self.assertEqual(removed, [])
        self.assertEqual(
            sorted(p.stem for p in self.out.glob("*.json")),
            sorted(group),
        )

    def test_group_constants_match_what_the_builders_produce(self):
        # The constants exist so a failed fetch can declare its group without
        # the builder's output. This asserts they cannot drift apart.
        from datetime import datetime, timezone

        from pipeline.taiwan_twse import (
            build_taiex_metrics,
            build_taiwan_breadth_metrics,
        )

        fetched_at = datetime(2026, 1, 3, tzinfo=timezone.utc)
        taiex = build_taiex_metrics(
            [
                {"date": "2026-01-01", "close": 1.0, "open": 1.0, "high": 1.0,
                 "low": 1.0, "trade_value": 1.0, "trade_volume": 1},
                {"date": "2026-01-02", "close": 2.0, "open": 2.0, "high": 2.0,
                 "low": 2.0, "trade_value": 2.0, "trade_volume": 2},
            ],
            fetched_at,
        )
        breadth = build_taiwan_breadth_metrics(
            [
                {"date": "2026-01-01", "advancing": 1, "declining": 1,
                 "unchanged": 1, "limit_up": 0, "limit_down": 0, "unmatched": 0},
                {"date": "2026-01-02", "advancing": 2, "declining": 1,
                 "unchanged": 1, "limit_up": 0, "limit_down": 0, "unmatched": 0},
            ],
            fetched_at,
        )

        self.assertEqual(
            sorted(self.module.TAIEX_GROUP_METRIC_IDS), sorted(taiex)
        )
        self.assertEqual(
            sorted(self.module.TAIWAN_BREADTH_GROUP_METRIC_IDS), sorted(breadth)
        )


class DerivedProvenanceProductionPathTests(unittest.TestCase):
    def setUp(self):
        self.module = load_refresh_module()
        self.module.WRITTEN_ARTIFACTS.clear()
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.out = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_fed_rate_regime_uses_raw_source_snapshots(self):
        legacy = metric_artifact("fed_target_legacy", units="percent", value=1.0)
        upper = metric_artifact("fed_target_upper", units="percent", value=2.0)
        (self.out / "fed_target_legacy.json").write_text(
            json.dumps(legacy), encoding="utf-8"
        )
        (self.out / "fed_target_upper.json").write_text(
            json.dumps(upper), encoding="utf-8"
        )

        self.module.maybe_build_fed_rate_outputs(self.out)
        first = json.loads(
            (self.out / "fed-rate-regime.json").read_text(encoding="utf-8")
        )
        self.module.maybe_build_fed_rate_outputs(self.out)
        second = json.loads(
            (self.out / "fed-rate-regime.json").read_text(encoding="utf-8")
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first["provenance"]["required_inputs"],
            ["rate_rows"],
        )
        self.assertEqual(
            [item["id"] for item in first["provenance"]["inputs"]],
            ["fed_target_legacy", "fed_target_upper", "rate_rows"],
        )
        rate_rows = next(
            item
            for item in first["provenance"]["inputs"]
            if item["id"] == "rate_rows"
        )
        self.assertIsNone(rate_rows["snapshot_at"])

    def test_cbc_rate_regime_is_stable_across_rebuild_wall_clock(self):
        source = self.out / "cbc.csv"
        source.write_text(
            (
                "date,discount_rate,collateral_rate,short_term_rate,source_url\n"
                "2024-01-01,1.875,,,https://www.cbc.gov.tw/en/lp-695-2.html\n"
                "2024-03-22,2.0,,,https://www.cbc.gov.tw/en/lp-695-2.html\n"
            ),
            encoding="utf-8",
        )

        self.module.refresh_cbc_rate_file(source, self.out)
        first = json.loads(
            (self.out / "taiwan-cbc-rate-regime.json").read_text(
                encoding="utf-8"
            )
        )
        self.module.refresh_cbc_rate_file(source, self.out)
        second = json.loads(
            (self.out / "taiwan-cbc-rate-regime.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first["provenance"]["required_inputs"],
            ["rate_rows"],
        )
        self.assertEqual(
            first["provenance"]["generated_at"],
            "2024-03-22T00:00:00Z",
        )
        self.assertIsNone(
            first["provenance"]["inputs"][0]["snapshot_at"]
        )


class TaiwanMacroAssemblyRefreshTests(unittest.TestCase):
    def setUp(self):
        self.module = load_refresh_module()
        self.module.WRITTEN_ARTIFACTS.clear()
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.out = Path(self.tmp.name) / "out"
        self.out.mkdir()
        self.addCleanup(self.tmp.cleanup)

    def write_source(self, name, rows):
        path = Path(self.tmp.name) / name
        header = "date,provider,series_id,value,unit,release_date,source_url\n"
        path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
        return path

    def test_full_union_writes_both_source_families(self):
        cier = self.write_source(
            "cier.csv",
            [
                "2026-01-01,CIER,tw_manufacturing_pmi,49,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
                "2026-02-01,CIER,tw_manufacturing_pmi,50,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
            ],
        )
        ndc = self.write_source(
            "ndc.csv",
            [
                "2026-01-01,NDC,tw_ndc_leading_index,100,index,2026-09-21,https://www.ndc.gov.tw/en/",
                "2026-02-01,NDC,tw_ndc_leading_index,101,index,2026-09-21,https://www.ndc.gov.tw/en/",
            ],
        )

        self.module.refresh_taiwan_macro_files([cier, ndc], self.out)

        self.assertTrue((self.out / "tw_manufacturing_pmi.json").exists())
        self.assertTrue((self.out / "tw_ndc_leading_index.json").exists())
        audit = json.loads(
            (self.out / "taiwan-macro-audit.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            {row["series_id"] for row in audit["rows"]},
            {"tw_manufacturing_pmi", "tw_ndc_leading_index"},
        )

    def seed_full_macro_state(self):
        cier = self.write_source(
            "cier.csv",
            [
                "2026-01-01,CIER,tw_manufacturing_pmi,49,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
                "2026-02-01,CIER,tw_manufacturing_pmi,50,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
            ],
        )
        ndc = self.write_source(
            "ndc.csv",
            [
                "2026-01-01,NDC,tw_ndc_leading_index,100,index,2026-09-21,https://www.ndc.gov.tw/en/",
                "2026-02-01,NDC,tw_ndc_leading_index,101,index,2026-09-21,https://www.ndc.gov.tw/en/",
            ],
        )
        self.module.refresh_taiwan_macro_files([cier, ndc], self.out)
        return cier, ndc

    def macro_bytes(self):
        return {
            path.name: path.read_bytes()
            for path in self.out.glob("*.json")
            if (
                path.stem in self.module.SERIES_META
                or path.name in {
                    "taiwan-macro-audit.json",
                    "taiwan-macro-regime.json",
                }
            )
        }

    def test_existing_macro_metrics_without_audit_fail_closed(self):
        cier, _ = self.seed_full_macro_state()
        (self.out / "taiwan-macro-audit.json").unlink()
        before = self.macro_bytes()
        self.module.WRITTEN_ARTIFACTS.clear()

        with self.assertRaisesRegex(
            ValueError,
            "require taiwan-macro-audit.json",
        ):
            self.module.refresh_taiwan_macro_files([cier], self.out)

        self.assertEqual(self.module.WRITTEN_ARTIFACTS, set())
        self.assertEqual(self.macro_bytes(), before)
        self.assertTrue((self.out / "tw_ndc_leading_index.json").exists())

    def test_clean_output_cli_stops_before_pruning_when_audit_is_missing(self):
        cier, _ = self.seed_full_macro_state()
        (self.out / "taiwan-macro-audit.json").unlink()
        ndc_path = self.out / "tw_ndc_leading_index.json"
        ndc_before = ndc_path.read_bytes()

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "refresh_data.py"),
                "--taiwan-macro-file",
                str(cier),
                "--output-dir",
                str(self.out),
                "--clean-output",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "require taiwan-macro-audit.json",
            result.stderr + result.stdout,
        )
        self.assertTrue(ndc_path.exists())
        self.assertEqual(ndc_path.read_bytes(), ndc_before)

    def test_stale_audit_missing_existing_ndc_series_fails_closed(self):
        cier, _ = self.seed_full_macro_state()
        audit_path = self.out / "taiwan-macro-audit.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["rows"] = [
            row for row in audit["rows"]
            if row["series_id"] == "tw_manufacturing_pmi"
        ]
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        before = self.macro_bytes()
        self.module.WRITTEN_ARTIFACTS.clear()

        with self.assertRaisesRegex(
            ValueError,
            "series do not match existing canonical",
        ):
            self.module.refresh_taiwan_macro_files([cier], self.out)

        self.assertEqual(self.module.WRITTEN_ARTIFACTS, set())
        self.assertEqual(self.macro_bytes(), before)
        self.assertTrue((self.out / "tw_ndc_leading_index.json").exists())

    def test_release_aware_older_vintage_fails_before_any_write(self):
        _, ndc = self.seed_full_macro_state()
        newer_cier = self.write_source(
            "cier-newer.csv",
            [
                "2026-01-01,CIER,tw_manufacturing_pmi,49.5,index,2026-12-31,https://www.cier.edu.tw/pmi-trend/",
                "2026-02-01,CIER,tw_manufacturing_pmi,50,index,2026-12-31,https://www.cier.edu.tw/pmi-trend/",
            ],
        )
        self.module.refresh_taiwan_macro_files([newer_cier, ndc], self.out)
        older_conflict = self.write_source(
            "cier-older.csv",
            [
                "2026-01-01,CIER,tw_manufacturing_pmi,48,index,2026-11-30,https://www.cier.edu.tw/pmi-trend/",
                "2026-02-01,CIER,tw_manufacturing_pmi,50,index,2026-11-30,https://www.cier.edu.tw/pmi-trend/",
            ],
        )
        before = self.macro_bytes()
        self.module.WRITTEN_ARTIFACTS.clear()

        with self.assertRaisesRegex(
            ValueError,
            "out-of-order release-aware revision",
        ):
            self.module.refresh_taiwan_macro_files(
                [older_conflict, ndc],
                self.out,
            )

        self.assertEqual(self.module.WRITTEN_ARTIFACTS, set())
        self.assertEqual(self.macro_bytes(), before)

    def test_metric_validation_failure_occurs_before_first_write(self):
        cier, _ = self.seed_full_macro_state()
        ndc_nan = self.write_source(
            "ndc-nan.csv",
            [
                "2026-01-01,NDC,tw_ndc_leading_index,nan,index,2026-09-21,https://www.ndc.gov.tw/en/",
                "2026-02-01,NDC,tw_ndc_leading_index,101,index,2026-09-21,https://www.ndc.gov.tw/en/",
            ],
        )
        before = self.macro_bytes()
        self.module.WRITTEN_ARTIFACTS.clear()

        with self.assertRaisesRegex(ValueError, "Non-finite observation"):
            self.module.refresh_taiwan_macro_files([cier, ndc_nan], self.out)

        self.assertEqual(self.module.WRITTEN_ARTIFACTS, set())
        self.assertEqual(self.macro_bytes(), before)

    def test_regime_failure_occurs_before_first_write(self):
        cier, ndc = self.seed_full_macro_state()
        before = self.macro_bytes()
        self.module.WRITTEN_ARTIFACTS.clear()
        original = self.module.validate_taiwan_macro_regime

        def fail_regime(_payload):
            raise ValueError("simulated regime validation failure")

        self.module.validate_taiwan_macro_regime = fail_regime
        try:
            with self.assertRaisesRegex(
                ValueError,
                "simulated regime validation failure",
            ):
                self.module.refresh_taiwan_macro_files([cier, ndc], self.out)
        finally:
            self.module.validate_taiwan_macro_regime = original

        self.assertEqual(self.module.WRITTEN_ARTIFACTS, set())
        self.assertEqual(self.macro_bytes(), before)

    def test_macro_refresh_supports_output_dir_outside_repo(self):
        cier = self.write_source(
            "cier-external.csv",
            [
                "2026-01-01,CIER,tw_manufacturing_pmi,49,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
                "2026-02-01,CIER,tw_manufacturing_pmi,50,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
            ],
        )
        ndc = self.write_source(
            "ndc-external.csv",
            [
                "2026-01-01,NDC,tw_ndc_leading_index,100,index,2026-09-21,https://www.ndc.gov.tw/en/",
                "2026-02-01,NDC,tw_ndc_leading_index,101,index,2026-09-21,https://www.ndc.gov.tw/en/",
            ],
        )
        with tempfile.TemporaryDirectory() as external_temp:
            external_out = Path(external_temp) / "out"
            report = self.module.refresh_taiwan_macro_files(
                [cier, ndc],
                external_out,
            )

            self.assertTrue((external_out / "tw_manufacturing_pmi.json").exists())
            self.assertTrue((external_out / "tw_ndc_leading_index.json").exists())
            self.assertTrue((external_out / "taiwan-macro-regime.json").exists())
            self.assertTrue((external_out / "taiwan-macro-audit.json").exists())
            self.assertEqual(len(report), 2)
            self.assertTrue(all(Path(item["path"]).is_absolute() for item in report))

    def test_refresh_cli_supports_external_output_dir_without_partial_path_failure(self):
        cier = self.write_source(
            "cier-external-cli.csv",
            [
                "2026-01-01,CIER,tw_manufacturing_pmi,49,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
                "2026-02-01,CIER,tw_manufacturing_pmi,50,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
            ],
        )
        ndc = self.write_source(
            "ndc-external-cli.csv",
            [
                "2026-01-01,NDC,tw_ndc_leading_index,100,index,2026-09-21,https://www.ndc.gov.tw/en/",
                "2026-02-01,NDC,tw_ndc_leading_index,101,index,2026-09-21,https://www.ndc.gov.tw/en/",
            ],
        )
        with tempfile.TemporaryDirectory() as external_temp:
            external_out = Path(external_temp) / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "refresh_data.py"),
                    "--taiwan-macro-file",
                    str(cier),
                    "--taiwan-macro-file",
                    str(ndc),
                    "--output-dir",
                    str(external_out),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((external_out / "tw_manufacturing_pmi.json").exists())
            self.assertTrue((external_out / "tw_ndc_leading_index.json").exists())
            report = json.loads(
                (external_out / "refresh-report.json").read_text(encoding="utf-8")
            )
            macro_results = [
                item for item in report["results"]
                if item.get("metric") in {
                    "tw_manufacturing_pmi",
                    "tw_ndc_leading_index",
                }
            ]
            self.assertEqual(len(macro_results), 2)
            self.assertTrue(
                all(Path(item["path"]).is_absolute() for item in macro_results)
            )

    def test_partial_followup_fails_before_overwriting_previous_outputs(self):
        cier = self.write_source(
            "cier.csv",
            [
                "2026-01-01,CIER,tw_manufacturing_pmi,49,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
                "2026-02-01,CIER,tw_manufacturing_pmi,50,index,2026-09-21,https://www.cier.edu.tw/pmi-trend/",
            ],
        )
        ndc = self.write_source(
            "ndc.csv",
            [
                "2026-01-01,NDC,tw_ndc_leading_index,100,index,2026-09-21,https://www.ndc.gov.tw/en/",
                "2026-02-01,NDC,tw_ndc_leading_index,101,index,2026-09-21,https://www.ndc.gov.tw/en/",
            ],
        )
        self.module.refresh_taiwan_macro_files([cier, ndc], self.out)
        ndc_before = (self.out / "tw_ndc_leading_index.json").read_bytes()
        audit_before = (self.out / "taiwan-macro-audit.json").read_bytes()

        with self.assertRaisesRegex(ValueError, "would drop existing series"):
            self.module.refresh_taiwan_macro_files([cier], self.out)

        self.assertEqual(
            (self.out / "tw_ndc_leading_index.json").read_bytes(),
            ndc_before,
        )
        self.assertEqual(
            (self.out / "taiwan-macro-audit.json").read_bytes(),
            audit_before,
        )


class CleanOutputTests(unittest.TestCase):
    def setUp(self):
        self.module = load_refresh_module()
        self.module.WRITTEN_ARTIFACTS.clear()
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.out = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def seed(self, name, payload):
        path = self.out / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_stale_restricted_series_is_removed_and_uncatalogued(self):
        # Exactly the #56 failure: an earlier --public run left sp500_index
        # behind, a later allowlist did not select it, and the catalog picked
        # it up again anyway.
        self.seed("sp500_index.json", metric_artifact("sp500_index"))
        kept = self.out / "nfci.json"
        self.module.atomic_json(kept, metric_artifact("nfci"))

        catalog_before = self.module.build_catalog(self.out)
        self.assertIn(
            "sp500_index",
            [entry["id"] for entry in catalog_before["metrics"]],
            "precondition: the stale artifact is catalogued without pruning",
        )

        removed = self.module.prune_unwritten_artifacts(
            self.out,
            preserved_metric_ids=set(),
        )

        self.assertEqual(removed, ["sp500_index.json"])
        self.assertFalse((self.out / "sp500_index.json").exists())
        self.assertTrue(kept.exists())

        catalog_after = self.module.build_catalog(self.out)
        self.assertEqual(
            [entry["id"] for entry in catalog_after["metrics"]],
            ["nfci"],
        )

    def test_other_unselected_families_are_removed_too(self):
        # Not just sp500_index: any optional family from an earlier run.
        for name in [
            "sp500_above_50dma_pct.json",
            "nyse_high_low.json",
            "tw_manufacturing_pmi.json",
            "ma-breadth-event-study.json",
            "taiwan-macro-regime.json",
        ]:
            self.seed(name, metric_artifact(Path(name).stem))
        self.module.atomic_json(self.out / "vix.json", metric_artifact("vix"))

        removed = self.module.prune_unwritten_artifacts(
            self.out,
            preserved_metric_ids=set(),
        )

        self.assertNotIn("vix.json", removed)
        self.assertEqual(len(removed), 5)
        self.assertEqual(
            sorted(p.name for p in self.out.glob("*.json")),
            ["vix.json"],
        )

    def test_an_artifact_preserved_by_a_failed_source_survives(self):
        # A source that errored and kept its previous snapshot must not have it
        # deleted underneath it; that would change the documented stale/error
        # semantics rather than just tightening the release set.
        self.seed("vix.json", metric_artifact("vix"))
        self.module.atomic_json(self.out / "nfci.json", metric_artifact("nfci"))

        removed = self.module.prune_unwritten_artifacts(
            self.out,
            preserved_metric_ids={"vix"},
        )

        self.assertEqual(removed, [])
        self.assertTrue((self.out / "vix.json").exists())

    def test_prune_is_a_no_op_when_every_artifact_was_written(self):
        for metric_id in ["nfci", "vix", "tw_taiex"]:
            self.module.atomic_json(
                self.out / f"{metric_id}.json",
                metric_artifact(metric_id),
            )

        self.assertEqual(
            self.module.prune_unwritten_artifacts(
                self.out,
                preserved_metric_ids=set(),
            ),
            [],
        )
        self.assertEqual(len(list(self.out.glob("*.json"))), 3)

    def test_backfilled_history_merged_by_this_run_is_kept(self):
        # scripts/bootstrap_taiwan_taiex.py writes tw_taiex* before the refresh
        # runs. --twse-current merges into those files, so they are rewritten
        # by this run and must survive the prune.
        backfilled = self.seed("tw_taiex.json", metric_artifact("tw_taiex"))
        self.module.atomic_json(backfilled, metric_artifact("tw_taiex", value=2.0))

        self.assertEqual(
            self.module.prune_unwritten_artifacts(
                self.out,
                preserved_metric_ids=set(),
            ),
            [],
        )
        self.assertTrue(backfilled.exists())


if __name__ == "__main__":
    unittest.main()
