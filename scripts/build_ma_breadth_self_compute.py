#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.artifacts import write_json_artifact as atomic_json
from pipeline.ma_breadth import audit_rows, build_ma_breadth_metrics, parse_ma_breadth_csv
from pipeline.ma_breadth_self_compute import (
    compute_point_in_time_breadth,
    load_price_directory,
    parse_historical_membership_csv,
    to_import_csv,
)
from pipeline.validate import validate_metric


DEFAULT_MEMBERSHIP_URL = (
    "https://raw.githubusercontent.com/chinobing/"
    "historical_sp500_constituents/main/sp_500_historical_components.csv"
)


def fetch_text(url: str, timeout: int = 60) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Market-Risk-Monitor/0.2 "
                "(https://github.com/world4jason/Market-Risk-Monitor)"
            )
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compute point-in-time S&P 500 20/50/200DMA breadth from "
            "historical membership snapshots and local per-ticker price CSVs."
        )
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--membership-file",
        type=Path,
        help="Local date,tickers historical membership CSV.",
    )
    source.add_argument(
        "--membership-url",
        default=DEFAULT_MEMBERSHIP_URL,
        help="Historical membership URL (default: open chinobing MIT dataset).",
    )
    parser.add_argument(
        "--price-dir",
        type=Path,
        required=True,
        help="Directory containing TICKER.csv price history files.",
    )
    parser.add_argument(
        "--price-adjustment",
        choices=["adjusted_close", "close"],
        default="adjusted_close",
    )
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument(
        "--max-missing-fraction",
        type=float,
        default=0.10,
        help="Fail if missing/unmatured prices exceed this share of membership for any output date/horizon.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "generated",
    )
    args = parser.parse_args()

    if not 0 <= args.max_missing_fraction <= 1:
        parser.error("--max-missing-fraction must be within [0,1]")

    if args.membership_file:
        membership_text = args.membership_file.read_text(encoding="utf-8-sig")
        source_name = str(args.membership_file)
    else:
        membership_text = fetch_text(args.membership_url)
        source_name = args.membership_url

    digest = hashlib.sha256(membership_text.encode("utf-8")).hexdigest()[:16]
    membership_snapshot = f"sp500-membership-sha256:{digest}"

    membership = parse_historical_membership_csv(membership_text)
    if args.start_date:
        membership = [row for row in membership if row["date"] >= args.start_date]
    if args.end_date:
        membership = [row for row in membership if row["date"] <= args.end_date]
    if not membership:
        raise SystemExit("No membership rows remain after date filtering.")

    tickers = {
        ticker
        for row in membership
        for ticker in row["tickers"]
    }
    prices = load_price_directory(
        args.price_dir,
        tickers,
        price_adjustment=args.price_adjustment,
    )

    rows = compute_point_in_time_breadth(
        membership,
        prices,
        membership_snapshot=membership_snapshot,
        price_adjustment=args.price_adjustment,
        provider="MRM self-compute / chinobing historical membership + local prices",
    )

    # Canonical self-compute requires a coverage floor. Missing includes absent
    # price files, missing daily observations, and insufficient SMA warmup.
    violations = []
    for row in rows:
        for horizon in (20, 50, 200):
            eligible = int(row[f"eligible_{horizon}d"])
            missing = int(row[f"missing_{horizon}d"])
            total = eligible + missing
            if total == 0:
                continue
            fraction = missing / total
            if fraction > args.max_missing_fraction:
                violations.append(
                    (
                        row["date"],
                        horizon,
                        fraction,
                        eligible,
                        missing,
                    )
                )
    if violations:
        sample = violations[:5]
        raise SystemExit(
            "Point-in-time breadth failed missing-price coverage guard. "
            f"{len(violations)} date/horizon rows exceed "
            f"{args.max_missing_fraction:.1%}; examples={sample}"
        )

    canonical_rows = parse_ma_breadth_csv(to_import_csv(rows))
    metrics = build_ma_breadth_metrics(
        canonical_rows,
        fetched_at=datetime.now(timezone.utc),
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        metric["source"]["url"] = source_name
        metric["source"]["redistribution"] = "unknown"
        metric["source"]["license_note"] = (
            "Membership source is the MIT-licensed chinobing historical "
            "constituent dataset when default URL is used. Price data is "
            "user-supplied and its usage/redistribution rights remain with "
            "the user/provider."
        )
        atomic_json(args.output_dir / f"{metric_id}.json", metric)

    audit = audit_rows(canonical_rows)
    audit["membership_source"] = source_name
    audit["membership_sha256"] = hashlib.sha256(
        membership_text.encode("utf-8")
    ).hexdigest()
    audit["price_directory"] = str(args.price_dir)
    audit["max_missing_fraction"] = args.max_missing_fraction
    audit["tickers_requested"] = len(tickers)
    audit["tickers_with_price_files"] = len(prices)
    atomic_json(args.output_dir / "ma-breadth-audit.json", audit)

    print(
        f"generated {len(metrics)} MA-breadth metrics from "
        f"{len(membership)} membership dates; "
        f"prices={len(prices)}/{len(tickers)} tickers"
    )


if __name__ == "__main__":
    main()
