#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.signals import build_signal_snapshot
from pipeline.validate import validate_metric


def load_metrics(output_dir: Path) -> dict[str, dict]:
    metrics = {}
    for path in sorted(output_dir.glob("*.json")):
        if path.name in {"catalog.json", "refresh-report.json", "signals.json"}:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validate_metric(payload)
        except Exception:
            continue
        metrics[payload["metric"]["id"]] = payload
    return metrics


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser(description="Build Deleveraging Watch from committed metric snapshots.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "generated",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "data" / "config" / "signals.json",
    )
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    metrics = load_metrics(args.output_dir)
    snapshot = build_signal_snapshot(metrics, config)
    atomic_json(args.output_dir / "signals.json", snapshot)

    summary = snapshot["current"]["summary"]
    print(
        f"signals: active={summary['active']} known={summary['known']} "
        f"unknown={summary['unknown']} total={summary['total']}"
    )


if __name__ == "__main__":
    main()
