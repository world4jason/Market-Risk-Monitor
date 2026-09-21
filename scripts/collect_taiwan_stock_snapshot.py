#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.taiwan_stock_panel import (
    append_snapshot,
    build_daily_panel_rows,
    fetch_company_master,
    fetch_stock_day_all,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Collect today's official TWSE listed-company OHLC snapshot "
            "for forward point-in-time breadth history."
        )
    )
    parser.add_argument(
        "--panel",
        type=Path,
        default=ROOT / ".cache" / "taiwan-stocks" / "twse-common-stock-panel.csv",
    )
    args = parser.parse_args()

    rows = build_daily_panel_rows(
        fetch_stock_day_all(),
        fetch_company_master(),
    )
    report = append_snapshot(args.panel, rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(
        "\nAfter enough sessions accumulate:\n"
        f"  python scripts/build_taiwan_trend_breadth.py --panel-file {args.panel}"
    )


if __name__ == "__main__":
    main()
