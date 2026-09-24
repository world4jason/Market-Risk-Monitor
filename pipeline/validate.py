from __future__ import annotations

from datetime import date, datetime
from math import isfinite


ALLOWED_STATES = {"fresh", "stale", "missing", "error", "insufficient_data"}
# Must stay in sync with observations[].status in
# schemas/metric-series.schema.json. Checking it here as well keeps the unit
# suite honest: tests call validate_metric() directly and would otherwise only
# see a contract break once scripts/validate_data.py ran on real artifacts.
ALLOWED_OBSERVATION_STATUSES = {
    "observed",
    "missing",
    "estimated",
    "revised",
    "insufficient_data",
}
ALLOWED_SIGNAL_STATES = {"active", "inactive", "unknown"}
ALLOWED_REFRESH_STATES = {"updated", "error"}
ALLOWED_AVAILABILITY_BASES = {
    "observation_date",
    "release_date",
    "unknown",
}
# Mirrors metric.comparison in schemas/metric-series.schema.json.
ALLOWED_COMPARISONS = {
    "absolute",
    "percent_change",
    "percentage_points",
    "basis_points",
    "none",
}


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


def _validate_digest(value: str, *, field: str) -> None:
    if (
        not isinstance(value, str)
        or not value.startswith("sha256:")
        or len(value) != 71
        or any(
            char not in "0123456789abcdef"
            for char in value.removeprefix("sha256:")
        )
    ):
        raise ValidationError(f"Invalid {field}: {value!r}")


def validate_derived_provenance(
    provenance: dict,
    *,
    context: str,
) -> None:
    if not isinstance(provenance, dict):
        raise ValidationError(f"{context}: provenance missing")
    if provenance.get("contract_version") != "1.0.0":
        raise ValidationError(
            f"{context}: unsupported provenance contract_version"
        )

    methodology = provenance.get("methodology")
    if not isinstance(methodology, dict):
        raise ValidationError(f"{context}: methodology missing")
    if not methodology.get("id") or not methodology.get("version"):
        raise ValidationError(
            f"{context}: methodology id/version required"
        )

    config = provenance.get("config")
    if not isinstance(config, dict) or not config.get("id"):
        raise ValidationError(f"{context}: config id required")
    _validate_digest(
        config.get("content_digest"),
        field=f"{context}.config.content_digest",
    )

    generated_at = provenance.get("generated_at")
    _datetime(generated_at, field=f"{context}.generated_at")

    required_inputs = provenance.get("required_inputs")
    if (
        not isinstance(required_inputs, list)
        or not required_inputs
        or any(
            not isinstance(input_id, str) or not input_id
            for input_id in required_inputs
        )
    ):
        raise ValidationError(
            f"{context}: required_inputs must be non-empty strings"
        )
    if required_inputs != sorted(required_inputs):
        raise ValidationError(
            f"{context}: required_inputs must be sorted"
        )
    if len(required_inputs) != len(set(required_inputs)):
        raise ValidationError(
            f"{context}: duplicate required input id"
        )

    inputs = provenance.get("inputs")
    if not isinstance(inputs, list):
        raise ValidationError(f"{context}: inputs must be a list")

    ids = []
    for index, item in enumerate(inputs):
        if not isinstance(item, dict):
            raise ValidationError(
                f"{context}: input[{index}] must be an object"
            )
        input_id = item.get("id")
        if not input_id:
            raise ValidationError(
                f"{context}: input[{index}].id required"
            )
        ids.append(input_id)

        as_of = item.get("as_of")
        if as_of is not None:
            _date(
                as_of,
                field=f"{context}.inputs[{input_id}].as_of",
            )
        snapshot_at = item.get("snapshot_at")
        if snapshot_at is not None:
            _datetime(
                snapshot_at,
                field=f"{context}.inputs[{input_id}].snapshot_at",
            )
        if as_of is None and snapshot_at is None:
            raise ValidationError(
                f"{context}: input[{input_id}] needs as_of or snapshot_at"
            )
        _validate_digest(
            item.get("content_digest"),
            field=f"{context}.inputs[{input_id}].content_digest",
        )

    if ids != sorted(ids):
        raise ValidationError(f"{context}: inputs must be sorted by id")
    if len(ids) != len(set(ids)):
        raise ValidationError(f"{context}: duplicate input id")
    build_revision = provenance.get("build_revision")
    if build_revision is not None and (
        not isinstance(build_revision, str) or not build_revision
    ):
        raise ValidationError(
            f"{context}: build_revision must be a non-empty string"
        )


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

    # Optional in-flight, but a declared value must be one we know how to
    # render. Generated artifacts are required to carry it by the JSON schema.
    comparison = metric["metric"].get("comparison")
    if comparison is not None and comparison not in ALLOWED_COMPARISONS:
        raise ValidationError(f"Invalid metric comparison {comparison!r}")

    availability_basis = metric["source"].get("availability_basis")
    if (
        availability_basis is not None
        and availability_basis not in ALLOWED_AVAILABILITY_BASES
    ):
        raise ValidationError(
            f"Invalid source availability_basis {availability_basis!r}"
        )

    historical_baseline_types = {
        "full_history_percentile",
        "rolling_percentile",
        "rolling_zscore",
        "rolling_robust_zscore",
        "event_window",
    }
    canonical_pit_baselines = [
        baseline
        for baseline in metric.get("baselines", [])
        if (
            baseline.get("type") in historical_baseline_types
            and baseline.get("point_in_time") is True
        )
    ]
    if (
        canonical_pit_baselines
        and (availability_basis is None or availability_basis == "unknown")
    ):
        raise ValidationError(
            "point-in-time baseline requires a known source availability_basis"
        )

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
        status = obs.get("status")
        if status not in ALLOWED_OBSERVATION_STATUSES:
            raise ValidationError(
                f"Invalid observation status {status!r} at {obs['date']}"
            )
        value = obs.get("value")
        if value is not None and not isfinite(float(value)):
            raise ValidationError(f"Non-finite observation at {obs['date']}")

        release_date = obs.get("release_date")
        if release_date is not None:
            _date(release_date, field="observation release_date")
        if (
            availability_basis == "release_date"
            and value is not None
            and not release_date
        ):
            raise ValidationError(
                f"release_date required for non-null observation at {obs['date']}"
            )

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
    validate_derived_provenance(
        payload.get("provenance"),
        context="signals.provenance",
    )
    if payload["provenance"]["methodology"]["id"] != "deleveraging-watch":
        raise ValidationError("signals: wrong provenance methodology id")
    if payload["provenance"]["generated_at"] != payload.get("generated_at"):
        raise ValidationError("signals: provenance/generated_at mismatch")
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


