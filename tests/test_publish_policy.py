import copy
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.publishing import (
    PublishingPolicyError,
    load_policy,
    metric_decisions,
    validate_public_release,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data" / "config" / "publishing.json"


def metric(metric_id, redistribution="unknown"):
    return {
        "metric": {"id": metric_id},
        "source": {"redistribution": redistribution},
        "observations": [{"date": "2026-01-01", "value": 1}],
    }


class PublishPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy(POLICY_PATH)

    def write(self, root, name, payload):
        path = Path(root) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_checked_in_public_release_passes(self):
        paths = sorted((ROOT / "data" / "generated").glob("*.json"))
        checked = validate_public_release(paths, self.policy)
        self.assertGreater(len(checked), 30)

    def test_unclassified_metric_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write(temp, "x.json", metric("brand_new_metric"))
            with self.assertRaisesRegex(PublishingPolicyError, "no publishing decision"):
                validate_public_release([path], self.policy)

    def test_local_only_metric_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write(temp, "sp500_index.json", metric("sp500_index", "restricted"))
            with self.assertRaisesRegex(PublishingPolicyError, "local_only"):
                validate_public_release([path], self.policy)

    def test_restricted_source_is_rejected_even_if_family_says_publish(self):
        with tempfile.TemporaryDirectory() as temp:
            path = self.write(temp, "vix.json", metric("vix", "restricted"))
            with self.assertRaisesRegex(PublishingPolicyError, "restricted source"):
                validate_public_release([path], self.policy)

    def test_special_artifact_cannot_smuggle_local_only_provenance(self):
        payload = {
            "schema_version": "1.0.0",
            "provenance": {
                "required_inputs": ["sp500_index"],
                "inputs": [{"id": "sp500_index"}],
            },
        }
        with tempfile.TemporaryDirectory() as temp:
            path = self.write(temp, "study.json", payload)
            with self.assertRaisesRegex(PublishingPolicyError, "local-only inputs"):
                validate_public_release([path], self.policy)

    def test_every_policy_metric_has_one_decision(self):
        decisions = metric_decisions(self.policy)
        self.assertEqual(decisions["sp500_index"]["decision"], "local_only")
        self.assertEqual(decisions["nfci"]["decision"], "publish")


if __name__ == "__main__":
    unittest.main()
