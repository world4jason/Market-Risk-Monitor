from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
from collections import deque
from datetime import date, datetime, timezone
from pathlib import Path

from .artifacts import write_json_artifact


class TaiwanTrendBreadthError(ValueError):
    pass


MA_HORIZONS = (20, 50, 200)
HIGH_LOW_WINDOW = 252
MARKET_SCOPE = "TWSE listed common stocks"


def normalize_tw_symbol(value: str) -> str:
    return str(value or "").strip().upper()


def _number(value):
    text = str(value or "").strip().replace(",", "")
    if text in {"", "--", "---", "NA", "N/A"}:
        return None
    return float(text)


def create_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.executescript(
        """
        CREATE TABLE prices (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            high REAL,
            low REAL,
            close REAL,
            PRIMARY KEY(symbol,date)
        ) WITHOUT ROWID;

        CREATE TABLE flags (
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            above20 INTEGER,
            above50 INTEGER,
            above200 INTEGER,
            new_high_52w INTEGER,
            new_low_52w INTEGER,
            PRIMARY KEY(date,symbol)
        ) WITHOUT ROWID;

        CREATE INDEX idx_tw_flags_date ON flags(date);
        """
    )
    return conn


def ingest_panel_csv(
    path: Path,
    conn: sqlite3.Connection,
) -> dict:
    """
    Input contract:
      date,symbol,high,low,close,market_scope,provider,membership_mode,price_adjustment

    Each row represents a security eligible for the breadth universe on that date.
    A missing close/high/low stays in the universe and becomes explicit missing
    breadth coverage, never an automatic bearish flag.
    """
    rows = 0
    scopes = set()
    providers = set()
    modes = set()
    adjustments = set()
    first_date = None
    last_date = None
    previous_key = None
    batch = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "date",
            "symbol",
            "high",
            "low",
            "close",
            "market_scope",
            "provider",
            "membership_mode",
            "price_adjustment",
        }
        if not reader.fieldnames:
            raise TaiwanTrendBreadthError("Taiwan panel CSV has no header")
        missing = required - set(reader.fieldnames)
        if missing:
            raise TaiwanTrendBreadthError(
                f"Taiwan panel CSV missing {sorted(missing)}"
            )

        for line_no, raw in enumerate(reader, start=2):
            try:
                obs_date = date.fromisoformat(
                    (raw.get("date") or "").strip()
                ).isoformat()
            except ValueError as exc:
                raise TaiwanTrendBreadthError(
                    f"row {line_no}: invalid date"
                ) from exc

            symbol = normalize_tw_symbol(raw.get("symbol"))
            if not symbol:
                raise TaiwanTrendBreadthError(
                    f"row {line_no}: blank symbol"
                )

            key = (obs_date, symbol)
            if previous_key is not None and key <= previous_key:
                raise TaiwanTrendBreadthError(
                    "panel rows must be strictly ordered by date,symbol; "
                    f"{key} follows {previous_key}"
                )
            previous_key = key

            scope = (raw.get("market_scope") or "").strip()
            provider = (raw.get("provider") or "").strip()
            mode = (raw.get("membership_mode") or "").strip()
            adjustment = (raw.get("price_adjustment") or "").strip()
            if not scope or not provider or not mode or not adjustment:
                raise TaiwanTrendBreadthError(
                    f"row {line_no}: scope/provider/membership/price adjustment required"
                )
            scopes.add(scope)
            providers.add(provider)
            modes.add(mode)
            adjustments.add(adjustment)

            high = _number(raw.get("high"))
            low = _number(raw.get("low"))
            close = _number(raw.get("close"))
            for field, value in (("high", high), ("low", low), ("close", close)):
                if value is not None and value <= 0:
                    raise TaiwanTrendBreadthError(
                        f"row {line_no}: {field} must be positive"
                    )

            batch.append((symbol, obs_date, high, low, close))
            rows += 1
            first_date = obs_date if first_date is None else min(first_date, obs_date)
            last_date = obs_date if last_date is None else max(last_date, obs_date)

            if len(batch) >= 50000:
                conn.executemany(
                    "INSERT INTO prices(symbol,date,high,low,close) VALUES (?,?,?,?,?)",
                    batch,
                )
                batch.clear()

    if batch:
        conn.executemany(
            "INSERT INTO prices(symbol,date,high,low,close) VALUES (?,?,?,?,?)",
            batch,
        )
    conn.commit()

    if rows == 0:
        raise TaiwanTrendBreadthError("Taiwan panel CSV has no rows")
    if scopes != {MARKET_SCOPE}:
        raise TaiwanTrendBreadthError(
            f"market_scope must be exactly {MARKET_SCOPE!r}; got {sorted(scopes)}"
        )
    if len(providers) != 1:
        raise TaiwanTrendBreadthError(
            f"one panel must use one provider; got {sorted(providers)}"
        )
    if len(modes) != 1:
        raise TaiwanTrendBreadthError(
            f"one panel must use one membership_mode; got {sorted(modes)}"
        )
    if len(adjustments) != 1:
        raise TaiwanTrendBreadthError(
            f"one panel must use one price_adjustment; got {sorted(adjustments)}"
        )

    return {
        "rows": rows,
        "first_date": first_date,
        "last_date": last_date,
        "provider": next(iter(providers)),
        "membership_mode": next(iter(modes)),
        "price_adjustment": next(iter(adjustments)),
        "market_scope": next(iter(scopes)),
    }


