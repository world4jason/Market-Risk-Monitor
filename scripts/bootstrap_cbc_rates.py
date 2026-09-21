#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.cbc_rates import fetch_cbc_rate_history


FIELDS = [
    "date",
    "discount_rate",
    "collateral_rate",
    "short_term_rate",
    "source_url",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download official CBC discount-rate history to normalized CSV."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".cache" / "taiwan-rates" / "cbc-rates.csv",
    )
    args = parser.parse_args()

    rows = fetch_cbc_rate_history()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(args.output)

    report = {
        "source": "Central Bank of the Republic of China (Taiwan)",
        "rows": len(rows),
        "start": rows[0]["date"],
        "end": rows[-1]["date"],
        "output": str(args.output),
    }
    print(json.dumps(report, indent=2))
    print(
        "\nNext:\n"
        f"  python scripts/refresh_data.py --cbc-rate-file {args.output}"
    )


if __name__ == "__main__":
    main()
