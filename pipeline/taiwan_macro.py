from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from .provenance import build_provenance, records_input


class TaiwanMacroError(ValueError):
    pass


SERIES_META = {
    "tw_ndc_monitoring_score": {
        "name": "Taiwan NDC Monitoring Score",
        "units": "score",
        "polarity": "contextual",
        "availability_basis": "unknown",
    },
    "tw_ndc_leading_index": {
        "name": "Taiwan NDC Leading Index",
        "units": "index",
        "polarity": "contextual",
        "availability_basis": "unknown",
    },
    "tw_ndc_coincident_index": {
        "name": "Taiwan NDC Coincident Index",
        "units": "index",
        "polarity": "contextual",
        "availability_basis": "unknown",
    },
    "tw_ndc_lagging_index": {
        "name": "Taiwan NDC Lagging Index",
        "units": "index",
        "polarity": "contextual",
        "availability_basis": "unknown",
    },
    "tw_manufacturing_pmi": {
        "name": "Taiwan Manufacturing PMI",
        "units": "index",
        "polarity": "contextual",
        "availability_basis": "release_date",
    },
    "tw_industrial_production": {
        "name": "Taiwan Industrial Production Index",
        "units": "index",
        "polarity": "contextual",
        "availability_basis": "release_date",
    },
    "tw_manufacturing_production": {
        "name": "Taiwan Manufacturing Production Index",
        "units": "index",
        "polarity": "contextual",
        "availability_basis": "release_date",
    },
}


