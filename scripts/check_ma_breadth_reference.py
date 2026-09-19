#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.ma_breadth import cross_check_reference
from pipeline.validate import validate_metric


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-check local S&P 500 50DMA breadth against an external reference."
    )
    parser.add_argument(
        "--metric",
        type=Path,
        default=ROOT / "data" / "generated" / "sp500_above_50dma_pct.json",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="JSON with date, reference_value, source/url, tolerance_pp.",
    )
    args = parser.parse_args()

    metric = json.loads(args.metric.read_text(encoding="utf-8"))
    validate_metric(metric)
    reference = json.loads(args.reference.read_text(encoding="utf-8"))

    target_date = reference["date"]
    observation = next(
        (
            obs
            for obs in metric["observations"]
            if obs["date"] == target_date and obs.get("value") is not None
        ),
        None,
    )
    if observation is None:
        raise SystemExit(f"local metric has no observation for {target_date}")

    result = cross_check_reference(
        observation["value"],
        reference["reference_value"],
        tolerance_pp=reference.get("tolerance_pp", 0.5),
    )
    result.update(
        {
            "date": target_date,
            "metric": metric["metric"]["id"],
            "local_provider": metric["source"]["provider"],
            "reference_source": reference.get("source"),
            "reference_symbol": reference.get("symbol"),
            "reference_url": reference.get("url"),
        }
    )
    print(json.dumps(result, indent=2))
    if not result["within_tolerance"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
