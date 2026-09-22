from __future__ import annotations

from bisect import bisect_left
from datetime import date
from statistics import median


class MovingAverageBreadthStudyError(ValueError):
    pass


def _valid(metric: dict) -> list[dict]:
    return [
        {"date": obs["date"], "value": float(obs["value"])}
        for obs in metric.get("observations", [])
        if obs.get("value") is not None
    ]


def _threshold_events(
    observations: list[dict],
    threshold: float,
    cooldown_sessions: int,
) -> list[dict]:
    """
    Detect threshold crossings without counting every choppy day as a new episode.

    An episode is anchored on its opening crossing. Inside the cooldown window
    that follows the anchor, at most one opposite-side recross is accepted (it
    closes the episode); every further crossing in that window is ignored.
    Once the cooldown has elapsed, the next crossing opens a new episode.

    Anchoring the cooldown instead of chaining it off the previous event is what
    keeps a value oscillating around the threshold from emitting one event per
    session. Only past observations are used, so an event that exists at time T
    never depends on future data.
    """
    events = []
    anchor_index = None
    anchor_direction = None
    opposite_used = False

    for i in range(1, len(observations)):
        prev = observations[i - 1]["value"]
        cur = observations[i]["value"]
        direction = None
        if prev >= threshold and cur < threshold:
            direction = "down"
        elif prev <= threshold and cur > threshold:
            direction = "up"

        if direction is None:
            continue

        if anchor_index is None or i - anchor_index >= cooldown_sessions:
            anchor_index = i
            anchor_direction = direction
            opposite_used = False
        elif direction != anchor_direction and not opposite_used:
            opposite_used = True
        else:
            continue

        events.append({"index": i, "direction": direction})
    return events


def _align_price(price_obs: list[dict], event_date: str):
    dates = [obs["date"] for obs in price_obs]
    pos = bisect_left(dates, event_date)
    if pos >= len(price_obs):
        return None
    return pos


def _return(start: float, end: float) -> float:
    return 100.0 * (end / start - 1.0)


def _positive_hit_rate(values: list[float]) -> float | None:
    if not values:
        return None
    return 100.0 * sum(v > 0 for v in values) / len(values)


def _unconditional(price_obs: list[dict], sessions: int):
    values = []
    for i in range(0, len(price_obs) - sessions):
        start = price_obs[i]["value"]
        end = price_obs[i + sessions]["value"]
        if start:
            values.append(_return(start, end))
    return {
        "sample_count": len(values),
        "median_return_pct": median(values) if values else None,
        "positive_hit_rate_pct": _positive_hit_rate(values),
    }


