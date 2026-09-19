from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path


class BreadthError(ValueError):
    pass


REQUIRED_COLUMNS = {"date", "market_scope", "provider"}
OPTIONAL_NUMERIC_COLUMNS = {
    "new_52w_highs",
    "new_52w_lows",
    "advancing_issues",
    "declining_issues",
    "unchanged_issues",
    "up_volume",
    "down_volume",
    "unchanged_volume",
    "total_issues",
}


def _parse_nonnegative(raw, *, column: str, row_number: int):
    if raw is None:
        return None
    text = str(raw).strip()
    if text in {"", ".", "NA", "N/A"}:
        return None
    try:
        value = float(text.replace(",", ""))
    except ValueError as exc:
        raise BreadthError(
            f"row {row_number}: {column} is not numeric: {raw!r}"
        ) from exc
    if value < 0:
        raise BreadthError(
            f"row {row_number}: {column} must be non-negative, got {value}"
        )
    return value


def parse_breadth_csv(text: str, *, required_scope: str = "NYSE") -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise BreadthError("breadth CSV has no header")

    headers = set(reader.fieldnames)
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise BreadthError(f"breadth CSV missing columns: {sorted(missing)}")

    rows = []
    seen_dates = set()
    scopes = set()
    providers = set()

    for row_number, row in enumerate(reader, start=2):
        raw_date = (row.get("date") or "").strip()
        if not raw_date:
            continue
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise BreadthError(
                f"row {row_number}: invalid date {raw_date!r}"
            ) from exc

        scope = (row.get("market_scope") or "").strip()
        provider = (row.get("provider") or "").strip()
        if not scope:
            raise BreadthError(f"row {row_number}: market_scope is blank")
        if not provider:
            raise BreadthError(f"row {row_number}: provider is blank")

        if parsed_date.isoformat() in seen_dates:
            raise BreadthError(f"duplicate date: {parsed_date.isoformat()}")
        seen_dates.add(parsed_date.isoformat())
        scopes.add(scope)
        providers.add(provider)

        parsed = {
            "date": parsed_date.isoformat(),
            "market_scope": scope,
            "provider": provider,
        }
        for column in OPTIONAL_NUMERIC_COLUMNS:
            parsed[column] = _parse_nonnegative(
                row.get(column),
                column=column,
                row_number=row_number,
            )

        rows.append(parsed)

    rows.sort(key=lambda row: row["date"])

    if len(scopes) > 1:
        raise BreadthError(f"mixed market scopes in one file: {sorted(scopes)}")
    if scopes and required_scope and scopes != {required_scope}:
        raise BreadthError(
            f"market scope must be {required_scope!r}, got {sorted(scopes)}"
        )
    if len(providers) > 1:
        raise BreadthError(
            "one canonical breadth snapshot must use one provider/export family; "
            f"got {sorted(providers)}"
        )

    if not rows:
        raise BreadthError("breadth CSV contains no data rows")

    return rows


def _freshness(as_of: str | None, fetched_at: datetime, max_age_days: int = 5):
    if as_of is None:
        return "missing", None
    age = max((fetched_at.date() - date.fromisoformat(as_of)).days, 0)
    return ("fresh" if age <= max_age_days else "stale"), age


def _metric(
    rows: list[dict],
    *,
    metric_id: str,
    name: str,
    field: str,
    units: str,
    polarity: str,
    fetched_at: datetime,
    description: str,
    lineage: dict | None = None,
) -> dict:
    observations = [
        {
            "date": row["date"],
            "value": row.get(field),
            "status": "observed" if row.get(field) is not None else "missing",
        }
        for row in rows
    ]
    present = [o for o in observations if o["value"] is not None]
    latest = present[-1] if present else None
    as_of = latest["date"] if latest else None
    state, age = _freshness(as_of, fetched_at)

    scope = rows[0]["market_scope"]
    provider = rows[0]["provider"]

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": metric_id,
            "name": name,
            "description": description,
            "pillar": "breadth",
            "units": units,
            "frequency": "daily",
            "polarity": polarity,
        },
        "source": {
            "provider": provider,
            "dataset": "Authorized NYSE breadth export",
            "series_id": None,
            "url": "https://github.com/world4jason/Market-Risk-Monitor/blob/main/docs/breadth-sources.md",
            "license_note": (
                "Imported from an authorized local export. Public redistribution "
                "rights depend on the provider license and are not assumed."
            ),
            "redistribution": "unknown",
            "market_scope": scope,
        },
        "coverage": {
            "history_start": observations[0]["date"],
            "history_end": observations[-1]["date"],
            "timezone": "America/New_York",
            "expected_observation_lag_days": 1,
        },
        "freshness": {
            "state": state,
            "max_age_days": 5,
            "age_days": age,
            "evaluated_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "reason": None,
        },
        "lineage": lineage
        or {
            "kind": "raw",
            "inputs": [],
            "formula": None,
            "transform_version": "breadth-raw-v1",
        },
        "baselines": [
            {
                "id": "expanding-pit",
                "type": "full_history_percentile",
                "window_observations": None,
                "min_observations": 252,
                "point_in_time": True,
                "notes": "Strict-past expanding baseline.",
            },
            {
                "id": "rolling-2520d",
                "type": "rolling_percentile",
                "window_observations": 2520,
                "min_observations": 504,
                "point_in_time": True,
                "notes": "Approximate trailing ten trading years.",
            },
        ],
        "latest": {
            "as_of": as_of,
            "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "value": latest["value"] if latest else None,
            "revision_tag": None,
        },
        "observations": observations,
    }


