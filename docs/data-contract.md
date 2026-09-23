# Data contract v1

Issue: #4

The UI reads one canonical metric-series contract. Data-source adapters may change independently.

Schema: `schemas/metric-series.schema.json`

## Required top-level fields

- `schema_version`
- `environment`
- `metric`
- `source`
- `coverage`
- `freshness`
- `lineage`
- `baselines`
- `latest`
- `observations`

## Freshness states

```text
fresh
stale
missing
error
insufficient_data
```

These states are semantically distinct.

- `fresh`: latest real observation is within the configured freshness limit.
- `stale`: last real observation exists but is older than the freshness limit.
- `missing`: expected source/data is absent.
- `error`: refresh/parsing/validation failed.
- `insufficient_data`: observations exist, but not enough history exists for the requested transform.

A stale or missing metric must never be silently treated as low risk.

## Observation statuses

`freshness.state` describes the metric. Each entry in `observations` carries its
own `status`, drawn from a separate vocabulary:

```text
observed
missing
estimated
revised
insufficient_data
```

- `observed`: a real source value for that date.
- `missing`: the source has no value for that date.
- `estimated` / `revised`: provider-flagged provisional or restated values.
- `insufficient_data`: the date exists, but the requested transform has too
  little history to produce a value there — for example the first row of a
  month-over-month or year-over-year change.

Methodology transforms in `pipeline/methodology.py` report their own internal
status vocabulary (`ok` / `missing` / `insufficient_data`). A derived metric must
translate that into the contract vocabulary via
`pipeline.methodology.to_observations()` before writing an artifact; `ok` is not
a valid observation status.

The enum lives in `schemas/metric-series.schema.json`, is mirrored by
`pipeline.validate.ALLOWED_OBSERVATION_STATUSES`, and the two are asserted equal
in `tests/test_validate.py`.

## Observation time vs fetch time

`latest.as_of` is the date represented by the source observation.

`latest.fetched_at` is when the repository snapshot was obtained.

They answer different questions and both must be preserved.

Example:

```json
{
  "as_of": "2026-08-31",
  "fetched_at": "2026-09-18T20:00:00Z"
}
```

A monthly source can therefore be fresh even though `as_of` is weeks earlier, provided its metric-specific freshness rule accounts for publication cadence.

## Historical availability and point-in-time guarantee

Issue #48 records **Option A** as the canonical contract decision: availability
timing belongs in the metric artifact itself. Audit artifacts remain diagnostic;
historical/PIT consumers must not depend on a family-specific audit file to know
when a canonical observation became available.

Each source may declare:

```text
source.availability_basis =
  observation_date | release_date | unknown
```

A missing `availability_basis` is treated as `unknown` for backward
compatibility.

- `observation_date`: the source observation date is itself the date the value
  is considered publicly available. This is appropriate only for sources where
  that guarantee is defensible, such as market closes/effective-date series.
- `release_date`: every non-null observation carries
  `observations[].release_date`. Historical consumers use that date rather
  than the reference-period date.
- `unknown`: the repository cannot reconstruct exact historical availability.
  The data may still be shown as retrospective absolute history, but it must not
  be represented as a canonical point-in-time percentile/event/backtest input.

For example:

```json
{
  "source": {
    "availability_basis": "release_date"
  },
  "observations": [
    {
      "date": "2026-08-01",
      "release_date": "2026-09-21",
      "value": 48.3,
      "status": "observed"
    }
  ]
}
```

`coverage.expected_observation_lag_days` remains useful for operational
freshness expectations. It is **not** evidence of the historical release date
and must not be used to turn `unknown` availability into a PIT guarantee.

### Same-release batches

Multiple reference periods can become known on the same release date. This is
common on the first ingest of a rolling source window. They are one information
arrival, not a sequence of independent historical arrivals.

PIT transforms therefore score every observation in one release-date batch
against the same prior baseline and only add the batch to history after the
whole batch has been scored. A first CIER ingest containing twelve historical
months all first verified on one date cannot manufacture eleven synthetic
strict-past comparisons.

