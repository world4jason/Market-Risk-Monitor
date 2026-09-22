# Presentation Contract

Issues: #51, #52

This document covers how values are *displayed*. It says nothing about whether a
move is good or bad; see [methodology.md](./methodology.md) for that.

## Comparison semantics

A period-to-period change is not meaningful in the same way for every metric.
A policy rate going 1.75% → 2.00% is **+25 bp**, not +14.29%. An index centred
on zero has no stable relative change at all. A metric that already *is* a
change should not be shown as a change of a change.

Each metric artifact therefore declares how its values are compared, rather than
leaving the UI to infer it from the numeric unit alone:

```json
{ "metric": { "comparison": "basis_points" } }
```

| value | meaning | rendered |
|---|---|---|
| `basis_points` | 100 × the absolute difference | `+25.0 bp` |
| `percentage_points` | absolute difference of a percent-valued series | `+5.00 pp` |
| `percent_change` | relative change against the prior observation | `+2.58%` |
| `absolute` | plain difference in the metric's own unit | `-0.002` |
| `none` | a change is not meaningful for this metric | `—` |

The enum lives in `schemas/metric-series.schema.json`, is mirrored by
`pipeline.validate.ALLOWED_COMPARISONS`, and both are asserted equal in
`tests/test_presentation.py`.

## How it is assigned

`pipeline/presentation.py` derives the value, and `scripts/refresh_data.py`
stamps it at the single point every artifact is written. Deriving it once and
validating it beats restating it in each builder, where it would drift.

| condition | comparison | why |
|---|---|---|
| transform is a percent change, or units are basis points | `none` | already a change |
| units are binary | `none` | a 0/1 indicator has no delta |
| percent **and** a policy-rate level | `basis_points` | the conventional unit for rate moves |
| percent, anything else | `percentage_points` | dimensionally correct default |
| percentile | `percentage_points` | ranks differ in points |
| count | `absolute` | includes net differences that cross zero |
| index, zero-centred (NFCI family, A-D line) | `absolute` | relative change has no stable sign |
| index, ratio, currency, shares | `percent_change` | strictly positive levels |
| anything unrecognised | `absolute` | always dimensionally honest |

### The safety property

Percentage points and basis points are the **same dimension**, differing only by
a factor of 100. So a percent-valued metric that has not been classified as a
rate is displayed as `+0.25 pp` instead of `+25.0 bp` — a different unit, never
a different meaning. The old failure mode, `+14.29%`, is unreachable for any
percent metric.

Two metric-id sets in `pipeline/presentation.py` carry the classifications that
cannot be read off the units: `RATE_LEVEL_METRIC_IDS` and
`ZERO_CENTRED_INDEX_METRIC_IDS`. Add to them when a new series of either kind
lands.

### Missing or zero priors

A metric with fewer than two non-null observations has no change. A
`percent_change` metric whose prior observation is zero has no defined relative
change. Both render as `—`; neither fabricates a value or divides by zero.

Metric cards and the detail dialog call the same `formatChange()` in
`assets/app.js`, so a value cannot be formatted one way in one place and
differently in the other.

## No pillar-level aggregation

The "Snapshot health by pillar" panel reports **freshness and coverage only**.

It previously showed the median of each pillar's metric percentiles. Percentiles
are comparable as ranks but not as economics: a high volatility percentile means
more stress, a high breadth percentile means stronger participation, and a high
valuation percentile is context rather than either. A median across them reads
as a pillar risk score, which is exactly the hidden composite this project
refuses to publish.

So the panel reports how many of a pillar's metrics are current, and nothing
else. Each metric's own historical percentile stays on its own card, where its
direction is legible next to its name, units and source.

Any future directional summary must first document, per metric, whether it is
higher-is-riskier, lower-is-riskier, two-sided, or contextual and therefore
ineligible — and stale, missing or unknown inputs must never become a benign
contribution to it. See #52.

## Dates

`latest.as_of` is the newest observation that actually has a value.
`coverage.history_end` is the end of the covered range, which may be a later
date whose observation is still `missing`.

The UI shows `latest.as_of` wherever it says "as of", and uses
`history_start → history_end` only to label a coverage range. Never present
`history_end` as the date of the newest data.