def _derived_rows(rows: list[dict]) -> list[dict]:
    out = []
    ad_line = 0.0
    have_ad = False

    t10 = None
    t05 = None
    valid_volume_run = 0
    volume_sum = None

    for row in rows:
        item = dict(row)

        highs = row.get("new_52w_highs")
        lows = row.get("new_52w_lows")
        total = row.get("total_issues")
        item["net_new_52w_highs"] = (
            None if highs is None or lows is None else highs - lows
        )
        item["high_low_pct"] = (
            None
            if item["net_new_52w_highs"] is None or total in (None, 0)
            else 100.0 * item["net_new_52w_highs"] / total
        )

        adv = row.get("advancing_issues")
        dec = row.get("declining_issues")
        item["advance_decline_diff"] = (
            None if adv is None or dec is None else adv - dec
        )
        item["advance_decline_pct"] = (
            None
            if adv is None or dec is None or (adv + dec) == 0
            else 100.0 * (adv - dec) / (adv + dec)
        )
        if item["advance_decline_diff"] is None:
            item["advance_decline_line"] = None
        else:
            ad_line += item["advance_decline_diff"]
            have_ad = True
            item["advance_decline_line"] = ad_line if have_ad else None

        upv = row.get("up_volume")
        dnv = row.get("down_volume")
        item["up_down_volume"] = None if upv is None or dnv is None else upv - dnv

        if item["up_down_volume"] is None:
            t10 = None
            t05 = None
            valid_volume_run = 0
            volume_sum = None
            item["volume_trend_10pct"] = None
            item["volume_trend_5pct"] = None
            item["mcclellan_volume_oscillator"] = None
            item["mcclellan_volume_summation"] = None
        else:
            x = float(item["up_down_volume"])
            if t10 is None:
                t10 = x
                t05 = x
                valid_volume_run = 1
            else:
                t10 = 0.10 * x + 0.90 * t10
                t05 = 0.05 * x + 0.95 * t05
                valid_volume_run += 1

            oscillator = t10 - t05
            item["volume_trend_10pct"] = t10
            item["volume_trend_5pct"] = t05

            if valid_volume_run < 39:
                item["mcclellan_volume_oscillator"] = None
                item["mcclellan_volume_summation"] = None
            else:
                item["mcclellan_volume_oscillator"] = oscillator
                if volume_sum is None:
                    volume_sum = 1000.0 + oscillator
                else:
                    volume_sum += oscillator
                item["mcclellan_volume_summation"] = volume_sum

        out.append(item)

    return out


