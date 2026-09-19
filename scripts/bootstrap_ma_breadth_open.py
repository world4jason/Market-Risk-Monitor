#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.ma_breadth_pit import compute_from_files

MEMBERSHIP_URL = (
    "https://raw.githubusercontent.com/chinobing/"
    "historical_sp500_constituents/main/sp_500_historical_components.csv"
)
PRICE_URL = (
    "https://huggingface.co/datasets/finsaber-team/FINSABER-reproduce/"
    "resolve/main/data/price/all_sp500_prices_2000_2024_delisted_include.csv"
)


def download(url: str, destination: Path, *, chunk_size: int = 1024 * 1024) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 1024:
        print(f"using cached {destination}")
        return destination

    tmp = destination.with_suffix(destination.suffix + ".tmp")
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Market-Risk-Monitor/0.2 "
                "(open-data MA breadth research bootstrap)"
            )
        },
    )
    downloaded = 0
    with urlopen(req, timeout=120) as response, tmp.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = 100.0 * downloaded / total
                print(
                    f"\r{destination.name}: {downloaded/1024/1024:.1f} MB "
                    f"({pct:.1f}%)",
                    end="",
                    flush=True,
                )
    print()
    tmp.replace(destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download open point-in-time S&P 500 membership + delisted-inclusive "
            "FINSABER prices and compute 20/50/200DMA breadth."
        )
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / ".cache" / "ma-breadth-open",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".cache" / "ma-breadth-open" / "sp500-ma-breadth-open.csv",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.90,
        help="Minimum fraction of PIT members with mature price history required.",
    )
    parser.add_argument(
        "--membership-file",
        type=Path,
        help="Use an existing membership CSV instead of downloading.",
    )
    parser.add_argument(
        "--price-file",
        type=Path,
        help="Use an existing FINSABER-compatible price CSV instead of downloading.",
    )
    parser.add_argument(
        "--work-db",
        type=Path,
        help="Optional persistent SQLite work DB path for debugging.",
    )
    args = parser.parse_args()

    membership_path = args.membership_file or (
        args.cache_dir / "sp_500_historical_components.csv"
    )
    price_path = args.price_file or (
        args.cache_dir / "all_sp500_prices_2000_2024_delisted_include.csv"
    )

    if args.membership_file is None:
        download(MEMBERSHIP_URL, membership_path)
    if args.price_file is None:
        download(PRICE_URL, price_path)

    report = compute_from_files(
        membership_path,
        price_path,
        args.output,
        provider="chinobing PIT membership + FINSABER-reproduce prices",
        min_coverage=args.min_coverage,
        work_db=args.work_db,
    )

    report.update(
        {
            "membership_source": MEMBERSHIP_URL,
            "membership_license": "MIT",
            "price_source": PRICE_URL,
            "price_dataset_license": "Apache-2.0",
            "price_field": "adjusted_close",
            "membership_mode": "point_in_time",
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
