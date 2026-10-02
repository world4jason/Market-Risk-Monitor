#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
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

MACRO_FIELDS = [
    "date",
    "provider",
    "series_id",
    "value",
    "unit",
    "release_date",
    "source_url",
]

CIER_METRIC_IDS = ["tw_manufacturing_pmi"]

NDC_METRIC_IDS = [
    "tw_ndc_monitoring_score",
    "tw_ndc_leading_index",
    "tw_ndc_coincident_index",
    "tw_ndc_lagging_index",
]


def write_macro_seed(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MACRO_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            {field: row.get(field, "") for field in MACRO_FIELDS}
            for row in sorted(rows, key=lambda item: (item["date"], item["series_id"]))
        )
    tmp.replace(path)


def seed_macro_retention_floor(
    output_dir: Path,
    *,
    cier_path: Path,
    ndc_path: Path,
) -> None:
    """Seed rolling-window bootstraps from the tracked canonical audit.

    GitHub-hosted runners start with an empty .cache. CIER and NDC expose
    rolling windows, so a clean cache would otherwise forget the oldest
    retained month on every run. The committed audit is the durable retention
    floor; live bootstraps merge their new windows on top of it.
    """
    audit_path = output_dir / "taiwan-macro-audit.json"
    if not audit_path.exists():
        return

    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    rows = audit.get("rows", [])
    cier_rows = [row for row in rows if row.get("provider") == "CIER"]
    ndc_rows = [row for row in rows if row.get("provider") == "NDC"]

    if cier_rows:
        write_macro_seed(cier_path, cier_rows)
    if ndc_rows:
        write_macro_seed(ndc_path, ndc_rows)


def run(*args: str) -> None:
    command = [sys.executable, *args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def refresh_seeded_source_with_fallback(
    *,
    label: str,
    script: str,
    output_path: Path,
) -> str | None:
    """Refresh a rolling source, retaining the last verified seed on failure.

    The seed is written from the committed canonical audit before this function
    runs. If the live fetch fails, restore that exact seed instead of blocking
    unrelated daily sources. The caller later annotates refresh-report.json so
    the UI treats the source as failed rather than newly refreshed.
    """
    retained = output_path.read_bytes() if output_path.exists() else None
    try:
        run(script, "--output", str(output_path))
        return None
    except subprocess.CalledProcessError as exc:
        if retained is None:
            raise
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(retained)
        message = (
            f"{label} live refresh failed with exit code {exc.returncode}; "
            "retained previous verified snapshot"
        )
        print(f"WARNING: {message}", file=sys.stderr, flush=True)
        return message


def annotate_refresh_report_source_failures(
    output_dir: Path,
    failures: list[tuple[list[str], str]],
) -> None:
    """Mark retained-source failures without discarding fresh unrelated data."""
    if not failures:
        return

    report_path = output_dir / "refresh-report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    results = payload.setdefault("results", [])
    by_metric = {
        item.get("metric"): item
        for item in results
        if item.get("metric")
    }

    for metric_ids, message in failures:
        for metric_id in metric_ids:
            item = by_metric.get(metric_id)
            if item is None:
                item = {"metric": metric_id}
                results.append(item)
                by_metric[metric_id] = item
            item["status"] = "error"
            item["error"] = message
            item["preserved_previous"] = True

    tmp = report_path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(report_path)


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

    # Rehydrate rolling-window retention from the tracked canonical audit.
    # Hosted runners are ephemeral, while CIER/NDC history must accumulate.
    seed_macro_retention_floor(
        output_dir,
        cier_path=cier_path,
        ndc_path=ndc_path,
    )

    # Prefetch every file-based dependency before the release mutates the
    # tracked output tree. A source failure here leaves the published snapshot
    # completely untouched.
    download(FINRA_URL, finra_path)
    download(discover_shiller_workbook_url(), shiller_path)
    source_failures: list[tuple[list[str], str]] = []

    cier_failure = refresh_seeded_source_with_fallback(
        label="CIER PMI",
        script="scripts/bootstrap_cier_pmi.py",
        output_path=cier_path,
    )
    if cier_failure:
        source_failures.append((CIER_METRIC_IDS, cier_failure))

    ndc_failure = refresh_seeded_source_with_fallback(
        label="NDC business cycle",
        script="scripts/bootstrap_ndc_business_cycle.py",
        output_path=ndc_path,
    )
    if ndc_failure:
        source_failures.append((NDC_METRIC_IDS, ndc_failure))

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
            annotate_refresh_report_source_failures(
                output_dir,
                source_failures,
            )
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
