#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bootstrap_sources import FINRA_URL, discover_shiller_workbook_url, download


FRED_PUBLIC_IDS = [
    "nfci",
    "nfci_risk",
    "nfci_credit",
    "nfci_nonfinancial_leverage",
    "us_recession",
    "fed_target_legacy",
    "fed_target_upper",
]


def run(*args: str) -> None:
    command = [sys.executable, *args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def restore_generated(backup_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    if backup_dir.exists():
        shutil.copytree(backup_dir, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch every approved public source, rebuild the tracked public "
            "snapshot, and run all release gates. On failure the prior "
            "data/generated tree is restored."
        )
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / ".cache" / "market-risk-monitor",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the deterministic unittest suite; release validation still runs.",
    )
    args = parser.parse_args()

    cache_dir = args.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir = ROOT / "data" / "generated"

    finra_path = cache_dir / "margin-statistics.xlsx"
    shiller_path = cache_dir / "ie_data.xls"
    cier_path = ROOT / ".cache" / "taiwan-macro" / "cier-pmi.csv"
    ndc_path = ROOT / ".cache" / "taiwan-macro" / "ndc-business-cycle.csv"
    cbc_path = ROOT / ".cache" / "taiwan-rates" / "cbc-rates.csv"

    # Prefetch every file-based dependency before the release mutates the
    # tracked output tree. A source failure here leaves the published snapshot
    # completely untouched.
    download(FINRA_URL, finra_path)
    download(discover_shiller_workbook_url(), shiller_path)
    run("scripts/bootstrap_cier_pmi.py", "--output", str(cier_path))
    run("scripts/bootstrap_ndc_business_cycle.py", "--output", str(ndc_path))
    run("scripts/bootstrap_cbc_rates.py", "--output", str(cbc_path))

    with tempfile.TemporaryDirectory(prefix="mrm-refresh-backup-") as temp:
        backup_dir = Path(temp) / "generated"
        if output_dir.exists():
            shutil.copytree(output_dir, backup_dir)

        refresh_args = [
            "scripts/refresh_data.py",
            "--clean-output",
        ]
        for series_id in FRED_PUBLIC_IDS:
            refresh_args.extend(["--fred-id", series_id])
        refresh_args.extend(
            [
                "--cboe-vix",
                "--finra-file",
                str(finra_path),
                "--shiller-file",
                str(shiller_path),
                "--twse-current",
                "--taiwan-macro-file",
                str(cier_path),
                "--taiwan-macro-file",
                str(ndc_path),
                "--cbc-rate-file",
                str(cbc_path),
            ]
        )

        try:
            run(*refresh_args)
            if not args.skip_tests:
                run("-m", "unittest", "discover", "-s", "tests")
            run("scripts/validate_data.py")
            run("scripts/check_publish_policy.py")
            run("scripts/site_smoke.py")
        except Exception:
            print(
                "refresh failed; restoring the previously published "
                "data/generated snapshot",
                file=sys.stderr,
                flush=True,
            )
            restore_generated(backup_dir, output_dir)
            raise

    print(
        "Public snapshot refresh completed successfully. "
        "Review/commit data/generated or let the scheduled workflow do it.",
        flush=True,
    )


if __name__ == "__main__":
    main()