def validate_overview(payload: dict) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ValidationError("overview: unsupported schema_version")
    _datetime(payload["generated_at"], field="overview.generated_at")

    rows = payload.get("metrics")
    if not isinstance(rows, list):
        raise ValidationError("overview: metrics must be a list")

    ids = []
    required_row_keys = {
        "metric",
        "source",
        "coverage",
        "freshness",
        "latest",
        "baselines",
        "summary",
    }
    required_metric_keys = {
        "id",
        "name",
        "pillar",
        "units",
        "frequency",
        "polarity",
        "comparison",
    }
    required_summary_keys = {
        "observation_count",
        "rolling_percentile",
        "recent_change",
        "preview_observations",
    }

    for row in rows:
        missing_row = required_row_keys - set(row)
        if missing_row:
            raise ValidationError(
                f"overview row missing keys: {sorted(missing_row)}"
            )

        metric = row["metric"]
        missing_metric = required_metric_keys - set(metric)
        if missing_metric:
            raise ValidationError(
                f"overview metric missing keys: {sorted(missing_metric)}"
            )

        metric_id = metric.get("id")
        if not metric_id:
            raise ValidationError("overview: metric id missing")
        ids.append(metric_id)

        if "observations" in row:
            raise ValidationError(
                f"overview[{metric_id}]: full observations are forbidden"
            )

        source = row["source"]
        for field in ("provider", "dataset", "url"):
            if not source.get(field):
                raise ValidationError(
                    f"overview[{metric_id}]: source.{field} missing"
                )
        availability_basis = source.get("availability_basis") or "unknown"
        if availability_basis not in ALLOWED_AVAILABILITY_BASES:
            raise ValidationError(
                f"overview[{metric_id}]: invalid availability_basis"
            )

        coverage = row["coverage"]
        start = coverage.get("history_start")
        end = coverage.get("history_end")
        if start:
            _date(start, field=f"overview[{metric_id}].coverage.history_start")
        if end:
            _date(end, field=f"overview[{metric_id}].coverage.history_end")
        if start and end and start > end:
            raise ValidationError(f"overview[{metric_id}]: coverage start > end")

        freshness = row["freshness"]
        if freshness.get("state") not in ALLOWED_STATES:
            raise ValidationError(
                f"overview[{metric_id}]: invalid freshness state"
            )
        evaluated_at = freshness.get("evaluated_at")
        if evaluated_at:
            _datetime(
                evaluated_at,
                field=f"overview[{metric_id}].freshness.evaluated_at",
            )

        comparison = metric.get("comparison")
        if comparison not in ALLOWED_COMPARISONS:
            raise ValidationError(
                f"overview[{metric_id}]: invalid comparison"
            )

        latest = row["latest"]
        if "value" not in latest or "as_of" not in latest or "fetched_at" not in latest:
            raise ValidationError(
                f"overview[{metric_id}]: latest is incomplete"
            )
        if latest.get("as_of"):
            _date(
                latest["as_of"],
                field=f"overview[{metric_id}].latest.as_of",
            )
        if latest.get("fetched_at"):
            _datetime(
                latest["fetched_at"],
                field=f"overview[{metric_id}].latest.fetched_at",
            )
        if latest.get("value") is not None and not isfinite(float(latest["value"])):
            raise ValidationError(
                f"overview[{metric_id}]: latest value is non-finite"
            )

        if not isinstance(row["baselines"], list):
            raise ValidationError(
                f"overview[{metric_id}]: baselines must be a list"
            )

        summary = row["summary"]
        missing_summary = required_summary_keys - set(summary)
        if missing_summary:
            raise ValidationError(
                f"overview[{metric_id}]: summary missing keys {sorted(missing_summary)}"
            )

        observation_count = summary.get("observation_count")
        if not isinstance(observation_count, int) or observation_count < 0:
            raise ValidationError(
                f"overview[{metric_id}]: invalid observation_count"
            )

        percentile = summary.get("rolling_percentile")
        if percentile is not None:
            if (
                not isfinite(float(percentile))
                or not 0 <= float(percentile) <= 100
            ):
                raise ValidationError(
                    f"overview[{metric_id}]: invalid rolling_percentile"
                )
            if source.get("point_in_time_membership") is False:
                raise ValidationError(
                    f"overview[{metric_id}]: membership-sensitive retrospective percentile is disabled"
                )

        change = summary.get("recent_change")
        if change is not None:
            if change.get("comparison") not in ALLOWED_COMPARISONS - {"none"}:
                raise ValidationError(
                    f"overview[{metric_id}]: invalid recent_change comparison"
                )
            value = change.get("value")
            if value is None or not isfinite(float(value)):
                raise ValidationError(
                    f"overview[{metric_id}]: invalid recent_change value"
                )

        preview = summary.get("preview_observations")
        if not isinstance(preview, list):
            raise ValidationError(
                f"overview[{metric_id}]: preview_observations must be a list"
            )
        if len(preview) > 30:
            raise ValidationError(
                f"overview[{metric_id}]: preview exceeds 30 observations"
            )

        dates = []
        for item in preview:
            _date(
                item["date"],
                field=f"overview[{metric_id}].preview.date",
            )
            dates.append(item["date"])
            if (
                item.get("value") is not None
                and not isfinite(float(item["value"]))
            ):
                raise ValidationError(
                    f"overview[{metric_id}]: non-finite preview value"
                )
            if item.get("status") not in ALLOWED_OBSERVATION_STATUSES:
                raise ValidationError(
                    f"overview[{metric_id}]: invalid preview status"
                )
            release_date = item.get("release_date")
            if release_date is not None:
                _date(
                    release_date,
                    field=f"overview[{metric_id}].preview.release_date",
                )
            if (
                availability_basis == "release_date"
                and item.get("value") is not None
                and not release_date
            ):
                raise ValidationError(
                    f"overview[{metric_id}]: release_date missing from preview"
                )

        if dates != sorted(dates) or len(dates) != len(set(dates)):
            raise ValidationError(
                f"overview[{metric_id}]: preview dates invalid"
            )
        if observation_count == 0 and preview:
            raise ValidationError(
                f"overview[{metric_id}]: zero observations with non-empty preview"
            )
        if observation_count > 0 and not preview:
            raise ValidationError(
                f"overview[{metric_id}]: observations exist but preview is empty"
            )
        if preview and latest.get("as_of") != preview[-1]["date"]:
            raise ValidationError(
                f"overview[{metric_id}]: preview/latest date mismatch"
            )
        if preview and latest.get("value") is not None:
            if float(latest["value"]) != float(preview[-1]["value"]):
                raise ValidationError(
                    f"overview[{metric_id}]: preview/latest value mismatch"
                )

    if len(ids) != len(set(ids)):
        raise ValidationError("overview: duplicate metric id")
        metric_id = metric.get("id")
        if not metric_id:
            raise ValidationError("overview: metric id missing")
        ids.append(metric_id)

        if "observations" in row:
            raise ValidationError(f"overview[{metric_id}]: full observations are forbidden")

        freshness = (row.get("freshness") or {}).get("state")
        if freshness not in ALLOWED_STATES:
            raise ValidationError(f"overview[{metric_id}]: invalid freshness state")

        comparison = metric.get("comparison")
        if comparison not in ALLOWED_COMPARISONS:
            raise ValidationError(f"overview[{metric_id}]: invalid comparison")

        summary = row.get("summary") or {}
        observation_count = summary.get("observation_count")
        if not isinstance(observation_count, int) or observation_count < 0:
            raise ValidationError(f"overview[{metric_id}]: invalid observation_count")

        percentile = summary.get("rolling_percentile")
        if percentile is not None:
            if not isfinite(float(percentile)) or not 0 <= float(percentile) <= 100:
                raise ValidationError(f"overview[{metric_id}]: invalid rolling_percentile")

        change = summary.get("recent_change")
        if change is not None:
            if change.get("comparison") not in ALLOWED_COMPARISONS - {"none"}:
                raise ValidationError(f"overview[{metric_id}]: invalid recent_change comparison")
            value = change.get("value")
            if value is None or not isfinite(float(value)):
                raise ValidationError(f"overview[{metric_id}]: invalid recent_change value")

        preview = summary.get("preview_observations", [])
        if len(preview) > 30:
            raise ValidationError(f"overview[{metric_id}]: preview exceeds 30 observations")
        for item in preview:
            _date(item["date"], field=f"overview[{metric_id}].preview.date")
            if item.get("value") is not None and not isfinite(float(item["value"])):
                raise ValidationError(f"overview[{metric_id}]: non-finite preview value")
            if item.get("status") not in ALLOWED_OBSERVATION_STATUSES:
                raise ValidationError(f"overview[{metric_id}]: invalid preview status")

    if len(ids) != len(set(ids)):
        raise ValidationError("overview: duplicate metric id")


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
    validate_derived_provenance(
        payload.get("provenance"),
        context="ma-breadth-study.provenance",
    )
    if (
        payload["provenance"]["methodology"]["id"]
        != "ma-breadth-event-study"
    ):
        raise ValidationError(
            "ma-breadth-study: wrong provenance methodology id"
        )
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
    validate_derived_provenance(
        payload.get("provenance"),
        context="taiwan-macro-regime.provenance",
    )
    if (
        payload["provenance"]["methodology"]["id"]
        != "taiwan-macro-regime"
    ):
        raise ValidationError(
            "taiwan-macro-regime: wrong provenance methodology id"
        )
    history = payload.get("history")
    if not isinstance(history, list):
        raise ValidationError("taiwan-macro-regime: history must be a list")

    methodology = payload.get("methodology") or {}
    historical_pit = methodology.get("historical_point_in_time")
    if historical_pit not in {True, False}:
        raise ValidationError(
            "taiwan-macro-regime: historical_point_in_time must be boolean"
        )
    history_semantics = methodology.get("history_semantics")
    if history_semantics not in {
        "point_in_time",
        "retrospective_current_vintage",
    }:
        raise ValidationError(
            "taiwan-macro-regime: invalid history_semantics"
        )
    revision_prone = methodology.get("revision_prone_inputs")
    if not isinstance(revision_prone, list):
        raise ValidationError(
            "taiwan-macro-regime: revision_prone_inputs must be a list"
        )
    if revision_prone and historical_pit is not False:
        raise ValidationError(
            "taiwan-macro-regime: revision-prone history cannot be PIT without vintages"
        )

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

    expected_current = history[-1] if history else None
    current = payload.get("current")
    if current != expected_current:
        raise ValidationError(
            "taiwan-macro-regime: current must match the latest history row"
        )

    expected_latest_known = next(
        (
            row
            for row in reversed(history)
            if row.get("regime") != "unknown"
        ),
        None,
    )
    latest_known = payload.get("latest_known")
    if latest_known != expected_latest_known:
        if expected_latest_known is None:
            raise ValidationError(
                "taiwan-macro-regime: latest_known must be null when history "
                "contains no known regime"
            )
        expected_date = expected_latest_known.get("date")
        actual_date = (
            latest_known.get("date")
            if isinstance(latest_known, dict)
            else None
        )
        if actual_date == expected_date:
            raise ValidationError(
                "taiwan-macro-regime: latest_known does not match the history "
                f"row it claims to be ({expected_date})"
            )
        raise ValidationError(
            "taiwan-macro-regime: latest_known must be the last non-unknown "
            f"history row ({expected_date}), got {actual_date!r}"
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
    validate_derived_provenance(
        payload.get("provenance"),
        context="rate-regime.provenance",
    )
    if payload["provenance"]["methodology"]["id"] != "policy-rate-regime":
        raise ValidationError("rate-regime: wrong provenance methodology id")
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
