from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path


class MovingAverageBreadthError(ValueError):
    pass


REQUIRED_COLUMNS = {"date", "market_scope", "provider"}

HORIZONS = {
    20: {
        "pct": "above_20dma_pct",
        "eligible": "eligible_20d",
        "count": "above_20d_count",
        "missing": "missing_20d",
        "metric_id": "sp500_above_20dma_pct",
        "name": "S&P 500 % Above 20DMA",
    },
    50: {
        "pct": "above_50dma_pct",
        "eligible": "eligible_50d",
        "count": "above_50d_count",
        "missing": "missing_50d",
        "metric_id": "sp500_above_50dma_pct",
        "name": "S&P 500 % Above 50DMA",
    },
    200: {
        "pct": "above_200dma_pct",
        "eligible": "eligible_200d",
        "count": "above_200d_count",
        "missing": "missing_200d",
        "metric_id": "sp500_above_200dma_pct",
        "name": "S&P 500 % Above 200DMA",
    },
}

META_COLUMNS = {
    "membership_mode",
    "membership_snapshot",
    "price_adjustment",
}


def _text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _number(raw, *, row_number: int, column: str, integer: bool = False):
    text = _text(raw)
    if text is None or text.upper() in {"NA", "N/A", "."}:
        return None
    try:
        value = float(text.replace(",", ""))
    except ValueError as exc:
        raise MovingAverageBreadthError(
            f"row {row_number}: {column} is not numeric: {raw!r}"
        ) from exc
    if integer and not value.is_integer():
        raise MovingAverageBreadthError(
            f"row {row_number}: {column} must be an integer, got {value}"
        )
    return int(value) if integer else value


def _bool_point_in_time(membership_mode: str | None):
    if membership_mode is None:
        return None
    normalized = membership_mode.lower()
    if normalized in {
        "point_in_time",
        "provider_point_in_time",
        "historical_point_in_time",
        "membership_events",
    }:
        return True
    if normalized in {
        "current_constituents_retroactive",
        "current_membership_backfill",
    }:
        return False
    return None


def parse_ma_breadth_csv(
    text: str,
    *,
    required_scope: str = "S&P 500",
) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise MovingAverageBreadthError("moving-average breadth CSV has no header")

    headers = set(reader.fieldnames)
    missing_required = REQUIRED_COLUMNS - headers
    if missing_required:
        raise MovingAverageBreadthError(
            f"moving-average breadth CSV missing columns: {sorted(missing_required)}"
        )

    if not any(spec["pct"] in headers for spec in HORIZONS.values()):
        raise MovingAverageBreadthError(
            "CSV must contain at least one of above_20dma_pct, "
            "above_50dma_pct, above_200dma_pct"
        )

    rows = []
    seen_dates = set()
    scopes = set()
    providers = set()
    membership_modes = set()
    price_adjustments = set()

    for row_number, raw in enumerate(reader, start=2):
        raw_date = _text(raw.get("date"))
        if raw_date is None:
            continue
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise MovingAverageBreadthError(
                f"row {row_number}: invalid date {raw_date!r}"
            ) from exc

        iso_date = parsed_date.isoformat()
        if iso_date in seen_dates:
            raise MovingAverageBreadthError(f"duplicate date: {iso_date}")
        seen_dates.add(iso_date)

        scope = _text(raw.get("market_scope"))
        provider = _text(raw.get("provider"))
        if scope is None:
            raise MovingAverageBreadthError(
                f"row {row_number}: market_scope is blank"
            )
        if provider is None:
            raise MovingAverageBreadthError(
                f"row {row_number}: provider is blank"
            )

        scopes.add(scope)
        providers.add(provider)

        membership_mode = _text(raw.get("membership_mode"))
        membership_snapshot = _text(raw.get("membership_snapshot"))
        price_adjustment = _text(raw.get("price_adjustment"))
        if membership_mode:
            membership_modes.add(membership_mode)
        if price_adjustment:
            price_adjustments.add(price_adjustment)

        item = {
            "date": iso_date,
            "market_scope": scope,
            "provider": provider,
            "membership_mode": membership_mode,
            "membership_snapshot": membership_snapshot,
            "price_adjustment": price_adjustment,
        }

        for horizon, spec in HORIZONS.items():
            pct = _number(
                raw.get(spec["pct"]),
                row_number=row_number,
                column=spec["pct"],
            )
            eligible = _number(
                raw.get(spec["eligible"]),
                row_number=row_number,
                column=spec["eligible"],
                integer=True,
            )
            above_count = _number(
                raw.get(spec["count"]),
                row_number=row_number,
                column=spec["count"],
                integer=True,
            )
            missing_count = _number(
                raw.get(spec["missing"]),
                row_number=row_number,
                column=spec["missing"],
                integer=True,
            )

            for name, value in (
                (spec["eligible"], eligible),
                (spec["count"], above_count),
                (spec["missing"], missing_count),
            ):
                if value is not None and value < 0:
                    raise MovingAverageBreadthError(
                        f"row {row_number}: {name} must be non-negative"
                    )

            if pct is not None and not 0 <= pct <= 100:
                raise MovingAverageBreadthError(
                    f"row {row_number}: {spec['pct']} must be within [0,100], got {pct}"
                )

            if (
                eligible is not None
                and above_count is not None
                and above_count > eligible
            ):
                raise MovingAverageBreadthError(
                    f"row {row_number}: {spec['count']}={above_count} "
                    f"exceeds {spec['eligible']}={eligible}"
                )

            if (
                eligible is not None
                and above_count is not None
                and eligible > 0
            ):
                computed = 100.0 * above_count / eligible
                if pct is None:
                    pct = computed
                elif abs(pct - computed) > 0.15:
                    raise MovingAverageBreadthError(
                        f"row {row_number}: {spec['pct']}={pct:.4f} disagrees "
                        f"with count/eligible={computed:.4f} by more than 0.15pp"
                    )

            item[spec["pct"]] = pct
            item[spec["eligible"]] = eligible
            item[spec["count"]] = above_count
            item[spec["missing"]] = missing_count

        rows.append(item)

    rows.sort(key=lambda row: row["date"])

    if not rows:
        raise MovingAverageBreadthError("moving-average breadth CSV has no rows")
    if len(scopes) != 1 or scopes != {required_scope}:
        raise MovingAverageBreadthError(
            f"market scope must be exactly {required_scope!r}; got {sorted(scopes)}"
        )
    if len(providers) != 1:
        raise MovingAverageBreadthError(
            f"one file must use one provider/export family; got {sorted(providers)}"
        )
    if len(membership_modes) > 1:
        raise MovingAverageBreadthError(
            f"membership_mode must remain constant; got {sorted(membership_modes)}"
        )
    if len(price_adjustments) > 1:
        raise MovingAverageBreadthError(
            f"price_adjustment must remain constant; got {sorted(price_adjustments)}"
        )

    return rows


