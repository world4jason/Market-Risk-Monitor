#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.ma_breadth_pit import compute_from_price_files, parse_membership_csv
from pipeline.ma_breadth_recent import (
    default_recent_start,
    exclusive_tomorrow,
    fetch_yfinance_recent,
    tickers_for_window,
)

MEMBERSHIP_URL = (
    "https://raw.githubusercontent.com/chinobing/"
    "historical_sp500_constituents/main/sp_500_historical_components.csv"
)
FINSABER_PRICE_URL = (
    "https://huggingface.co/datasets/finsaber-team/FINSABER-reproduce/"
    "resolve/main/data/price/all_sp500_prices_2000_2024_delisted_include.csv"
)


def require(path: Path, hint: str) -> None:
    if not path.exists():
        raise SystemExit(f"Missing {path}. {hint}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extend open PIT S&P 500 moving-average breadth through the current "
            "date using a local-only Yahoo/yfinance recent-price supplement."
        )
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / ".cache" / "ma-breadth-open",
    )
    parser.add_argument(
        "--membership-file",
        type=Path,
        help="PIT membership CSV; defaults to open-bootstrap cache.",
    )
    parser.add_argument(
        "--historical-price-file",
        type=Path,
        help="FINSABER price CSV; defaults to open-bootstrap cache.",
    )
    parser.add_argument(
        "--recent-start",
        default=default_recent_start(2025),
        help="Recent provider start date; default 2024-01-01 for 200DMA lookback.",
    )
    parser.add_argument(
        "--recent-end",
        default=exclusive_tomorrow(),
        help="Recent provider exclusive end date; defaults to tomorrow.",
    )
    parser.add_argument("--batch-size", type=int, default=75)
    parser.add_argument("--min-coverage", type=float, default=0.90)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".cache" / "ma-breadth-open" / "sp500-ma-breadth-hybrid.csv",
    )
    parser.add_argument("--work-db", type=Path)
    args = parser.parse_args()

    membership_path = args.membership_file or (
        args.cache_dir / "sp_500_historical_components.csv"
    )
    historical_path = args.historical_price_file or (
        args.cache_dir / "all_sp500_prices_2000_2024_delisted_include.csv"
    )
    recent_path = args.cache_dir / "yahoo_recent_prices.csv"
    failures_path = args.cache_dir / "yahoo_recent_failures.json"

    require(
        membership_path,
        "Run scripts/bootstrap_ma_breadth_open.py first or pass --membership-file.",
    )
    require(
        historical_path,
        "Run scripts/bootstrap_ma_breadth_open.py first or pass --historical-price-file.",
    )

    snapshots = parse_membership_csv(
        membership_path.read_text(encoding="utf-8-sig")
    )
    tickers = tickers_for_window(
        snapshots,
        args.recent_start,
        args.recent_end,
    )

    recent_report = fetch_yfinance_recent(
        tickers,
        start_date=args.recent_start,
        end_date=args.recent_end,
        output_path=recent_path,
        failures_path=failures_path,
        batch_size=args.batch_size,
    )

    if recent_report["rows"] == 0:
        raise SystemExit(
            "Recent provider returned zero usable rows; historical output was not replaced."
        )

    provider = (
        "chinobing PIT membership + FINSABER-reproduce historical prices "
        "+ Yahoo Finance recent supplement (local research)"
    )
    report = compute_from_price_files(
        membership_path,
        [historical_path, recent_path],
        args.output,
        provider=provider,
        min_coverage=args.min_coverage,
        work_db=args.work_db,
        source_labels=[
            "FINSABER-reproduce 2000-2024 delisted-inclusive adjusted_close",
            "Yahoo Finance via yfinance recent local supplement",
        ],
    )
    report.update(
        {
            "membership_source": MEMBERSHIP_URL,
            "historical_price_source": FINSABER_PRICE_URL,
            "recent_price_source": "Yahoo Finance via yfinance",
            "recent_price_rights": (
                "yfinance documents Yahoo Finance API data as intended for "
                "personal use; review Yahoo terms before redistribution"
            ),
            "recent_fetch": recent_report,
            "membership_mode": "point_in_time",
            "price_adjustment": "adjusted_close",
        }
    )

    print(json.dumps(report, indent=2))
    print(
        "\nNext:\n"
        f"  python scripts/refresh_data.py --ma-breadth-file {args.output}\n"
        "  python scripts/build_ma_breadth_study.py\n"
        "  python scripts/validate_data.py"
    )


if __name__ == "__main__":
    main()
