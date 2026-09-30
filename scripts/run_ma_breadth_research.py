#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.validate import validate_metric


def run_python(script: str, *args: str) -> None:
    command = [sys.executable, str(ROOT / "scripts" / script), *args]
    subprocess.run(command, cwd=ROOT, check=True)


def copy_validated_sp500_index(source: Path, output_dir: Path) -> Path:
    payload = json.loads(source.read_text(encoding="utf-8"))
    validate_metric(payload)
    metric_id = payload.get("metric", {}).get("id")
    if metric_id != "sp500_index":
        raise SystemExit(
            f"--sp500-index-file must contain metric.id='sp500_index'; got {metric_id!r}"
        )
    destination = output_dir / "sp500_index.json"
    shutil.copyfile(source, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the final local-only S&P 500 moving-average breadth research "
            "validation from an authorized point-in-time breadth export and a "
            "local-only daily S&P 500 index metric."
        )
    )
    parser.add_argument(
        "--ma-breadth-file",
        type=Path,
        required=True,
        help=(
            "Authorized PIT 20/50/200DMA breadth CSV using the canonical "
            "docs/moving-average-breadth-sources.md contract."
        ),
    )
    parser.add_argument(
        "--sp500-index-file",
        type=Path,
        required=True,
        help=(
            "Local-only canonical sp500_index JSON used for forward returns. "
            "Do not publish restricted vendor data."
        ),
    )
    parser.add_argument(
        "--reference",
        action="append",
        type=Path,
        default=[],
        help=(
            "Optional fixed external-reference JSON. May be repeated. Any "
            "out-of-tolerance check fails closed before the event study."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / ".cache" / "ma-breadth-research",
        help="Local working/output directory; defaults under .cache/.",
    )
    args = parser.parse_args()

    if not args.ma_breadth_file.exists():
        raise SystemExit(f"Missing --ma-breadth-file: {args.ma_breadth_file}")
    if not args.sp500_index_file.exists():
        raise SystemExit(f"Missing --sp500-index-file: {args.sp500_index_file}")
    for reference in args.reference:
        if not reference.exists():
            raise SystemExit(f"Missing --reference: {reference}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    run_python(
        "refresh_data.py",
        "--ma-breadth-file",
        str(args.ma_breadth_file),
        "--output-dir",
        str(args.output_dir),
    )

    index_path = copy_validated_sp500_index(
        args.sp500_index_file,
        args.output_dir,
    )

    breadth_metric = args.output_dir / "sp500_above_50dma_pct.json"
    if not breadth_metric.exists():
        raise SystemExit(
            "refresh_data.py did not produce sp500_above_50dma_pct.json"
        )

    for reference in args.reference:
        run_python(
            "check_ma_breadth_reference.py",
            "--metric",
            str(breadth_metric),
            "--reference",
            str(reference),
        )

    run_python(
        "build_ma_breadth_study.py",
        "--output-dir",
        str(args.output_dir),
    )

    study_path = args.output_dir / "ma-breadth-event-study.json"
    study = json.loads(study_path.read_text(encoding="utf-8"))
    if study.get("status") != "ready":
        raise SystemExit(
            "Canonical MA-breadth event study is not ready: "
            f"status={study.get('status')!r}. "
            "Use point-in-time membership and an authorized history."
        )

    validation_paths = [
        path
        for path in sorted(args.output_dir.glob("*.json"))
        if path.name
        not in {
            "catalog.json",
            "overview.json",
            "refresh-report.json",
            "signals.json",
        }
    ]
    run_python(
        "validate_data.py",
        *[str(path) for path in validation_paths],
    )

    summary = {
        "status": "ready",
        "ma_breadth_file": str(args.ma_breadth_file),
        "sp500_index_file": str(args.sp500_index_file),
        "sp500_index_working_copy": str(index_path),
        "references_checked": [str(path) for path in args.reference],
        "event_count": len(study.get("events", [])),
        "summary_count": len(study.get("summaries", [])),
        "study": str(study_path),
        "output_dir": str(args.output_dir),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