def compute_flags(conn: sqlite3.Connection) -> int:
    current_symbol = None
    close_windows = {h: deque(maxlen=h) for h in MA_HORIZONS}
    close_sums = {h: 0.0 for h in MA_HORIZONS}
    high_window = deque(maxlen=HIGH_LOW_WINDOW - 1)
    low_window = deque(maxlen=HIGH_LOW_WINDOW - 1)
    batch = []
    count = 0

    rows = conn.execute(
        "SELECT symbol,date,high,low,close FROM prices ORDER BY symbol,date"
    )
    for symbol, obs_date, high, low, close in rows:
        if symbol != current_symbol:
            current_symbol = symbol
            close_windows = {h: deque(maxlen=h) for h in MA_HORIZONS}
            close_sums = {h: 0.0 for h in MA_HORIZONS}
            high_window = deque(maxlen=HIGH_LOW_WINDOW - 1)
            low_window = deque(maxlen=HIGH_LOW_WINDOW - 1)

        above = {}
        for horizon in MA_HORIZONS:
            window = close_windows[horizon]
            if close is None:
                above[horizon] = None
                # Missing closes break SMA continuity for that symbol.
                window.clear()
                close_sums[horizon] = 0.0
                continue

            if len(window) == horizon:
                close_sums[horizon] -= window[0]
            window.append(close)
            close_sums[horizon] += close
            above[horizon] = (
                None
                if len(window) < horizon
                else 1 if close > close_sums[horizon] / horizon else 0
            )

        new_high = None
        new_low = None
        if high is None or low is None:
            high_window.clear()
            low_window.clear()
        else:
            if (
                len(high_window) == HIGH_LOW_WINDOW - 1
                and len(low_window) == HIGH_LOW_WINDOW - 1
            ):
                new_high = 1 if high >= max(high_window) else 0
                new_low = 1 if low <= min(low_window) else 0
            high_window.append(high)
            low_window.append(low)

        batch.append(
            (
                obs_date,
                symbol,
                above[20],
                above[50],
                above[200],
                new_high,
                new_low,
            )
        )
        count += 1
        if len(batch) >= 50000:
            conn.executemany(
                """
                INSERT INTO flags(
                    date,symbol,above20,above50,above200,new_high_52w,new_low_52w
                ) VALUES (?,?,?,?,?,?,?)
                """,
                batch,
            )
            batch.clear()

    if batch:
        conn.executemany(
            """
            INSERT INTO flags(
                date,symbol,above20,above50,above200,new_high_52w,new_low_52w
            ) VALUES (?,?,?,?,?,?,?)
            """,
            batch,
        )
    conn.commit()
    return count


