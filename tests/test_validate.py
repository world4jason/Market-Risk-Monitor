import copy
import unittest

from pipeline.validate import ValidationError, validate_metric


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


if __name__ == "__main__":
    unittest.main()
