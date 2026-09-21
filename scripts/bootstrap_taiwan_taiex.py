#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.taiwan_twse import (
    build_taiex_metrics,
    fetch_taiex_month,
    merge_taiex_rows,
    parse_taiex_month_json,
)
from pipeline.validate import validate_metric


def month_iter(start: str, end: str):
    sy, sm = [int(x) for x in start.split("-")]
    ey, em = [int(x) for x in end.split("-")]
    cursor_y, cursor_m = sy, sm
    while (cursor_y, cursor_m) <= (ey, em):
        yield cursor_y, cursor_m
        cursor_m += 1
        if cursor_m == 13:
            cursor_y += 1
            cursor_m = 1


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def main():
    today = date.today()
    parser = argparse.ArgumentParser(
        description="Backfill official monthly TAIEX OHLC from TWSE."
    )
    parser.add_argument(
        "--start",
        default="1997-01",
        help="First month YYYY-MM. Default 1997-01.",
    )
    parser.add_argument(
        "--end",
        default=f"{today.year:04d}-{today.month:02d}",
        help="Last month YYYY-MM. Defaults to current month.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.2,
        help="Delay between uncached TWSE requests.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / ".cache" / "taiwan-taiex",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "generated",
    )
    args = parser.parse_args()

    groups = []
    errors = []
    for year, month in month_iter(args.start, args.end):
        cache = args.cache_dir / f"{year:04d}-{month:02d}.json"
        try:
            if cache.exists():
                text = cache.read_text(encoding="utf-8")
            else:
                text = fetch_taiex_month(year, month, timeout=45)
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(text, encoding="utf-8")
                if args.delay > 0:
                    time.sleep(args.delay)

            rows = parse_taiex_month_json(text)
            if rows:
                groups.append(rows)
                print(
                    f"OK {year:04d}-{month:02d}: "
                    f"{len(rows)} observations"
                )
            else:
                print(f"EMPTY {year:04d}-{month:02d}")
        except Exception as exc:
            errors.append(
                {
                    "month": f"{year:04d}-{month:02d}",
                    "error": str(exc),
                }
            )
            print(
                f"WARN {year:04d}-{month:02d}: {exc}",
                file=sys.stderr,
            )

    if not groups:
        raise SystemExit("No TAIEX observations fetched.")

    merged = merge_taiex_rows(*groups)
    metrics = build_taiex_metrics(
        merged,
        datetime.now(timezone.utc),
    )
    written = []
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = args.output_dir / f"{metric_id}.json"
        atomic_json(dest, metric)
        written.append(str(dest.relative_to(ROOT)))

    report = {
        "source": "TWSE monthly MI_5MINS_HIST",
        "start": merged[0]["date"],
        "end": merged[-1]["date"],
        "observations": len(merged),
        "metrics": written,
        "errors": errors,
        "cache_dir": str(args.cache_dir),
    }
    atomic_json(
        args.cache_dir / "backfill-report.json",
        report,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