def parse_taiwan_macro_csv(text: str) -> list[dict]:
    """
    Normalized official-source snapshot contract:

    date,provider,series_id,value,unit,release_date,source_url
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise TaiwanMacroError("Taiwan macro CSV has no header")

    required = {
        "date",
        "provider",
        "series_id",
        "value",
        "unit",
        "release_date",
        "source_url",
    }
    missing = required - set(reader.fieldnames)
    if missing:
        raise TaiwanMacroError(
            f"Taiwan macro CSV missing columns: {sorted(missing)}"
        )

    rows = []
    seen = set()
    for line_no, raw in enumerate(reader, start=2):
        series_id = (raw.get("series_id") or "").strip()
        if series_id not in SERIES_META:
            raise TaiwanMacroError(
                f"row {line_no}: unsupported series_id {series_id!r}"
            )
        try:
            obs_date = date.fromisoformat(
                (raw.get("date") or "").strip()
            ).isoformat()
            release_date = date.fromisoformat(
                (raw.get("release_date") or "").strip()
            ).isoformat()
            value = float((raw.get("value") or "").replace(",", ""))
        except ValueError as exc:
            raise TaiwanMacroError(
                f"row {line_no}: invalid date/value"
            ) from exc

        key = (series_id, obs_date)
        if key in seen:
            raise TaiwanMacroError(
                f"row {line_no}: duplicate {series_id} {obs_date}"
            )
        seen.add(key)

        provider = (raw.get("provider") or "").strip()
        unit = (raw.get("unit") or "").strip()
        source_url = (raw.get("source_url") or "").strip()
        if not provider or not unit or not source_url:
            raise TaiwanMacroError(
                f"row {line_no}: provider/unit/source_url required"
            )

        rows.append(
            {
                "date": obs_date,
                "provider": provider,
                "series_id": series_id,
                "value": value,
                "unit": unit,
                "release_date": release_date,
                "source_url": source_url,
            }
        )

    rows.sort(key=lambda r: (r["series_id"], r["date"]))
    return rows


def _freshness(as_of: str, fetched_at: datetime, max_age_days: int = 75):
    age = max(
        (fetched_at.date() - date.fromisoformat(as_of)).days,
        0,
    )
    return ("fresh" if age <= max_age_days else "stale"), age


def build_macro_metrics(
    rows: list[dict],
    fetched_at: datetime | None = None,
) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[row["series_id"]].append(row)

    metrics = {}
    for series_id, series_rows in groups.items():
        meta = SERIES_META[series_id]
        series_rows.sort(key=lambda r: r["date"])
        latest = series_rows[-1]
        state, age = _freshness(latest["date"], fetched_at)
        providers = sorted(set(r["provider"] for r in series_rows))
        urls = sorted(set(r["source_url"] for r in series_rows))

        metric = {
            "schema_version": "1.0.0",
            "environment": "production",
            "metric": {
                "id": series_id,
                "name": meta["name"],
                "description": (
                    "Official/public Taiwan macro input used independently "
                    "and by the transparent MRM Taiwan macro regime."
                ),
                "pillar": "context",
                "units": meta["units"],
                "frequency": "monthly",
                "polarity": meta["polarity"],
            },
            "source": {
                "provider": " / ".join(providers),
                "dataset": "Taiwan official/public macro release",
                "series_id": series_id,
                "url": urls[-1],
                "license_note": (
                    "Official/public release. Full-history redistribution "
                    "rights depend on the source; source attribution retained."
                ),
                "redistribution": "unknown",
                "market_scope": "Taiwan",
                "membership_mode": None,
                "membership_snapshot": None,
                "price_adjustment": None,
                "point_in_time_membership": None,
                "availability_basis": meta["availability_basis"],
            },
            "coverage": {
                "history_start": series_rows[0]["date"],
                "history_end": latest["date"],
                "timezone": "Asia/Taipei",
                "expected_observation_lag_days": 35,
            },
            "freshness": {
                "state": state,
                "max_age_days": 75,
                "age_days": age,
                "evaluated_at": fetched_at.isoformat().replace("+00:00", "Z"),
                "reason": None,
            },
            "lineage": {
                "kind": "raw",
                "inputs": [],
                "formula": None,
                "transform_version": "taiwan-macro-raw-v1",
            },
            "baselines": [
                {
                    "id": "expanding-pit",
                    "type": "full_history_percentile",
                    "window_observations": None,
                    "min_observations": 24,
                    "point_in_time": meta["availability_basis"] == "release_date",
                    "notes": (
                        "Release-aware strict-past percentile; same-day release batches do not enter one another's baseline."
                        if meta["availability_basis"] == "release_date"
                        else "Retrospective only. NDC history is revision-prone and canonical artifacts do not retain vintages."
                    ),
                }
            ],
            "latest": {
                "as_of": latest["date"],
                "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
                "value": latest["value"],
                "revision_tag": None,
            },
            "observations": [
                {
                    "date": r["date"],
                    "value": r["value"],
                    "status": "observed",
                    "release_date": r["release_date"],
                }
                for r in series_rows
            ],
        }
        metrics[series_id] = metric
    return metrics


def monitoring_light(score: float, config: dict) -> str | None:
    for band in config.get("ndc_monitoring_bands", []):
        if float(band["min"]) <= score <= float(band["max"]):
            return band["label"]
    return None


def _series_values(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["series_id"]].append(row)
    for series_rows in grouped.values():
        series_rows.sort(key=lambda r: r["date"])
    return grouped


def _value_at(series: list[dict], obs_date: str):
    for index, row in enumerate(series):
        if row["date"] == obs_date:
            return index, row
    return None, None


def _component_vote(
    series: list[dict],
    obs_date: str,
    spec: dict,
) -> tuple[float | None, str | None, str | None]:
    index, row = _value_at(series, obs_date)
    if row is None:
        return None, None, None

    rule_type = spec["type"]
    threshold = float(spec.get("threshold", 0))
    higher_positive = bool(spec.get("higher_is_positive", True))

    if rule_type == "level":
        raw = float(row["value"])
    else:
        periods = int(spec["periods"])
        if index < periods:
            return None, None, None
        prior = float(series[index - periods]["value"])
        current = float(row["value"])
        if rule_type == "delta":
            raw = current - prior
        elif rule_type == "return":
            if prior == 0:
                return None, None, None
            raw = 100.0 * (current / prior - 1.0)
        else:
            raise TaiwanMacroError(
                f"unsupported macro component rule {rule_type!r}"
            )

    positive = raw >= threshold if higher_positive else raw <= threshold
    vote = 1.0 if positive else -1.0
    return vote, row["release_date"], f"{raw:.4g}"


def build_macro_regime(
    rows: list[dict],
    config: dict,
    *,
    config_id: str = "data/config/taiwan-macro.json",
) -> dict:
    grouped = _series_values(rows)
    regime_cfg = config["mrm_regime"]
    components = regime_cfg["components"]
    min_known = int(regime_cfg["min_known_components"])
    momentum_periods = int(regime_cfg["momentum_periods"])

    dates = sorted(
        set(
            row["date"]
            for series_id, series_rows in grouped.items()
            if series_id in components
            for row in series_rows
        )
    )

    provisional = []
    for obs_date in dates:
        component_rows = {}
        votes = []
        release_dates = []

        for series_id, spec in components.items():
            vote, release_date, raw = _component_vote(
                grouped.get(series_id, []),
                obs_date,
                spec,
            )
            component_rows[series_id] = {
                "vote": vote,
                "raw_rule_value": raw,
            }
            if vote is not None:
                votes.append(vote)
            if release_date:
                release_dates.append(release_date)

        score = (
            sum(votes) / len(votes)
            if len(votes) >= min_known
            else None
        )
        provisional.append(
            {
                "date": obs_date,
                "score": score,
                "known_components": len(votes),
                "total_components": len(components),
                "confidence": (
                    len(votes) / len(components)
                    if components
                    else 0
                ),
                "available_on": (
                    max(release_dates)
                    if release_dates
                    else None
                ),
                "components": component_rows,
            }
        )

    labels = regime_cfg["labels"]
    for index, row in enumerate(provisional):
        score = row["score"]
        if score is None:
            row["regime"] = "unknown"
            row["score_momentum"] = None
            continue

        previous = (
            provisional[index - momentum_periods]["score"]
            if index >= momentum_periods
            else None
        )
        momentum = (
            score - previous
            if previous is not None
            else None
        )
        row["score_momentum"] = momentum

        if score >= 0:
            row["regime"] = (
                labels["positive_rising"]
                if momentum is None or momentum >= 0
                else labels["positive_falling"]
            )
        else:
            row["regime"] = (
                labels["negative_rising"]
                if momentum is not None and momentum > 0
                else labels["negative_falling"]
            )

    ndc_scores = {
        r["date"]: r["value"]
        for r in grouped.get("tw_ndc_monitoring_score", [])
    }
    for row in provisional:
        ndc_score = ndc_scores.get(row["date"])
        row["ndc_monitoring_score"] = ndc_score
        row["ndc_monitoring_light"] = (
            monitoring_light(float(ndc_score), config)
            if ndc_score is not None
            else None
        )

    current = next(
        (
            row
            for row in reversed(provisional)
            if row["regime"] != "unknown"
        ),
        None,
    )
    provenance_inputs = [
        records_input(
            series_id,
            series_rows,
            as_of=max(row["date"] for row in series_rows),
            snapshot_at=max(
                row["release_date"]
                for row in series_rows
            ),
        )
        for series_id, series_rows in sorted(grouped.items())
    ]
    provenance = build_provenance(
        methodology_id="taiwan-macro-regime",
        methodology_version="taiwan-macro-regime-v1",
        config_id=config_id,
        config=config,
        inputs=provenance_inputs,
    )
    return {
        "schema_version": "1.0.0",
        "provenance": provenance,
        "name": "MRM Taiwan Macro Regime",
        "description": (
            "Transparent public-input regime; does not reproduce MacroMicro/MM."
        ),
        "methodology": {
            "component_vote_range": [-1, 1],
            "minimum_known_components": min_known,
            "momentum_periods": momentum_periods,
            "no_proprietary_mm_formula": True,
            "release_dates_retained": True,
            "historical_point_in_time": False,
            "history_semantics": "retrospective_current_vintage",
            "revision_prone_inputs": sorted(
                series_id
                for series_id in components
                if series_id.startswith("tw_ndc_")
            ),
        },
        "current": current,
        "history": provisional,
    }


def build_macro_audit(rows: list[dict]) -> dict:
    return {
        "schema_version": "1.0.0",
        "rows": rows,
    }


def write_macro_outputs(
    rows: list[dict],
    config: dict,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    for metric_id, metric in build_macro_metrics(rows).items():
        dest = output_dir / f"{metric_id}.json"
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(metric, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(dest)
        paths.append(dest)

    for name, payload in (
        ("taiwan-macro-regime.json", build_macro_regime(rows, config)),
        ("taiwan-macro-audit.json", build_macro_audit(rows)),
    ):
        dest = output_dir / name
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(dest)
        paths.append(dest)

    return paths
