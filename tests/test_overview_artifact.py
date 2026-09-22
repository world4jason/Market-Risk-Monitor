from __future__ import annotations

import copy
import unittest

from pipeline.overview import build_overview, recent_change, rolling_percentile
from pipeline.validate import ValidationError, validate_overview


def metric_fixture(
    metric_id: str = "fixture",
    *,
    frequency: str = "monthly",
    comparison: str = "percent_change",
    polarity: str = "contextual",
    values: list[float] | None = None,
    point_in_time_membership: bool | None = None,
) -> dict:
    values = values or [float(i) for i in range(1, 41)]
    observations = [
        {
            "date": f"2023-{((i - 1) % 12) + 1:02d}-{min(((i - 1) // 12) + 1, 28):02d}",
            "value": value,
            "status": "observed",
        }
        for i, value in enumerate(values, start=1)
    ]
    # Keep the dates strictly increasing for the test fixture.
    observations = [
        {
            "date": f"2023-01-{i:02d}" if i <= 28 else f"2023-02-{i - 28:02d}",
            "value": value,
            "status": "observed",
        }
        for i, value in enumerate(values, start=1)
    ]
    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": metric_id,
            "name": metric_id,
            "description": "fixture",
            "pillar": "leverage",
            "units": "index",
            "frequency": frequency,
            "polarity": polarity,
            "comparison": comparison,
        },
        "source": {
            "provider": "fixture",
            "dataset": "fixture",
            "series_id": metric_id,
            "url": "https://example.com",
            "license_note": "fixture",
            "redistribution": "unknown",
            "point_in_time_membership": point_in_time_membership,
        },
        "coverage": {
            "history_start": observations[0]["date"],
            "history_end": observations[-1]["date"],
            "timezone": "UTC",
            "expected_observation_lag_days": 1,
        },
        "freshness": {
            "state": "fresh",
            "max_age_days": 60,
            "age_days": 1,
            "evaluated_at": "2026-09-22T00:00:00Z",
            "reason": None,
        },
        "lineage": {
            "kind": "raw",
            "inputs": [],
            "formula": None,
            "transform_version": "fixture-v1",
        },
        "baselines": [
            {
                "id": "rolling",
                "type": "rolling_percentile",
                "window_observations": 12,
                "min_observations": 6,
                "point_in_time": True,
                "notes": "fixture",
            }
        ],
        "latest": {
            "as_of": observations[-1]["date"],
            "fetched_at": "2026-09-22T10:00:00Z",
            "value": observations[-1]["value"],
            "revision_tag": None,
        },
        "observations": observations,
    }


class OverviewArtifactTests(unittest.TestCase):
    def test_summary_is_small_and_deterministic(self) -> None:
        metric = metric_fixture(values=[float(i) for i in range(1, 41)])
        first = build_overview({metric["metric"]["id"]: metric})
        second = build_overview({metric["metric"]["id"]: copy.deepcopy(metric)})

        self.assertEqual(first, second)
        self.assertEqual(first["generated_at"], "2026-09-22T10:00:00Z")
        self.assertEqual(len(first["metrics"]), 1)

        row = first["metrics"][0]
        self.assertNotIn("observations", row)
        self.assertEqual(row["summary"]["observation_count"], 40)
        self.assertEqual(len(row["summary"]["preview_observations"]), 30)
        self.assertEqual(
            row["summary"]["preview_observations"][-1]["value"],
            metric["latest"]["value"],
        )
        validate_overview(first)

    def test_summary_matches_full_metric_presentation_values(self) -> None:
        metric = metric_fixture(values=[float(i) for i in range(1, 41)])
        overview = build_overview({"fixture": metric})
        row = overview["metrics"][0]

        self.assertEqual(row["summary"]["recent_change"], recent_change(metric))
        self.assertEqual(
            row["summary"]["rolling_percentile"],
            rolling_percentile(metric),
        )

    def test_non_pit_membership_blocks_historical_percentile(self) -> None:
        metric = metric_fixture(
            metric_id="sp500_above_50dma_pct",
            values=[float(i) for i in range(1, 41)],
            point_in_time_membership=False,
        )
        self.assertIsNone(rolling_percentile(metric))
        overview = build_overview({metric["metric"]["id"]: metric})
        self.assertIsNone(overview["metrics"][0]["summary"]["rolling_percentile"])

    def test_checked_in_overview_is_materially_smaller_than_full_histories(self) -> None:
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        overview_path = root / "data" / "generated" / "overview.json"
        catalog = __import__("json").loads(
            (root / "data" / "generated" / "catalog.json").read_text(encoding="utf-8")
        )
        full_bytes = sum(
            (root / "data" / "generated" / item["path"].removeprefix("./")).stat().st_size
            for item in catalog["metrics"]
        )
        overview_bytes = overview_path.stat().st_size

        self.assertGreater(full_bytes, 0)
        self.assertLess(
            overview_bytes,
            full_bytes * 0.10,
            f"overview is {overview_bytes} bytes vs {full_bytes} bytes of full histories",
        )

    def test_validator_rejects_full_history_inside_overview(self) -> None:
        metric = metric_fixture()
        overview = build_overview({"fixture": metric})
        overview["metrics"][0]["observations"] = metric["observations"]

        with self.assertRaisesRegex(ValidationError, "full observations are forbidden"):
            validate_overview(overview)

    def test_validator_rejects_oversized_preview(self) -> None:
        metric = metric_fixture(values=[float(i) for i in range(1, 41)])
        overview = build_overview({"fixture": metric})
        overview["metrics"][0]["summary"]["preview_observations"] = (
            metric["observations"][-31:]
        )

        with self.assertRaisesRegex(ValidationError, "preview exceeds 30"):
            validate_overview(overview)


if __name__ == "__main__":
    unittest.main()
