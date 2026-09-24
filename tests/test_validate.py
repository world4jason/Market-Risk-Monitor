import copy
import json
import unittest
from pathlib import Path

from pipeline.validate import (
    ALLOWED_AVAILABILITY_BASES,
    ALLOWED_OBSERVATION_STATUSES,
    ValidationError,
    validate_metric,
)


BASE = {
    "schema_version": "1.0.0",
    "environment": "fixture",
    "metric": {
        "id": "qa_fixture",
        "name": "QA fixture",
        "pillar": "context",
        "units": "index",
        "frequency": "monthly",
        "polarity": "neutral",
    },
    "source": {
        "provider": "Fixture",
        "dataset": "Fixture",
        "series_id": None,
        "url": "https://example.com",
        "license_note": "fixture",
        "redistribution": "allowed",
        "availability_basis": "observation_date",
    },
    "coverage": {
        "history_start": "2026-01-31",
        "history_end": "2026-03-31",
        "timezone": "UTC",
        "expected_observation_lag_days": 0,
    },
    "freshness": {
        "state": "fresh",
        "max_age_days": 40,
        "age_days": 1,
        "evaluated_at": "2026-04-01T00:00:00Z",
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
        "as_of": "2026-03-31",
        "fetched_at": "2026-04-01T00:00:00Z",
        "value": 3.0,
        "revision_tag": None,
    },
    "observations": [
        {"date": "2026-01-31", "value": 1.0, "status": "observed"},
        {"date": "2026-02-28", "value": 2.0, "status": "observed"},
        {"date": "2026-03-31", "value": 3.0, "status": "observed"},
    ],
}


class ValidateTests(unittest.TestCase):
    def test_valid_fixture(self):
        validate_metric(copy.deepcopy(BASE))

    def test_duplicate_timestamp_rejected(self):
        payload = copy.deepcopy(BASE)
        payload["observations"][1]["date"] = "2026-01-31"
        with self.assertRaises(ValidationError):
            validate_metric(payload)

    def test_non_monotonic_timestamp_rejected(self):
        payload = copy.deepcopy(BASE)
        payload["observations"][0], payload["observations"][1] = (
            payload["observations"][1],
            payload["observations"][0],
        )
        payload["coverage"]["history_start"] = payload["observations"][0]["date"]
        with self.assertRaises(ValidationError):
            validate_metric(payload)

    def test_latest_value_mismatch_rejected(self):
        payload = copy.deepcopy(BASE)
        payload["latest"]["value"] = 99.0
        with self.assertRaises(ValidationError):
            validate_metric(payload)

    def test_freshness_states_are_distinct_and_valid(self):
        for state in ["fresh", "stale", "missing", "error", "insufficient_data"]:
            payload = copy.deepcopy(BASE)
            payload["freshness"]["state"] = state
            validate_metric(payload)

    def test_unknown_freshness_state_rejected(self):
        payload = copy.deepcopy(BASE)
        payload["freshness"]["state"] = "safe"
        with self.assertRaises(ValidationError):
            validate_metric(payload)

    def test_observation_statuses_match_the_canonical_contract(self):
        for status in ALLOWED_OBSERVATION_STATUSES:
            payload = copy.deepcopy(BASE)
            payload["observations"][0]["status"] = status
            validate_metric(payload)

    def test_unknown_observation_status_rejected(self):
        # "ok" is a methodology-transform status, not a contract status; a
        # derived metric must translate before it is written to an artifact.
        payload = copy.deepcopy(BASE)
        payload["observations"][0]["status"] = "ok"
        with self.assertRaises(ValidationError):
            validate_metric(payload)

    def test_release_date_basis_requires_release_date(self):
        payload = copy.deepcopy(BASE)
        payload["source"]["availability_basis"] = "release_date"
        with self.assertRaisesRegex(ValidationError, "release_date required"):
            validate_metric(payload)

        for observation in payload["observations"]:
            observation["release_date"] = "2026-04-01"
        validate_metric(payload)

    def test_release_date_cannot_precede_observation_date(self):
        payload = copy.deepcopy(BASE)
        payload["source"]["availability_basis"] = "release_date"
        for observation in payload["observations"]:
            observation["release_date"] = "2026-04-01"
        payload["observations"][0]["release_date"] = "2025-12-31"

        with self.assertRaisesRegex(
            ValidationError,
            "release_date cannot precede observation date",
        ):
            validate_metric(payload)

    def test_unknown_availability_cannot_claim_pit_baseline(self):
        payload = copy.deepcopy(BASE)
        payload["source"]["availability_basis"] = "unknown"
        payload["baselines"] = [
            {
                "id": "pit",
                "type": "rolling_percentile",
                "window_observations": 12,
                "min_observations": 2,
                "point_in_time": True,
                "notes": "fixture",
            }
        ]
        with self.assertRaisesRegex(
            ValidationError,
            "point-in-time baseline requires",
        ):
            validate_metric(payload)

        payload["baselines"][0]["point_in_time"] = False
        validate_metric(payload)

    def test_invalid_availability_basis_rejected(self):
        payload = copy.deepcopy(BASE)
        payload["source"]["availability_basis"] = "guessed"
        with self.assertRaisesRegex(ValidationError, "availability_basis"):
            validate_metric(payload)

    def test_observation_status_vocabulary_matches_json_schema(self):
        schema = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "schemas"
                / "metric-series.schema.json"
            ).read_text(encoding="utf-8")
        )
        schema_statuses = set(
            schema["properties"]["observations"]["items"]["properties"]["status"]["enum"]
        )
        self.assertEqual(schema_statuses, set(ALLOWED_OBSERVATION_STATUSES))
        schema_bases = set(
            schema["properties"]["source"]["properties"]["availability_basis"]["enum"]
        )
        self.assertEqual(schema_bases, set(ALLOWED_AVAILABILITY_BASES))
        self.assertIn(
            "release_date",
            schema["properties"]["observations"]["items"]["properties"],
        )


if __name__ == "__main__":
    unittest.main()
