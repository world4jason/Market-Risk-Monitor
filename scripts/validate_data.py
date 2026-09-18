#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.validate import (
    validate_catalog,
    validate_coverage_report,
    validate_metric,
    validate_refresh_report,
    validate_signal_snapshot,
)


SPECIAL_VALIDATORS = {
    "catalog.json": validate_catalog,
    "coverage.json": validate_coverage_report,
    "refresh-report.json": validate_refresh_report,
    "signals.json": validate_signal_snapshot,
}


def validator_for(path: Path):
    return SPECIAL_VALIDATORS.get(path.name, validate_metric)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="*",
        help="JSON files; defaults to all data/generated/*.json",
    )
    args = parser.parse_args()

    paths = (
        [Path(p) for p in args.paths]
        if args.paths
        else sorted((ROOT / "data" / "generated").glob("*.json"))
    )

    failures = []
    checked = 0

    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            validator_for(path)(payload)
            checked += 1
            print(f"OK {path}")
        except Exception as exc:
            failures.append((path, str(exc)))
            print(f"FAIL {path}: {exc}", file=sys.stderr)

    if not paths:
        print("No generated JSON files found.", file=sys.stderr)
        raise SystemExit(1)

    print(f"validated={checked} failed={len(failures)}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
