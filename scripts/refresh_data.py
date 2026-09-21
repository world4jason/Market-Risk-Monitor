#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.breadth import build_breadth_metrics, parse_breadth_csv
from pipeline.cboe import build_vix_metric, fetch_vix_csv, parse_vix_csv
from pipeline.finra import build_finra_metrics, parse_finra_csv, parse_finra_xlsx
from pipeline.fred import build_metric, fetch_fred_csv, parse_fred_csv
from pipeline.ma_breadth import (
    assert_history_not_truncated,
    audit_rows as audit_ma_breadth_rows,
    build_ma_breadth_metrics,
    parse_ma_breadth_csv,
)
from pipeline.ma_breadth_study import (
    build_event_study as build_ma_breadth_event_study,
)
from pipeline.shiller import build_shiller_metrics, parse_shiller_xls
from pipeline.signals import build_signal_snapshot
from pipeline.tradermonty_ma_breadth import (
    build_tradermonty_metrics,
    fetch_tradermonty_csv,
)
from pipeline.taiwan_macro import (
    build_macro_audit,
    build_macro_metrics,
    build_macro_regime,
    parse_taiwan_macro_csv,
)
from pipeline.taiwan_twse import (
    build_taiex_metrics,
    build_taiwan_breadth_metrics,
    fetch_fmtqik_current,
    fetch_market_breadth_day,
    fetch_taiex_month,
    merge_taiex_rows,
    parse_fmtqik_json,
    parse_mi_index_market_summary_json,
    parse_taiex_month_json,
    parse_taiwan_breadth_csv,
)
from pipeline.validate import validate_metric


SPECIAL_ARTIFACTS = {
    "catalog.json",
    "refresh-report.json",
    "signals.json",
    "coverage.json",
    "ma-breadth-audit.json",
    "ma-breadth-event-study.json",
    "taiwan-macro-regime.json",
    "taiwan-macro-audit.json",
}


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def refresh_fred(
    config_path: Path,
    output_dir: Path,
    selected: set[str] | None,
) -> list[dict]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    report = []
    fetched_at = datetime.now(timezone.utc)

    for item in config["fred"]:
        if selected and item["id"] not in selected:
            continue

        dest = output_dir / f"{item['id']}.json"
        try:
            observations = parse_fred_csv(
                fetch_fred_csv(item["series_id"]),
                item["series_id"],
            )
            expected_start = item.get("expected_history_start")
            if expected_start and (
                not observations or observations[0]["date"] > expected_start
            ):
                raise ValueError(
                    f"{item['id']} history starts at "
                    f"{observations[0]['date'] if observations else 'missing'}, "
                    f"expected <= {expected_start}"
                )

            metric = build_metric(item, observations, fetched_at)
            validate_metric(metric)
            atomic_json(dest, metric)
            report.append(
                {
                    "metric": item["id"],
                    "status": "updated",
                    "path": str(dest.relative_to(ROOT)),
                }
            )
        except Exception as exc:
            report.append(
                {
                    "metric": item["id"],
                    "status": "error",
                    "error": str(exc),
                    "preserved_previous": dest.exists(),
                }
            )
    return report


def refresh_cboe_vix(output_dir: Path) -> list[dict]:
    dest = output_dir / "vix.json"
    try:
        observations = parse_vix_csv(fetch_vix_csv())
        if not observations or observations[0]["date"] > "1990-01-31":
            raise ValueError(
                "VIX history unexpectedly starts at "
                f"{observations[0]['date'] if observations else 'missing'}"
            )
        metric = build_vix_metric(observations)
        validate_metric(metric)
        atomic_json(dest, metric)
        return [
            {
                "metric": "vix",
                "status": "updated",
                "path": str(dest.relative_to(ROOT)),
            }
        ]
    except Exception as exc:
        return [
            {
                "metric": "vix",
                "status": "error",
                "error": str(exc),
                "preserved_previous": dest.exists(),
            }
        ]


