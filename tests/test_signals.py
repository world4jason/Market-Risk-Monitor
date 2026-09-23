import unittest
from datetime import datetime, timezone

from pipeline.signals import build_signal_snapshot, evaluate_rule


def metric(
    metric_id,
    values,
    *,
    frequency="monthly",
    freshness="fresh",
    lag=0,
    availability_basis="observation_date",
    release_dates=None,
):
    release_dates = release_dates or {}
    observations = []
    for obs_date, value in values:
        observation = {
            "date": obs_date,
            "value": value,
            "status": "observed",
        }
        if obs_date in release_dates:
            observation["release_date"] = release_dates[obs_date]
        observations.append(observation)
    return {
        "metric": {"id": metric_id, "frequency": frequency},
        "source": {"availability_basis": availability_basis},
        "coverage": {"expected_observation_lag_days": lag},
        "freshness": {"state": freshness},
        "observations": observations,
    }


class SignalTests(unittest.TestCase):
    def test_any_unknown_is_not_silently_inactive(self):
        metrics = {
            "x": metric("x", [("2026-01-31", 1.0)], freshness="stale"),
            "y": metric("y", [("2026-01-31", -1.0)]),
        }
        rule = {
            "type": "any",
            "children": [
                {"type": "latest_above", "metric": "x", "threshold": 0},
                {"type": "latest_above", "metric": "y", "threshold": 0},
            ],
        }
        result = evaluate_rule(
            rule,
            metrics,
            datetime(2026, 2, 1, tzinfo=timezone.utc).date(),
            respect_publication_lag=False,
            require_fresh_current=True,
        )
        self.assertEqual(result["status"], "unknown")

    def test_release_date_blocks_future_knowledge(self):
        metrics = {
            "x": metric(
                "x",
                [("2026-01-31", 5.0)],
                lag=25,
                availability_basis="release_date",
                release_dates={"2026-01-31": "2026-02-25"},
            )
        }
        rule = {"type": "latest_above", "metric": "x", "threshold": 0}

        too_early = evaluate_rule(
            rule,
            metrics,
            datetime(2026, 2, 10, tzinfo=timezone.utc).date(),
            respect_publication_lag=True,
            require_fresh_current=False,
        )
        available = evaluate_rule(
            rule,
            metrics,
            datetime(2026, 3, 1, tzinfo=timezone.utc).date(),
            respect_publication_lag=True,
            require_fresh_current=False,
        )

        self.assertEqual(too_early["status"], "unknown")
        self.assertEqual(available["status"], "active")

    def test_unknown_availability_is_not_recovered_from_expected_lag(self):
        metrics = {
            "x": metric(
                "x",
                [("2026-01-31", 5.0)],
                lag=1,
                availability_basis="unknown",
            )
        }
        rule = {"type": "latest_above", "metric": "x", "threshold": 0}
        result = evaluate_rule(
            rule,
            metrics,
            datetime(2026, 3, 1, tzinfo=timezone.utc).date(),
            respect_publication_lag=True,
            require_fresh_current=False,
        )
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["reason"], "no observation available")

    def test_same_release_batch_is_fully_available_after_release(self):
        values = [
            ("2026-01-31", 1.0),
            ("2026-02-28", 2.0),
            ("2026-03-31", 3.0),
            ("2026-04-30", 5.0),
        ]
        release_dates = {
            obs_date: "2026-09-21"
            for obs_date, _ in values
        }
        metrics = {
            "x": metric(
                "x",
                values,
                availability_basis="release_date",
                release_dates=release_dates,
            )
        }
        rule = {
            "type": "delta_periods_above",
            "metric": "x",
            "periods": 3,
            "threshold": 3,
        }

        before = evaluate_rule(
            rule,
            metrics,
            datetime(2026, 9, 20, tzinfo=timezone.utc).date(),
            respect_publication_lag=True,
            require_fresh_current=False,
        )
        after = evaluate_rule(
            rule,
            metrics,
            datetime(2026, 9, 21, tzinfo=timezone.utc).date(),
            respect_publication_lag=True,
            require_fresh_current=False,
        )

        self.assertEqual(before["status"], "unknown")
        self.assertEqual(after["status"], "active")
        self.assertEqual(after["as_of"], "2026-04-30")
        self.assertAlmostEqual(after["value"], 4.0)

    def test_same_release_siblings_do_not_seed_signal_percentile(self):
        first_batch = [
            ("2026-01-31", 1.0),
            ("2026-02-28", 2.0),
            ("2026-03-31", 3.0),
            ("2026-04-30", 4.0),
        ]
        release_dates = {
            obs_date: "2026-09-21"
            for obs_date, _ in first_batch
        }
        metrics = {
            "x": metric(
                "x",
                first_batch,
                availability_basis="release_date",
                release_dates=release_dates,
            )
        }
        rule = {
            "type": "percentile_above",
            "metric": "x",
            "threshold": 90,
            "min_observations": 2,
        }

        same_day = evaluate_rule(
            rule,
            metrics,
            datetime(2026, 9, 21, tzinfo=timezone.utc).date(),
            respect_publication_lag=True,
            require_fresh_current=False,
        )
        self.assertEqual(same_day["status"], "unknown")

        second_batch = first_batch + [("2026-05-31", 5.0)]
        second_releases = {
            **release_dates,
            "2026-05-31": "2026-10-21",
        }
        later = evaluate_rule(
            rule,
            {
                "x": metric(
                    "x",
                    second_batch,
                    availability_basis="release_date",
                    release_dates=second_releases,
                )
            },
            datetime(2026, 10, 21, tzinfo=timezone.utc).date(),
            respect_publication_lag=True,
            require_fresh_current=False,
        )
        self.assertEqual(later["status"], "active")
        self.assertAlmostEqual(later["value"], 100.0)

    def test_strict_past_percentile(self):
        values = [(f"2020-{month:02d}-01", float(month)) for month in range(1, 13)]
        metrics = {"x": metric("x", values)}
        rule = {
            "type": "percentile_above",
            "metric": "x",
            "threshold": 90,
            "min_observations": 5,
        }
        result = evaluate_rule(
            rule,
            metrics,
            datetime(2020, 12, 2, tzinfo=timezone.utc).date(),
            respect_publication_lag=False,
            require_fresh_current=False,
        )
        self.assertEqual(result["status"], "active")
        self.assertAlmostEqual(result["value"], 100.0)

    def test_build_snapshot_keeps_unknown_count(self):
        config = {
            "schema_version": "1.0.0",
            "history_start": "2026-01-31",
            "conditions": [
                {
                    "id": "a",
                    "name": "A",
                    "description": "",
                    "rules": {
                        "type": "latest_above",
                        "metric": "known",
                        "threshold": 0,
                    },
                },
                {
                    "id": "b",
                    "name": "B",
                    "description": "",
                    "rules": {
                        "type": "latest_above",
                        "metric": "missing",
                        "threshold": 0,
                    },
                },
            ],
        }
        metrics = {
            "known": metric(
                "known",
                [("2026-01-31", 1.0), ("2026-02-28", 2.0)],
            )
        }
        snapshot = build_signal_snapshot(
            metrics,
            config,
            datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
        summary = snapshot["current"]["summary"]
        self.assertEqual(summary["active"], 1)
        self.assertEqual(summary["unknown"], 1)
        self.assertEqual(summary["known"], 1)


if __name__ == "__main__":
    unittest.main()
