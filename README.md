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

Refresh the public no-key TraderMonty 50DMA/200DMA breadth convenience source:

```bash
python scripts/refresh_data.py --tradermonty-ma-breadth
```

This source is useful for current/recent monitoring, but its implementation uses the current S&P 500 constituent list for historical price backfill. MRM therefore marks it `current_constituents_retroactive`: raw levels are shown, while historical percentiles/signals/event studies remain non-canonical/blocked.

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

Optional: fetch user-authorized Tiingo EOD prices into a resumable local cache:

```bash
export TIINGO_API_TOKEN=...
python scripts/fetch_tiingo_pit_prices.py \
  --start-date 2022-01-01 \
  --end-date 2026-09-18 \
  --output-dir .cache/tiingo-sp500-prices
```

The downloader uses the open historical membership source by default, caches one CSV per ticker, resumes safely, records ticker aliases/failures in a manifest, and never commits the token. Tiingo's license is internal-use by default, so these raw price files stay local and are ignored by the repository.

Self-compute point-in-time 20/50/200DMA breadth from the open historical S&P 500 membership file plus user-authorized per-ticker prices:

```bash
python scripts/build_ma_breadth_self_compute.py \
  --price-dir /path/to/ticker-price-csvs \
  --price-adjustment adjusted_close
```

By default this uses the MIT-licensed `chinobing/historical_sp500_constituents` membership snapshots (1996-present), hashes the exact membership file for reproducibility, and fails if missing price coverage exceeds the configured tolerance.

Import an authorized S&P 500 moving-average breadth export:

```bash
python scripts/refresh_data.py \
  --ma-breadth-file /path/to/sp500-ma-breadth.csv
```

Required contract and survivorship rules:

- `docs/moving-average-breadth-sources.md`
- `docs/moving-average-breadth-methodology.md`

Build/rebuild the <25% / <15% 50DMA threshold event study after the breadth and SPX price snapshots exist:

```bash
python scripts/build_ma_breadth_study.py
```

Cross-check one local 50DMA observation against an external reference fixture/export:

```bash
python scripts/check_ma_breadth_reference.py \
  --reference /path/to/reference.json
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


## Moving-Average Breadth

The Trend Participation module supports:

- S&P 500 % above 20DMA
- S&P 500 % above 50DMA
- S&P 500 % above 200DMA
- optional custom 15/25/75/85 heuristic overlays
- SPX overlay when the S&P 500 price metric is available
- strict-past / rolling percentile history
- threshold-crossing event study for 25% and 15%
- independent Deleveraging Watch conditions

Historical event-study/backfill use requires point-in-time constituent-aware breadth. A current-constituent retroactive reconstruction is blocked from canonical historical analysis.
