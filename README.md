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
- `docs/derived-provenance.md`
- `docs/data-sources.md`
- `docs/methodology.md`
- `docs/signals.md`
- `docs/qa.md`
- `docs/cache-policy.md`

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

### Producing a release snapshot

A published snapshot is **not** produced by `scripts/bootstrap_sources.py`,
which defaults to including the TraderMonty moving-average breadth source. It
uses an explicit source allowlist and `--clean-output`:

```bash
python scripts/bootstrap_taiwan_taiex.py

python scripts/refresh_data.py --clean-output \
  --fred-id nfci --fred-id nfci_risk --fred-id nfci_credit \
  --fred-id nfci_nonfinancial_leverage --fred-id us_recession \
  --fred-id fed_target_legacy --fred-id fed_target_upper \
  --cboe-vix \
  --finra-file <margin-statistics.xlsx> \
  --shiller-file <ie_data.xls> \
  --twse-current \
  --cbc-rate-file <cbc-rates.csv>

python scripts/build_signals.py
python scripts/validate_data.py
python scripts/site_smoke.py
```

`--clean-output` is not optional. Without it a refresh is additive: an
unselected source is skipped rather than cleared, and the catalog globs the
whole output directory, so an artifact left by an earlier run with different
flags is published again. That is how a `redistribution: "restricted"` series
can survive an allowlist written to exclude it.

Full procedure, exclusions and pre-publish checks: [docs/release.md](docs/release.md).

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


### Open point-in-time MA breadth research path

For historical S&P 500 20/50/200DMA breadth without a paid breadth export:

```bash
python scripts/bootstrap_ma_breadth_open.py

python scripts/refresh_data.py \
  --ma-breadth-file .cache/ma-breadth-open/sp500-ma-breadth-open.csv

python scripts/build_ma_breadth_study.py
python scripts/validate_data.py
```

This path uses:
- MIT-licensed community point-in-time S&P 500 membership history (1996+)
- Apache-2.0 FINSABER delisted-inclusive adjusted-close prices (2000–2024)

The ~253MB price file is cached under `.cache/` and is not committed to this repository. The resulting breadth is a reproducible open-data reconstruction, not an official S&P Dow Jones breadth feed.

See `docs/moving-average-breadth-sources.md` for source, survivorship, and post-2024 limitations.


### Extend MA breadth through current date (optional local research)

The open FINSABER dataset ends at 2024-12-31. To extend the point-in-time reconstruction into 2025/2026:

```bash
python -m pip install -r requirements-research.txt
python scripts/bootstrap_ma_breadth_open.py
python scripts/bootstrap_ma_breadth_hybrid.py

python scripts/refresh_data.py \
  --ma-breadth-file .cache/ma-breadth-open/sp500-ma-breadth-hybrid.csv

python scripts/build_ma_breadth_study.py
python scripts/validate_data.py
```

The hybrid path uses Yahoo Finance through yfinance only as an optional local recent-price supplement. yfinance documents the underlying Yahoo Finance API data as intended for personal use; review Yahoo's terms before redistributing any resulting recent data. Raw recent files remain under `.cache/` and are not committed.


## Taiwan Market Regime

The dashboard now has a separate Taiwan market section built from transparent official/public inputs rather than attempting to clone proprietary MM/Breadth formulas.

### Current TAIEX + official TWSE advance/decline

```bash
python scripts/refresh_data.py --twse-current
```

### Backfill official TAIEX history

```bash
python scripts/bootstrap_taiwan_taiex.py --start 1997-01
```

Monthly TWSE responses are cached under `.cache/taiwan-taiex/`. Current refreshes merge into the backfill instead of truncating it.

### Collect forward point-in-time TWSE common-stock panel

```bash
python scripts/collect_taiwan_stock_snapshot.py
```

After sufficient sessions accumulate, compute transparent trend/extreme breadth:

```bash
python scripts/build_taiwan_trend_breadth.py \
  --panel-file .cache/taiwan-stocks/twse-common-stock-panel.csv
```

This produces:
- % TWSE common stocks above 20/50/200DMA
- new 52-week highs/lows
- net new highs
- normalized High-Low %

### Import official/public Taiwan macro releases

Normalized contract:

```text
date,provider,series_id,value,unit,release_date,source_url
```

Then pass every source-owned snapshot in the same refresh. The option is
repeatable, so CIER and NDC can remain separate files while the pipeline builds
one deterministic union:

```bash
python scripts/refresh_data.py \
  --taiwan-macro-file .cache/taiwan-macro/cier-pmi.csv \
  --taiwan-macro-file /path/to/ndc-current-vintage.csv
```

Each canonical `series_id` must belong to exactly one input file, with one
stable provider/unit identity per series. Existing canonical macro metrics and
`taiwan-macro-audit.json` are cross-checked before refresh; a missing/stale audit
fails closed. A later refresh that omits an existing series or truncates its
published dates also fails before writing anything. Release-aware series use forward-only vintage chronology. NDC keeps
`availability_basis=unknown` and may revise current-vintage history, but an older
verified snapshot cannot replay over a newer one. Canonical provider/unit are
validated on first ingest and across refreshes. This keeps a CIER-only refresh
from silently deleting NDC artifacts (and vice versa), including under
`--clean-output`.

The MRM Taiwan macro regime is documented in `docs/taiwan-macro-methodology.md` and is explicitly **not** a reconstruction of MacroMicro/MM.

### CBC + Fed rate velocity

Fetch official CBC change-date history:

```bash
python scripts/bootstrap_cbc_rates.py
python scripts/refresh_data.py \
  --cbc-rate-file .cache/taiwan-rates/cbc-rates.csv
```

Fed target-rate velocity is rebuilt from the configured FRED legacy target + modern target-range-upper series during a normal FRED/public refresh:

```bash
python scripts/refresh_data.py --public
```

Rate methodology: `docs/rate-velocity-methodology.md`.

### Taiwan historical event comparison

Taiwan event anchors live in `data/taiwan-events.json`.

The UI supports:
- raw levels
- strict-past historical percentiles
- event-normalized paths

Membership-sensitive breadth generated from non-point-in-time constituent lists is blocked from canonical historical percentile/event analysis.

### Taiwan references

- `docs/taiwan-sources.md`
- `docs/taiwan-macro-methodology.md`
- `docs/rate-velocity-methodology.md`
