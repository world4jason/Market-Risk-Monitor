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

from pipeline.cier_pmi import (
    CIER_PMI_URL,
    HEADLINE_SERIES_ID,
    fetch_cier_pmi_rows,
    merge_macro_rows,
    parse_cier_pmi_html,
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
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download the official CIER manufacturing PMI table into the "
            "normalized Taiwan macro CSV contract. The source table is a "
            "12-month rolling window, so this merges into an accumulating "
            "history rather than backfilling one."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / ".cache" / "taiwan-macro" / "cier-pmi.csv",
    )
    parser.add_argument(
        "--page-file",
        type=Path,
        help="Parse a previously saved page instead of fetching (offline use).",
    )
    parser.add_argument(
        "--observed-at",
        type=date.fromisoformat,
        default=datetime.now(timezone.utc).date(),
        help=(
            "Date the values were verified public; recorded as release_date. "
            "Defaults to today (UTC)."
        ),
    )
    args = parser.parse_args()

    if args.page_file:
        rows = parse_cier_pmi_html(args.page_file.read_text(encoding="utf-8"))
    else:
        rows = fetch_cier_pmi_rows()

    incoming = to_macro_rows(rows, observed_at=args.observed_at)
    existing = read_existing(args.output)
    merged = merge_macro_rows(existing, incoming)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(merged)
    tmp.replace(args.output)

    sectors = sorted(rows[-1]["sectors"]) if rows else []
    report = {
        "source": "Chung-Hua Institution for Economic Research (CIER)",
        "source_url": CIER_PMI_URL,
        "series_id": HEADLINE_SERIES_ID,
        "window_months_on_page": len(rows),
        "rows_after_merge": len(merged),
        "previous_rows": len(existing),
        "start": merged[0]["date"] if merged else None,
        "end": merged[-1]["date"] if merged else None,
        "observed_at": args.observed_at.isoformat(),
        "sector_columns_parsed_but_not_canonical": sectors,
        "output": str(args.output),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        "\nThe official table is a rolling window; run this regularly so "
        "coverage accumulates.\n"
        "\nNext:\n"
        f"  python scripts/refresh_data.py --taiwan-macro-file {args.output}"
    )


if __name__ == "__main__":
    main()
