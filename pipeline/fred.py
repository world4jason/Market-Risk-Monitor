from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen


FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


class FredError(RuntimeError):
    pass


def _parse_number(raw: str):
    raw = (raw or "").strip()
    if raw in {"", ".", "NA", "N/A"}:
        return None
    return float(raw)


def parse_fred_csv(text: str, series_id: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise FredError("FRED CSV has no header")

    date_col = next((c for c in reader.fieldnames if c.upper() in {"DATE", "OBSERVATION_DATE"}), None)
    if not date_col:
        raise FredError(f"FRED CSV missing date column: {reader.fieldnames}")

    value_col = next((c for c in reader.fieldnames if c == series_id), None)
    if not value_col:
        candidates = [c for c in reader.fieldnames if c != date_col]
        if len(candidates) != 1:
            raise FredError(f"Cannot identify value column for {series_id}: {reader.fieldnames}")
        value_col = candidates[0]

    out: list[dict] = []
    for row in reader:
        raw_date = (row.get(date_col) or "").strip()
        if not raw_date:
            continue
        try:
            parsed = date.fromisoformat(raw_date)
        except ValueError as exc:
            raise FredError(f"Invalid date {raw_date!r}") from exc
        value = _parse_number(row.get(value_col, ""))
        out.append({
            "date": parsed.isoformat(),
            "value": value,
            "status": "observed" if value is not None else "missing",
        })

    out.sort(key=lambda x: x["date"])
    seen = set()
    for obs in out:
        if obs["date"] in seen:
            raise FredError(f"Duplicate observation date {obs['date']}")
        seen.add(obs["date"])
    return out


def fetch_fred_csv(series_id: str, timeout: int = 30) -> str:
    url = FRED_CSV.format(series_id=series_id)
    req = Request(url, headers={"User-Agent": "Market-Risk-Monitor/0.1"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        raise FredError(f"Failed to fetch {series_id} from FRED: {exc}") from exc


def freshness_state(as_of: str | None, evaluated_at: datetime, max_age_days: int):
    if not as_of:
        return {"state": "missing", "age_days": None, "reason": "No non-null observation"}
    obs_date = date.fromisoformat(as_of)
    age = (evaluated_at.date() - obs_date).days
    state = "fresh" if age <= max_age_days else "stale"
    return {"state": state, "age_days": max(age, 0), "reason": None}


def build_metric(config: dict, observations: list[dict], fetched_at: datetime | None = None) -> dict:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    non_null = [o for o in observations if o["value"] is not None]
    latest = non_null[-1] if non_null else None
    as_of = latest["date"] if latest else None
    fresh = freshness_state(as_of, fetched_at, int(config["max_age_days"]))

    history_start = observations[0]["date"] if observations else config.get("expected_history_start")
    history_end = observations[-1]["date"] if observations else None

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": config["id"],
            "name": config["name"],
            "description": config.get("description", ""),
            "pillar": config["pillar"],
            "units": config["units"],
            "frequency": config["frequency"],
            "polarity": config["polarity"],
        },
        "source": {
            "provider": "Federal Reserve Bank of St. Louis (FRED)",
            "dataset": config["dataset"],
            "series_id": config["series_id"],
            "url": f"https://fred.stlouisfed.org/series/{config['series_id']}",
            "license_note": config.get("license_note"),
            "redistribution": config.get("redistribution", "unknown"),
        },
        "coverage": {
            "history_start": history_start,
            "history_end": history_end,
            "timezone": config.get("timezone", "America/Chicago"),
            "expected_observation_lag_days": config.get("expected_observation_lag_days"),
        },
        "freshness": {
            "state": fresh["state"],
            "max_age_days": int(config["max_age_days"]),
            "age_days": fresh["age_days"],
            "evaluated_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "reason": fresh["reason"],
        },
        "lineage": {
            "kind": "raw",
            "inputs": [],
            "formula": None,
            "transform_version": "fred-raw-v1",
        },
        "baselines": config.get("baselines", []),
        "latest": {
            "as_of": as_of,
            "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "value": latest["value"] if latest else None,
            "revision_tag": None,
        },
        "observations": observations,
    }


def refresh_one(config: dict, output_dir: Path, timeout: int = 30) -> Path:
    text = fetch_fred_csv(config["series_id"], timeout=timeout)
    observations = parse_fred_csv(text, config["series_id"])
    metric = build_metric(config, observations)
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / f"{config['id']}.json"
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(metric, indent=2) + "\n", encoding="utf-8")
    tmp.replace(dest)
    return dest
