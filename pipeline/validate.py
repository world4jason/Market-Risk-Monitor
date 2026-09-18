from __future__ import annotations

from datetime import date
from math import isfinite


ALLOWED_STATES = {"fresh","stale","missing","error","insufficient_data"}


class ValidationError(ValueError):
    pass


def validate_metric(metric: dict) -> None:
    required = {"schema_version","environment","metric","source","coverage","freshness","lineage","baselines","latest","observations"}
    missing = required - set(metric)
    if missing:
        raise ValidationError(f"Missing top-level keys: {sorted(missing)}")
    if metric["schema_version"] != "1.0.0":
        raise ValidationError("Unsupported schema_version")
    if metric["environment"] not in {"production","fixture"}:
        raise ValidationError("Invalid environment")
    if metric["freshness"]["state"] not in ALLOWED_STATES:
        raise ValidationError("Invalid freshness state")

    dates=[]
    for obs in metric["observations"]:
        try:
            date.fromisoformat(obs["date"])
        except Exception as exc:
            raise ValidationError(f"Invalid observation date: {obs.get('date')}") from exc
        dates.append(obs["date"])
        value=obs.get("value")
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

    present=[o for o in metric["observations"] if o.get("value") is not None]
    latest=present[-1] if present else None
    if latest:
        if metric["latest"]["as_of"] != latest["date"]:
            raise ValidationError("latest.as_of does not match last non-null observation")
        if float(metric["latest"]["value"]) != float(latest["value"]):
            raise ValidationError("latest.value does not match last non-null observation")
    else:
        if metric["latest"]["value"] is not None:
            raise ValidationError("latest.value must be null when all observations are missing")
