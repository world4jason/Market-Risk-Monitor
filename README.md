# Market Risk Monitor

A public, explainable dashboard for monitoring U.S. market leverage, financial stress, volatility, credit/risk conditions, and historical regime context.

## Product questions

1. Is leverage / risk appetite historically elevated?
2. Is stress actually rising?
3. Is deleveraging underway?
4. How does the current regime compare with prior cycles?

This project intentionally avoids hidden BUY / SELL logic. Current values are paired with source, as-of date, freshness, and historical context.

## Current architecture

- GitHub Pages frontend
- buildless HTML / CSS / browser JavaScript
- static JSON metric snapshots
- local or external-runner Python refresh pipeline
- no GitHub Actions dependency
- point-in-time historical transforms with no-look-ahead rules

See:
- `docs/architecture.md`
- `docs/data-contract.md`
- `docs/data-sources.md`
- `docs/methodology.md`
- `docs/signals.md`
- `docs/qa.md`

## Quick start

Install pipeline dependencies:

```bash
python -m pip install -r requirements.txt
```

Bootstrap official sources, refresh snapshots, validate data, and run the static-site smoke check in one command:

```bash
python scripts/bootstrap_sources.py
```

FINRA may occasionally require a browser download because its CDN can reject automated workbook requests; the bootstrap command prints the exact manual fallback without substituting another data provider.

Run deterministic tests:

```bash
python -m unittest discover -s tests -v
```

Refresh network-accessible public sources (configured FRED series + official Cboe VIX):

```bash
python scripts/refresh_data.py --public
```

Refresh configured FRED series only:

```bash
python scripts/refresh_data.py --fred
```

Refresh official Cboe VIX only:

```bash
python scripts/refresh_data.py --cboe-vix
```

Refresh only selected FRED metrics:

```bash
python scripts/refresh_data.py --fred --fred-id nfci --fred-id vix
```

Import an official FINRA margin-statistics file already downloaded locally:

```bash
python scripts/refresh_data.py --finra-file /path/to/margin-statistics.xlsx
```

FINRA source page:

`https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics`

Import the live Robert Shiller workbook downloaded from shillerdata.com:

```bash
python scripts/refresh_data.py --shiller-file /path/to/ie_data.xls
```

Build/rebuild Deleveraging Watch from whatever valid metric snapshots are present:

```bash
python scripts/build_signals.py
```

Validate all generated JSON artifacts:

```bash
python scripts/validate_data.py
```

Run the no-GHA static-site smoke check:

```bash
python scripts/site_smoke.py
```

Serve locally:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/`.

## GitHub Pages without GHA

Repository Pages settings should use:

- Source: **Deploy from a branch**
- Branch: **main**
- Folder: **/(root)**

The root `.nojekyll` marker is committed. The deployed site is already publish-ready static content; no Actions build is required.

Data refresh is intentionally separate from Pages publication. A successful refresh updates `data/generated/*.json`; after validation, those snapshots can be committed normally.

## Historical comparison

Historical context is first-class.

The dashboard keeps each metric's maximum valid history instead of truncating everything to one common date. Event comparisons are defined in `data/events.json` and currently include:

- Dot-com peak / unwind
- Global Financial Crisis
- COVID shock
- 2022 tightening / bear market
- current period

If a metric did not exist for an older event, the UI shows it as unavailable rather than silently substituting a proxy.

Historical percentiles and robust z-scores are strict-past by default: a score at time T cannot use observations after T.

## Data safety rules

- `fresh`, `stale`, `missing`, `error`, and `insufficient_data` are distinct states.
- A failed fetch never writes a fabricated replacement number.
- Previous real data may remain visible only with its original as-of date and stale state.
- Fixture data is never treated as production current data.
- Derived metrics retain formula and input lineage.
- Restricted third-party history is not bundled automatically.

## Roadmap

See issue #1 and child tickets.

Current sequence:

`research → architecture → data contract → history/FINRA → methodology → UI → history explorer → signals → QA → deploy`

## Status

Completed:
- benchmark research
- no-GHA architecture
- canonical data contract
- point-in-time historical methodology
- FRED / FINRA / Cboe VIX / Shiller ingestion adapters
- static responsive dashboard
- absolute / point-in-time percentile / rolling percentile / rate-of-change history views
- event-window comparison with recession context
- transparent Deleveraging Watch with historical backfill
- runtime stale/error protection and QA fixtures

In progress:
- production long-history snapshots
- official FINRA 1997+ import verification
- complete production dashboard data population
- execute the deterministic QA suite against real generated snapshots
- final Pages publication
