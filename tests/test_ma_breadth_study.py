import copy
import unittest

from pipeline.ma_breadth_study import build_event_study
from pipeline.validate import validate_ma_breadth_study


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

        # One 25% episode that contains one deeper 15% episode. Levels between
        # the crossings stay inside the 15-25 band so that each intended event
        # is the only crossing of its own threshold at that point.
        breadth_values = []
        for i, d in enumerate(self.dates):
            value = 40.0
            if i == 10:
                value = 24.0  # down-cross 25
            elif 11 <= i < 40:
                value = 20.0
            elif i == 40:
                value = 14.0  # down-cross 15
            elif 41 <= i < 50:
                value = 12.0
            elif i == 50:
                value = 16.0  # up-cross 15
            elif 51 <= i < 71:
                value = 20.0
            elif i == 71:
                value = 26.0  # up-cross 25
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
        validate_ma_breadth_study(result)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(
            result,
            build_event_study(
                copy.deepcopy(self.breadth),
                copy.deepcopy(self.price),
                copy.deepcopy(self.config),
            ),
        )
        pairs = {(e["threshold"], e["direction"]) for e in result["events"]}
        self.assertIn((25.0, "down"), pairs)
        self.assertIn((25.0, "up"), pairs)
        self.assertIn((15.0, "down"), pairs)
        self.assertIn((15.0, "up"), pairs)
        self.assertEqual(len(result["events"]), 4)

    def test_daily_chop_around_threshold_is_deduplicated(self):
        # Breadth oscillates across 25 every single session for 30 sessions.
        # That is one choppy oversold stretch, not 30 independent signals.
        chop_values = []
        raw_crossings = 0
        previous = None
        for i, d in enumerate(self.dates):
            if 10 <= i < 40:
                value = 24.0 if i % 2 == 0 else 26.0
            else:
                value = 40.0
            if previous is not None and (
                (previous >= 25.0 > value) or (previous <= 25.0 < value)
            ):
                raw_crossings += 1
            previous = value
            chop_values.append((d, value))
        self.assertEqual(raw_crossings, 30)

        result = build_event_study(
            metric("sp500_above_50dma_pct", chop_values),
            self.price,
            self.config,
        )

        # cooldown_sessions=20, so the 30-session stretch yields two episodes,
        # each allowed one opposite-side recross.
        self.assertEqual(len(result["events"]), 4)
        indexes = [self.dates.index(event["date"]) for event in result["events"]]
        self.assertEqual(sorted(indexes), [10, 11, 30, 31])

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
