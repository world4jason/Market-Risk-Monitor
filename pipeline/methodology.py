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

AVAILABILITY_BASES = {
    "observation_date",
    "release_date",
    "unknown",
}


def observation_availability_date(
    observation: dict,
    availability_basis: str,
) -> str | None:
    if availability_basis == "observation_date":
        return observation.get("date")
    if availability_basis == "release_date":
        return observation.get("release_date")
    if availability_basis == "unknown":
        return None
    raise ValueError(f"unknown availability_basis {availability_basis!r}")


def historical_analysis_eligibility(metric: dict) -> tuple[bool, str | None]:
    source = metric.get("source", {})
    if source.get("point_in_time_membership") is False:
        return False, "historical membership is not point-in-time"

    basis = source.get("availability_basis") or "unknown"
    if basis not in AVAILABILITY_BASES:
        return False, f"unknown availability basis {basis!r}"
    if basis == "unknown":
        return False, "observation availability timing is unknown"

    if basis == "release_date":
        missing = [
            obs.get("date")
            for obs in metric.get("observations", [])
            if obs.get("value") is not None and not obs.get("release_date")
        ]
        if missing:
            return False, "release-date availability is declared but release_date is missing"

    return True, None


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
    availability_basis: str = "observation_date",
) -> list[dict]:
    """
    Compute a strict-past percentile using observation availability, not merely
    reference-period order.

    Observations that become available on the same date are scored against the
    same prior baseline and are appended to history only after the whole release
    batch is scored. This prevents a first ingest containing many historical
    rows from masquerading as many independent point-in-time arrivals.
    """
    if availability_basis not in AVAILABILITY_BASES - {"unknown"}:
        raise ValueError("point-in-time percentile requires a known availability basis")

    history: list[float] = []
    out: list[dict | None] = [None] * len(observations)
    groups: dict[str, list[tuple[int, dict]]] = {}

    for index, obs in enumerate(observations):
        value = obs.get("value")
        if value is None:
            out[index] = {
                "date": obs["date"],
                "value": value,
                "percentile": None,
                "status": "missing",
                "availability_date": observation_availability_date(
                    obs, availability_basis
                ),
            }
            continue

        available = observation_availability_date(obs, availability_basis)
        if not available:
            raise ValueError(
                f"observation {obs.get('date')} has no availability date"
            )
        groups.setdefault(available, []).append((index, obs))

    for available in sorted(groups):
        baseline = (
            history[-window_observations:]
            if window_observations
            else history[:]
        )
        batch = groups[available]
        for index, obs in batch:
            value = obs.get("value")
            if len(baseline) < min_observations:
                pct = None
                status = "insufficient_data"
            else:
                pct = percentile_rank(value, baseline)
                status = "ok"
            out[index] = {
                "date": obs["date"],
                "value": value,
                "percentile": pct,
                "status": status,
                "availability_date": available,
            }

        history.extend(
            float(obs["value"])
            for _, obs in batch
            if obs.get("value") is not None
        )

    return [item for item in out if item is not None]


def point_in_time_robust_zscores(
    observations: list[dict],
    *,
    window_observations: int | None = None,
    min_observations: int = 20,
    availability_basis: str = "observation_date",
) -> list[dict]:
    if availability_basis not in AVAILABILITY_BASES - {"unknown"}:
        raise ValueError("point-in-time robust z-score requires a known availability basis")

    history: list[float] = []
    out: list[dict | None] = [None] * len(observations)
    groups: dict[str, list[tuple[int, dict]]] = {}

    for index, obs in enumerate(observations):
        value = obs.get("value")
        if value is None:
            out[index] = {
                "date": obs["date"],
                "value": value,
                "robust_z": None,
                "status": "missing",
                "availability_date": observation_availability_date(
                    obs, availability_basis
                ),
            }
            continue

        available = observation_availability_date(obs, availability_basis)
        if not available:
            raise ValueError(
                f"observation {obs.get('date')} has no availability date"
            )
        groups.setdefault(available, []).append((index, obs))

    for available in sorted(groups):
        baseline = (
            history[-window_observations:]
            if window_observations
            else history[:]
        )
        batch = groups[available]
        for index, obs in batch:
            value = obs.get("value")
            if len(baseline) < min_observations:
                z = None
                status = "insufficient_data"
            else:
                z = robust_zscore(value, baseline)
                status = "ok" if z is not None else "insufficient_data"
            out[index] = {
                "date": obs["date"],
                "value": value,
                "robust_z": z,
                "status": status,
                "availability_date": available,
            }

        history.extend(
            float(obs["value"])
            for _, obs in batch
            if obs.get("value") is not None
        )

    return [item for item in out if item is not None]


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