For event/backfill consumers, one availability date contributes at most one
state to the point-in-time sequence; the latest reference-period value in that
release batch represents what became known at that arrival.

### Relationship to baselines

`baselines[].point_in_time: true` is valid only when the source has a known
availability basis. Validation rejects canonical PIT baselines when
availability is missing/unknown. Membership-sensitive metrics are additionally
subject to their constituent-membership PIT gate.

A non-PIT baseline may still describe retrospective history, but the UI must
label or disable PIT modes rather than silently upgrading it.

## History coverage

`coverage.history_start` and `coverage.history_end` are per metric.

The dashboard must not force all series to share the newest common start date.

Examples:
- long-run valuation may begin in the 19th century;
- financial-conditions history may begin in the 1970s;
- VIX begins later;
- FINRA margin history begins later again.

When an older event predates a metric, the UI renders that metric as unavailable for that event.

## Source metadata

Each metric records:
- provider;
- dataset;
- optional series id;
- canonical source URL;
- license/redistribution note;
- redistribution status.

The raw-history ticket (#5) must review redistribution terms before committing vendor-restricted historical data.

## Lineage

Raw source:

```json
{
  "kind": "raw",
  "inputs": [],
  "formula": null,
  "transform_version": "raw-v1"
}
```

Derived metric:

```json
{
  "kind": "derived",
  "inputs": ["finra_margin_debt"],
  "formula": "(x_t / x_t-12 - 1) * 100",
  "transform_version": "yoy-v1"
}
```

Derived series must remain reproducible from documented inputs.

## Baselines

A metric declares the historical contexts it supports.

Supported baseline types:
- `full_history_percentile`
- `rolling_percentile`
- `rolling_zscore`
- `rolling_robust_zscore`
- `event_window`
- `none`

`point_in_time: true` means that when evaluating a historical date T, the baseline may use only observations available through T.

This prevents the historical explorer from accidentally using future data to normalize older crises.

## Frequency-aware freshness

The contract stores `max_age_days` on each metric rather than hard-coding a global rule.

Initial policy is intentionally conservative and will be finalized per source during ingestion:
- daily series: a few calendar days, allowing weekends/holidays;
- weekly series: roughly one to two release intervals;
- monthly series: enough time for expected publication lag.

The source adapter owns the configured limit. The UI only renders the resulting state.

## Missing observations

Individual observation values may be `null` and may include:

```json
{"date":"2020-03-01","value":null,"status":"missing"}
```

This is distinct from a top-level refresh failure.

## Fixtures

Contract examples:
- `data/fixtures/metric-daily.json`
- `data/fixtures/metric-weekly.json`
- `data/fixtures/metric-monthly.json`

All are explicitly marked `environment: "fixture"` and must never be served as production current data.

## Versioning

Current schema version: `1.0.0`.

Breaking contract changes require a schema-version bump. Additive source metadata can be introduced only if the schema and fixtures are updated together.

### Before the first production release

Making a previously absent field required is a breaking change by that rule.
`metric.comparison` became required while every artifact still declared
`schema_version: 1.0.0`, which is a contradiction worth naming rather than
leaving implicit.

No production data-backed release has yet been published under `1.0.0`.
**Until that first release, this project treats `1.0.0` as a pre-release
contract and does not guarantee compatibility across finalization changes.**
After v0.1 publishes, breaking changes require a schema-version bump.

This is a policy, not a claim about who is reading the repository. The repo is
public, so we cannot assert that nothing consumes the contract; we can only
state that nothing has been promised about it yet.

The condition attached to that allowance is the part that matters: a
finalization change must update the schema, `pipeline/validate.py`, every
producer, and **all canonical fixtures and examples in the same change**.
`metric.comparison` initially did not, and `data/fixtures/metric-*.json` were
left violating the repository's own schema.

`tests/test_artifact_writer.py` now validates every metric-shaped JSON in the
repository outside `data/generated/` against the same JSON Schema
`scripts/validate_data.py` applies, so an example cannot be left behind again.

Once v0.1 is published this allowance ends, and the normal bump rule applies.
