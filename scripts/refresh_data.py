#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
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
from pipeline.overview import build_overview
from pipeline.artifacts import write_json_artifact
from pipeline.rate_velocity import (
    build_rate_metrics,
    build_rate_regime_artifact,
    cbc_rows_to_rate_rows,
    combine_fed_target_metrics,
    parse_cbc_rate_csv,
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
from pipeline.taiwan_trend_breadth import compute_from_panel as compute_taiwan_trend_breadth
from pipeline.taiwan_twse import (
    build_taiex_metrics,
    build_taiwan_breadth_metrics,
    fetch_fmtqik_current,
    fetch_market_breadth_day,
    fetch_taiex_month,
    merge_metric_history,
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
    "overview.json",
    "ma-breadth-audit.json",
    "ma-breadth-event-study.json",
    "taiwan-macro-regime.json",
    "taiwan-macro-audit.json",
    "taiwan-cbc-rate-regime.json",
    "fed-rate-regime.json",
    "taiwan-trend-breadth-audit.json",
}


# Every artifact this process wrote. A refresh only ever adds or replaces
# files, so without a ledger there is no way to tell an artifact produced by
# this run from one left behind by an earlier run with different flags.
WRITTEN_ARTIFACTS: set[Path] = set()


def atomic_json(path: Path, payload: dict) -> None:
    # pipeline.artifacts is the shared finalize/write path; this only adds the
    # ledger the release prune needs.
    write_json_artifact(path, payload)
    WRITTEN_ARTIFACTS.add(path.resolve())


# A single fetch can produce several metrics. When one fails, the report names
# one representative metric, so the preserved set has to be declared explicitly
# rather than inferred from that name -- otherwise --clean-output prunes the
# siblings that the failed refresh was supposed to preserve.
#
# tests/test_release_clean_output.py asserts these match what the builders
# actually produce, so they cannot drift.
TAIEX_GROUP_METRIC_IDS = [
    "tw_market_trade_value",
    "tw_market_trade_volume",
    "tw_taiex",
    "tw_taiex_high",
    "tw_taiex_low",
    "tw_taiex_open",
]

TAIWAN_BREADTH_GROUP_METRIC_IDS = [
    "tw_advance_decline_diff",
    "tw_advance_decline_line",
    "tw_advance_decline_pct",
    "tw_advancing_stocks",
    "tw_declining_stocks",
    "tw_unchanged_stocks",
]


def preserved_ids_from_report(report: list[dict]) -> set[str]:
    """
    Metric ids a failed source deliberately kept a previous snapshot for.

    An entry may declare the whole group it speaks for; otherwise it speaks
    only for itself.
    """
    preserved: set[str] = set()
    for item in report:
        if item.get("status") != "error" or not item.get("preserved_previous"):
            continue
        preserved.update(
            item.get("preserved_metric_ids") or [item.get("metric")]
        )
    preserved.discard(None)
    return preserved


def should_run_fred(args) -> bool:
    """
    --fred-id is an allowlist, not merely a filter.

    Requiring a separate --fred alongside it meant a command built entirely out
    of --fred-id refreshed no FRED series at all, while previously generated
    ones stayed on disk and were still catalogued -- so an allowlist written to
    exclude a restricted series appeared to work while doing nothing.
    """
    return bool(args.fred or args.public or args.fred_id)


def prune_unwritten_artifacts(
    output_dir: Path,
    *,
    preserved_metric_ids: set[str],
) -> list[str]:
    """
    Reduce the output directory to exactly what this run produced.

    A refresh is otherwise additive: an unselected source is skipped, not
    cleared, while build_catalog() and build_signals() glob the whole
    directory. An artifact from an earlier run with different flags therefore
    reappears in the catalog even though this run never asked for it -- which
    is how a redistribution-restricted series survived an allowlist that was
    written specifically to exclude it.

    Artifacts a failed source deliberately preserved are kept, so this does not
    quietly change the documented stale/error semantics.
    """
    removed = []
    for path in sorted(output_dir.glob("*.json")):
        if path.resolve() in WRITTEN_ARTIFACTS:
            continue
        if path.stem in preserved_metric_ids:
            continue
        path.unlink()
        removed.append(path.name)
    return removed


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
    *,
    merge_existing: bool = False,
) -> list[dict]:
    report = []
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest = output_dir / f"{metric_id}.json"

        if merge_existing and dest.exists():
            try:
                previous = json.loads(dest.read_text(encoding="utf-8"))
                validate_metric(previous)
                metric = merge_metric_history(previous, metric)
                validate_metric(metric)
            except Exception as exc:
                raise ValueError(
                    f"failed to merge existing {metric_id} history: {exc}"
                ) from exc

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
                merge_existing=True,
            )
        )
    except Exception as exc:
        report.append(
            {
                "metric": "tw_taiex",
                "status": "error",
                "error": str(exc),
                "preserved_previous": any(
                    (output_dir / f"{metric_id}.json").exists()
                    for metric_id in TAIEX_GROUP_METRIC_IDS
                ),
                "preserved_metric_ids": TAIEX_GROUP_METRIC_IDS,
            }
        )
        # Breadth needs the latest session date from the TAIEX fetch, so it
        # cannot run. Say so: a dependent group that was never attempted must
        # still declare its previous snapshots as preserved, or --clean-output
        # deletes them on the strength of a failure elsewhere.
        report.append(
            {
                "metric": "tw_advance_decline_diff",
                "status": "error",
                "error": (
                    "not attempted: TWSE breadth needs the latest session date "
                    f"from the TAIEX fetch, which failed ({exc})"
                ),
                "preserved_previous": any(
                    (output_dir / f"{metric_id}.json").exists()
                    for metric_id in TAIWAN_BREADTH_GROUP_METRIC_IDS
                ),
                "preserved_metric_ids": TAIWAN_BREADTH_GROUP_METRIC_IDS,
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
                merge_existing=True,
            )
        )
    except Exception as exc:
        report.append(
            {
                "metric": "tw_advance_decline_diff",
                "status": "error",
                "error": str(exc),
                "preserved_previous": any(
                    (output_dir / f"{metric_id}.json").exists()
                    for metric_id in TAIWAN_BREADTH_GROUP_METRIC_IDS
                ),
                "preserved_metric_ids": TAIWAN_BREADTH_GROUP_METRIC_IDS,
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
        merge_existing=True,
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


def refresh_cbc_rate_file(
    input_path: Path,
    output_dir: Path,
) -> list[dict]:
    rows = parse_cbc_rate_csv(
        input_path.read_text(encoding="utf-8-sig")
    )
    rate_rows = cbc_rows_to_rate_rows(rows)
    metrics = build_rate_metrics(
        rate_rows,
        prefix="tw_cbc",
        name_prefix="Taiwan CBC Discount Rate",
        provider="Central Bank of the Republic of China (Taiwan)",
        source_url="https://www.cbc.gov.tw/en/lp-695-2.html",
        market_scope="Taiwan",
    )
    report = _write_metric_group(metrics, output_dir)
    config = json.loads(
        (ROOT / "data" / "config" / "rates.json").read_text(
            encoding="utf-8"
        )
    )
    atomic_json(
        output_dir / "taiwan-cbc-rate-regime.json",
        build_rate_regime_artifact(
            rate_rows,
            config,
            name="Taiwan CBC Rate Regime",
        ),
    )
    return report


def maybe_build_fed_rate_outputs(output_dir: Path) -> list[dict]:
    legacy_path = output_dir / "fed_target_legacy.json"
    upper_path = output_dir / "fed_target_upper.json"
    if not legacy_path.exists() and not upper_path.exists():
        return []

    legacy = None
    upper = None
    if legacy_path.exists():
        legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
        validate_metric(legacy)
    if upper_path.exists():
        upper = json.loads(upper_path.read_text(encoding="utf-8"))
        validate_metric(upper)

    rate_rows = combine_fed_target_metrics(legacy, upper)
    if not rate_rows:
        return []

    metrics = build_rate_metrics(
        rate_rows,
        prefix="us_fed_policy",
        name_prefix="Fed Policy Rate",
        provider="Board of Governors / FOMC via FRED",
        source_url="https://fred.stlouisfed.org/series/DFEDTARU",
        market_scope="United States",
    )
    report = _write_metric_group(metrics, output_dir)
    config = json.loads(
        (ROOT / "data" / "config" / "rates.json").read_text(
            encoding="utf-8"
        )
    )
    atomic_json(
        output_dir / "fed-rate-regime.json",
        build_rate_regime_artifact(
            rate_rows,
            config,
            name="Fed Policy Rate Regime",
            input_metrics=[
                metric
                for metric in (legacy, upper)
                if metric is not None
            ],
        ),
    )
    return report


def refresh_taiwan_trend_panel(
    input_path: Path,
    output_dir: Path,
) -> list[dict]:
    report = []
    with tempfile.TemporaryDirectory(prefix="mrm-tw-trend-") as temp:
        temp_out = Path(temp) / "out"
        result = compute_taiwan_trend_breadth(
            input_path,
            temp_out,
        )

        for metric_id in result["metrics"]:
            src = temp_out / f"{metric_id}.json"
            metric = json.loads(src.read_text(encoding="utf-8"))
            validate_metric(metric)
            dest = output_dir / src.name

            if dest.exists():
                previous = json.loads(dest.read_text(encoding="utf-8"))
                validate_metric(previous)
                assert_history_not_truncated(previous, metric)

            atomic_json(dest, metric)
            report.append(
                {
                    "metric": metric_id,
                    "status": "updated",
                    "path": str(dest.relative_to(ROOT)),
                }
            )

        audit = json.loads(
            (temp_out / "taiwan-trend-breadth-audit.json").read_text(
                encoding="utf-8"
            )
        )
        atomic_json(
            output_dir / "taiwan-trend-breadth-audit.json",
            audit,
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
    # TWSE MI_5MINS_HIST refuses any query before 1999-01-05, so that is the
    # real floor for official TAIEX daily OHLC, not the exchange's own age.
    "tw_taiex": "1999-01-05",
    "tw_taiex_open": "1999-01-05",
    "tw_taiex_high": "1999-01-05",
    "tw_taiex_low": "1999-01-05",
    # Earliest change date on CBC's official discount-rate history page.
    "tw_cbc_rate": "2000-12-29",
    "tw_cbc_step_bp": "2000-12-29",
    "tw_cbc_change_3m_bp": "2000-12-29",
    "tw_cbc_change_6m_bp": "2000-12-29",
    "tw_cbc_change_12m_bp": "2000-12-29",
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
        "--taiwan-trend-panel",
        type=Path,
        help=(
            "Point-in-time TWSE common-stock daily panel for 20/50/200DMA "
            "and 52-week high/low breadth."
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
        "--cbc-rate-file",
        type=Path,
        help=(
            "Normalized CBC policy-rate history CSV: "
            "date,discount_rate,collateral_rate,short_term_rate,source_url."
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
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help=(
            "Reduce the output directory to exactly the artifacts this run "
            "produces. Use for release builds: without it a refresh is "
            "additive and artifacts from earlier runs with different flags "
            "stay on disk and are still catalogued."
        ),
    )
    args = parser.parse_args()

    run_fred = should_run_fred(args)
    run_vix = args.cboe_vix or args.public

    if not any(
        [
            run_fred,
            run_vix,
            args.twse_current,
            args.twse_breadth_file,
            args.taiwan_trend_panel,
            args.taiwan_macro_file,
            args.cbc_rate_file,
            args.tradermonty_ma_breadth,
            args.breadth_file,
            args.ma_breadth_file,
            args.finra_file,
            args.shiller_file,
        ]
    ):
        parser.error(
            "choose --public, --fred, --cboe-vix, --twse-current, "
            "--twse-breadth-file, --taiwan-trend-panel, --taiwan-macro-file, --cbc-rate-file, "
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

    if args.taiwan_trend_panel:
        report.extend(
            refresh_taiwan_trend_panel(
                args.taiwan_trend_panel,
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

    if args.cbc_rate_file:
        report.extend(
            refresh_cbc_rate_file(
                args.cbc_rate_file,
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

    # Prune before anything derived is built: signals, coverage and the
    # catalog all glob the output directory, so a leftover artifact would
    # otherwise be baked into them.
    removed_artifacts = []
    if args.clean_output:
        removed_artifacts = prune_unwritten_artifacts(
            args.output_dir,
            preserved_metric_ids=preserved_ids_from_report(report),
        )

    # Derived Fed policy velocity is rebuilt whenever raw target series exist.
    report.extend(maybe_build_fed_rate_outputs(args.output_dir))

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
        args.output_dir / "overview.json",
        build_overview(load_generated_metrics(args.output_dir)),
    )
    atomic_json(
        args.output_dir / "refresh-report.json",
        {
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "results": report,
            # Derived artifacts are rebuilt after the prune, so report only
            # what is actually absent from the finished release.
            "removed_artifacts": sorted(
                name
                for name in removed_artifacts
                # The report itself is being written right now, so it is not
                # on disk yet and would otherwise report its own removal.
                if name != "refresh-report.json"
                and not (args.output_dir / name).exists()
            ),
        },
    )

    errors = [item for item in report if item["status"] == "error"]
    print(json.dumps(report, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
