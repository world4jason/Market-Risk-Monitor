from __future__ import annotations

from math import isfinite

from .methodology import (
    historical_analysis_eligibility,
    point_in_time_percentiles,
)


PREVIEW_OBSERVATIONS = 30


def _default_rolling_window(metric: dict) -> int:
    frequency = metric.get("metric", {}).get("frequency")
    if frequency == "daily":
        return 2520
    if frequency == "weekly":
        return 520
    if frequency == "monthly":
        return 120
    return 40


def _baseline_config(metric: dict, kind: str) -> dict | None:
    return next(
        (item for item in metric.get("baselines", []) if item.get("type") == kind),
        None,
    )


def _percentile_rank(value: float, baseline: list[float]) -> float | None:
    if not baseline:
        return None
    less = sum(item < value for item in baseline)
    equal = sum(item == value for item in baseline)
    return 100.0 * (less + 0.5 * equal) / len(baseline)


def rolling_percentile(metric: dict) -> float | None:
    config = _baseline_config(metric, "rolling_percentile") or {}

    # A current retrospective rank can still be useful when exact historical
    # release timing is unavailable. Membership-sensitive backfills are the
    # exception: current-constituent history can distort the distribution itself.
    if metric.get("source", {}).get("point_in_time_membership") is False:
        return None

    observations = metric.get("observations", [])
    present = [
        index
        for index, item in enumerate(observations)
        if item.get("value") is not None
    ]
    if len(present) < 3:
        return None

    window = int(
        config.get("window_observations")
        or _default_rolling_window(metric)
    )
    min_observations = int(
        config.get("min_observations") or min(20, window)
    )

    eligible, _ = historical_analysis_eligibility(metric)
    if config.get("point_in_time") is True and eligible:
        basis = (
            metric.get("source", {}).get("availability_basis")
            or "unknown"
        )
        series = point_in_time_percentiles(
            observations,
            window_observations=window,
            min_observations=min_observations,
            availability_basis=basis,
        )
        return series[present[-1]].get("percentile")

    # Retrospective current context: rank today's latest reference-period value
    # against prior reference-period observations. This fallback also preserves
    # the pre-#48 presentation behavior for metrics that never declared a
    # rolling baseline. It is descriptive only, not a PIT/backtest guarantee.
    values = [
        float(item["value"])
        for item in observations
        if item.get("value") is not None
    ]
    baseline = values[
        max(0, len(values) - 1 - window) : -1
    ]
    if len(baseline) < min_observations:
        return None
    return _percentile_rank(values[-1], baseline)


def recent_change(metric: dict) -> dict | None:
    comparison = metric.get("metric", {}).get("comparison", "absolute")
    if comparison == "none":
        return None

    observations = [
        item
        for item in metric.get("observations", [])
        if item.get("value") is not None
    ]
    if len(observations) < 2:
        return None

    prior = float(observations[-2]["value"])
    current = float(observations[-1]["value"])
    if not (isfinite(prior) and isfinite(current)):
        return None

    delta = current - prior
    if comparison == "percent_change":
        if prior == 0:
            return None
        value = ((current / prior) - 1.0) * 100.0
    elif comparison == "basis_points":
        value = delta * 100.0
    elif comparison in {"percentage_points", "absolute"}:
        value = delta
    else:
        return None

    return {"value": value, "comparison": comparison}


def summarize_metric(metric: dict) -> dict:
    observations = [
        item
        for item in metric.get("observations", [])
        if item.get("value") is not None
    ]
    preview = [
        {
            "date": item.get("date"),
            "value": item.get("value"),
            "status": item.get("status"),
            **(
                {"release_date": item.get("release_date")}
                if "release_date" in item
                else {}
            ),
        }
        for item in observations[-PREVIEW_OBSERVATIONS:]
    ]

    return {
        "metric": dict(metric["metric"]),
        "source": dict(metric["source"]),
        "coverage": dict(metric["coverage"]),
        "freshness": dict(metric["freshness"]),
        "latest": dict(metric["latest"]),
        "baselines": [dict(item) for item in metric.get("baselines", [])],
        "summary": {
            "observation_count": len(observations),
            "rolling_percentile": rolling_percentile(metric),
            "recent_change": recent_change(metric),
            "preview_observations": preview,
        },
    }


def build_overview(metrics: dict[str, dict]) -> dict:
    rows = [
        summarize_metric(metric)
        for _, metric in sorted(metrics.items(), key=lambda item: item[0])
    ]

    fetched_at = [
        row.get("latest", {}).get("fetched_at")
        for row in rows
        if row.get("latest", {}).get("fetched_at")
    ]
    generated_at = max(fetched_at) if fetched_at else "1970-01-01T00:00:00Z"

    return {
        "schema_version": "1.0.0",
        "generated_at": generated_at,
        "metrics": rows,
    }
