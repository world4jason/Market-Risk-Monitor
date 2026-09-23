# Frontend cache and loading policy

The dashboard is a static GitHub Pages application. Generated artifact URLs are
stable across releases, so cache behavior must preserve snapshot correctness
without paying the cost of downloading every historical series on first paint.

## Current snapshot artifacts

Examples:

- `data/generated/overview.json`
- `data/generated/catalog.json`
- `data/generated/signals.json`
- `data/generated/refresh-report.json`

These are fetched with `cache: "no-store"`.

Reason: the paths are reused when a new release snapshot is committed. The
decision-first overview should not reuse a prior release's current-state
summary merely because the browser has an older response cached.

## Full metric history

Per-metric files under `data/generated/<metric>.json` are **not** fetched on
the default render path. They are fetched only when a user opens a metric
detail or requests a historical/research view.

The browser request uses `cache: "no-cache"`, which allows normal HTTP
revalidation while avoiding blind reuse of an old same-path artifact across
releases.

Within one page session, `ensureMetricLoaded()` provides a stronger cache:

1. a fully loaded metric already in memory is returned immediately;
2. an in-flight request for the same metric is shared;
3. successful loads replace the lightweight summary in `state.metrics`.

Reopening the same metric therefore does not issue another request during the
same session.

## Deferred below-fold context

Event definitions, optional MA study/config artifacts, Taiwan macro regime, and
rate-regime context are not part of the first-view request set. The frontend
loads them only when the corresponding below-fold section approaches the
viewport or when the user requests a history/event view. This keeps the
decision-first render bounded to catalog + overview + signals + refresh report.

## Static configuration and event definitions

Examples:

- `data/events.json`
- `data/taiwan-events.json`
- `data/config/ma-breadth.json`
- optional regime/study context artifacts used below the overview

These use the browser's default cache policy. They are not the current market
snapshot and do not justify bypassing the browser cache on every reload.

## Future versioned artifacts

If generated artifacts gain immutable, content-addressed or release-versioned
URLs, historical files can move to a long-lived immutable cache policy. Do not
apply `immutable` semantics to the current stable filenames: a later release
can legitimately replace their contents.
