from __future__ import annotations

import copy
import json
from pathlib import Path

"""
Declared comparison semantics for metric display.

A period-to-period change is not meaningful in the same way for every metric.
A policy rate moving 1.75% -> 2.00% is +25 bp, not +14.29%; an index centred on
zero has no stable relative change at all; and a metric that already *is* a
change should not be shown as a change of a change.

The artifact therefore declares how its values should be compared, rather than
leaving the UI to infer it from the numeric unit alone. The derivation lives
here so it is written once, validated, and tested, instead of being restated in
every builder where it would drift.

See docs/presentation-contract.md.
"""

COMPARISONS = {
    "absolute",
    "percent_change",
    "percentage_points",
    "basis_points",
    "none",
}

_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "config" / "presentation.json"


def _load_registry() -> dict:
    payload = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    overrides = payload.get("metric_overrides")
    if not isinstance(overrides, dict):
        raise ValueError("presentation registry must define metric_overrides")
    unknown = set(overrides.values()) - COMPARISONS
    if unknown:
        raise ValueError(f"presentation registry has invalid comparisons: {sorted(unknown)}")
    return payload


PRESENTATION_REGISTRY = _load_registry()
METRIC_OVERRIDES = PRESENTATION_REGISTRY["metric_overrides"]

_RELATIVE_UNITS = {
    "USD millions",
    "TWD",
    "shares",
    "index",
    "ratio",
}


def comparison_for(metric: dict) -> str:
    meta = metric.get("metric", {})
    units = meta.get("units")
    metric_id = meta.get("id", "")
    transform = str(metric.get("lineage", {}).get("transform_version") or "")

    declared = METRIC_OVERRIDES.get(metric_id)
    if declared:
        return declared

    # Already a change: showing a change of it compounds two different things.
    if transform.startswith("pct-change") or units == "basis points":
        return "none"

    # A 0/1 indicator has no meaningful delta.
    if units == "binary":
        return "none"

    if units == "percent":
        if transform.startswith("rate-velocity"):
            return "basis_points"
        # Safety default: any other percent-valued metric still compares in
        # percentage points. That is dimensionally correct even for a series we
        # have not classified, so an unclassified rate is shown as +0.25 pp
        # rather than the wrong +14.29%.
        return "percentage_points"

    if units == "percentile":
        return "percentage_points"

    if units == "count":
        # Counts here include net differences that cross zero.
        return "absolute"

    if units == "index":
        # Index levels are ambiguous: some are positive price indexes while
        # others cross zero. New index IDs must be classified explicitly in
        # data/config/presentation.json; until then absolute is fail-safe.
        return "absolute"

    if units in _RELATIVE_UNITS:
        return "percent_change"

    # Unknown units: an absolute delta is always dimensionally honest.
    return "absolute"


def apply_presentation(payload: dict) -> dict:
    """
    Return a copy of a metric artifact with its comparison semantics declared.

    Payloads that are not metric artifacts, and artifacts that already declare
    a comparison, are returned unchanged.
    """
    meta = payload.get("metric")
    if not isinstance(meta, dict) or "observations" not in payload:
        return payload
    if meta.get("comparison") in COMPARISONS:
        return payload

    stamped = copy.deepcopy(payload)
    stamped["metric"]["comparison"] = comparison_for(payload)
    return stamped
