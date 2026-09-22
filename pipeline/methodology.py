from __future__ import annotations

from math import isfinite
from statistics import median
from typing import Iterable


# Methodology transforms report their own status vocabulary. The canonical
# observation contract uses a different one, so derived metrics must translate
# before they are written into a metric artifact.
TRANSFORM_TO_OBSERVATION_STATUS = {
    "ok": "observed",
    "missing": "missing",
    "insufficient_data": "insufficient_data",
}


def observation_status(transform_status: str) -> str:
    try:
        return TRANSFORM_TO_OBSERVATION_STATUS[transform_status]
    except KeyError as exc:
        raise ValueError(
            f"unknown transform status {transform_status!r}"
        ) from exc


def to_observations(transform_rows: list[dict]) -> list[dict]:
    """Convert transform output rows into canonical contract observations."""
    return [
        {
            "date": row["date"],
            "value": row.get("value"),
            "status": observation_status(row["status"]),
        }
        for row in transform_rows
    ]


def _values(values: Iterable[float | int | None]) -> list[float]:
    out = []
    for value in values:
        if value is None:
            continue
        f = float(value)
        if isfinite(f):
            out.append(f)
    return out


def percentile_rank(value: float | int | None, baseline: Iterable[float | int | None]) -> float | None:
    """
    Mid-rank percentile against the supplied baseline.
    The caller controls point-in-time safety by ensuring baseline contains
    only observations available before the evaluated observation.
    """
    if value is None:
        return None
    xs = _values(baseline)
    if not xs:
        return None
    v = float(value)
    less = sum(x < v for x in xs)
    equal = sum(x == v for x in xs)
    return 100.0 * (less + 0.5 * equal) / len(xs)


def robust_zscore(value: float | int | None, baseline: Iterable[float | int | None]) -> float | None:
    """
    Robust z-score using median and MAD:
    0.67448975 * (x - median) / MAD.
    """
    if value is None:
        return None
    xs = _values(baseline)
    if not xs:
        return None
    med = median(xs)
    deviations = [abs(x - med) for x in xs]
    mad = median(deviations)
    if mad == 0:
        return None
    return 0.67448975 * (float(value) - med) / mad


def point_in_time_percentiles(
    observations: list[dict],
    *,
    window_observations: int | None = None,
    min_observations: int = 20,
) -> list[dict]:
    """
    Computes a strict-past percentile for each observation.
    Observation i is scored only against observations before i.
    """
    history: list[float] = []
    out: list[dict] = []
    for obs in observations:
        value = obs.get("value")
        baseline = history[-window_observations:] if window_observations else history[:]
        if value is None:
            pct = None
            status = "missing"
        elif len(baseline) < min_observations:
            pct = None
            status = "insufficient_data"
        else:
            pct = percentile_rank(value, baseline)
            status = "ok"
        out.append({"date": obs["date"], "value": value, "percentile": pct, "status": status})
        if value is not None:
            history.append(float(value))
    return out


def point_in_time_robust_zscores(
    observations: list[dict],
    *,
    window_observations: int | None = None,
    min_observations: int = 20,
) -> list[dict]:
    history: list[float] = []
    out: list[dict] = []
    for obs in observations:
        value = obs.get("value")
        baseline = history[-window_observations:] if window_observations else history[:]
        if value is None:
            z = None
            status = "missing"
        elif len(baseline) < min_observations:
            z = None
            status = "insufficient_data"
        else:
            z = robust_zscore(value, baseline)
            status = "ok" if z is not None else "insufficient_data"
        out.append({"date": obs["date"], "value": value, "robust_z": z, "status": status})
        if value is not None:
            history.append(float(value))
    return out


def period_pct_change(observations: list[dict], periods: int) -> list[dict]:
    if periods < 1:
        raise ValueError("periods must be >= 1")
    out: list[dict] = []
    values = [obs.get("value") for obs in observations]
    for i, obs in enumerate(observations):
        value = obs.get("value")
        change = None
        status = "insufficient_data"
        if i >= periods and value is not None and values[i - periods] not in (None, 0):
            change = (float(value) / float(values[i - periods]) - 1.0) * 100.0
            status = "ok"
        elif value is None:
            status = "missing"
        out.append({"date": obs["date"], "value": change, "status": status})
    return out


def normalize_event_window(
    observations: list[dict],
    anchor_date: str,
    *,
    pre_observations: int,
    post_observations: int,
) -> list[dict]:
    """
    Indexes the anchor observation to 100 and returns observation-index offsets.
    The anchor must be an exact observation date. Future observations may appear
    after T=0 because this function is for retrospective event-path comparison;
    the baseline value itself is the anchor observation only.
    """
    index = next((i for i, obs in enumerate(observations) if obs["date"] == anchor_date), None)
    if index is None:
        raise ValueError(f"anchor date {anchor_date} not found")
    anchor = observations[index].get("value")
    if anchor in (None, 0):
        raise ValueError("anchor observation must be non-zero and non-missing")

    start = max(0, index - pre_observations)
    end = min(len(observations), index + post_observations + 1)
    out = []
    for i in range(start, end):
        value = observations[i].get("value")
        out.append({
            "date": observations[i]["date"],
            "offset": i - index,
            "index_100": None if value is None else float(value) / float(anchor) * 100.0,
        })
    return out
