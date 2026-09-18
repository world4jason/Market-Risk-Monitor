from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

VIX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
SOURCE_PAGE = "https://www.cboe.com/tradable_products/vix/vix_historical_data"


class CboeError(RuntimeError):
    pass


def _number(raw):
    raw = (raw or "").strip()
    if raw in {"", ".", "NA", "N/A"}:
        return None
    return float(raw)


def parse_vix_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CboeError("Cboe VIX CSV has no header")
    headers = {h.upper(): h for h in reader.fieldnames}
    if "DATE" not in headers or "CLOSE" not in headers:
        raise CboeError(f"Expected DATE and CLOSE columns; got {reader.fieldnames}")

    out = []
    for row in reader:
        raw_date = (row.get(headers["DATE"]) or "").strip()
        if not raw_date:
            continue
        parsed = None
        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                pass
        if parsed is None:
            raise CboeError(f"Invalid VIX date: {raw_date!r}")
        value = _number(row.get(headers["CLOSE"]))
        out.append({
            "date": parsed.isoformat(),
            "value": value,
            "status": "observed" if value is not None else "missing",
        })

    out.sort(key=lambda o: o["date"])
    dates = [o["date"] for o in out]
    if len(dates) != len(set(dates)):
        raise CboeError("Duplicate VIX observation date")
    return out


def fetch_vix_csv(timeout: int = 30) -> str:
    req = Request(VIX_URL, headers={"User-Agent": "Market-Risk-Monitor/0.1"})
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8-sig")
    except Exception as exc:
        raise CboeError(f"Failed to fetch Cboe VIX history: {exc}") from exc


def build_vix_metric(observations: list[dict], fetched_at: datetime | None = None) -> dict:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    present = [o for o in observations if o["value"] is not None]
    latest = present[-1] if present else None
    as_of = latest["date"] if latest else None

    age = None if as_of is None else max((fetched_at.date() - date.fromisoformat(as_of)).days, 0)
    state = "missing" if as_of is None else ("fresh" if age <= 5 else "stale")

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": "vix",
            "name": "Cboe Volatility Index (VIX)",
            "description": "Daily VIX closing level from Cboe's official historical CSV.",
            "pillar": "volatility",
            "units": "index",
            "frequency": "daily",
            "polarity": "higher_is_riskier",
        },
        "source": {
            "provider": "Cboe Global Markets",
            "dataset": "VIX Historical Price Data",
            "series_id": "VIX",
            "url": SOURCE_PAGE,
            "license_note": "Cboe official historical-data page; review Cboe terms before third-party redistribution outside this project.",
            "redistribution": "unknown",
        },
        "coverage": {
            "history_start": observations[0]["date"] if observations else None,
            "history_end": observations[-1]["date"] if observations else None,
            "timezone": "America/Chicago",
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
            "formula": None,
            "transform_version": "cboe-vix-raw-v1",
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


def refresh_vix(output_dir: Path, timeout: int = 30) -> Path:
    metric = build_vix_metric(parse_vix_csv(fetch_vix_csv(timeout=timeout)))
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / "vix.json"
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(metric, indent=2) + "\n", encoding="utf-8")
    tmp.replace(dest)
    return dest
