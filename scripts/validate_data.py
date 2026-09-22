#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.validate import (
    validate_catalog,
    validate_coverage_report,
    validate_ma_breadth_audit,
    validate_ma_breadth_study,
    validate_metric,
    validate_overview,
    validate_refresh_report,
    validate_rate_regime,
    validate_signal_snapshot,
    validate_taiwan_macro_audit,
    validate_taiwan_macro_regime,
    validate_taiwan_trend_breadth_audit,
)


METRIC_SCHEMA = json.loads(
    (ROOT / "schemas" / "metric-series.schema.json").read_text(encoding="utf-8")
)
METRIC_SCHEMA_VALIDATOR = Draft202012Validator(
    METRIC_SCHEMA,
    format_checker=FormatChecker(),
)


SPECIAL_VALIDATORS = {
    "catalog.json": validate_catalog,
    "coverage.json": validate_coverage_report,
    "overview.json": validate_overview,
    "refresh-report.json": validate_refresh_report,
    "signals.json": validate_signal_snapshot,
    "ma-breadth-audit.json": validate_ma_breadth_audit,
    "ma-breadth-event-study.json": validate_ma_breadth_study,
    "taiwan-macro-regime.json": validate_taiwan_macro_regime,
    "taiwan-macro-audit.json": validate_taiwan_macro_audit,
    "taiwan-cbc-rate-regime.json": validate_rate_regime,
    "fed-rate-regime.json": validate_rate_regime,
    "taiwan-trend-breadth-audit.json": validate_taiwan_trend_breadth_audit,
}


def validate_metric_with_schema(payload: dict) -> None:
    errors = sorted(
        METRIC_SCHEMA_VALIDATOR.iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(p) for p in first.absolute_path) or "<root>"
        raise ValueError(f"schema error at {location}: {first.message}")
    validate_metric(payload)


def validator_for(path: Path):
    return SPECIAL_VALIDATORS.get(path.name, validate_metric_with_schema)


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