def _freshness(as_of: str | None, fetched_at: datetime, max_age_days: int = 5):
    if as_of is None:
        return "missing", None
    age = max((fetched_at.date() - date.fromisoformat(as_of)).days, 0)
    return ("fresh" if age <= max_age_days else "stale"), age


def _metric_for_horizon(
    rows: list[dict],
    horizon: int,
    fetched_at: datetime,
) -> dict | None:
    spec = HORIZONS[horizon]
    observations = [
        {
            "date": row["date"],
            "value": row.get(spec["pct"]),
            "status": "observed" if row.get(spec["pct"]) is not None else "missing",
        }
        for row in rows
    ]

    if not any(o["value"] is not None for o in observations):
        return None

    present = [o for o in observations if o["value"] is not None]
    latest = present[-1]
    state, age = _freshness(latest["date"], fetched_at)

    membership_mode = rows[0].get("membership_mode")
    point_in_time = _bool_point_in_time(membership_mode)
    provider = rows[0]["provider"]
    price_adjustment = rows[0].get("price_adjustment")

    count_available = any(
        row.get(spec["count"]) is not None and row.get(spec["eligible"]) is not None
        for row in rows
    )

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": spec["metric_id"],
            "name": spec["name"],
            "description": (
                f"Percentage of eligible S&P 500 constituents above their "
                f"{horizon}-day moving average."
            ),
            "pillar": "breadth",
            "units": "percent",
            "frequency": "daily",
            "polarity": "lower_is_riskier",
        },
        "source": {
            "provider": provider,
            "dataset": "Authorized S&P 500 moving-average breadth export",
            "series_id": None,
            "url": (
                "https://github.com/world4jason/Market-Risk-Monitor/blob/main/"
                "docs/moving-average-breadth-sources.md"
            ),
            "license_note": (
                "Imported from an authorized local/provider export. "
                "Public redistribution rights are not assumed."
            ),
            "redistribution": "unknown",
            "market_scope": "S&P 500",
            "membership_mode": membership_mode,
            "membership_snapshot": rows[-1].get("membership_snapshot"),
            "price_adjustment": price_adjustment,
            "point_in_time_membership": point_in_time,
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
        "lineage": {
            "kind": "raw",
            "inputs": [],
            "formula": (
                f"100 * above_{horizon}d_count / eligible_{horizon}d"
                if count_available
                else None
            ),
            "transform_version": "sp500-ma-breadth-v1",
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
            "as_of": latest["date"],
            "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "value": latest["value"],
            "revision_tag": None,
        },
        "observations": observations,
    }


def build_ma_breadth_metrics(
    rows: list[dict],
    fetched_at: datetime | None = None,
) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    metrics = {}
    for horizon in HORIZONS:
        metric = _metric_for_horizon(rows, horizon, fetched_at)
        if metric is not None:
            metrics[metric["metric"]["id"]] = metric
    return metrics


def audit_rows(rows: list[dict]) -> dict:
    horizons = {}
    for horizon, spec in HORIZONS.items():
        valid = [row for row in rows if row.get(spec["pct"]) is not None]
        horizons[str(horizon)] = {
            "observations": len(valid),
            "first": valid[0]["date"] if valid else None,
            "last": valid[-1]["date"] if valid else None,
            "count_audit_available": sum(
                row.get(spec["count"]) is not None
                and row.get(spec["eligible"]) is not None
                for row in rows
            ),
            "missing_price_audit_available": sum(
                row.get(spec["missing"]) is not None for row in rows
            ),
        }

    return {
        "schema_version": "1.0.0",
        "market_scope": rows[0]["market_scope"],
        "provider": rows[0]["provider"],
        "membership_mode": rows[0].get("membership_mode"),
        "point_in_time_membership": _bool_point_in_time(
            rows[0].get("membership_mode")
        ),
        "price_adjustment": rows[0].get("price_adjustment"),
        "horizons": horizons,
    }


def write_ma_breadth_metrics(
    rows: list[dict],
    output_dir: Path,
    fetched_at: datetime | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for metric_id, metric in build_ma_breadth_metrics(rows, fetched_at).items():
        dest = output_dir / f"{metric_id}.json"
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(metric, indent=2) + "\n", encoding="utf-8")
        tmp.replace(dest)
        written.append(dest)

    audit_dest = output_dir / "ma-breadth-audit.json"
    tmp = audit_dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(audit_rows(rows), indent=2) + "\n", encoding="utf-8")
    tmp.replace(audit_dest)
    written.append(audit_dest)
    return written