def build_breadth_metrics(
    rows: list[dict],
    fetched_at: datetime | None = None,
) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    derived = _derived_rows(rows)

    specs = [
        ("nyse_new_52w_highs", "NYSE New 52-Week Highs", "new_52w_highs", "count", "contextual", "Daily number of NYSE issues making a new 52-week high."),
        ("nyse_new_52w_lows", "NYSE New 52-Week Lows", "new_52w_lows", "count", "higher_is_riskier", "Daily number of NYSE issues making a new 52-week low."),
        ("nyse_net_new_52w_highs", "NYSE Net New 52-Week Highs", "net_new_52w_highs", "count", "lower_is_riskier", "NYSE new 52-week highs minus new 52-week lows."),
        ("nyse_high_low_pct", "NYSE High-Low Breadth %", "high_low_pct", "percent", "lower_is_riskier", "Net new 52-week highs divided by total active NYSE issues when a consistent denominator is available."),
        ("nyse_advancing_issues", "NYSE Advancing Issues", "advancing_issues", "count", "contextual", "Daily NYSE advancing issues."),
        ("nyse_declining_issues", "NYSE Declining Issues", "declining_issues", "count", "higher_is_riskier", "Daily NYSE declining issues."),
        ("nyse_advance_decline_diff", "NYSE Advance-Decline Difference", "advance_decline_diff", "count", "lower_is_riskier", "NYSE advancing issues minus declining issues."),
        ("nyse_advance_decline_pct", "NYSE Advance-Decline %", "advance_decline_pct", "percent", "lower_is_riskier", "NYSE advance-decline difference normalized by advancing plus declining issues."),
        ("nyse_advance_decline_line", "NYSE Advance-Decline Line", "advance_decline_line", "index", "contextual", "Cumulative NYSE advance-decline difference, initialized at the first valid imported observation."),
        ("nyse_up_volume", "NYSE Up Volume", "up_volume", "shares", "contextual", "Daily NYSE advancing-share volume."),
        ("nyse_down_volume", "NYSE Down Volume", "down_volume", "shares", "higher_is_riskier", "Daily NYSE declining-share volume."),
        ("nyse_up_down_volume", "NYSE Up-Down Volume", "up_down_volume", "shares", "lower_is_riskier", "NYSE up volume minus down volume."),
        ("nyse_volume_trend_10pct", "NYSE Up-Down Volume 10% Trend", "volume_trend_10pct", "shares", "contextual", "10% exponential trend of NYSE up-minus-down volume."),
        ("nyse_volume_trend_5pct", "NYSE Up-Down Volume 5% Trend", "volume_trend_5pct", "shares", "contextual", "5% exponential trend of NYSE up-minus-down volume."),
        ("mrm_mcclellan_volume_oscillator", "MRM McClellan Volume Oscillator", "mcclellan_volume_oscillator", "index", "lower_is_riskier", "10% Trend minus 5% Trend of NYSE up-minus-down volume after a 39-observation warmup."),
        ("mrm_mcclellan_volume_summation", "MRM Classic McClellan Volume Summation", "mcclellan_volume_summation", "index", "lower_is_riskier", "Cumulative MRM McClellan Volume Oscillator initialized at a base of 1000 after warmup."),
    ]

    raw_fields = {
        "new_52w_highs",
        "new_52w_lows",
        "advancing_issues",
        "declining_issues",
        "up_volume",
        "down_volume",
    }

    metrics = {}
    for metric_id, name, field, units, polarity, description in specs:
        if not any(row.get(field) is not None for row in derived):
            continue

        if field in raw_fields:
            lineage = {
                "kind": "raw",
                "inputs": [],
                "formula": None,
                "transform_version": "breadth-raw-v1",
            }
        else:
            formulas = {
                "net_new_52w_highs": "new_52w_highs - new_52w_lows",
                "high_low_pct": "100 * (new_52w_highs - new_52w_lows) / total_issues",
                "advance_decline_diff": "advancing_issues - declining_issues",
                "advance_decline_pct": "100 * (advancing_issues - declining_issues) / (advancing_issues + declining_issues)",
                "advance_decline_line": "cumsum(advancing_issues - declining_issues)",
                "up_down_volume": "up_volume - down_volume",
                "volume_trend_10pct": "0.10*x_t + 0.90*T10_t-1",
                "volume_trend_5pct": "0.05*x_t + 0.95*T05_t-1",
                "mcclellan_volume_oscillator": "T10 - T05 after 39 consecutive valid observations",
                "mcclellan_volume_summation": "1000 + cumulative McClellan Volume Oscillator after warmup",
            }
            input_map = {
                "net_new_52w_highs": ["nyse_new_52w_highs", "nyse_new_52w_lows"],
                "high_low_pct": ["nyse_new_52w_highs", "nyse_new_52w_lows"],
                "advance_decline_diff": ["nyse_advancing_issues", "nyse_declining_issues"],
                "advance_decline_pct": ["nyse_advancing_issues", "nyse_declining_issues"],
                "advance_decline_line": ["nyse_advance_decline_diff"],
                "up_down_volume": ["nyse_up_volume", "nyse_down_volume"],
                "volume_trend_10pct": ["nyse_up_down_volume"],
                "volume_trend_5pct": ["nyse_up_down_volume"],
                "mcclellan_volume_oscillator": ["nyse_up_down_volume"],
                "mcclellan_volume_summation": ["mrm_mcclellan_volume_oscillator"],
            }
            lineage = {
                "kind": "derived",
                "inputs": input_map.get(field, []),
                "formula": formulas.get(field),
                "transform_version": "breadth-derived-v1",
            }

        metrics[metric_id] = _metric(
            derived,
            metric_id=metric_id,
            name=name,
            field=field,
            units=units,
            polarity=polarity,
            fetched_at=fetched_at,
            description=description,
            lineage=lineage,
        )

    return metrics


def write_breadth_metrics(
    rows: list[dict],
    output_dir: Path,
    fetched_at: datetime | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for metric_id, metric in build_breadth_metrics(rows, fetched_at).items():
        dest = output_dir / f"{metric_id}.json"
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(metric, indent=2) + "\n", encoding="utf-8")
        tmp.replace(dest)
        paths.append(dest)
    return paths
