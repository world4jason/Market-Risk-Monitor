from __future__ import annotations

import copy
import json
import unittest
from datetime import datetime
from pathlib import Path

from pipeline.provenance import (
    build_provenance,
    content_digest,
    metric_input,
    records_input,
)
from pipeline.signals import build_signal_snapshot
from pipeline.validate import (
    ValidationError,
    validate_derived_provenance,
    validate_ma_breadth_study,
    validate_rate_regime,
    validate_signal_snapshot,
    validate_taiwan_macro_regime,
)


class ProvenanceTests(unittest.TestCase):
    def test_digest_is_canonical_and_order_independent(self) -> None:
        left = {"b": 2, "a": {"y": 2, "x": 1}}
        right = {"a": {"x": 1, "y": 2}, "b": 2}
        self.assertEqual(content_digest(left), content_digest(right))

    def test_config_change_is_distinguishable_from_input_change(self) -> None:
        base_input = records_input(
            "fixture",
            [{"date": "2026-01-01", "value": 1}],
            as_of="2026-01-01",
            snapshot_at="2026-01-02T00:00:00Z",
        )
        base = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"threshold": 1},
            inputs=[base_input],
        )
        changed_config = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"threshold": 2},
            inputs=[base_input],
        )
        changed_input = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"threshold": 1},
            inputs=[
                records_input(
                    "fixture",
                    [{"date": "2026-01-01", "value": 2}],
                    as_of="2026-01-01",
                    snapshot_at="2026-01-02T00:00:00Z",
                )
            ],
        )

        self.assertNotEqual(
            base["config"]["content_digest"],
            changed_config["config"]["content_digest"],
        )
        self.assertEqual(
            base["inputs"][0]["content_digest"],
            changed_config["inputs"][0]["content_digest"],
        )
        self.assertEqual(
            base["config"]["content_digest"],
            changed_input["config"]["content_digest"],
        )
        self.assertNotEqual(
            base["inputs"][0]["content_digest"],
            changed_input["inputs"][0]["content_digest"],
        )

    def test_mixed_timezone_offsets_normalize_and_order_by_instant(self) -> None:
        provenance = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[
                {
                    "id": "earlier",
                    "as_of": "2026-01-01",
                    "snapshot_at": "2026-01-01T09:00:00+08:00",
                    "content_digest": "sha256:" + "a" * 64,
                },
                {
                    "id": "later",
                    "as_of": "2026-01-01",
                    "snapshot_at": "2026-01-01T02:00:00Z",
                    "content_digest": "sha256:" + "b" * 64,
                },
            ],
        )

        self.assertEqual(
            provenance["generated_at"],
            "2026-01-01T02:00:00Z",
        )
        snapshots = {
            item["id"]: item["snapshot_at"]
            for item in provenance["inputs"]
        }
        self.assertEqual(
            snapshots["earlier"],
            "2026-01-01T01:00:00Z",
        )
        self.assertEqual(
            snapshots["later"],
            "2026-01-01T02:00:00Z",
        )

    def test_equivalent_snapshot_offsets_produce_same_manifest_timestamp(self) -> None:
        base = {
            "id": "fixture",
            "as_of": "2026-01-01",
            "content_digest": "sha256:" + "c" * 64,
        }
        left = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[
                {
                    **base,
                    "snapshot_at": "2026-01-01T09:00:00+08:00",
                }
            ],
        )
        right = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[
                {
                    **base,
                    "snapshot_at": "2026-01-01T01:00:00Z",
                }
            ],
        )

        self.assertEqual(left, right)

    def test_required_inputs_can_record_missing_artifacts(self) -> None:
        provenance = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[],
            required_input_ids=["missing_metric"],
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(
            provenance["required_inputs"],
            ["missing_metric"],
        )
        self.assertEqual(provenance["inputs"], [])
        validate_derived_provenance(
            provenance,
            context="fixture.provenance",
        )

    def test_optional_consumed_input_can_be_outside_required_set(self) -> None:
        provenance = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[
                records_input(
                    "optional_context",
                    [{"date": "2026-01-01", "value": 1}],
                    as_of="2026-01-01",
                    snapshot_at="2026-01-02T00:00:00Z",
                )
            ],
            required_input_ids=["missing_required"],
        )

        self.assertEqual(
            provenance["required_inputs"],
            ["missing_required"],
        )
        self.assertEqual(
            [item["id"] for item in provenance["inputs"]],
            ["optional_context"],
        )
        validate_derived_provenance(
            provenance,
            context="fixture.provenance",
        )

    def test_builder_parameters_change_the_manifest(self) -> None:
        base_input = records_input(
            "fixture",
            [{"date": "2026-01-01", "value": 1}],
            as_of="2026-01-01",
            snapshot_at=None,
        )
        first = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[base_input],
            parameters={"name": "A"},
        )
        second = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[base_input],
            parameters={"name": "B"},
        )
        self.assertNotEqual(first, second)
        validate_derived_provenance(first, context="fixture.provenance")

    def test_validator_rejects_incomplete_provenance(self) -> None:
        provenance = build_provenance(
            methodology_id="fixture-method",
            methodology_version="v1",
            config_id="fixture-config",
            config={"x": 1},
            inputs=[
                records_input(
                    "fixture",
                    [{"date": "2026-01-01", "value": 1}],
                    as_of="2026-01-01",
                    snapshot_at="2026-01-02T00:00:00Z",
                )
            ],
        )
        broken = copy.deepcopy(provenance)
        del broken["config"]["content_digest"]
        with self.assertRaises(ValidationError):
            validate_derived_provenance(
                broken,
                context="fixture.provenance",
            )

    def test_signals_rebuild_is_deterministic_from_same_snapshot(self) -> None:
        metric = {
            "metric": {"id": "x", "frequency": "monthly"},
            "source": {"availability_basis": "observation_date"},
            "freshness": {"state": "fresh"},
            "latest": {
                "as_of": "2026-02-28",
                "fetched_at": "2026-03-01T12:00:00Z",
                "value": 2.0,
            },
            "observations": [
                {
                    "date": "2026-01-31",
                    "value": 1.0,
                    "status": "observed",
                },
                {
                    "date": "2026-02-28",
                    "value": 2.0,
                    "status": "observed",
                },
            ],
        }
        config = {
            "schema_version": "1.0.0",
            "history_start": "2026-01-31",
            "conditions": [
                {
                    "id": "x_high",
                    "name": "X high",
                    "description": "",
                    "rules": {
                        "type": "latest_above",
                        "metric": "x",
                        "threshold": 0,
                    },
                }
            ],
        }

        first = build_signal_snapshot({"x": metric}, config)
        second = build_signal_snapshot(
            {"x": copy.deepcopy(metric)},
            copy.deepcopy(config),
        )

        self.assertEqual(first, second)
        self.assertEqual(
            first["generated_at"],
            "2026-03-01T12:00:00Z",
        )
        self.assertEqual(
            first["provenance"]["generated_at"],
            first["generated_at"],
        )


    def test_unrelated_metric_does_not_change_signal_evaluation_time(self) -> None:
        referenced = {
            "metric": {"id": "x", "frequency": "monthly"},
            "source": {"availability_basis": "observation_date"},
            "freshness": {"state": "fresh"},
            "latest": {
                "as_of": "2026-02-28",
                "fetched_at": "2026-03-01T12:00:00Z",
                "value": 2.0,
            },
            "observations": [
                {
                    "date": "2026-01-31",
                    "value": 1.0,
                    "status": "observed",
                },
                {
                    "date": "2026-02-28",
                    "value": 2.0,
                    "status": "observed",
                },
            ],
        }
        unrelated = copy.deepcopy(referenced)
        unrelated["metric"]["id"] = "unrelated"
        unrelated["latest"]["as_of"] = "2030-01-31"
        unrelated["latest"]["fetched_at"] = "2030-02-01T00:00:00Z"
        unrelated["observations"] = [
            {
                "date": "2030-01-31",
                "value": 99.0,
                "status": "observed",
            }
        ]
        config = {
            "schema_version": "1.0.0",
            "history_start": "2026-01-31",
            "conditions": [
                {
                    "id": "x_high",
                    "name": "X high",
                    "description": "",
                    "rules": {
                        "type": "latest_above",
                        "metric": "x",
                        "threshold": 0,
                    },
                }
            ],
        }

        expected = build_signal_snapshot({"x": referenced}, config)
        with_unrelated = build_signal_snapshot(
            {"x": referenced, "unrelated": unrelated},
            config,
        )

        self.assertEqual(expected, with_unrelated)
        self.assertEqual(
            with_unrelated["generated_at"],
            "2026-03-01T12:00:00Z",
        )
        self.assertEqual(
            [item["id"] for item in with_unrelated["provenance"]["inputs"]],
            ["x"],
        )

    def test_signals_choose_latest_fractional_snapshot_instant(self) -> None:
        def metric(metric_id, fetched_at, value):
            return {
                "metric": {"id": metric_id, "frequency": "monthly"},
                "source": {"availability_basis": "observation_date"},
                "freshness": {"state": "fresh"},
                "latest": {
                    "as_of": "2026-02-28",
                    "fetched_at": fetched_at,
                    "value": value,
                },
                "observations": [
                    {
                        "date": "2026-02-28",
                        "value": value,
                        "status": "observed",
                    }
                ],
            }

        config = {
            "schema_version": "1.0.0",
            "history_start": "2026-02-28",
            "conditions": [
                {
                    "id": "x",
                    "name": "X",
                    "rules": {
                        "type": "latest_above",
                        "metric": "x",
                        "threshold": 0,
                    },
                },
                {
                    "id": "y",
                    "name": "Y",
                    "rules": {
                        "type": "latest_above",
                        "metric": "y",
                        "threshold": 0,
                    },
                },
            ],
        }
        snapshot = build_signal_snapshot(
            {
                "x": metric("x", "2026-03-01T12:00:00Z", 1),
                "y": metric("y", "2026-03-01T12:00:00.500000Z", 2),
            },
            config,
        )

        self.assertEqual(
            snapshot["generated_at"],
            "2026-03-01T12:00:00.500000Z",
        )

    def test_explicit_signal_evaluation_time_is_normalized_before_date_semantics(self) -> None:
        metric = {
            "metric": {"id": "x", "frequency": "daily"},
            "source": {"availability_basis": "observation_date"},
            "freshness": {"state": "fresh"},
            "latest": {
                "as_of": "2026-03-01",
                "fetched_at": "2026-03-01T02:00:00Z",
                "value": 2.0,
            },
            "observations": [
                {"date": "2026-02-28", "value": 1.0, "status": "observed"},
                {"date": "2026-03-01", "value": 2.0, "status": "observed"},
            ],
        }
        config = {
            "schema_version": "1.0.0",
            "history_start": "2026-02-28",
            "conditions": [
                {
                    "id": "x_high",
                    "name": "X high",
                    "description": "",
                    "rules": {
                        "type": "latest_above",
                        "metric": "x",
                        "threshold": 0,
                    },
                }
            ],
        }
        plus_eight = datetime.fromisoformat("2026-03-01T00:30:00+08:00")
        utc = datetime.fromisoformat("2026-02-28T16:30:00+00:00")

        left = build_signal_snapshot(
            {"x": copy.deepcopy(metric)},
            copy.deepcopy(config),
            evaluated_at=plus_eight,
        )
        right = build_signal_snapshot(
            {"x": copy.deepcopy(metric)},
            copy.deepcopy(config),
            evaluated_at=utc,
        )

        self.assertEqual(left, right)
        self.assertEqual(left["generated_at"], "2026-02-28T16:30:00Z")
        self.assertEqual(left["current"]["as_of"], "2026-02-28")
        leaf = left["current"]["conditions"][0]["rules"]
        self.assertEqual(leaf["as_of"], "2026-02-28")

    def test_signals_all_missing_inputs_is_still_deterministic(self) -> None:
        config = {
            "schema_version": "1.0.0",
            "history_start": "2026-01-31",
            "conditions": [
                {
                    "id": "missing",
                    "name": "Missing",
                    "description": "",
                    "rules": {
                        "type": "latest_above",
                        "metric": "not_published",
                        "threshold": 0,
                    },
                }
            ],
        }

        first = build_signal_snapshot({}, config)
        second = build_signal_snapshot({}, copy.deepcopy(config))

        self.assertEqual(first, second)
        self.assertEqual(
            first["generated_at"],
            "1970-01-01T00:00:00Z",
        )
        self.assertEqual(
            first["provenance"]["required_inputs"],
            ["not_published"],
        )
        self.assertEqual(first["provenance"]["inputs"], [])

    def test_signal_validator_rejects_coercible_non_numeric_leaf_values(self) -> None:
        root = Path(__file__).resolve().parents[1] / "data" / "generated"
        payload = json.loads(
            (root / "signals.json").read_text(encoding="utf-8")
        )
        broken = copy.deepcopy(payload)
        leaf = broken["current"]["conditions"][0]["rules"]["children"][0]
        leaf["value"] = ""
        with self.assertRaisesRegex(ValidationError, "rule value must be"):
            validate_signal_snapshot(broken)

        broken = copy.deepcopy(payload)
        leaf = broken["current"]["conditions"][0]["rules"]["children"][1]
        leaf["periods"] = "3"
        with self.assertRaisesRegex(ValidationError, "periods must be"):
            validate_signal_snapshot(broken)

    def test_checked_in_derived_artifacts_have_valid_provenance(self) -> None:
        root = Path(__file__).resolve().parents[1] / "data" / "generated"
        required = {
            "signals.json": validate_signal_snapshot,
            "fed-rate-regime.json": validate_rate_regime,
            "taiwan-cbc-rate-regime.json": validate_rate_regime,
        }
        optional = {
            "taiwan-macro-regime.json": validate_taiwan_macro_regime,
            "ma-breadth-event-study.json": validate_ma_breadth_study,
        }

        for name, validator in {**required, **optional}.items():
            path = root / name
            if name in optional and not path.exists():
                continue
            self.assertTrue(path.exists(), name)
            payload = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(name=name):
                validator(payload)
                self.assertIn("provenance", payload)
                self.assertTrue(
                    payload["provenance"]["required_inputs"]
                )



if __name__ == "__main__":
    unittest.main()