def aggregate_daily(conn: sqlite3.Connection) -> list[dict]:
    output = []
    dates = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT date FROM flags ORDER BY date"
        )
    ]
    for obs_date in dates:
        rows = conn.execute(
            """
            SELECT above20,above50,above200,new_high_52w,new_low_52w
            FROM flags WHERE date=?
            """,
            (obs_date,),
        ).fetchall()
        total = len(rows)
        row = {"date": obs_date, "total_members": total}

        for index, horizon in enumerate(MA_HORIZONS):
            values = [item[index] for item in rows if item[index] is not None]
            eligible = len(values)
            above = sum(values)
            row[f"eligible_{horizon}d"] = eligible
            row[f"above_{horizon}d_count"] = above
            row[f"missing_{horizon}d"] = total - eligible
            row[f"above_{horizon}dma_pct"] = (
                None if not eligible else 100.0 * above / eligible
            )

        high_values = [item[3] for item in rows if item[3] is not None]
        low_values = [item[4] for item in rows if item[4] is not None]
        if high_values and low_values:
            highs = sum(high_values)
            lows = sum(low_values)
            eligible = min(len(high_values), len(low_values))
            row["eligible_52w"] = eligible
            row["new_52w_highs"] = highs
            row["new_52w_lows"] = lows
            row["net_new_52w_highs"] = highs - lows
            row["high_low_pct"] = (
                100.0 * (highs - lows) / eligible
                if eligible
                else None
            )
        else:
            row.update(
                {
                    "eligible_52w": 0,
                    "new_52w_highs": None,
                    "new_52w_lows": None,
                    "net_new_52w_highs": None,
                    "high_low_pct": None,
                }
            )
        output.append(row)
    return output


