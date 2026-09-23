from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

SOURCE_PAGE = "https://shillerdata.com/"


class ShillerError(RuntimeError):
    pass


def _num(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s in {"", "NA", "N/A"}:
        return None
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return None


def parse_shiller_rows(rows: list[list]) -> list[dict]:
    """
    Parse the current Shiller 'Data' sheet layout.

    Relevant columns:
      0 Date (ambiguous float for Oct vs Jan in some years)
      1 Price
      5 Date Fraction (mid-month; authoritative for deriving month)
      7 Real Price
      9 Real Total Return Price
      12 CAPE

    Date Fraction is used because e.g. 2025.10 and 2025.1 are identical once
    stored as a numeric cell. The monthly sequence is cross-checked from 1871-01.
    """
    series = []
    skipped_tail = 0

    for row_idx, row in enumerate(rows):
        if len(row) <= 12:
            continue
        date_value = _num(row[0])
        frac = _num(row[5])
        if date_value is None or frac is None:
            continue

        year = int(frac)
        month = round((frac - year) * 12 + 0.5)
        if month < 1 or month > 12:
            raise ShillerError(f"Bad month derived from Date Fraction {frac} at row {row_idx}")

        expected_year = 1871 + len(series) // 12
        expected_month = len(series) % 12 + 1
        if year != expected_year or month != expected_month:
            # Shiller's newest workbook can include rows with an incomplete tail.
            # Sequence errors in the historical body are not tolerated.
            if series and year >= expected_year and skipped_tail:
                break
            raise ShillerError(
                f"Monthly sequence broke at row {row_idx}: "
                f"derived {year}-{month:02d}, expected {expected_year}-{expected_month:02d}"
            )

        real_total_return_price = _num(row[9])
        if real_total_return_price is None:
            skipped_tail += 1
            continue

        series.append({
            "date": f"{year:04d}-{month:02d}-01",
            "price": _num(row[1]),
            "real_price": _num(row[7]),
            "real_total_return_price": real_total_return_price,
            "cape": _num(row[12]),
        })

    if len(series) < 120:
        raise ShillerError(f"Parsed only {len(series)} monthly observations; workbook layout likely changed")

    # The live workbook's final row is partial and may contain estimated current
    # month values. Drop it to keep the committed snapshot stable/reproducible.
    series.pop()
    return series


def parse_shiller_xls(path: str | Path) -> list[dict]:
    try:
        import xlrd
    except ImportError as exc:
        raise ShillerError("xlrd is required for Shiller .xls import; install requirements.txt") from exc

    book = xlrd.open_workbook(path)
    try:
        sheet = book.sheet_by_name("Data")
    except Exception as exc:
        raise ShillerError(f"No 'Data' worksheet; found {book.sheet_names()}") from exc
    rows = [sheet.row_values(i) for i in range(sheet.nrows)]
    return parse_shiller_rows(rows)


def _metric(rows: list[dict], *, metric_id: str, name: str, field: str, units: str, pillar: str,
            polarity: str, fetched_at: datetime) -> dict:
    observations = [
        {
            "date": row["date"],
            "value": row[field],
            "status": "observed" if row[field] is not None else "missing",
        }
        for row in rows
    ]
    present = [o for o in observations if o["value"] is not None]
    latest = present[-1] if present else None
    as_of = latest["date"] if latest else None
    age = None if as_of is None else max((fetched_at.date() - date.fromisoformat(as_of)).days, 0)
    state = "missing" if as_of is None else ("fresh" if age <= 75 else "stale")

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": metric_id,
            "name": name,
            "description": "Robert Shiller monthly U.S. stock-market data, excluding the current partial month.",
            "pillar": pillar,
            "units": units,
            "frequency": "monthly",
            "polarity": polarity,
        },
        "source": {
            "provider": "Robert J. Shiller",
            "dataset": "U.S. Stock Market Data used in Irrational Exuberance",
            "series_id": None,
            "url": SOURCE_PAGE,
            "license_note": "Public workbook distributed by Robert Shiller; preserve attribution and provenance.",
            "redistribution": "unknown",
            "availability_basis": "unknown",
        },
        "coverage": {
            "history_start": observations[0]["date"] if observations else None,
            "history_end": observations[-1]["date"] if observations else None,
            "timezone": "America/New_York",
            "expected_observation_lag_days": 35,
        },
        "freshness": {
            "state": state,
            "max_age_days": 75,
            "age_days": age,
            "evaluated_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "reason": "Current partial month intentionally excluded." if latest else None,
        },
        "lineage": {
            "kind": "raw",
            "inputs": [],
            "formula": None,
            "transform_version": "shiller-raw-v1",
        },
        "baselines": [
            {
                "id": "expanding-pit",
                "type": "full_history_percentile",
                "window_observations": None,
                "min_observations": 120,
                "point_in_time": False,
                "notes": "Strict-past by observation order only; exact release timing is not retained, so this is not a canonical PIT baseline.",
            },
            {
                "id": "rolling-120m",
                "type": "rolling_percentile",
                "window_observations": 120,
                "min_observations": 60,
                "point_in_time": False,
                "notes": "Trailing ten-year monthly baseline; exact release timing is not retained, so this is not a canonical PIT baseline.",
            },
        ],
        "latest": {
            "as_of": as_of,
            "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "value": latest["value"] if latest else None,
            "revision_tag": "partial-current-month-excluded",
        },
        "observations": observations,
    }


def build_shiller_metrics(rows: list[dict], fetched_at: datetime | None = None) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    metrics = [
        _metric(
            rows,
            metric_id="shiller_price",
            name="Shiller U.S. Stock Price Index",
            field="price",
            units="index",
            pillar="market",
            polarity="contextual",
            fetched_at=fetched_at,
        ),
        _metric(
            rows,
            metric_id="shiller_cape",
            name="Shiller CAPE",
            field="cape",
            units="ratio",
            pillar="valuation",
            polarity="contextual",
            fetched_at=fetched_at,
        ),
        _metric(
            rows,
            metric_id="shiller_real_tr_price",
            name="Shiller Real Total Return Price",
            field="real_total_return_price",
            units="index",
            pillar="market",
            polarity="contextual",
            fetched_at=fetched_at,
        ),
    ]
    return {m["metric"]["id"]: m for m in metrics}


def refresh_shiller(path: str | Path, output_dir: Path) -> list[Path]:
    rows = parse_shiller_xls(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for metric_id, metric in build_shiller_metrics(rows).items():
        dest = output_dir / f"{metric_id}.json"
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(metric, indent=2) + "\n", encoding="utf-8")
        tmp.replace(dest)
        written.append(dest)
    return written
