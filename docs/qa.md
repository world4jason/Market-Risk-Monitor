# QA and failure semantics

Issue: #11

The dashboard must fail visibly rather than convert a data problem into a false low-risk state.

## Validation command

Run:

```bash
python scripts/validate_data.py
```

The command exits non-zero when any generated metric fails validation.

Run deterministic unit tests:

```bash
python -m unittest discover -s tests -v
```

## Covered invariants

The test suite contains fixtures/tests for:
- FRED parsing;
- FINRA current and legacy free-credit schemas;
- Cboe VIX parsing;
- Shiller date-fraction parsing;
- point-in-time percentiles and event transforms;
- Deleveraging Watch unknown/publication-lag semantics;
- duplicate timestamps;
- non-monotonic timestamps;
- latest-value consistency;
- freshness-state vocabulary.

## Refresh failure behavior

Refresh writes are atomic.

For a metric:
1. fetch;
2. parse;
3. build canonical contract;
4. validate;
5. replace the old JSON only after success.

If a network refresh fails, the prior real metric file is not overwritten.

`refresh-report.json` records the failed metric and whether the previous snapshot was preserved.

The browser combines:
- the original metric `as_of`;
- its configured freshness SLA;
- the latest refresh report.

If the newest refresh explicitly failed, that metric is shown as `error`, even if an older snapshot remains on disk.

If no explicit failure exists but the old observation exceeds its freshness SLA, it is shown as `stale`.

This avoids the dangerous case where a months-old JSON file continues to display a frozen `fresh` badge merely because it was fresh when originally generated.

## Signal failure behavior

Current Deleveraging Watch conditions require fresh source metrics.

If any metric required by a condition is:
- stale;
- missing;
- errored;

that condition is displayed as `unknown`, not `inactive`.

The summary denominator reports known and unknown conditions separately.

## No fallback numbers

No parser or UI path may replace a missing live value with:
- a demo value;
- a fixture value;
- a hard-coded "reasonable" value;
- a third-party mirror value silently substituted for the canonical source.

Fixtures are explicitly tagged `environment: fixture`.

## Historical reproducibility

Derived history declares input lineage and formula/version.

Point-in-time percentile and signal-history logic use only observations that are historically available at the evaluation point. Signal backfill additionally applies the configured publication lag.

## Manual release checklist

Before publishing a data refresh:

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python scripts/validate_data.py`
- [ ] inspect `data/generated/refresh-report.json`
- [ ] confirm no production metric has fixture environment
- [ ] confirm expected history start/end did not unexpectedly shrink
- [ ] confirm latest `as_of` is plausible for the source frequency
- [ ] confirm source/provenance URLs remain canonical
- [ ] confirm Deleveraging Watch unknown count is explained by real missing/stale data
