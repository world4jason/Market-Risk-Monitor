import unittest

from pipeline.ma_breadth_study import build_event_study


def metric(metric_id, values, *, point_in_time=True, scope="S&P 500"):
    return {
        "metric": {"id": metric_id},
        "source": {
            "provider": "fixture",
            "market_scope": scope,
            "membership_mode": "point_in_time" if point_in_time else "current_constituents_retroactive",
            "point_in_time_membership": point_in_time,
        },
        "coverage": {
            "history_start": values[0][0],
            "history_end": values[-1][0],
        },
        "observations": [
            {"date": date, "value": value, "status": "observed"}
            for date, value in values
        ],
    }


class MovingAverageBreadthStudyTests(unittest.TestCase):
    def setUp(self):
        # business-day labels are not required for unit math; session index is what matters
        self.dates = [f"2025-01-{i:02d}" for i in range(1, 29)] + [
            f"2025-02-{i:02d}" for i in range(1, 29)
        ] + [f"2025-03-{i:02d}" for i in range(1, 29)] + [
            f"2025-04-{i:02d}" for i in range(1, 29)
        ] + [f"2025-05-{i:02d}" for i in range(1, 29)]
        self.dates = self.dates[:130]

        breadth_values = []
        for i, d in enumerate(self.dates):
            value = 40.0
            if i == 10:
                value = 24.0  # down-cross 25
            elif 11 <= i < 18:
                value = 20.0
            elif i == 18:
                value = 26.0  # up-cross 25
            elif i == 40:
                value = 14.0  # down-cross 15
            elif 41 <= i < 50:
                value = 12.0
            elif i == 50:
                value = 16.0  # up-cross 15
            breadth_values.append((d, value))

        prices = [(d, 100.0 + i) for i, d in enumerate(self.dates)]

        self.breadth = metric("sp500_above_50dma_pct", breadth_values)
        self.price = {
            "metric": {"id": "sp500_index"},
            "source": {"provider": "fixture"},
            "coverage": {
                "history_start": prices[0][0],
                "history_end": prices[-1][0],
            },
            "observations": [
                {"date": d, "value": v, "status": "observed"}
                for d, v in prices
            ],
        }
        self.config = {
            "event_study": {
                "metric": "sp500_above_50dma_pct",
                "thresholds": [25, 15],
                "directions": ["down", "up"],
                "cooldown_sessions": 20,
                "forward_sessions": {"1W": 5, "1M": 21},
                "local_low_window_sessions": 21,
            }
        }

    def test_event_crossings_are_not_consecutive_day_duplicates(self):
        result = build_event_study(self.breadth, self.price, self.config)
        self.assertEqual(result["status"], "ready")
        pairs = {(e["threshold"], e["direction"]) for e in result["events"]}
        self.assertIn((25.0, "down"), pairs)
        self.assertIn((25.0, "up"), pairs)
        self.assertIn((15.0, "down"), pairs)
        self.assertIn((15.0, "up"), pairs)
        self.assertEqual(len(result["events"]), 4)

    def test_non_point_in_time_membership_blocks_canonical_study(self):
        blocked = metric(
            "sp500_above_50dma_pct",
            [(d, v["value"]) for d, v in zip(
                self.dates,
                self.breadth["observations"],
            )],
            point_in_time=False,
        )
        result = build_event_study(blocked, self.price, self.config)
        self.assertEqual(result["status"], "blocked_non_point_in_time")
        self.assertEqual(result["events"], [])

    def test_forward_return_and_unconditional_comparison_exist(self):
        result = build_event_study(self.breadth, self.price, self.config)
        down25 = [
            s for s in result["summaries"]
            if s["threshold"] == 25 and s["direction"] == "down" and s["horizon"] == "1W"
        ][0]
        self.assertEqual(down25["sample_count"], 1)
        self.assertIsNotNone(down25["median_return_pct"])
        self.assertIsNotNone(down25["unconditional_median_return_pct"])


if __name__ == "__main__":
    unittest.main()
