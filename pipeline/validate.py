from __future__ import annotations

from datetime import date, datetime
from math import isfinite


ALLOWED_STATES = {"fresh", "stale", "missing", "error", "insufficient_data"}
ALLOWED_SIGNAL_STATES = {"active", "inactive", "unknown"}
ALLOWED_REFRESH_STATES = {"updated", "error"}


class ValidationError(ValueError):
    pass


def _date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except Exception as exc:
        raise ValidationError(f"Invalid {field}: {value!r}") from exc


def _datetime(value: str, *, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValidationError(f"Invalid {field}: {value!r}") from exc


def validate_metric(metric: dict) -> None:
    required = {
        "schema_version",
        "environment",
        "metric",
        "source",
        "coverage",
        "freshness",
        "lineage",
        "baselines",
        "latest",
        "observations",
    }
    missing = required - set(metric)
    if missing:
        raise ValidationError(f"Missing top-level keys: {sorted(missing)}")
    if metric["schema_version"] != "1.0.0":
        raise ValidationError("Unsupported schema_version")
    if metric["environment"] not in {"production", "fixture"}:
        raise ValidationError("Invalid environment")
    if metric["freshness"]["state"] not in ALLOWED_STATES:
        raise ValidationError("Invalid freshness state")

    if metric["metric"].get("pillar") == "breadth":
        scope = metric["source"].get("market_scope")
        metric_id = metric["metric"].get("id", "")
        if metric_id.startswith("sp500_above_"):
            if scope != "S&P 500":
                raise ValidationError(
                    f"S&P 500 moving-average breadth scope must be 'S&P 500', got {scope!r}"
                )
            for obs in metric.get("observations", []):
                value = obs.get("value")
                if value is not None and not 0 <= float(value) <= 100:
                    raise ValidationError(
                        f"{metric_id}: moving-average breadth outside [0,100] at {obs.get('date')}"
                    )
        elif metric_id.startswith("nyse_") or metric_id.startswith("mrm_mcclellan_"):
            if scope != "NYSE":
                raise ValidationError(
                    f"NYSE breadth metric market_scope must be 'NYSE', got {scope!r}"
                )
        elif not scope:
            raise ValidationError("breadth metric market_scope is required")

    dates = []
    for obs in metric["observations"]:
        _date(obs["date"], field="observation date")
        dates.append(obs["date"])
        value = obs.get("value")
        if value is not None and not isfinite(float(value)):
            raise ValidationError(f"Non-finite observation at {obs['date']}")

    if dates != sorted(dates):
        raise ValidationError("Observation dates are not monotonically ascending")
    if len(dates) != len(set(dates)):
        raise ValidationError("Duplicate observation dates")

    if dates:
        if metric["coverage"]["history_start"] != dates[0]:
            raise ValidationError("coverage.history_start does not match first observation")
        if metric["coverage"]["history_end"] != dates[-1]:
            raise ValidationError("coverage.history_end does not match last observation")

    present = [o for o in metric["observations"] if o.get("value") is not None]
    latest = present[-1] if present else None
    if latest:
        if metric["latest"]["as_of"] != latest["date"]:
            raise ValidationError("latest.as_of does not match last non-null observation")
        if float(metric["latest"]["value"]) != float(latest["value"]):
            raise ValidationError("latest.value does not match last non-null observation")
    else:
        if metric["latest"]["value"] is not None:
            raise ValidationError("latest.value must be null when all observations are missing")


def _validate_signal_summary(summary: dict, *, context: str) -> None:
    required = {"active", "inactive", "unknown", "known", "total"}
    if required - set(summary):
        raise ValidationError(f"{context}: incomplete summary")

    values = {key: int(summary[key]) for key in required}
    if any(value < 0 for value in values.values()):
        raise ValidationError(f"{context}: negative summary count")
    if values["known"] != values["active"] + values["inactive"]:
        raise ValidationError(f"{context}: known != active + inactive")
    if values["total"] != values["known"] + values["unknown"]:
        raise ValidationError(f"{context}: total != known + unknown")


def validate_signal_snapshot(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("signals: unsupported schema_version")
    if "current" not in payload or "history" not in payload:
        raise ValidationError("signals: missing current/history")
    _datetime(payload["generated_at"], field="signals.generated_at")
    _date(payload["current"]["as_of"], field="signals.current.as_of")

    current_conditions = payload["current"].get("conditions", [])
    ids = [condition.get("id") for condition in current_conditions]
    if len(ids) != len(set(ids)):
        raise ValidationError("signals: duplicate current condition id")
    for condition in current_conditions:
        if condition.get("status") not in ALLOWED_SIGNAL_STATES:
            raise ValidationError(
                f"signals: invalid condition status {condition.get('status')!r}"
            )

    _validate_signal_summary(payload["current"]["summary"], context="signals.current")
    if payload["current"]["summary"]["total"] != len(current_conditions):
        raise ValidationError("signals.current: total does not match condition count")

    dates = []
    for point in payload["history"]:
        _date(point["date"], field="signals.history.date")
        dates.append(point["date"])
        _validate_signal_summary(point["summary"], context=f"signals.history[{point['date']}]")
        for status in point.get("conditions", {}).values():
            if status not in ALLOWED_SIGNAL_STATES:
                raise ValidationError(
                    f"signals.history[{point['date']}]: invalid status {status!r}"
                )

    if dates != sorted(dates):
        raise ValidationError("signals: history dates are not monotonically ascending")
    if len(dates) != len(set(dates)):
        raise ValidationError("signals: duplicate history dates")


def validate_coverage_report(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("coverage: unsupported schema_version")
    _datetime(payload["generated_at"], field="coverage.generated_at")

    ids = []
    for metric in payload.get("metrics", []):
        metric_id = metric.get("id")
        if not metric_id:
            raise ValidationError("coverage: metric id missing")
        ids.append(metric_id)

        start = metric.get("actual_history_start")
        end = metric.get("actual_history_end")
        if start:
            _date(start, field=f"coverage[{metric_id}].actual_history_start")
        if end:
            _date(end, field=f"coverage[{metric_id}].actual_history_end")
        if start and end and start > end:
            raise ValidationError(f"coverage[{metric_id}]: start > end")
        if int(metric.get("observations", 0)) < 0:
            raise ValidationError(f"coverage[{metric_id}]: negative observation count")
        if metric.get("status") not in {"ok", "short_history"}:
            raise ValidationError(
                f"coverage[{metric_id}]: invalid status {metric.get('status')!r}"
            )

    if len(ids) != len(set(ids)):
        raise ValidationError("coverage: duplicate metric id")


def validate_catalog(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("catalog: unsupported schema_version")
    generated_at = payload.get("generated_at")
    if generated_at is not None:
        _datetime(generated_at, field="catalog.generated_at")

    ids = []
    for metric in payload.get("metrics", []):
        metric_id = metric.get("id")
        if not metric_id:
            raise ValidationError("catalog: metric id missing")
        ids.append(metric_id)
        path = metric.get("path")
        if not isinstance(path, str) or not path.startswith("./"):
            raise ValidationError(f"catalog[{metric_id}]: path must be project-relative")
        if metric.get("freshness") not in ALLOWED_STATES:
            raise ValidationError(f"catalog[{metric_id}]: invalid freshness state")

    if len(ids) != len(set(ids)):
        raise ValidationError("catalog: duplicate metric id")


def validate_refresh_report(payload: dict) -> None:
    _datetime(payload["generated_at"], field="refresh-report.generated_at")
    for result in payload.get("results", []):
        if result.get("status") not in ALLOWED_REFRESH_STATES:
            raise ValidationError(
                f"refresh-report: invalid result status {result.get('status')!r}"
            )
        if not result.get("metric"):
            raise ValidationError("refresh-report: result metric missing")
        if result["status"] == "error" and not result.get("error"):
            raise ValidationError("refresh-report: error result missing error message")


def validate_ma_breadth_audit(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("ma-breadth-audit: unsupported schema_version")
    if payload.get("market_scope") != "S&P 500":
        raise ValidationError("ma-breadth-audit: market_scope must be S&P 500")
    if not payload.get("provider"):
        raise ValidationError("ma-breadth-audit: provider missing")
    point_in_time = payload.get("point_in_time_membership")
    if point_in_time not in {True, False, None}:
        raise ValidationError("ma-breadth-audit: invalid point_in_time_membership")
    horizons = payload.get("horizons", {})
    for horizon in ("20", "50", "200"):
        if horizon not in horizons:
            raise ValidationError(f"ma-breadth-audit: missing horizon {horizon}")
        item = horizons[horizon]
        if int(item.get("observations", 0)) < 0:
            raise ValidationError(f"ma-breadth-audit: negative observations for {horizon}")
        first = item.get("first")
        last = item.get("last")
        if first:
            _date(first, field=f"ma-breadth-audit[{horizon}].first")
        if last:
            _date(last, field=f"ma-breadth-audit[{horizon}].last")
        if first and last and first > last:
            raise ValidationError(f"ma-breadth-audit[{horizon}]: first > last")

    dates = []
    for obs in payload.get("observations", []):
        _date(obs["date"], field="ma-breadth-audit.observation.date")
        dates.append(obs["date"])
        for horizon in ("20", "50", "200"):
            item = obs.get(horizon, {})
            pct = item.get("pct")
            eligible = item.get("eligible")
            above = item.get("above")
            missing_price = item.get("missing_price")
            if pct is not None and not 0 <= float(pct) <= 100:
                raise ValidationError(
                    f"ma-breadth-audit[{obs['date']}][{horizon}]: pct outside [0,100]"
                )
            for name, value in (
                ("eligible", eligible),
                ("above", above),
                ("missing_price", missing_price),
            ):
                if value is not None and int(value) < 0:
                    raise ValidationError(
                        f"ma-breadth-audit[{obs['date']}][{horizon}]: negative {name}"
                    )
            if eligible is not None and above is not None and int(above) > int(eligible):
                raise ValidationError(
                    f"ma-breadth-audit[{obs['date']}][{horizon}]: above > eligible"
                )

    if dates != sorted(dates):
        raise ValidationError("ma-breadth-audit: dates not monotonically ascending")
    if len(dates) != len(set(dates)):
        raise ValidationError("ma-breadth-audit: duplicate dates")


def validate_ma_breadth_study(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("ma-breadth-study: unsupported schema_version")
    if payload.get("status") not in {"ready", "blocked_non_point_in_time"}:
        raise ValidationError(
            f"ma-breadth-study: invalid status {payload.get('status')!r}"
        )
    if payload.get("breadth_metric") != "sp500_above_50dma_pct":
        raise ValidationError("ma-breadth-study: unexpected breadth metric")
    if payload.get("status") == "blocked_non_point_in_time":
        if payload.get("events"):
            raise ValidationError("ma-breadth-study: blocked study must not contain events")
        return

    for event in payload.get("events", []):
        _date(event["date"], field="ma-breadth-study.event.date")
        value = float(event["breadth_value"])
        if not 0 <= value <= 100:
            raise ValidationError("ma-breadth-study: event breadth outside [0,100]")
        if event.get("direction") not in {"down", "up"}:
            raise ValidationError("ma-breadth-study: invalid event direction")
        if float(event.get("threshold")) not in {15.0, 25.0}:
            raise ValidationError("ma-breadth-study: unexpected threshold")
    for row in payload.get("summaries", []):
        if int(row.get("sample_count", 0)) < 0:
            raise ValidationError("ma-breadth-study: negative sample count")
        if row.get("horizon") not in {"1W", "1M", "3M", "6M"}:
            raise ValidationError("ma-breadth-study: unexpected horizon")


def validate_taiwan_macro_regime(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("taiwan-macro-regime: unsupported schema_version")
    history = payload.get("history")
    if not isinstance(history, list):
        raise ValidationError("taiwan-macro-regime: history must be a list")

    allowed = {
        "expansion",
        "deceleration",
        "recovery",
        "contraction",
        "unknown",
    }
    dates = []
    for row in history:
        _date(row["date"], field="taiwan-macro-regime.date")
        dates.append(row["date"])
        if row.get("regime") not in allowed:
            raise ValidationError(
                f"taiwan-macro-regime: invalid regime {row.get('regime')!r}"
            )
        confidence = float(row.get("confidence", 0))
        if not 0 <= confidence <= 1:
            raise ValidationError(
                "taiwan-macro-regime: confidence outside [0,1]"
            )
        available_on = row.get("available_on")
        if available_on:
            _date(
                available_on,
                field="taiwan-macro-regime.available_on",
            )

    if dates != sorted(dates):
        raise ValidationError(
            "taiwan-macro-regime: dates not monotonically ascending"
        )
    if len(dates) != len(set(dates)):
        raise ValidationError("taiwan-macro-regime: duplicate dates")

    current = payload.get("current")
    if current is not None:
        if current.get("regime") == "unknown":
            raise ValidationError(
                "taiwan-macro-regime: current should be latest known regime"
            )


def validate_taiwan_macro_audit(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("taiwan-macro-audit: unsupported schema_version")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValidationError("taiwan-macro-audit: rows must be a list")

    keys = set()
    for row in rows:
        series_id = row.get("series_id")
        obs_date = row.get("date")
        release_date = row.get("release_date")
        if not series_id or not obs_date or not release_date:
            raise ValidationError(
                "taiwan-macro-audit: series/date/release_date required"
            )
        _date(obs_date, field="taiwan-macro-audit.date")
        _date(release_date, field="taiwan-macro-audit.release_date")
        key = (series_id, obs_date)
        if key in keys:
            raise ValidationError(
                f"taiwan-macro-audit: duplicate {series_id} {obs_date}"
            )
        keys.add(key)
        try:
            value = float(row["value"])
        except Exception as exc:
            raise ValidationError(
                "taiwan-macro-audit: invalid value"
            ) from exc
        if not isfinite(value):
            raise ValidationError(
                "taiwan-macro-audit: non-finite value"
            )


def validate_rate_regime(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("rate-regime: unsupported schema_version")
    allowed = {
        "easing",
        "stable",
        "gradual_tightening",
        "aggressive_tightening",
        "unknown",
    }
    history = payload.get("history")
    if not isinstance(history, list):
        raise ValidationError("rate-regime: history must be a list")
    dates = []
    for row in history:
        _date(row["date"], field="rate-regime.date")
        dates.append(row["date"])
        if row.get("regime") not in allowed:
            raise ValidationError(
                f"rate-regime: invalid regime {row.get('regime')!r}"
            )
        for field in (
            "rate",
            "step_bp",
            "change_3m_bp",
            "change_6m_bp",
            "change_12m_bp",
        ):
            value = row.get(field)
            if value is not None and not isfinite(float(value)):
                raise ValidationError(
                    f"rate-regime: non-finite {field} at {row['date']}"
                )
    if dates != sorted(dates):
        raise ValidationError("rate-regime: dates not monotonically ascending")
    if len(dates) != len(set(dates)):
        raise ValidationError("rate-regime: duplicate dates")
    current = payload.get("current")
    if history and current != history[-1]:
        raise ValidationError("rate-regime: current must equal last history row")


def validate_taiwan_trend_breadth_audit(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError(
            "taiwan-trend-breadth-audit: unsupported schema_version"
        )
    if payload.get("market_scope") != "TWSE listed common stocks":
        raise ValidationError(
            "taiwan-trend-breadth-audit: wrong market_scope"
        )
    if not payload.get("provider"):
        raise ValidationError(
            "taiwan-trend-breadth-audit: provider missing"
        )
    pit = payload.get("point_in_time_membership")
    if pit not in {True, False, None}:
        raise ValidationError(
            "taiwan-trend-breadth-audit: invalid point_in_time_membership"
        )

    start = payload.get("history_start")
    end = payload.get("history_end")
    if start:
        _date(start, field="taiwan-trend-breadth-audit.history_start")
    if end:
        _date(end, field="taiwan-trend-breadth-audit.history_end")
    if start and end and start > end:
        raise ValidationError(
            "taiwan-trend-breadth-audit: history_start > history_end"
        )

    dates = []
    for row in payload.get("observations", []):
        obs_date = row.get("date")
        _date(obs_date, field="taiwan-trend-breadth-audit.date")
        dates.append(obs_date)
        total = int(row.get("total_members", 0))
        if total < 0:
            raise ValidationError(
                "taiwan-trend-breadth-audit: negative total_members"
            )
        for horizon in (20, 50, 200):
            eligible = int(row.get(f"eligible_{horizon}d", 0))
            above = int(row.get(f"above_{horizon}d_count", 0))
            missing = int(row.get(f"missing_{horizon}d", 0))
            pct = row.get(f"above_{horizon}dma_pct")
            if min(eligible, above, missing) < 0:
                raise ValidationError(
                    f"taiwan-trend-breadth-audit: negative {horizon}d count"
                )
            if above > eligible:
                raise ValidationError(
                    f"taiwan-trend-breadth-audit: above > eligible for {horizon}d"
                )
            if eligible + missing != total:
                raise ValidationError(
                    f"taiwan-trend-breadth-audit: eligible+missing != total for {horizon}d"
                )
            if pct is not None and not 0 <= float(pct) <= 100:
                raise ValidationError(
                    f"taiwan-trend-breadth-audit: pct outside [0,100] for {horizon}d"
                )

        highs = row.get("new_52w_highs")
        lows = row.get("new_52w_lows")
        eligible52 = int(row.get("eligible_52w", 0))
        if highs is not None and int(highs) > eligible52:
            raise ValidationError(
                "taiwan-trend-breadth-audit: new highs > eligible"
            )
        if lows is not None and int(lows) > eligible52:
            raise ValidationError(
                "taiwan-trend-breadth-audit: new lows > eligible"
            )

    if dates != sorted(dates):
        raise ValidationError(
            "taiwan-trend-breadth-audit: dates not monotonic"
        )
    if len(dates) != len(set(dates)):
        raise ValidationError(
            "taiwan-trend-breadth-audit: duplicate dates"
        )
