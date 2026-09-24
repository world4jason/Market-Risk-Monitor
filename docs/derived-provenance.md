# Derived artifact provenance contract

Issue: #55

Derived dashboard outputs are deterministic analytics, not raw source series.
They therefore need provenance that can distinguish:

- source/input data changes;
- methodology/code changes;
- config/threshold/event-definition changes;
- missing required inputs.

This contract applies to aggregate/derived artifacts such as Deleveraging Watch,
policy-rate regimes, Taiwan macro regime, and the moving-average breadth event
study.

## Shape

Every covered artifact carries a top-level `provenance` object:

```json
{
  "provenance": {
    "contract_version": "1.0.0",
    "methodology": {
      "id": "deleveraging-watch",
      "version": "signals-v2"
    },
    "config": {
      "id": "data/config/signals.json",
      "content_digest": "sha256:..."
    },
    "required_inputs": [
      "finra_margin_debt_yoy_pct",
      "vix"
    ],
    "inputs": [
      {
        "id": "vix",
        "as_of": "2026-09-21",
        "snapshot_at": "2026-09-22T10:54:31Z",
        "content_digest": "sha256:..."
      }
    ],
    "generated_at": "2026-09-22T10:54:33Z"
  }
}
```

`build_revision` may be added as supporting provenance, but it is optional and
never replaces methodology/config/input provenance.

## Deterministic digests

All digests are SHA-256 over canonical JSON:

- UTF-8;
- sorted object keys;
- compact separators;
- no NaN/Infinity.

A config digest therefore changes when a threshold, rule, horizon, event
definition, or other config value changes, even if nobody manually bumps a
version number.

Input `content_digest` covers the complete consumed artifact/record payload.
A source revision therefore changes the input digest even when the metric id and
as-of date stay the same.

## Reading changes

Use the fields together:

| What changed | Interpretation |
|---|---|
| methodology version changed | analytics/code methodology changed |
| config digest changed | threshold/rule/config changed |
| input content digest changed | source/input snapshot changed or was revised |
| required input missing from `inputs` | output was built with a required input unavailable |
| only `generated_at` changed | rebuild timing changed; investigate whether the caller supplied a different evaluation time |

A Git commit hash can help during investigation, but it is not sufficient by
itself because it does not say which config and input snapshots were consumed.

## Required inputs vs actual inputs

`required_inputs` is the complete sorted set the methodology/config requires.

`inputs` is the sorted manifest of artifacts/records actually present and
consumed. It may include optional context that affects the output even though
that input is not required for the artifact to exist. Conversely, a required
input may be absent from `inputs`; that absence stays machine-readable rather
than being silently collapsed into the actual-input set.

This distinction is important for Deleveraging Watch: a missing breadth family
must remain visible in provenance even when the runtime condition correctly
becomes `unknown`.

For artifact types that cannot validly build without all inputs, the builder
fails before writing the artifact.

## Snapshot metadata

Each actual input records:

- `id`;
- `as_of` — latest represented observation/reference date where available;
- `snapshot_at` — when that input snapshot was obtained/verified;
- `content_digest`.

At least one of `as_of` or `snapshot_at` must be present.

`as_of` and `snapshot_at` are not interchangeable. If a source/input has a
known effective/reference date but no defensible verification timestamp,
record the date in `as_of` and leave `snapshot_at` null. Do not copy an
effective date into `snapshot_at` merely to make the field non-null.

## Generated time and determinism

Derived builders must not use wall-clock time when the same committed inputs
already provide a deterministic snapshot time.

The default generated timestamp is derived from input snapshot metadata.
Deleveraging Watch also accepts an explicit evaluation time because its current
condition semantics are evaluation-date dependent; if omitted, it derives that
time only from the input metrics referenced by its configured rules. Unrelated
artifacts in the same output directory cannot move the signal evaluation time.

Therefore, rebuilding the same committed fixtures with the same methodology and
config produces byte-equivalent logical output, including provenance.

## Covered artifacts

The convention is enforced by validation for:

- `signals.json`;
- `fed-rate-regime.json`;
- `taiwan-cbc-rate-regime.json`;
- `taiwan-macro-regime.json` when published;
- `ma-breadth-event-study.json` when published.

Validators reject missing/malformed methodology, config digest, required-input
manifest, input snapshot metadata, or content digests.

No GitHub Actions dependency is required; all checks run through the existing
local/external-runner test and validation commands.
