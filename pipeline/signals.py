from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from .methodology import percentile_rank


class SignalError(ValueError):
    pass


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _month_end(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _next_month_end(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 31)
    first = date(d.year, d.month + 1, 1)
    return _month_end(first)


def referenced_metrics(rule: dict) -> set[str]:
    if rule["type"] in {"any", "all"}:
        out: set[str] = set()
        for child in rule.get("children", []):
            out |= referenced_metrics(child)
        return out
    metric = rule.get("metric")
    return {metric} if metric else set()


def _available_observations(
    metric: dict,
    evaluation_date: date,
    *,
    respect_publication_lag: bool,
) -> list[dict]:
    lag = int(metric.get("coverage", {}).get("expected_observation_lag_days") or 0)
    out = []
    for obs in metric.get("observations", []):
        if obs.get("value") is None:
            continue
        obs_date = _parse_date(obs["date"])
        available_date = obs_date + timedelta(days=lag if respect_publication_lag else 0)
        if available_date <= evaluation_date:
            out.append(obs)
        else:
            break
    return out


def _rule_value(rule: dict, observations: list[dict]):
    rule_type = rule["type"]
    threshold = float(rule.get("threshold", 0))

    if not observations:
        return None, None, "no observation available"

    latest = float(observations[-1]["value"])

    if rule_type == "latest_above":
        return latest >= threshold, latest, f"latest {latest:.4g} ≥ {threshold:g}"
    if rule_type == "latest_below":
        return latest <= threshold, latest, f"latest {latest:.4g} ≤ {threshold:g}"

    if rule_type in {"delta_periods_above", "delta_periods_below", "return_periods_below", "return_periods_above"}:
        periods = int(rule["periods"])
        if len(observations) <= periods:
            return None, None, f"needs {periods + 1} observations"
        prior = float(observations[-1 - periods]["value"])

        if rule_type.startswith("delta_periods"):
            value = latest - prior
            active = value >= threshold if rule_type.endswith("above") else value <= threshold
            return active, value, f"change {value:.4g} vs threshold {threshold:g}"

        if prior == 0:
            return None, None, "prior observation is zero"
        value = (latest / prior - 1.0) * 100.0
        active = value >= threshold if rule_type.endswith("above") else value <= threshold
        return active, value, f"return {value:.4g}% vs threshold {threshold:g}%"

    if rule_type in {"percentile_above", "percentile_below"}:
        min_observations = int(rule.get("min_observations", 20))
        if len(observations) <= min_observations:
            return None, None, f"needs > {min_observations} observations"

        baseline = [float(o["value"]) for o in observations[:-1]]
        value = percentile_rank(latest, baseline)
        if value is None:
            return None, None, "percentile unavailable"
        active = value >= threshold if rule_type.endswith("above") else value <= threshold
        return active, value, f"strict-past percentile {value:.2f} vs threshold {threshold:g}"

    raise SignalError(f"Unknown signal rule type: {rule_type}")


def evaluate_rule(
    rule: dict,
    metrics: dict[str, dict],
    evaluation_date: date,
    *,
    respect_publication_lag: bool,
    require_fresh_current: bool,
) -> dict:
    rule_type = rule["type"]

    if rule_type in {"any", "all"}:
        children = [
            evaluate_rule(
                child,
                metrics,
                evaluation_date,
                respect_publication_lag=respect_publication_lag,
                require_fresh_current=require_fresh_current,
            )
            for child in rule.get("children", [])
        ]
        statuses = [child["status"] for child in children]

        if rule_type == "any":
            if "active" in statuses:
                status = "active"
            elif "unknown" in statuses:
                status = "unknown"
            else:
                status = "inactive"
        else:
            if "inactive" in statuses:
                status = "inactive"
            elif "unknown" in statuses:
                status = "unknown"
            else:
                status = "active"

        return {
            "type": rule_type,
            "status": status,
            "children": children,
            "label": rule.get("label"),
        }

    metric_id = rule.get("metric")
    metric = metrics.get(metric_id)
    if metric is None:
        return {
            "type": rule_type,
            "status": "unknown",
            "metric": metric_id,
            "label": rule.get("label"),
            "value": None,
            "reason": "metric missing",
        }

    if require_fresh_current and metric.get("freshness", {}).get("state") != "fresh":
        return {
            "type": rule_type,
            "status": "unknown",
            "metric": metric_id,
            "label": rule.get("label"),
            "value": None,
            "reason": f"metric freshness={metric.get('freshness', {}).get('state')}",
        }

    if (
        str(metric_id).startswith("sp500_above_")
        and rule_type in {"percentile_above", "percentile_below"}
        and metric.get("source", {}).get("point_in_time_membership") is not True
    ):
        return {
            "type": rule_type,
            "status": "unknown",
            "metric": metric_id,
            "label": rule.get("label"),
            "value": None,
            "reason": (
                "MA-breadth percentile baseline requires point-in-time "
                "constituent membership"
            ),
        }

    if (
        respect_publication_lag
        and str(metric_id).startswith("sp500_above_")
        and metric.get("source", {}).get("point_in_time_membership") is not True
    ):
        return {
            "type": rule_type,
            "status": "unknown",
            "metric": metric_id,
            "label": rule.get("label"),
            "value": None,
            "reason": "historical MA breadth requires point-in-time constituent membership",
        }

    observations = _available_observations(
        metric,
        evaluation_date,
        respect_publication_lag=respect_publication_lag,
    )
    active, value, reason = _rule_value(rule, observations)
    status = "unknown" if active is None else ("active" if active else "inactive")

    return {
        "type": rule_type,
        "status": status,
        "metric": metric_id,
        "label": rule.get("label"),
        "value": value,
        "threshold": rule.get("threshold"),
        "periods": rule.get("periods"),
        "as_of": observations[-1]["date"] if observations else None,
        "reason": reason,
    }


def evaluate_condition(
    condition: dict,
    metrics: dict[str, dict],
    evaluation_date: date,
    *,
    respect_publication_lag: bool,
    require_fresh_current: bool,
) -> dict:
    result = evaluate_rule(
        condition["rules"],
        metrics,
        evaluation_date,
        respect_publication_lag=respect_publication_lag,
        require_fresh_current=require_fresh_current,
    )
    return {
        "id": condition["id"],
        "name": condition["name"],
        "description": condition.get("description", ""),
        "status": result["status"],
        "rules": result,
        "metrics": sorted(referenced_metrics(condition["rules"])),
    }


def summarize_conditions(conditions: Iterable[dict]) -> dict:
    items = list(conditions)
    active = sum(c["status"] == "active" for c in items)
    inactive = sum(c["status"] == "inactive" for c in items)
    unknown = sum(c["status"] == "unknown" for c in items)
    return {
        "active": active,
        "inactive": inactive,
        "unknown": unknown,
        "known": active + inactive,
        "total": len(items),
    }


def _monthly_history(
    metrics: dict[str, dict],
    config: dict,
    start: date,
    end: date,
) -> list[dict]:
    points = []
    cursor = _month_end(start)

    while cursor <= end:
        conditions = [
            evaluate_condition(
                condition,
                metrics,
                cursor,
                respect_publication_lag=True,
                require_fresh_current=False,
            )
            for condition in config["conditions"]
        ]
        points.append(
            {
                "date": cursor.isoformat(),
                "summary": summarize_conditions(conditions),
                "conditions": {c["id"]: c["status"] for c in conditions},
            }
        )
        cursor = _next_month_end(cursor)

    return points


def build_signal_snapshot(
    metrics: dict[str, dict],
    config: dict,
    evaluated_at: datetime | None = None,
) -> dict:
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    evaluation_date = evaluated_at.date()

    current_conditions = [
        evaluate_condition(
            condition,
            metrics,
            evaluation_date,
            respect_publication_lag=False,
            require_fresh_current=True,
        )
        for condition in config["conditions"]
    ]

    start = _parse_date(config.get("history_start", "1997-01-31"))
    history = _monthly_history(metrics, config, start, _month_end(evaluation_date))

    return {
        "schema_version": "1.0.0",
        "name": config.get("name", "Deleveraging Watch"),
        "description": config.get("description", ""),
        "generated_at": evaluated_at.isoformat().replace("+00:00", "Z"),
        "current": {
            "as_of": evaluation_date.isoformat(),
            "summary": summarize_conditions(current_conditions),
            "conditions": current_conditions,
        },
        "history": history,
        "methodology": {
            "current_freshness_required": True,
            "historical_publication_lag_respected": True,
            "unknown_is_not_inactive": True,
            "no_single_condition_is_a_crisis_label": True,
        },
    }
