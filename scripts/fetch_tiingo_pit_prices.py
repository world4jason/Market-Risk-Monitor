#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.ma_breadth_self_compute import parse_historical_membership_csv


TIINGO_BASE = "https://api.tiingo.com/tiingo/daily"


def fetch_text(url: str, token: str, timeout: int = 45) -> str:
    req = Request(
        url,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": (
                "Market-Risk-Monitor/0.2 "
                "(https://github.com/world4jason/Market-Risk-Monitor)"
            ),
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def ticker_candidates(ticker: str) -> list[str]:
    """
    Try the literal historical symbol first, then common dot/dash variants.

    We never silently map one company to another. A successful candidate is
    recorded in the manifest so every symbol translation is auditable.
    """
    candidates = [ticker]
    for candidate in (
        ticker.replace(".", "-"),
        ticker.replace("-", "."),
    ):
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def tiingo_prices_url(ticker: str, start_date: str, end_date: str) -> str:
    query = urlencode(
        {
            "startDate": start_date,
            "endDate": end_date,
            "format": "csv",
            "columns": "date,close,adjClose",
        }
    )
    return f"{TIINGO_BASE}/{ticker}/prices?{query}"


def normalize_csv(text: str) -> str:
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError("Tiingo returned empty/non-CSV response")

    date_col = next((c for c in reader.fieldnames if c.lower() == "date"), None)
    adj_col = next(
        (c for c in reader.fieldnames if c.lower() in {"adjclose", "adj_close"}),
        None,
    )
    close_col = next((c for c in reader.fieldnames if c.lower() == "close"), None)
    if date_col is None or (adj_col is None and close_col is None):
        raise ValueError(
            f"Tiingo CSV missing expected date/close columns: {reader.fieldnames}"
        )

    output = ["Date,Close,Adj Close"]
    count = 0
    for row in reader:
        raw_date = (row.get(date_col) or "").strip()
        if not raw_date:
            continue
        date = raw_date[:10]
        close = (row.get(close_col) or "").strip() if close_col else ""
        adj = (row.get(adj_col) or "").strip() if adj_col else ""
        if not close and not adj:
            continue
        output.append(f"{date},{close},{adj}")
        count += 1

    if count == 0:
        raise ValueError("Tiingo returned no usable price rows")
    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Resumably download Tiingo EOD price histories for the tickers needed "
            "by point-in-time S&P 500 moving-average breadth computation."
        )
    )
    parser.add_argument(
        "--membership-file",
        type=Path,
        required=True,
        help="Historical date,tickers membership CSV.",
    )
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / ".cache" / "tiingo-sp500-prices",
    )
    parser.add_argument(
        "--token-env",
        default="TIINGO_API_TOKEN",
        help="Environment variable containing the Tiingo token.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.15,
        help="Delay between network requests; increase if your plan rate-limits.",
    )
    parser.add_argument(
        "--max-new-symbols",
        type=int,
        default=0,
        help=(
            "Stop after this many newly downloaded symbols (0 = no explicit cap). "
            "Useful for Tiingo Starter's monthly unique-symbol limit."
        ),
    )
    args = parser.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(
            f"Missing {args.token_env}. Put the Tiingo token in the environment; "
            "never commit it to this repository."
        )

    membership_text = args.membership_file.read_text(encoding="utf-8-sig")
    membership = parse_historical_membership_csv(membership_text)
    membership = [
        row
        for row in membership
        if args.start_date <= row["date"] <= args.end_date
    ]
    if not membership:
        raise SystemExit("No membership rows in requested date range.")

    tickers = sorted(
        {
            ticker
            for row in membership
            for ticker in row["tickers"]
        }
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "manifest.json"
    manifest = {
        "schema_version": "1.0.0",
        "provider": "Tiingo EOD",
        "source": "https://www.tiingo.com/documentation/end-of-day",
        "start_date": args.start_date,
        "end_date": args.end_date,
        "membership_file": str(args.membership_file),
        "requested_tickers": len(tickers),
        "downloaded": {},
        "failed": {},
        "skipped_cached": [],
    }
    if manifest_path.exists():
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["downloaded"].update(prior.get("downloaded", {}))
            manifest["failed"].update(prior.get("failed", {}))
        except Exception:
            pass

    new_downloads = 0
    for index, ticker in enumerate(tickers, start=1):
        path = args.output_dir / f"{ticker}.csv"
        if path.exists() and path.stat().st_size > 32:
            manifest["skipped_cached"].append(ticker)
            continue

        if args.max_new_symbols and new_downloads >= args.max_new_symbols:
            break

        success = False
        errors = []
        for candidate in ticker_candidates(ticker):
            try:
                text = fetch_text(
                    tiingo_prices_url(candidate, args.start_date, args.end_date),
                    token,
                )
                normalized = normalize_csv(text)
                tmp = path.with_suffix(".csv.tmp")
                tmp.write_text(normalized, encoding="utf-8")
                tmp.replace(path)
                manifest["downloaded"][ticker] = {
                    "provider_ticker": candidate,
                    "file": path.name,
                }
                manifest["failed"].pop(ticker, None)
                success = True
                new_downloads += 1
                print(
                    f"[{index}/{len(tickers)}] OK {ticker} -> {candidate} "
                    f"({new_downloads} new)"
                )
                break
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                time.sleep(max(args.sleep_seconds, 0))

        if not success:
            manifest["failed"][ticker] = errors
            print(
                f"[{index}/{len(tickers)}] FAIL {ticker}: "
                + " | ".join(errors[:2]),
                file=sys.stderr,
            )

        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        time.sleep(max(args.sleep_seconds, 0))

    manifest["new_downloads_this_run"] = new_downloads
    manifest["files_present"] = sum(
        1
        for ticker in tickers
        if (args.output_dir / f"{ticker}.csv").exists()
    )
    manifest["failure_count"] = len(manifest["failed"])
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"done: files={manifest['files_present']}/{len(tickers)}, "
        f"new={new_downloads}, failures={manifest['failure_count']}"
    )
    print(
        "Next: python scripts/build_ma_breadth_self_compute.py "
        f"--membership-file {args.membership_file} "
        f"--price-dir {args.output_dir} "
        f"--start-date {args.start_date} --end-date {args.end_date}"
    )


if __name__ == "__main__":
    main()
