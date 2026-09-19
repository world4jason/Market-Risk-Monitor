#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.ma_breadth_study import build_event_study
from pipeline.validate import validate_metric


def load_metric(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_metric(payload)
    return payload


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the S&P 500 50DMA breadth threshold event study."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "generated",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "data" / "config" / "ma-breadth.json",
    )
    args = parser.parse_args()

    breadth_path = args.output_dir / "sp500_above_50dma_pct.json"
    price_path = args.output_dir / "sp500_index.json"
    if not breadth_path.exists():
        raise SystemExit(
            "Missing sp500_above_50dma_pct.json. Import an authorized MA breadth file first."
        )
    if not price_path.exists():
        raise SystemExit(
            "Missing sp500_index.json. Refresh configured FRED SP500 or provide a compatible daily price metric."
        )

    config = json.loads(args.config.read_text(encoding="utf-8"))
    study = build_event_study(
        load_metric(breadth_path),
        load_metric(price_path),
        config,
    )
    atomic_json(args.output_dir / "ma-breadth-event-study.json", study)

    print(
        f"MA breadth study status={study['status']} "
        f"events={len(study.get('events', []))} "
        f"summaries={len(study.get('summaries', []))}"
    )


if __name__ == "__main__":
    main()
