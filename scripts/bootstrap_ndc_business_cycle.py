#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.taiwan_macro import parse_taiwan_macro_csv
from pipeline.ndc_business_cycle import (
    SERIES,
    fetch_ndc_snapshot,
    merge_current_vintage_rows,
    parse_ndc_snapshot_json,
    to_macro_rows,
)

FIELDS = [
    "date",
    "provider",
    "series_id",
    "value",
    "unit",
    "release_date",
    "source_url",
]


def read_existing(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = parse_taiwan_macro_csv(path.read_text(encoding="utf-8"))
    unexpected = sorted(
        {row["series_id"] for row in rows}
        - {spec["series_id"] for spec in SERIES.values()}
    )
    if unexpected:
        raise ValueError(
            "existing NDC bootstrap output contains non-NDC series: "
            + ", ".join(unexpected)
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch or normalize the public NDC business-cycle chart JSON into "
            "the Taiwan macro CSV contract. The public chart surface is a "
            "12-month rolling window; older locally retained months are kept "
            "as latest-observed vintages, never as historical PIT claims."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".cache" / "taiwan-macro" / "ndc-business-cycle.csv",
    )
    parser.add_argument(
        "--snapshot-file",
        type=Path,
        help="Parse a previously saved combined NDC JSON snapshot instead of fetching.",
    )
    parser.add_argument(
        "--observed-at",
        type=date.fromisoformat,
        default=None,
        help=(
            "Date the snapshot was actually verified public. Required with "
            "--snapshot-file; live fetches default to today (UTC). This is an "
            "ingestion watermark, not a PIT release-history claim."
        ),
    )
    args = parser.parse_args()

    if args.snapshot_file:
        if args.observed_at is None:
            parser.error(
                "--observed-at is required with --snapshot-file; use the date "
                "the saved NDC JSON was actually fetched/verified public"
            )
        payload = parse_ndc_snapshot_json(
            args.snapshot_file.read_text(encoding="utf-8")
        )
        observed_at = args.observed_at
    else:
        payload = fetch_ndc_snapshot()
        observed_at = args.observed_at or datetime.now(timezone.utc).date()

    incoming = to_macro_rows(payload, observed_at=observed_at)
    existing = read_existing(args.output)
    merged = merge_current_vintage_rows(existing, incoming)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(merged)
    tmp.replace(args.output)

    windows = {
        key: {
            "start": block["line"][0]["x"],
            "end": block["line"][-1]["x"],
            "months": len(block["line"]),
            "next_update": block["next"],
        }
        for key, block in payload.items()
        if key in SERIES
    }
    report = {
        "source": "National Development Council (Taiwan)",
        "series": {key: spec["series_id"] for key, spec in SERIES.items()},
        "observed_at": observed_at.isoformat(),
        "incoming_rows": len(incoming),
        "previous_rows": len(existing),
        "rows_after_merge": len(merged),
        "windows": windows,
        "output": str(args.output),
        "history_semantics": "latest_observed_vintage_non_pit",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        "\nNext:\n"
        f"  python scripts/refresh_data.py --taiwan-macro-file {args.output}"
    )


if __name__ == "__main__":
    main()