def _metric(
    rows: list[dict],
    meta: dict,
    *,
    metric_id: str,
    name: str,
    field: str,
    units: str,
    polarity: str,
    lineage: dict,
    fetched_at: datetime,
) -> dict | None:
    observations = [
        {
            "date": row["date"],
            "value": row.get(field),
            "status": "observed" if row.get(field) is not None else "missing",
        }
        for row in rows
    ]
    present = [o for o in observations if o["value"] is not None]
    if not present:
        return None
    latest = present[-1]
    age = max(
        (fetched_at.date() - date.fromisoformat(latest["date"])).days,
        0,
    )
    pit = meta["membership_mode"] in {
        "point_in_time",
        "daily_point_in_time",
        "official_daily_snapshot",
    }

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": metric_id,
            "name": name,
            "description": (
                "Transparent TWSE common-stock trend/extreme breadth. "
                "Historical canonical use depends on point-in-time membership."
            ),
            "pillar": "breadth",
            "units": units,
            "frequency": "daily",
            "polarity": polarity,
        },
        "source": {
            "provider": meta["provider"],
            "dataset": "TWSE common-stock daily panel",
            "series_id": None,
            "url": "https://www.twse.com.tw/en/trading/historical/stock-day.html",
            "license_note": (
                "Source panel provenance must be retained. Official public daily "
                "history is available from 2010-01-04; corporate-action adjustment "
                "convention is explicit in price_adjustment."
            ),
            "redistribution": "unknown",
            "market_scope": MARKET_SCOPE,
            "membership_mode": meta["membership_mode"],
            "membership_snapshot": None,
            "price_adjustment": meta["price_adjustment"],
            "point_in_time_membership": pit,
        },
        "coverage": {
            "history_start": observations[0]["date"],
            "history_end": observations[-1]["date"],
            "timezone": "Asia/Taipei",
            "expected_observation_lag_days": 1,
        },
        "freshness": {
            "state": "fresh" if age <= 5 else "stale",
            "max_age_days": 5,
            "age_days": age,
            "evaluated_at": fetched_at.isoformat().replace("+00:00", "Z"),
            "reason": None,
        },
        "lineage": lineage,
        "baselines": [
            {
                "id": "expanding-pit",
                "type": "full_history_percentile",
                "window_observations": None,
                "min_observations": 252,
                "point_in_time": True,
                "notes": "Use canonically only for point-in-time membership.",
            },
            {
                "id": "rolling-1260d",
                "type": "rolling_percentile",
                "window_observations": 1260,
                "min_observations": 504,
                "point_in_time": True,
                "notes": "Approximate trailing five trading years.",
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


def build_metrics(
    daily: list[dict],
    meta: dict,
    fetched_at: datetime | None = None,
) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    specs = [
        ("tw_above_20dma_pct", "TWSE Common Stocks % Above 20DMA", "above_20dma_pct", "percent", "lower_is_riskier"),
        ("tw_above_50dma_pct", "TWSE Common Stocks % Above 50DMA", "above_50dma_pct", "percent", "lower_is_riskier"),
        ("tw_above_200dma_pct", "TWSE Common Stocks % Above 200DMA", "above_200dma_pct", "percent", "lower_is_riskier"),
        ("tw_new_52w_highs", "TWSE New 52-Week Highs", "new_52w_highs", "count", "contextual"),
        ("tw_new_52w_lows", "TWSE New 52-Week Lows", "new_52w_lows", "count", "higher_is_riskier"),
        ("tw_net_new_52w_highs", "TWSE Net New 52-Week Highs", "net_new_52w_highs", "count", "lower_is_riskier"),
        ("tw_high_low_pct", "TWSE High-Low Breadth %", "high_low_pct", "percent", "lower_is_riskier"),
    ]
    metrics = {}
    for metric_id, name, field, units, polarity in specs:
        if field.startswith("above_"):
            lineage = {
                "kind": "derived",
                "inputs": [],
                "formula": (
                    f"100 * above / eligible; moving average includes current "
                    f"close and requires its full trading-session window"
                ),
                "transform_version": "tw-trend-breadth-v1",
            }
        elif field in {"new_52w_highs", "new_52w_lows"}:
            lineage = {
                "kind": "derived",
                "inputs": [],
                "formula": (
                    "current high/low is >=/<=' previous 251-session extreme; "
                    "requires 252 valid symbol observations"
                ),
                "transform_version": "tw-high-low-v1",
            }
        elif field == "net_new_52w_highs":
            lineage = {
                "kind": "derived",
                "inputs": ["tw_new_52w_highs", "tw_new_52w_lows"],
                "formula": "new_52w_highs - new_52w_lows",
                "transform_version": "tw-high-low-v1",
            }
        else:
            lineage = {
                "kind": "derived",
                "inputs": ["tw_new_52w_highs", "tw_new_52w_lows"],
                "formula": "100 * (new_highs - new_lows) / eligible_52w",
                "transform_version": "tw-high-low-v1",
            }

        metric = _metric(
            daily,
            meta,
            metric_id=metric_id,
            name=name,
            field=field,
            units=units,
            polarity=polarity,
            lineage=lineage,
            fetched_at=fetched_at,
        )
        if metric:
            metrics[metric_id] = metric
    return metrics


def build_audit(daily: list[dict], meta: dict) -> dict:
    return {
        "schema_version": "1.0.0",
        "market_scope": MARKET_SCOPE,
        "provider": meta["provider"],
        "membership_mode": meta["membership_mode"],
        "point_in_time_membership": meta["membership_mode"] in {
            "point_in_time",
            "daily_point_in_time",
            "official_daily_snapshot",
        },
        "price_adjustment": meta["price_adjustment"],
        "history_start": daily[0]["date"] if daily else None,
        "history_end": daily[-1]["date"] if daily else None,
        "observations": daily,
    }


def compute_from_panel(
    input_path: Path,
    output_dir: Path,
    *,
    work_db: Path | None = None,
) -> dict:
    temporary = None
    if work_db is None:
        temporary = tempfile.TemporaryDirectory(prefix="mrm-tw-breadth-")
        work_db = Path(temporary.name) / "work.sqlite3"
    else:
        work_db.parent.mkdir(parents=True, exist_ok=True)
        if work_db.exists():
            work_db.unlink()

    try:
        conn = create_db(work_db)
        meta = ingest_panel_csv(input_path, conn)
        flag_rows = compute_flags(conn)
        daily = aggregate_daily(conn)
        conn.close()

        output_dir.mkdir(parents=True, exist_ok=True)
        metrics = build_metrics(daily, meta)
        for metric_id, metric in metrics.items():
            write_json_artifact(output_dir / f"{metric_id}.json", metric)

        audit_path = output_dir / "taiwan-trend-breadth-audit.json"
        write_json_artifact(audit_path, build_audit(daily, meta))

        return {
            **meta,
            "flag_rows": flag_rows,
            "daily_rows": len(daily),
            "output_start": daily[0]["date"] if daily else None,
            "output_end": daily[-1]["date"] if daily else None,
            "metrics": sorted(metrics),
            "audit": str(audit_path),
        }
    finally:
        if temporary is not None:
            temporary.cleanup()