def build_event_study(
    breadth_metric: dict,
    price_metric: dict,
    config: dict,
) -> dict:
    if breadth_metric.get("metric", {}).get("id") != config["event_study"]["metric"]:
        raise MovingAverageBreadthStudyError("breadth metric id does not match event-study config")

    if breadth_metric.get("source", {}).get("market_scope") != "S&P 500":
        raise MovingAverageBreadthStudyError("breadth metric must have S&P 500 scope")

    point_in_time = breadth_metric.get("source", {}).get("point_in_time_membership")
    breadth_obs = _valid(breadth_metric)
    price_obs = _valid(price_metric)

    result = {
        "schema_version": "1.0.0",
        "status": "ready" if point_in_time is True else "blocked_non_point_in_time",
        "breadth_metric": breadth_metric["metric"]["id"],
        "breadth_provider": breadth_metric["source"]["provider"],
        "membership_mode": breadth_metric["source"].get("membership_mode"),
        "point_in_time_membership": point_in_time,
        "breadth_coverage": {
            "start": breadth_metric["coverage"]["history_start"],
            "end": breadth_metric["coverage"]["history_end"],
        },
        "price_metric": price_metric["metric"]["id"],
        "price_provider": price_metric["source"]["provider"],
        "price_coverage": {
            "start": price_metric["coverage"]["history_start"],
            "end": price_metric["coverage"]["history_end"],
        },
        "cooldown_sessions": int(config["event_study"]["cooldown_sessions"]),
        "events": [],
        "summaries": [],
        "unconditional": {},
    }

    if point_in_time is not True:
        result["reason"] = (
            "Historical event study requires point-in-time S&P 500 membership "
            "or a provider breadth series documented as point-in-time."
        )
        return result

    forward_sessions = {
        label: int(sessions)
        for label, sessions in config["event_study"]["forward_sessions"].items()
    }
    local_low_window = int(config["event_study"]["local_low_window_sessions"])

    for label, sessions in forward_sessions.items():
        result["unconditional"][label] = _unconditional(price_obs, sessions)

    for threshold in config["event_study"]["thresholds"]:
        threshold = float(threshold)
        threshold_events = _threshold_events(
            breadth_obs,
            threshold,
            int(config["event_study"]["cooldown_sessions"]),
        )
        for direction in config["event_study"]["directions"]:
            crossing_indexes = [
                event["index"]
                for event in threshold_events
                if event["direction"] == direction
            ]
            event_rows = []

            for breadth_index in crossing_indexes:
                breadth_point = breadth_obs[breadth_index]
                price_index = _align_price(price_obs, breadth_point["date"])
                if price_index is None:
                    continue

                price_start_date = price_obs[price_index]["date"]
                date_gap = (
                    date.fromisoformat(price_start_date)
                    - date.fromisoformat(breadth_point["date"])
                ).days
                if date_gap > 3:
                    continue

                start_price = price_obs[price_index]["value"]
                event = {
                    "date": breadth_point["date"],
                    "breadth_value": breadth_point["value"],
                    "price_date": price_start_date,
                    "price": start_price,
                    "threshold": threshold,
                    "direction": direction,
                    "forward_returns_pct": {},
                    "max_adverse_excursion_pct": {},
                    "sessions_to_63d_low": None,
                }

                for label, sessions in forward_sessions.items():
                    end_index = price_index + sessions
                    if end_index >= len(price_obs):
                        event["forward_returns_pct"][label] = None
                        event["max_adverse_excursion_pct"][label] = None
                        continue

                    event["forward_returns_pct"][label] = _return(
                        start_price,
                        price_obs[end_index]["value"],
                    )
                    window = [
                        obs["value"]
                        for obs in price_obs[price_index : end_index + 1]
                    ]
                    event["max_adverse_excursion_pct"][label] = _return(
                        start_price,
                        min(window),
                    )

                low_end = min(price_index + local_low_window, len(price_obs) - 1)
                if low_end > price_index:
                    window = price_obs[price_index : low_end + 1]
                    low_relative = min(
                        range(len(window)),
                        key=lambda i: window[i]["value"],
                    )
                    event["sessions_to_63d_low"] = low_relative

                event_rows.append(event)
                result["events"].append(event)

            for label in forward_sessions:
                returns = [
                    event["forward_returns_pct"][label]
                    for event in event_rows
                    if event["forward_returns_pct"][label] is not None
                ]
                maes = [
                    event["max_adverse_excursion_pct"][label]
                    for event in event_rows
                    if event["max_adverse_excursion_pct"][label] is not None
                ]
                unconditional = result["unconditional"][label]
                result["summaries"].append(
                    {
                        "threshold": threshold,
                        "direction": direction,
                        "horizon": label,
                        "sample_count": len(returns),
                        "median_return_pct": median(returns) if returns else None,
                        "positive_hit_rate_pct": _positive_hit_rate(returns),
                        "median_max_adverse_excursion_pct": (
                            median(maes) if maes else None
                        ),
                        "unconditional_median_return_pct": unconditional[
                            "median_return_pct"
                        ],
                        "unconditional_positive_hit_rate_pct": unconditional[
                            "positive_hit_rate_pct"
                        ],
                        "median_return_difference_pct": (
                            (
                                median(returns)
                                - unconditional["median_return_pct"]
                            )
                            if returns
                            and unconditional["median_return_pct"] is not None
                            else None
                        ),
                    }
                )

    result["events"].sort(key=lambda event: (event["date"], event["threshold"], event["direction"]))
    return result
