from __future__ import annotations

import bisect
import csv
import sqlite3
import tempfile
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path


class PointInTimeBreadthError(ValueError):
    pass


HORIZONS = (20, 50, 200)


def normalize_ticker(value: str) -> str:
    """
    Normalize common S&P membership / market-data ticker spelling differences.

    The open membership history commonly uses BRK.B / BF.B while many price
    datasets use BRK-B / BF-B.  Both sides are normalized to dash form.
    """
    value = (value or "").strip().upper()
    return value.replace(".", "-")


@dataclass(frozen=True)
class MembershipSnapshot:
    date: str
    tickers: frozenset[str]


def parse_membership_csv(text: str) -> list[MembershipSnapshot]:
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames or not {"date", "tickers"} <= set(reader.fieldnames):
        raise PointInTimeBreadthError("membership CSV must contain date,tickers")

    snapshots: list[MembershipSnapshot] = []
    previous_date: str | None = None
    for row_number, row in enumerate(reader, start=2):
        raw_date = (row.get("date") or "").strip()
        raw_tickers = (row.get("tickers") or "").strip()
        if not raw_date:
            continue
        try:
            parsed = date.fromisoformat(raw_date).isoformat()
        except ValueError as exc:
            raise PointInTimeBreadthError(
                f"membership row {row_number}: invalid date {raw_date!r}"
            ) from exc

        if previous_date is not None and parsed <= previous_date:
            raise PointInTimeBreadthError(
                "membership dates must be strictly increasing; "
                f"{parsed} follows {previous_date}"
            )
        previous_date = parsed

        tickers = frozenset(
            normalize_ticker(ticker)
            for ticker in raw_tickers.split(",")
            if normalize_ticker(ticker)
        )
        if not tickers:
            raise PointInTimeBreadthError(
                f"membership row {row_number}: ticker list is empty"
            )
        snapshots.append(MembershipSnapshot(parsed, tickers))

    if not snapshots:
        raise PointInTimeBreadthError("membership CSV has no snapshots")
    return snapshots


def membership_for_date(
    snapshots: list[MembershipSnapshot],
    target_date: str,
) -> MembershipSnapshot | None:
    dates = [snapshot.date for snapshot in snapshots]
    index = bisect.bisect_right(dates, target_date) - 1
    return snapshots[index] if index >= 0 else None


def _detect_price_columns(fieldnames: list[str] | None) -> tuple[str, str, str]:
    if not fieldnames:
        raise PointInTimeBreadthError("price CSV has no header")
    lower = {name.lower(): name for name in fieldnames}

    date_col = lower.get("date")
    symbol_col = lower.get("symbol") or lower.get("ticker")
    adjusted_col = (
        lower.get("adjusted_close")
        or lower.get("adj_close")
        or lower.get("adjusted close")
        or lower.get("adj close")
    )
    if not date_col or not symbol_col or not adjusted_col:
        raise PointInTimeBreadthError(
            "price CSV requires date, symbol/ticker, adjusted_close/adj_close"
        )
    return date_col, symbol_col, adjusted_col


def _create_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")
    conn.executescript(
        """
        CREATE TABLE prices (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            adjusted_close REAL NOT NULL,
            PRIMARY KEY(symbol, date)
        ) WITHOUT ROWID;

        CREATE TABLE flags (
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            above20 INTEGER,
            above50 INTEGER,
            above200 INTEGER,
            PRIMARY KEY(date, symbol)
        ) WITHOUT ROWID;

        CREATE INDEX idx_flags_date ON flags(date);
        """
    )
    return conn


def ingest_prices_csv(price_path: Path, conn: sqlite3.Connection) -> dict:
    inserted = 0
    skipped = 0
    min_date = None
    max_date = None

    with price_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        date_col, symbol_col, adjusted_col = _detect_price_columns(reader.fieldnames)

        batch = []
        for row_number, row in enumerate(reader, start=2):
            raw_date = (row.get(date_col) or "").strip()
            symbol = normalize_ticker(row.get(symbol_col) or "")
            raw_price = (row.get(adjusted_col) or "").strip()
            if not raw_date or not symbol or not raw_price:
                skipped += 1
                continue
            try:
                parsed_date = date.fromisoformat(raw_date[:10]).isoformat()
                price = float(raw_price)
            except (ValueError, TypeError):
                skipped += 1
                continue
            if price <= 0:
                skipped += 1
                continue

            batch.append((symbol, parsed_date, price))
            min_date = parsed_date if min_date is None else min(min_date, parsed_date)
            max_date = parsed_date if max_date is None else max(max_date, parsed_date)

            if len(batch) >= 50000:
                conn.executemany(
                    "INSERT OR REPLACE INTO prices(symbol,date,adjusted_close) VALUES (?,?,?)",
                    batch,
                )
                inserted += len(batch)
                batch.clear()

        if batch:
            conn.executemany(
                "INSERT OR REPLACE INTO prices(symbol,date,adjusted_close) VALUES (?,?,?)",
                batch,
            )
            inserted += len(batch)

    conn.commit()
    if inserted == 0:
        raise PointInTimeBreadthError("no usable price rows were ingested")
    return {
        "rows": inserted,
        "skipped": skipped,
        "first_date": min_date,
        "last_date": max_date,
    }