def refresh_breadth(input_path: Path, output_dir: Path) -> list[dict]:
    rows = parse_breadth_csv(input_path.read_text(encoding="utf-8-sig"))
    metrics = build_breadth_metrics(rows)
    report = []
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = output_dir / f"{metric_id}.json"
        atomic_json(dest, metric)
        report.append(
            {
                "metric": metric_id,
                "status": "updated",
                "path": str(dest.relative_to(ROOT)),
            }
        )
    return report


def refresh_ma_breadth(input_path: Path, output_dir: Path) -> list[dict]:
    rows = parse_ma_breadth_csv(input_path.read_text(encoding="utf-8-sig"))
    metrics = build_ma_breadth_metrics(rows)
    report = []

    # Once canonical history exists, a later import may extend it but may not
    # silently truncate its start date.
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = output_dir / f"{metric_id}.json"
        if dest.exists():
            try:
                previous = json.loads(dest.read_text(encoding="utf-8"))
                validate_metric(previous)
                assert_history_not_truncated(previous, metric)
            except ValueError:
                raise
            except Exception:
                # An invalid prior artifact must not block a valid replacement.
                pass

        atomic_json(dest, metric)
        report.append(
            {
                "metric": metric_id,
                "status": "updated",
                "path": str(dest.relative_to(ROOT)),
            }
        )

    atomic_json(
        output_dir / "ma-breadth-audit.json",
        audit_ma_breadth_rows(rows),
    )
    return report


def refresh_tradermonty_ma_breadth(output_dir: Path) -> list[dict]:
    """
    Public convenience source for current/recent context.

    TraderMonty's historical computation uses a current constituent universe,
    so it is explicitly non-PIT and must never overwrite an existing PIT
    canonical history.
    """
    metrics = build_tradermonty_metrics(fetch_tradermonty_csv())
    report = []

    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = output_dir / f"{metric_id}.json"

        if dest.exists():
            try:
                previous = json.loads(dest.read_text(encoding="utf-8"))
                validate_metric(previous)
                if (
                    previous.get("source", {}).get("point_in_time_membership")
                    is True
                    and metric.get("source", {}).get(
                        "point_in_time_membership"
                    )
                    is not True
                ):
                    report.append(
                        {
                            "metric": metric_id,
                            "status": "error",
                            "error": (
                                "refusing to overwrite canonical point-in-time "
                                "MA breadth with current-constituent retroactive "
                                "source"
                            ),
                            "preserved_previous": True,
                        }
                    )
                    continue
            except Exception:
                # If the previous artifact itself is unreadable, allow a valid
                # current-context replacement rather than preserving corruption.
                pass

        atomic_json(dest, metric)
        report.append(
            {
                "metric": metric_id,
                "status": "updated",
                "path": str(dest.relative_to(ROOT)),
            }
        )
    return report


def _write_metric_group(
    metrics: dict[str, dict],
    output_dir: Path,
) -> list[dict]:
    report = []
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = output_dir / f"{metric_id}.json"
        atomic_json(dest, metric)
        report.append(
            {
                "metric": metric_id,
                "status": "updated",
                "path": str(dest.relative_to(ROOT)),
            }
        )
    return report


def refresh_twse_current(output_dir: Path) -> list[dict]:
    report = []
    try:
        fmt_rows = parse_fmtqik_json(fetch_fmtqik_current())
        if not fmt_rows:
            raise ValueError("TWSE FMTQIK returned no rows")
        latest = fmt_rows[-1]["date"]
        latest_dt = datetime.fromisoformat(latest)
        month_rows = parse_taiex_month_json(
            fetch_taiex_month(latest_dt.year, latest_dt.month)
        )
        taiex_rows = merge_taiex_rows(month_rows, fmt_rows)
        report.extend(
            _write_metric_group(
                build_taiex_metrics(taiex_rows),
                output_dir,
            )
        )
    except Exception as exc:
        report.append(
            {
                "metric": "tw_taiex",
                "status": "error",
                "error": str(exc),
                "preserved_previous": (
                    output_dir / "tw_taiex.json"
                ).exists(),
            }
        )
        return report

    try:
        latest = fmt_rows[-1]["date"]
        breadth_row = parse_mi_index_market_summary_json(
            fetch_market_breadth_day(latest)
        )
        report.extend(
            _write_metric_group(
                build_taiwan_breadth_metrics([breadth_row]),
                output_dir,
            )
        )
    except Exception as exc:
        report.append(
            {
                "metric": "tw_advance_decline_diff",
                "status": "error",
                "error": str(exc),
                "preserved_previous": (
                    output_dir / "tw_advance_decline_diff.json"
                ).exists(),
            }
        )
    return report


