import unittest

from pipeline.methodology import (
    historical_analysis_eligibility,
    normalize_event_window,
    percentile_rank,
    period_pct_change,
    point_in_time_percentiles,
    robust_zscore,
)


class MethodologyTests(unittest.TestCase):
    def test_percentile_midrank(self):
        self.assertAlmostEqual(percentile_rank(3, [1,2,3,3,5]), 60.0)

    def test_point_in_time_excludes_current_and_future(self):
        obs = [
            {"date":"2000-01-01","value":10},
            {"date":"2000-02-01","value":20},
            {"date":"2000-03-01","value":30},
            {"date":"2000-04-01","value":40},
        ]
        out = point_in_time_percentiles(obs, min_observations=2)
        self.assertEqual(out[0]["status"], "insufficient_data")
        self.assertEqual(out[1]["status"], "insufficient_data")
        self.assertEqual(out[2]["status"], "ok")
        self.assertAlmostEqual(out[2]["percentile"], 100.0)
        self.assertAlmostEqual(
            out[2]["percentile"],
            point_in_time_percentiles(obs[:3], min_observations=2)[2]["percentile"],
        )

    def test_release_date_batch_is_not_counted_as_sequential_arrivals(self):
        dates = [
            "2025-09-01", "2025-10-01", "2025-11-01", "2025-12-01",
            "2026-01-01", "2026-02-01", "2026-03-01", "2026-04-01",
            "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-01",
            "2026-09-01",
        ]
        observations = [
            {
                "date": obs_date,
                "value": index + 1,
                "release_date": (
                    "2026-09-21" if index < 12 else "2026-10-21"
                ),
            }
            for index, obs_date in enumerate(dates)
        ]
        out = point_in_time_percentiles(
            observations,
            min_observations=2,
            availability_basis="release_date",
        )

        self.assertTrue(
            all(item["percentile"] is None for item in out[:12])
        )
        self.assertEqual(
            {item["availability_date"] for item in out[:12]},
            {"2026-09-21"},
        )
        self.assertIsNotNone(out[12]["percentile"])
        self.assertEqual(out[12]["availability_date"], "2026-10-21")

    def test_unknown_availability_is_not_pit_eligible(self):
        metric = {
            "source": {
                "availability_basis": "unknown",
                "point_in_time_membership": None,
            },
            "observations": [
                {"date": "2026-01-01", "value": 1.0},
            ],
        }
        eligible, reason = historical_analysis_eligibility(metric)
        self.assertFalse(eligible)
        self.assertIn("availability timing is unknown", reason)
        with self.assertRaisesRegex(ValueError, "known availability basis"):
            point_in_time_percentiles(
                metric["observations"],
                availability_basis="unknown",
            )

    def test_rolling_window(self):
        obs=[{"date":f"2000-0{i+1}-01","value":v} for i,v in enumerate([10,20,30,5])]
        out=point_in_time_percentiles(obs,window_observations=2,min_observations=2)
        self.assertAlmostEqual(out[3]["percentile"],0.0)

    def test_robust_z(self):
        z=robust_zscore(5,[1,2,3,4,5,6,7])
        self.assertIsNotNone(z)
        self.assertGreater(z,0)

    def test_robust_z_insufficient_when_mad_zero(self):
        self.assertIsNone(robust_zscore(2,[1,1,1,1]))

    def test_period_change(self):
        obs=[
            {"date":"2025-01-31","value":100},
            {"date":"2025-02-28","value":110},
            {"date":"2025-03-31","value":121},
        ]
        out=period_pct_change(obs,1)
        self.assertIsNone(out[0]["value"])
        self.assertAlmostEqual(out[1]["value"],10.0)
        self.assertAlmostEqual(out[2]["value"],10.0)

    def test_event_normalization(self):
        obs=[
            {"date":"2020-01-01","value":80},
            {"date":"2020-02-01","value":100},
            {"date":"2020-03-01","value":50},
        ]
        out=normalize_event_window(obs,"2020-02-01",pre_observations=1,post_observations=1)
        self.assertEqual([x["offset"] for x in out],[-1,0,1])
        self.assertAlmostEqual(out[0]["index_100"],80)
        self.assertAlmostEqual(out[1]["index_100"],100)
        self.assertAlmostEqual(out[2]["index_100"],50)


if __name__ == "__main__":
    unittest.main()
