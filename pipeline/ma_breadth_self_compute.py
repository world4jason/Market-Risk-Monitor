from __future__ import annotations

import csv
import io
from collections import deque
from pathlib import Path


class PointInTimeBreadthError(ValueError):
    pass


HORIZONS = (20, 50, 200)


def parse_historical_membership_csv(text: str) -> list[dict]:
    """
    Parse daily point-in-time S&P 500 membership snapshots in the open
    chinobing/historical_sp500_constituents format:

        date,tickers
        2024-01-02,"AAPL,MSFT,..."
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not {"date", "tickers"}.issubset(reader.fieldnames):
        raise PointInTimeBreadthError(
            "membership CSV must contain date,tickers columns"
        )

    rows = []
    previous = None
    seen = set()

    for row_number, row in enumerate(reader, start=2):
        date = (row.get("date") or "").strip()
        if not date:
            continue
        if date in seen:
            raise PointInTimeBreadthError(f"duplicate membership date {date}")
        if previous is not None and date < previous:
            raise PointInTimeBreadthError(
                f"membership dates must ascend: {date} follows {previous}"
            )
        tickers = [
            ticker.strip()
            for ticker in (row.get("tickers") or "").split(",")
            if ticker.strip()
        ]
        if not tickers:
            raise PointInTimeBreadthError(
                f"row {row_number}: membership snapshot contains no tickers"
            )
        if len(tickers) != len(set(tickers)):
            raise PointInTimeBreadthError(
                f"row {row_number}: membership snapshot contains duplicate tickers"
            )
        rows.append({"date": date, "tickers": tickers})
        seen.add(date)
        previous = date

    if not rows:
        raise PointInTimeBreadthError("membership CSV contains no rows")
    return rows


def parse_price_csv(
    text: str,
    *,
    price_adjustment: str = "adjusted_close",
) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise PointInTimeBreadthError("price CSV has no header")

    date_col = next(
        (c for c in reader.fieldnames if c.lower() == "date"),
        None,
    )
    if date_col is None:
        raise PointInTimeBreadthError("price CSV must contain Date/date")

    if price_adjustment == "adjusted_close":
        aliases = {"adj close", "adjclose", "adjusted_close", "adjusted close"}
    elif price_adjustment == "close":
        aliases = {"close"}
    else:
        raise PointInTimeBreadthError(
            "price_adjustment must be adjusted_close or close"
        )

    value_col = next(
        (c for c in reader.fieldnames if c.strip().lower() in aliases),
        None,
    )
    if value_col is None:
        raise PointInTimeBreadthError(
            f"price CSV missing required {price_adjustment} column"
        )

    rows = []
    seen = set()
    previous = None

    for row_number, row in enumerate(reader, start=2):
        date = (row.get(date_col) or "").strip()
        raw = (row.get(value_col) or "").strip()
        if not date or not raw or raw.upper() in {"NA", "N/A", "NAN", "."}:
            continue
        if date in seen:
            raise PointInTimeBreadthError(f"duplicate price date {date}")
        if previous is not None and date < previous:
            raise PointInTimeBreadthError(
                f"price dates must ascend: {date} follows {previous}"
            )
        try:
            value = float(raw.replace(",", ""))
        except ValueError as exc:
            raise PointInTimeBreadthError(
                f"row {row_number}: non-numeric price {raw!r}"
            ) from exc
        if value <= 0:
            raise PointInTimeBreadthError(
                f"row {row_number}: price must be positive"
            )
        rows.append({"date": date, "price": value})
        seen.add(date)
        previous = date

    if not rows:
        raise PointInTimeBreadthError("price CSV contains no valid observations")
    return rows


def above_ma_flags(
    price_rows: list[dict],
    *,
    horizons: tuple[int, ...] = HORIZONS,
) -> dict[int, dict[str, bool]]:
    """
    Return date -> close > arithmetic SMA_N flags for each horizon.

    The current date is included in the SMA, matching the project methodology.
    A flag is emitted only after N valid price observations exist.
    """
    windows = {h: deque() for h in horizons}
    sums = {h: 0.0 for h in horizons}
    result = {h: {} for h in horizons}

    for row in price_rows:
        value = float(row["price"])
        date = row["date"]

        for horizon in horizons:
            window = windows[horizon]
            window.append(value)
            sums[horizon] += value
            if len(window) > horizon:
                sums[horizon] -= window.popleft()
            if len(window) == horizon:
                sma = sums[horizon] / horizon
                result[horizon][date] = value > sma

    return result


def compute_point_in_time_breadth(
    membership_rows: list[dict],
    price_rows_by_ticker: dict[str, list[dict]],
    *,
    membership_snapshot: str,
    price_adjustment: str,
    provider: str = "MRM self-compute / point-in-time membership",
) -> list[dict]:
    if not membership_snapshot:
        raise PointInTimeBreadthError("membership_snapshot is required")

    flags_by_ticker = {
        ticker: above_ma_flags(rows)
        for ticker, rows in price_rows_by_ticker.items()
        if rows
    }

    output = []

    for membership in membership_rows:
        date = membership["date"]
        tickers = membership["tickers"]
        row = {
            "date": date,
            "market_scope": "S&P 500",
            "provider": provider,
            "membership_mode": "point_in_time",
            "membership_snapshot": membership_snapshot,
            "price_adjustment": price_adjustment,
        }

        for horizon in HORIZONS:
            eligible = 0
            above = 0
            missing = 0

            for ticker in tickers:
                ticker_flags = flags_by_ticker.get(ticker)
                if ticker_flags is None:
                    missing += 1
                    continue
                flag = ticker_flags[horizon].get(date)
                if flag is None:
                    missing += 1
                    continue
                eligible += 1
                if flag:
                    above += 1

            row[f"eligible_{horizon}d"] = eligible
            row[f"above_{horizon}d_count"] = above
            row[f"missing_{horizon}d"] = missing
            row[f"above_{horizon}dma_pct"] = (
                None if eligible == 0 else 100.0 * above / eligible
            )

        output.append(row)

    return output


def load_price_directory(
    directory: str | Path,
    tickers: set[str],
    *,
    price_adjustment: str,
) -> dict[str, list[dict]]:
    directory = Path(directory)
    if not directory.exists():
        raise PointInTimeBreadthError(
            f"price directory does not exist: {directory}"
        )

    out = {}
    for ticker in sorted(tickers):
        candidates = [
            directory / f"{ticker}.csv",
            directory / f"{ticker.replace('.', '-')}.csv",
        ]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            continue
        out[ticker] = parse_price_csv(
            path.read_text(encoding="utf-8-sig"),
            price_adjustment=price_adjustment,
        )
    return out


def to_import_csv(rows: list[dict]) -> str:
    fieldnames = [
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
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                name: "" if row.get(name) is None else row.get(name)
                for name in fieldnames
            }
        )
    return out.getvalue()