def refresh_twse_breadth_file(
    input_path: Path,
    output_dir: Path,
) -> list[dict]:
    rows = parse_taiwan_breadth_csv(
        input_path.read_text(encoding="utf-8-sig")
    )
    return _write_metric_group(
        build_taiwan_breadth_metrics(rows),
        output_dir,
    )


def refresh_taiwan_macro_file(
    input_path: Path,
    output_dir: Path,
) -> list[dict]:
    rows = parse_taiwan_macro_csv(
        input_path.read_text(encoding="utf-8-sig")
    )
    report = _write_metric_group(
        build_macro_metrics(rows),
        output_dir,
    )
    config = json.loads(
        (ROOT / "data" / "config" / "taiwan-macro.json").read_text(
            encoding="utf-8"
        )
    )
    atomic_json(
        output_dir / "taiwan-macro-regime.json",
        build_macro_regime(rows, config),
    )
    atomic_json(
        output_dir / "taiwan-macro-audit.json",
        build_macro_audit(rows),
    )
    return report


def refresh_finra(input_path: Path, output_dir: Path) -> list[dict]:
    if input_path.suffix.lower() == ".csv":
        rows = parse_finra_csv(
            input_path.read_text(encoding="utf-8-sig")
        )
    elif input_path.suffix.lower() in {".xlsx", ".xlsm"}:
        rows = parse_finra_xlsx(input_path)
    else:
        raise SystemExit("FINRA input must be CSV or XLSX")

    if not rows or rows[0]["date"] > "1997-01-31":
        raise SystemExit(
            "FINRA historical file does not reach the official Jan-1997 start; "
            f"first parsed month={rows[0]['date'] if rows else 'missing'}"
        )

    metrics = build_finra_metrics(rows)
    report = []
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = output_dir / f"{metric_id}.json"
        atomic_json(dest, metric)
        report.append(
            {
                "metric": metric_id,
                "status": "updated",
                "path": str(dest.relative_to(ROOT)),
            }
        )
    return report


def refresh_shiller(input_path: Path, output_dir: Path) -> list[dict]:
    if input_path.suffix.lower() != ".xls":
        raise SystemExit(
            "Shiller input must be the official ie_data.xls workbook "
            "from shillerdata.com"
        )

    rows = parse_shiller_xls(input_path)
    if not rows or rows[0]["date"] != "1871-01-01":
        raise SystemExit(
            "Shiller workbook coverage changed unexpectedly; "
            f"first parsed month={rows[0]['date'] if rows else 'missing'}"
        )

    metrics = build_shiller_metrics(rows)
    report = []
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = output_dir / f"{metric_id}.json"
        atomic_json(dest, metric)
        report.append(
            {
                "metric": metric_id,
                "status": "updated",
                "path": str(dest.relative_to(ROOT)),
            }
        )
    return report


def load_generated_metrics(output_dir: Path) -> dict[str, dict]:
    metrics = {}
    for path in sorted(output_dir.glob("*.json")):
        if path.name in SPECIAL_ARTIFACTS:
            continue
        try:
            metric = json.loads(path.read_text(encoding="utf-8"))
            validate_metric(metric)
        except Exception:
            continue
        metrics[metric["metric"]["id"]] = metric
    return metrics


def build_signals(output_dir: Path) -> dict:
    config = json.loads(
        (ROOT / "data" / "config" / "signals.json").read_text(
            encoding="utf-8"
        )
    )
    return build_signal_snapshot(
        load_generated_metrics(output_dir),
        config,
    )


