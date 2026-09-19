from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

from .ma_breadth_pit import MembershipSnapshot


class RecentPriceError(RuntimeError):
    pass


PRICE_FIELDS = [
    "date",
    "symbol",
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
]


def tickers_for_window(
    snapshots: list[MembershipSnapshot],
    start_date: str,
    end_date: str,
) -> list[str]:
    """
    Return every ticker that can be required by PIT membership during the window.

    Include the latest snapshot before start_date plus all snapshots through
    end_date so removals/replacements during the window are not silently lost.
    """
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        raise RecentPriceError("end_date must be >= start_date")

    latest_before = None
    selected = []
    for snapshot in snapshots:
        snapshot_date = date.fromisoformat(snapshot.date)
        if snapshot_date <= start:
            latest_before = snapshot
        if start < snapshot_date <= end:
            selected.append(snapshot)

    if latest_before is not None:
        selected.insert(0, latest_before)

    tickers = set()
    for snapshot in selected:
        tickers.update(snapshot.tickers)
    if not tickers:
        raise RecentPriceError(
            f"no constituent membership found for {start_date}..{end_date}"
        )
    return sorted(tickers)


def _extract_ticker_frame(data, ticker: str):
    """
    Normalize yfinance's current MultiIndex/single-index return shapes.
    """
    import pandas as pd

    if data is None or data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        level0 = set(str(x) for x in data.columns.get_level_values(0))
        level1 = set(str(x) for x in data.columns.get_level_values(1))
        if ticker in level0:
            frame = data[ticker].copy()
        elif ticker in level1:
            frame = data.xs(ticker, axis=1, level=1).copy()
        else:
            return None
    else:
        frame = data.copy()

    frame = frame.dropna(how="all")
    return None if frame.empty else frame


def _field(frame, candidates: tuple[str, ...]):
    columns = {str(column).lower(): column for column in frame.columns}
    for candidate in candidates:
        column = columns.get(candidate.lower())
        if column is not None:
            return column
    return None


def fetch_yfinance_recent(
    tickers: list[str],
    *,
    start_date: str,
    end_date: str,
    output_path: Path,
    failures_path: Path,
    batch_size: int = 75,
) -> dict:
    """
    Fetch recent daily prices with yfinance for local research use only.

    Yahoo Finance data rights are not granted by the yfinance software license.
    The caller is responsible for complying with Yahoo's terms. Raw files should
    remain local and uncommitted.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RecentPriceError(
            "yfinance is required; install requirements-research.txt"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    failures_path.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    failures: dict[str, str] = {}
    seen = set()

    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRICE_FIELDS)
        writer.writeheader()

        for offset in range(0, len(tickers), batch_size):
            batch = tickers[offset : offset + batch_size]
            try:
                data = yf.download(
                    batch,
                    start=start_date,
                    end=end_date,
                    interval="1d",
                    auto_adjust=False,
                    actions=False,
                    threads=True,
                    progress=False,
                    group_by="ticker",
                    multi_level_index=True,
                )
            except Exception as exc:
                for ticker in batch:
                    failures[ticker] = f"batch download failed: {exc}"
                continue

            for ticker in batch:
                frame = _extract_ticker_frame(data, ticker)
                if frame is None:
                    failures[ticker] = "no rows returned"
                    continue

                open_col = _field(frame, ("Open",))
                high_col = _field(frame, ("High",))
                low_col = _field(frame, ("Low",))
                close_col = _field(frame, ("Close",))
                adj_col = _field(frame, ("Adj Close", "Adjusted Close"))
                volume_col = _field(frame, ("Volume",))

                if adj_col is None:
                    failures[ticker] = "adjusted close missing"
                    continue

                ticker_rows = 0
                for index, row in frame.iterrows():
                    adjusted = row.get(adj_col)
                    if adjusted is None:
                        continue
                    try:
                        if adjusted != adjusted or float(adjusted) <= 0:
                            continue
                    except (TypeError, ValueError):
                        continue

                    obs_date = index.date().isoformat()
                    key = (ticker, obs_date)
                    if key in seen:
                        continue
                    seen.add(key)

                    def value(column):
                        if column is None:
                            return ""
                        raw = row.get(column)
                        try:
                            return "" if raw != raw else raw
                        except TypeError:
                            return raw

                    writer.writerow(
                        {
                            "date": obs_date,
                            "symbol": ticker,
                            "open": value(open_col),
                            "high": value(high_col),
                            "low": value(low_col),
                            "close": value(close_col),
                            "adjusted_close": float(adjusted),
                            "volume": value(volume_col),
                        }
                    )
                    rows_written += 1
                    ticker_rows += 1

                if ticker_rows == 0:
                    failures[ticker] = "no valid adjusted-close rows"

    tmp.replace(output_path)
    failures_path.write_text(
        json.dumps(
            {
                "source": "Yahoo Finance via yfinance",
                "intended_use": "local research / personal use",
                "start": start_date,
                "end_exclusive": end_date,
                "tickers_requested": len(tickers),
                "tickers_failed": len(failures),
                "failures": failures,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "source": "Yahoo Finance via yfinance",
        "start": start_date,
        "end_exclusive": end_date,
        "tickers_requested": len(tickers),
        "tickers_failed": len(failures),
        "rows": rows_written,
        "output": str(output_path),
        "failures": str(failures_path),
        "raw_data_commit_policy": "local_cache_only",
    }


def default_recent_start(year: int = 2025) -> str:
    """
    Fetch a generous calendar lookback so a 200-session SMA is already mature
    at the beginning of the target year after merging with historical data.
    """
    return date(year - 1, 1, 1).isoformat()


def exclusive_tomorrow(today: date | None = None) -> str:
    today = today or date.today()
    return (today + timedelta(days=1)).isoformat()
