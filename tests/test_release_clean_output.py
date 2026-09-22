"""
Behavioural coverage for the release build's output semantics.

A source-code grep cannot show that an allowlist actually produces an exact
release set. These tests pre-seed artifacts an earlier run would have left
behind, drive the real prune path, and assert they are gone from both the
directory and the catalog.
"""
import importlib.util
import json
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


class CleanOutputTests(unittest.TestCase):
    def setUp(self):
        self.module = load_refresh_module()
        self.module.WRITTEN_ARTIFACTS.clear()
        self.tmp = tempfile.TemporaryDirectory()
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