def maybe_build_ma_breadth_study(output_dir: Path) -> dict | None:
    breadth_path = output_dir / "sp500_above_50dma_pct.json"
    price_path = output_dir / "sp500_index.json"
    if not breadth_path.exists() or not price_path.exists():
        return None

    breadth = json.loads(breadth_path.read_text(encoding="utf-8"))
    price = json.loads(price_path.read_text(encoding="utf-8"))
    validate_metric(breadth)
    validate_metric(price)

    config = json.loads(
        (ROOT / "data" / "config" / "ma-breadth.json").read_text(
            encoding="utf-8"
        )
    )
    return build_ma_breadth_event_study(breadth, price, config)


EXPECTED_STARTS = {
    "nfci": "1971-01-08",
    "nfci_risk": "1971-01-08",
    "nfci_credit": "1971-01-08",
    "nfci_nonfinancial_leverage": "1971-01-08",
    "us_recession": "1854-12-01",
    "vix": "1990-01-31",
    "finra_margin_debt": "1997-01-31",
    "finra_total_free_credit": "1997-01-31",
    "finra_margin_debt_mom_pct": "1997-01-31",
    "finra_margin_debt_yoy_pct": "1997-01-31",
    "margin_debt_to_free_credit": "1997-01-31",
    "finra_cash_free_credit": "2010-02-28",
    "finra_margin_free_credit": "2010-02-28",
    "shiller_price": "1871-01-01",
    "shiller_cape": "1871-01-01",
    "shiller_real_tr_price": "1871-01-01",
}


def build_coverage(output_dir: Path) -> dict:
    rows = []
    for metric_id, metric in sorted(
        load_generated_metrics(output_dir).items()
    ):
        actual_start = metric["coverage"]["history_start"]
        expected_start = EXPECTED_STARTS.get(metric_id)
        status = "ok"
        if expected_start and actual_start and actual_start > expected_start:
            status = "short_history"

        rows.append(
            {
                "id": metric_id,
                "name": metric["metric"]["name"],
                "latest_acceptable_history_start": expected_start,
                "actual_history_start": actual_start,
                "actual_history_end": metric["coverage"]["history_end"],
                "observations": len(metric.get("observations", [])),
                "status": status,
            }
        )

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "metrics": rows,
    }


