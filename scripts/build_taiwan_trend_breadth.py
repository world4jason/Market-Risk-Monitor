#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.taiwan_trend_breadth import compute_from_panel
from pipeline.validate import validate_metric


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compute TWSE common-stock 20/50/200DMA and 52-week breadth "
            "from a point-in-time daily panel."
        )
    )
    parser.add_argument(
        "--panel-file",
        type=Path,
        required=True,
        help=(
            "CSV: date,symbol,high,low,close,market_scope,provider,"
            "membership_mode,price_adjustment"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "generated",
    )
    parser.add_argument("--work-db", type=Path)
    args = parser.parse_args()

    report = compute_from_panel(
        args.panel_file,
        args.output_dir,
        work_db=args.work_db,
    )

    for metric_id in report["metrics"]:
        metric = json.loads(
            (args.output_dir / f"{metric_id}.json").read_text(
                encoding="utf-8"
            )
        )
        validate_metric(metric)

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
