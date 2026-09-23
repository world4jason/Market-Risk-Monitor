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

The unittest suite invokes the executable frontend behavior matrix through
Node's built-in test runner. No npm install or live network is required.
Node.js 20+ is required for this UI contract layer.

Run the UI behavior layer directly when debugging frontend semantics:

```bash
python scripts/test_ui_behavior.py
```

It executes production functions from `assets/app.js` against committed
`tests/fixtures/ui_behavior.json` cases for freshness/error states, unit-aware
formatting, Taiwan breadth, PIT gating, unavailable modules, core snapshot
failure, keyboard interaction, and overview interpretation.

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

Derived history declares input lineage and formula/version. Aggregate derived
artifacts also carry and validate the [derived provenance contract](./derived-provenance.md):
methodology version, config digest, required/actual input manifests, snapshot
metadata, and input content digests.

Point-in-time percentile and signal-history logic use only observations that are historically available at the evaluation point. Signal backfill follows the canonical `source.availability_basis` / `observations[].release_date` contract; an operational expected lag never upgrades unknown historical availability into PIT data.

## Accessibility interaction expectations

The public dashboard targets WCAG 2.2 AA interaction behavior where applicable:

- **2.1.1 Keyboard** — interactive metric cards, buttons, selects, disclosure
  controls, and the metric dialog are operable without a pointer.
- **2.4.7 Focus Visible** and **2.4.11 Focus Not Obscured (Minimum)** — keyboard
  focus uses an explicit high-contrast outline and the modal keeps the focused
  close control visible.
- **1.4.1 Use of Color** — freshness and signal state remain available as text
  (`fresh`, `stale`, `error`, `active`, `unknown`) rather than color alone.
- **2.5.3 Label in Name** and **4.1.2 Name, Role, Value** — custom metric-card
  controls expose button role, accessible name, and keyboard activation;
  dialog/select/toggle controls retain programmatic labels.
- Chart SVGs have meaningful names and are paired with visually-hidden text
  summaries containing key coverage dates and values so the plotted line is not
  the only way to obtain the information.

Keyboard-only verification for the core path:

1. Tab to a metric card and confirm a visible focus indicator.
2. Open with Enter, close with Escape, and confirm focus returns to that card.
3. Re-open with Space and confirm the page does not scroll/double-activate.
4. Tab through Reload, theme, history selects, disclosure summary, and source
   links; every control must retain a visible focus indicator.
5. In the metric dialog, confirm the Close control receives focus immediately.
6. At desktop and 390px widths, confirm focused controls are not hidden or
   clipped by the viewport.

Relevant W3C understanding references:
- https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html
- https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html
- https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html
- https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html

## Manual release checklist

The release command itself is in [release.md](./release.md). It is not
`scripts/bootstrap_sources.py`, and it requires `--clean-output`.

Before publishing a data refresh:

- [ ] generated with the command in [release.md](./release.md), including `--clean-output`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `python scripts/validate_data.py`
- [ ] inspect `data/generated/refresh-report.json`
- [ ] confirm no production metric has fixture environment
- [ ] confirm expected history start/end did not unexpectedly shrink
- [ ] confirm latest `as_of` is plausible for the source frequency
- [ ] confirm source/provenance URLs remain canonical
- [ ] confirm Deleveraging Watch unknown count is explained by real missing/stale data
- [ ] confirm no artifact declares `redistribution: "restricted"` (see [release.md](./release.md))
- [ ] confirm `refresh-report.json` `removed_artifacts` contains nothing unexpected
