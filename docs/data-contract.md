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
