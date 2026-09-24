from __future__ import annotations

import csv
import io
import json
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path

from .provenance import build_provenance, metric_input, records_input


class RateVelocityError(ValueError):
    pass


def parse_cbc_rate_csv(text: str) -> list[dict]:
    """
    Normalized CBC change-date contract:
    date,discount_rate,collateral_rate,short_term_rate,source_url
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise RateVelocityError("CBC rate CSV has no header")
    required = {"date", "discount_rate"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise RateVelocityError(
            f"CBC rate CSV missing {sorted(missing)}"
        )

    rows = []
    previous = None
    for line_no, raw in enumerate(reader, start=2):
        try:
            obs_date = date.fromisoformat(raw["date"].strip()).isoformat()
            discount = float(raw["discount_rate"])
        except Exception as exc:
            raise RateVelocityError(
                f"row {line_no}: invalid date/discount_rate"
            ) from exc
        if previous is not None and obs_date <= previous:
            raise RateVelocityError(
                f"row {line_no}: dates must be strictly increasing"
            )
        previous = obs_date

        def optional_float(name):
            value = (raw.get(name) or "").strip()
            return None if not value else float(value)

        rows.append(
            {
                "date": obs_date,
                "discount_rate": discount,
                "collateral_rate": optional_float("collateral_rate"),
                "short_term_rate": optional_float("short_term_rate"),
                "source_url": (
                    (raw.get("source_url") or "").strip()
                    or "https://www.cbc.gov.tw/en/lp-695-2-2-20.html"
                ),
            }
        )
    if not rows:
        raise RateVelocityError("CBC rate CSV has no rows")
    return rows


def combine_fed_target_metrics(
    legacy: dict | None,
    upper: dict | None,
) -> list[dict]:
    """
    Merge legacy single-target and modern upper-bound series, then compress
    the daily FRED observations into effective-date change points.

    This makes step_bp represent an actual FOMC target change rather than a
    stream of zero changes on non-meeting days.
    """
    by_date = {}
    if legacy:
        for obs in legacy.get("observations", []):
            if obs.get("value") is not None:
                by_date[obs["date"]] = float(obs["value"])
    if upper:
        for obs in upper.get("observations", []):
            if obs.get("value") is not None:
                # Modern target-range upper bound takes precedence.
                by_date[obs["date"]] = float(obs["value"])

    output = []
    previous = None
    for obs_date in sorted(by_date):
        value = by_date[obs_date]
        if previous is None or value != previous:
            output.append({"date": obs_date, "value": value})
            previous = value
    return output


def _months_before(d: date, months: int) -> date:
    year = d.year
    month = d.month - months
    while month <= 0:
        year -= 1
        month += 12
    day = min(d.day, monthrange(year, month)[1])
    return date(year, month, day)


def _value_on_or_before(observations: list[dict], target: date):
    value = None
    for obs in observations:
        obs_date = date.fromisoformat(obs["date"])
        if obs_date <= target:
            value = float(obs["value"])
        else:
            break
    return value


def rate_velocity_rows(observations: list[dict]) -> list[dict]:
    if not observations:
        return []
    observations = sorted(observations, key=lambda x: x["date"])
    out = []
    previous_rate = None
    for obs in observations:
        rate = float(obs["value"])
        d = date.fromisoformat(obs["date"])
        step = (
            None
            if previous_rate is None
            else 100.0 * (rate - previous_rate)
        )

        row = {
            "date": obs["date"],
            "rate": rate,
            "step_bp": step,
        }
        for months in (3, 6, 12):
            prior = _value_on_or_before(
                observations,
                _months_before(d, months),
            )
            row[f"change_{months}m_bp"] = (
                None if prior is None else 100.0 * (rate - prior)
            )
        out.append(row)
        previous_rate = rate
    return out


def rate_regime(row: dict, config: dict) -> str:
    six = row.get("change_6m_bp")
    step = row.get("step_bp")
    cfg = config["regimes"]

    if six is None:
        # The series can be too short for a 6M cumulative change while still
        # containing an unambiguous outsized policy step. Falling through to
        # "unknown" there would hide a decisive move such as a 75bp hike.
        if step is None:
            return "unknown"
        aggressive_step = float(cfg["aggressive_single_step_bp"])
        if step >= aggressive_step:
            return "aggressive_tightening"
        if step <= -aggressive_step:
            return "easing"
        return "unknown"

    if six <= float(cfg["easing_max_6m_bp"]):
        return "easing"
    if (
        abs(six) <= float(cfg["stable_abs_6m_bp"])
        and abs(step or 0) < float(cfg["aggressive_single_step_bp"])
    ):
        return "stable"
    if (
        six >= float(cfg["aggressive_tightening_min_6m_bp"])
        or (step or 0) >= float(cfg["aggressive_single_step_bp"])
    ):
        return "aggressive_tightening"
    if six > 0:
        return "gradual_tightening"
    return "stable"


def _build_metric(
    rows: list[dict],
    *,
    metric_id: str,
    name: str,
    field: str,
    provider: str,
    source_url: str,
    market_scope: str,
    fetched_at: datetime,
    units: str,
    polarity: str,
    lineage: dict,
) -> dict | None:
    observations = [
        {
            "date": row["date"],
            "value": row.get(field),
            "status": (
                "observed"
                if row.get(field) is not None
                else "missing"
            ),
        }
        for row in rows
    ]
    present = [o for o in observations if o["value"] is not None]
    if not present:
        return None
    latest = present[-1]

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": metric_id,
            "name": name,
            "description": "Policy-rate level/change velocity.",
            "pillar": "context",
            "units": units,
            "frequency": "irregular",
            "polarity": polarity,
        },
        "source": {
            "provider": provider,
            "dataset": "Policy rate history",
            "series_id": metric_id,
            "url": source_url,
            "license_note": "Official/first-party or FRED-distributed policy-rate source; retain attribution.",
            "redistribution": "unknown",
            "market_scope": market_scope,
            "membership_mode": None,
            "membership_snapshot": None,
            "price_adjustment": None,
            "point_in_time_membership": None,
            "availability_basis": "observation_date",
        },
        "coverage": {
            "history_start": observations[0]["date"],
            "history_end": observations[-1]["date"],
            "timezone": "UTC",
            "expected_observation_lag_days": 1,
        },
        "freshness": {
            # A policy rate can validly remain unchanged for a long time.
            "state": "fresh",
            "max_age_days": 2000,
            "age_days": max(
                (fetched_at.date() - date.fromisoformat(latest["date"])).days,
                0,
            ),
            "evaluated_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "reason": "Irregular change-date series; old effective date can still be current.",
        },
        "lineage": lineage,
        "baselines": [],
        "latest": {
            "as_of": latest["date"],
            "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "value": latest["value"],
            "revision_tag": None,
        },
        "observations": observations,
    }


def build_rate_metrics(
    rate_rows: list[dict],
    *,
    prefix: str,
    name_prefix: str,
    provider: str,
    source_url: str,
    market_scope: str,
    fetched_at: datetime | None = None,
) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    velocity = rate_velocity_rows(rate_rows)
    specs = [
        ("rate", "Rate", "percent", "contextual"),
        ("step_bp", "Step", "basis points", "higher_is_riskier"),
        ("change_3m_bp", "3M cumulative change", "basis points", "higher_is_riskier"),
        ("change_6m_bp", "6M cumulative change", "basis points", "higher_is_riskier"),
        ("change_12m_bp", "12M cumulative change", "basis points", "higher_is_riskier"),
    ]
    metrics = {}
    for field, label, units, polarity in specs:
        metric_id = f"{prefix}_{field}"
        metric = _build_metric(
            velocity,
            metric_id=metric_id,
            name=f"{name_prefix} {label}",
            field=field,
            provider=provider,
            source_url=source_url,
            market_scope=market_scope,
            fetched_at=fetched_at,
            units=units,
            polarity=polarity,
            lineage={
                "kind": "raw" if field == "rate" else "derived",
                "inputs": [] if field == "rate" else [f"{prefix}_rate"],
                "formula": (
                    None
                    if field == "rate"
                    else {
                        "step_bp": "100 * (rate_t - rate_t-1)",
                        "change_3m_bp": "100 * (rate_t - last_rate_on_or_before(t-3m))",
                        "change_6m_bp": "100 * (rate_t - last_rate_on_or_before(t-6m))",
                        "change_12m_bp": "100 * (rate_t - last_rate_on_or_before(t-12m))",
                    }[field]
                ),
                "transform_version": "rate-velocity-v1",
            },
        )
        if metric:
            metrics[metric_id] = metric
    return metrics


def build_rate_regime_artifact(
    rate_rows: list[dict],
    config: dict,
    *,
    name: str,
    input_metrics: list[dict] | None = None,
    config_id: str = "data/config/rates.json",
) -> dict:
    rows = rate_velocity_rows(rate_rows)
    history = [
        {**row, "regime": rate_regime(row, config)}
        for row in rows
    ]

    latest_date = rate_rows[-1]["date"] if rate_rows else None
    provenance_inputs = [
        records_input(
            "rate_rows",
            rate_rows,
            as_of=latest_date,
            snapshot_at=None,
        )
    ]
    provenance_inputs.extend(
        metric_input(metric)
        for metric in (input_metrics or [])
    )

    provenance = build_provenance(
        methodology_id="policy-rate-regime",
        methodology_version="rate-regime-v1",
        config_id=config_id,
        config=config,
        inputs=provenance_inputs,
        required_input_ids=["rate_rows"],
    )
    return {
        "schema_version": "1.0.0",
        "name": name,
        "provenance": provenance,
        "current": history[-1] if history else None,
        "history": history,
    }


def cbc_rows_to_rate_rows(rows: list[dict]) -> list[dict]:
    return [
        {"date": row["date"], "value": row["discount_rate"]}
        for row in rows
    ]
