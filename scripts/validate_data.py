#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from pipeline.validate import validate_metric


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("paths",nargs="*",help="Metric JSON files; defaults to data/generated/*.json")
    args=parser.parse_args()
    paths=[Path(p) for p in args.paths] if args.paths else sorted((ROOT/"data"/"generated").glob("*.json"))
    paths=[p for p in paths if p.name not in {"catalog.json","refresh-report.json"}]
    failures=[]
    for path in paths:
        try:
            payload=json.loads(path.read_text())
            validate_metric(payload)
            print(f"OK {path}")
        except Exception as exc:
            failures.append((path,str(exc)))
            print(f"FAIL {path}: {exc}",file=sys.stderr)
    if failures:
        raise SystemExit(1)


if __name__=="__main__":
    main()
