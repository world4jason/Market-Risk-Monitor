from __future__ import annotations

import copy

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

# Percent-valued series that are policy-rate levels. Basis points and
# percentage points are the same dimension, so misclassifying one of these
# changes the unit shown, never the meaning -- see the safety note below.
RATE_LEVEL_METRIC_IDS = {
    "us_fed_policy_rate",
    "tw_cbc_rate",
    "fed_target_legacy",
    "fed_target_upper",
}

# Index-valued series that sit around zero and go negative, so the sign of a
# relative change is undefined.
ZERO_CENTRED_INDEX_METRIC_IDS = {
    "nfci",
    "nfci_risk",
    "nfci_credit",
    "nfci_nonfinancial_leverage",
    "tw_advance_decline_line",
}

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

    # Already a change: showing a change of it compounds two different things.
    if transform.startswith("pct-change") or units == "basis points":
        return "none"

    # A 0/1 indicator has no meaningful delta.
    if units == "binary":
        return "none"

    if units == "percent":
        if metric_id in RATE_LEVEL_METRIC_IDS or transform.startswith("rate-velocity"):
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

    if units == "index" and metric_id in ZERO_CENTRED_INDEX_METRIC_IDS:
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