def compute_flags(conn: sqlite3.Connection) -> dict:
    """
    Compute close > SMA20/50/200 per ticker.

    The SQLite ORDER BY makes this deterministic even when the source CSV is
    grouped by ticker, grouped by date, or otherwise unsorted.
    """
    current_symbol = None
    windows = {h: deque(maxlen=h) for h in HORIZONS}
    sums = {h: 0.0 for h in HORIZONS}
    batch = []
    rows = 0

    cursor = conn.execute(
        "SELECT symbol,date,adjusted_close FROM prices ORDER BY symbol,date"
    )
    for symbol, obs_date, price in cursor:
        if symbol != current_symbol:
            current_symbol = symbol
            windows = {h: deque(maxlen=h) for h in HORIZONS}
            sums = {h: 0.0 for h in HORIZONS}

        flags = {}
        for horizon in HORIZONS:
            window = windows[horizon]
            if len(window) == horizon:
                sums[horizon] -= window[0]
            window.append(price)
            sums[horizon] += price

            if len(window) < horizon:
                flags[horizon] = None
            else:
                sma = sums[horizon] / horizon
                flags[horizon] = 1 if price > sma else 0

        batch.append(
            (
                obs_date,
                symbol,
                flags[20],
                flags[50],
                flags[200],
            )
        )
        rows += 1

        if len(batch) >= 50000:
            conn.executemany(
                """
                INSERT OR REPLACE INTO flags(date,symbol,above20,above50,above200)
                VALUES (?,?,?,?,?)
                """,
                batch,
            )
            batch.clear()

    if batch:
        conn.executemany(
            """
            INSERT OR REPLACE INTO flags(date,symbol,above20,above50,above200)
            VALUES (?,?,?,?,?)
            """,
            batch,
        )
    conn.commit()
    return {"rows": rows}


def _date_rows(conn: sqlite3.Connection):
    for (obs_date,) in conn.execute(
        "SELECT DISTINCT date FROM flags ORDER BY date"
    ):
        yield obs_date


def aggregate_point_in_time_breadth(
    conn: sqlite3.Connection,
    snapshots: list[MembershipSnapshot],
    *,
    provider: str,
    price_adjustment: str = "adjusted_close",
    min_coverage: float = 0.90,
) -> list[dict]:
    if not 0 < min_coverage <= 1:
        raise PointInTimeBreadthError("min_coverage must be within (0,1]")

    output = []
    for obs_date in _date_rows(conn):
        snapshot = membership_for_date(snapshots, obs_date)
        if snapshot is None:
            continue

        rows = conn.execute(
            "SELECT symbol,above20,above50,above200 FROM flags WHERE date=?",
            (obs_date,),
        ).fetchall()
        by_symbol = {
            symbol: (above20, above50, above200)
            for symbol, above20, above50, above200 in rows
        }

        result = {
            "date": obs_date,
            "market_scope": "S&P 500",
            "provider": provider,
            "membership_mode": "point_in_time",
            "membership_snapshot": snapshot.date,
            "price_adjustment": price_adjustment,
        }

        members = snapshot.tickers
        total_members = len(members)
        for index, horizon in enumerate(HORIZONS):
            valid_flags = [
                by_symbol[symbol][index]
                for symbol in members
                if symbol in by_symbol and by_symbol[symbol][index] is not None
            ]
            eligible = len(valid_flags)
            above = sum(valid_flags)
            missing = total_members - eligible
            coverage = eligible / total_members if total_members else 0.0

            result[f"eligible_{horizon}d"] = eligible
            result[f"above_{horizon}d_count"] = above
            result[f"missing_{horizon}d"] = missing
            result[f"above_{horizon}dma_pct"] = (
                100.0 * above / eligible
                if eligible and coverage >= min_coverage
                else None
            )

        # At least one horizon must have sufficient coverage.
        if any(
            result[f"above_{horizon}dma_pct"] is not None
            for horizon in HORIZONS
        ):
            output.append(result)

    if not output:
        raise PointInTimeBreadthError(
            "no breadth rows met the minimum coverage requirement"
        )
    return output


OUTPUT_FIELDS = [
    "date",
    "market_scope",
    "provider",
    "above_20dma_pct",
    "above_50dma_pct",
    "above_200dma_pct",
    "eligible_20d",
    "eligible_50d",
    "eligible_200d",
    "above_20d_count",
    "above_50d_count",
    "above_200d_count",
    "missing_20d",
    "missing_50d",
    "missing_200d",
    "membership_mode",
    "membership_snapshot",
    "price_adjustment",
]


def write_output_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    tmp.replace(path)


def compute_from_files(
    membership_path: Path,
    price_path: Path,
    output_path: Path,
    *,
    provider: str = "Open PIT membership + FINSABER",
    min_coverage: float = 0.90,
    work_db: Path | None = None,
) -> dict:
    snapshots = parse_membership_csv(
        membership_path.read_text(encoding="utf-8-sig")
    )

    temporary = None
    if work_db is None:
        temporary = tempfile.TemporaryDirectory(prefix="mrm-ma-breadth-")
        work_db = Path(temporary.name) / "work.sqlite3"
    else:
        work_db.parent.mkdir(parents=True, exist_ok=True)
        if work_db.exists():
            work_db.unlink()

    try:
        conn = _create_db(work_db)
        price_report = ingest_prices_csv(price_path, conn)
        flag_report = compute_flags(conn)
        breadth_rows = aggregate_point_in_time_breadth(
            conn,
            snapshots,
            provider=provider,
            min_coverage=min_coverage,
        )
        conn.close()

        write_output_csv(breadth_rows, output_path)
        return {
            "membership_snapshots": len(snapshots),
            "membership_start": snapshots[0].date,
            "membership_end": snapshots[-1].date,
            "price": price_report,
            "flags": flag_report,
            "output_rows": len(breadth_rows),
            "output_start": breadth_rows[0]["date"],
            "output_end": breadth_rows[-1]["date"],
            "min_coverage": min_coverage,
            "output": str(output_path),
        }
    finally:
        if temporary is not None:
            temporary.cleanup()
