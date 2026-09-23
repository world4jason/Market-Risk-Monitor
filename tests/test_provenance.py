from __future__ import annotations

import copy
import json
import unittest
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