def build_catalog(output_dir: Path) -> dict:
    metrics = []
    for path in sorted(output_dir.glob("*.json")):
        if path.name in SPECIAL_ARTIFACTS:
            continue

        try:
            metric = json.loads(path.read_text(encoding="utf-8"))
            validate_metric(metric)
        except Exception:
            continue

        metrics.append(
            {
                "id": metric["metric"]["id"],
                "name": metric["metric"]["name"],
                "pillar": metric["metric"]["pillar"],
                "frequency": metric["metric"]["frequency"],
                "history_start": metric["coverage"]["history_start"],
                "history_end": metric["coverage"]["history_end"],
                "freshness": metric["freshness"]["state"],
                "as_of": metric["latest"]["as_of"],
                "path": f"./{path.name}",
            }
        )

    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "metrics": metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh Market Risk Monitor static snapshots without GitHub Actions."
        )
    )
    parser.add_argument(
        "--fred",
        action="store_true",
        help="Refresh configured FRED series.",
    )
    parser.add_argument(
        "--fred-id",
        action="append",
        default=[],
        help="Refresh only a configured FRED metric id; may be repeated.",
    )
    parser.add_argument(
        "--cboe-vix",
        action="store_true",
        help="Refresh official Cboe VIX 1990-present daily history.",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="Refresh all network-accessible public sources (FRED + Cboe VIX).",
    )
    parser.add_argument(
        "--twse-current",
        action="store_true",
        help=(
            "Refresh current Taiwan TAIEX and official TWSE stock advance/decline breadth."
        ),
    )
    parser.add_argument(
        "--twse-breadth-file",
        type=Path,
        help=(
            "Normalized historical Taiwan breadth CSV: "
            "date,advancing,declining,unchanged,limit_up,limit_down,unmatched."
        ),
    )
    parser.add_argument(
        "--taiwan-macro-file",
        type=Path,
        help=(
            "Normalized Taiwan official/public macro CSV using "
            "docs/taiwan-sources.md contract."
        ),
    )
    parser.add_argument(
        "--tradermonty-ma-breadth",
        action="store_true",
        help=(
            "Fetch public TraderMonty S&P 500 50/200DMA breadth. "
            "Historical rows are current-constituent retroactive and non-PIT."
        ),
    )
    parser.add_argument(
        "--breadth-file",
        type=Path,
        help=(
            "Authorized NYSE breadth CSV using docs/breadth-sources.md contract."
        ),
    )
    parser.add_argument(
        "--ma-breadth-file",
        type=Path,
        help=(
            "S&P 500 20/50/200DMA breadth CSV using "
            "docs/moving-average-breadth-sources.md contract."
        ),
    )
    parser.add_argument(
        "--finra-file",
        type=Path,
        help=(
            "Official FINRA margin-statistics CSV/XLSX downloaded from FINRA."
        ),
    )
    parser.add_argument(
        "--shiller-file",
        type=Path,
        help=(
            "Official live ie_data.xls downloaded from shillerdata.com."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "generated",
    )
    args = parser.parse_args()

    run_fred = args.fred or args.public
    run_vix = args.cboe_vix or args.public

    if not any(
        [
            run_fred,
            run_vix,
            args.twse_current,
            args.twse_breadth_file,
            args.taiwan_macro_file,
            args.tradermonty_ma_breadth,
            args.breadth_file,
            args.ma_breadth_file,
            args.finra_file,
            args.shiller_file,
        ]
    ):
        parser.error(
            "choose --public, --fred, --cboe-vix, --twse-current, "
            "--twse-breadth-file, --taiwan-macro-file, "
            "--tradermonty-ma-breadth, --breadth-file, "
            "--ma-breadth-file, --finra-file and/or --shiller-file"
        )

    report = []

    if run_fred:
        report.extend(
            refresh_fred(
                ROOT / "data" / "config" / "series.json",
                args.output_dir,
                set(args.fred_id) or None,
            )
        )

    if run_vix:
        report.extend(refresh_cboe_vix(args.output_dir))

    if args.twse_current:
        report.extend(refresh_twse_current(args.output_dir))

    if args.twse_breadth_file:
        report.extend(
            refresh_twse_breadth_file(
                args.twse_breadth_file,
                args.output_dir,
            )
        )

    if args.taiwan_macro_file:
        report.extend(
            refresh_taiwan_macro_file(
                args.taiwan_macro_file,
                args.output_dir,
            )
        )

    if args.tradermonty_ma_breadth:
        report.extend(
            refresh_tradermonty_ma_breadth(args.output_dir)
        )

    if args.breadth_file:
        report.extend(
            refresh_breadth(args.breadth_file, args.output_dir)
        )

    if args.ma_breadth_file:
        report.extend(
            refresh_ma_breadth(args.ma_breadth_file, args.output_dir)
        )

    if args.finra_file:
        report.extend(
            refresh_finra(args.finra_file, args.output_dir)
        )

    if args.shiller_file:
        report.extend(
            refresh_shiller(args.shiller_file, args.output_dir)
        )

    atomic_json(
        args.output_dir / "signals.json",
        build_signals(args.output_dir),
    )

    ma_study = maybe_build_ma_breadth_study(args.output_dir)
    if ma_study is not None:
        atomic_json(
            args.output_dir / "ma-breadth-event-study.json",
            ma_study,
        )

    atomic_json(
        args.output_dir / "coverage.json",
        build_coverage(args.output_dir),
    )
    atomic_json(
        args.output_dir / "catalog.json",
        build_catalog(args.output_dir),
    )
    atomic_json(
        args.output_dir / "refresh-report.json",
        {
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "results": report,
        },
    )

    errors = [item for item in report if item["status"] == "error"]
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
