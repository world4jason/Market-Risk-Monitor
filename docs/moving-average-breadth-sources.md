# Moving-Average Breadth Sources

Issue: #23

## Target metrics

The v0.2b Trend Participation module tracks the percentage of S&P 500 constituents above:

- 20-day moving average — common provider symbol `S5TW`
- 50-day moving average — common provider symbol `S5FI`
- 200-day moving average — common provider symbol `S5TH`

The core 50-day reference is the TradingView/Barchart-style `S5FI` series.

## Candidate sources

### 1. TradingView `INDEX:S5FI`

Reference:
https://www.tradingview.com/symbols/INDEX-S5FI/

TradingView identifies `S5FI` as **S&P 500 Stocks Above 50-Day Average**.

Pros:
- directly matches the supplied chart's metric class;
- long chart/history is visible;
- useful external cross-check.

Cons:
- TradingView is not used as a production scraper target;
- the public page is a chart/product surface, not a documented bulk-data contract;
- redistribution rights for historical values must not be assumed;
- 20D/200D equivalents are not guaranteed to share the exact same provider/universe/maintenance rules.

v0.2b role: **reference/cross-check only**.

### 2. Barchart `$S5FI`

Reference:
https://www.barchart.com/stocks/quotes/%24S5FI/price-history

Barchart identifies `$S5FI` as **S&P 500 Stocks Above 50-Day Average**.

As a fixed validation reference observed during implementation, Barchart reported **45.52 on 2026-09-01**. This value is stored only as a small QA fixture/reference, not as a replacement historical dataset.

Its public historical page states:
- site visitors can view recent daily history;
- members may access longer downloadable history;
- Historical Data Download / API products provide deeper history, with availability depending on product/symbol;
- Barchart's price-history documentation says site/member daily history can extend to two years in the regular view, while its Historical Data product can provide daily data back to 01/01/2000 and lower-frequency history farther back, depending on symbol.

Pros:
- exact S5FI-style series;
- historical export/API path exists;
- useful for cross-provider validation.

Cons:
- proprietary data/product;
- long-history export can require membership/product access;
- public GitHub redistribution rights are not assumed.

v0.2b role: **preferred authorized export/API candidate for 50DMA**, subject to the user's access/license.

### 3. StockCharts Percent Above Moving Average family

Reference:
https://chartschool.stockcharts.com/table-of-contents/market-indicators/percent-above-moving-average

StockCharts documents S&P 500 percentage-above-moving-average breadth and explicitly references:
- `$SPXA50R` for S&P 500 % above 50-day SMA;
- the same indicator family supports S&P 500 percentage/number above selected moving averages, including 50/150/200-day averages.

StockCharts also documents common interpretation:
- above 70% is often considered overbought;
- below 30% is often considered oversold;
- oversold is **not automatically a buy signal**.

Pros:
- methodology is clearly documented;
- index scope is explicit;
- strong cross-check for 50DMA and 200DMA breadth;
- percentage representation is directly comparable across time.

Cons:
- proprietary service/data;
- redistribution rights are not assumed;
- 20DMA availability is not guaranteed in the same documented symbol family.

v0.2b role: **methodology/reference and authorized-export candidate**.

### 4. Self-computed point-in-time S&P 500 breadth

Formula for horizon N:

```text
Breadth_N(t) =
100 * count(eligible S&P500 constituents with close_t > SMA_N,t)
      / count(eligible S&P500 constituents)
```

Pros:
- transparent;
- all 20D/50D/200D horizons can use one consistent universe;
- numerator/denominator can be preserved;
- historical event study is fully reproducible if source inputs are licensed.

Cons:
- requires **point-in-time historical S&P 500 membership**, not today's list;
- requires constituent price history with one documented adjustment convention;
- a naive present-day membership backfill creates survivorship bias;
- licensing/redistribution for membership and prices must be handled separately.

v0.2b role: **best reproducibility path when point-in-time membership and prices are available**.

## Canonical v0.2b ingest path

v0.2b supports an **authorized local CSV contract**.

A provider export can be imported without hard-coding a web scraper and without assuming the public repo may redistribute the underlying vendor history.

Required columns:

```text
date
market_scope
provider
above_20dma_pct
above_50dma_pct
above_200dma_pct
```

Optional audit columns:

```text
eligible_20d
eligible_50d
eligible_200d
above_20d_count
above_50d_count
above_200d_count
missing_20d
missing_50d
missing_200d
membership_mode
membership_snapshot
price_adjustment
```

Required invariants:
- `market_scope = S&P 500`
- one provider/export family per file
- percentage values are within [0,100]
- numerator <= denominator when raw counts are supplied
- missing counts are explicit; they are never interpreted as below-MA constituents

## Point-in-time membership policy

Historical self-computation must use membership appropriate to each historical date.

Acceptable:
- provider-supplied precomputed breadth whose universe methodology is documented;
- point-in-time constituent membership snapshots;
- a membership event history that can reconstruct the constituent set on each date.

Not acceptable as "point-in-time accurate":
- using today's S&P 500 members for 2008, 2020, or any prior date;
- silently removing delisted constituents;
- filling unavailable historical membership with current membership.

If only a current-membership reconstruction is available, it must be labeled:

```text
membership_mode = current_constituents_retroactive
```

and is **not eligible** for canonical historical event studies or Deleveraging Watch backfills.

## Price convention for self-computation

One convention must be declared for every self-computed file.

Recommended default:
- daily adjusted close for split continuity;
- all constituents use the same adjustment convention;
- SMA_N is the arithmetic mean of the preceding N available trading-session closes including date t.

If a provider's precomputed series uses another convention, preserve the provider series as canonical instead of forcing a synthetic match.

## Historical coverage

Coverage depends on the authorized source actually imported.

The pipeline records actual coverage and does not invent a universal start date.

Practical target:
- 50DMA: use the deepest authorized S5FI/SPXA50R history available;
- 200DMA: same provider/universe where possible;
- 20DMA: same provider/universe or self-computed point-in-time series.

## Cross-provider validation

The 50DMA series should be cross-checked against at least one external reference observation:
- TradingView `INDEX:S5FI`
- Barchart `$S5FI`
- StockCharts `$SPXA50R`

A mismatch is not automatically an error because providers may differ in:
- constituent eligibility;
- corporate-action timing;
- index reconstitution timing;
- price adjustment;
- session cutoff.

The validation record must retain date, provider, reference value, local value, absolute difference, and tolerance.

## Redistribution policy

- Do not commit paid/proprietary long-history values to the public repository unless redistribution rights are verified.
- Authorized local imports may be used to generate local snapshots.
- Public-repo fixtures use synthetic data only.
- TradingView/Barchart/StockCharts pages are references, not scraping targets.


## 5. TraderMonty public breadth CSV — automated 50DMA / 200DMA convenience source

Project:
https://github.com/tradermonty/market-breadth-analysis

Public detail CSV:
https://tradermonty.github.io/market-breadth-analysis/market_breadth_data.csv

The project README documents:
- S&P 500 breadth calculation;
- both 200-day and 50-day moving-average breadth;
- a stable public CSV published through GitHub Pages;
- roughly 10 years / ~2,500 daily rows in the current analyzer workflow;
- no API key required to consume the published CSV.

MRM now provides:

```bash
python scripts/refresh_data.py --tradermonty-ma-breadth
```

Mapping:
- `Breadth_50_Index_Raw * 100` → `sp500_above_50dma_pct`
- `Breadth_Index_Raw * 100` → `sp500_above_200dma_pct`

### Critical survivorship limitation

TraderMonty's current implementation fetches the **current S&P 500 constituent list** from FMP and then retrieves historical prices for those symbols before computing historical breadth.

Therefore MRM marks the imported source:

```text
membership_mode = current_constituents_retroactive
point_in_time_membership = false
```

Consequences:
- useful for current/recent monitoring and independent comparison;
- **not canonical for historical threshold studies**;
- **not allowed in historical Deleveraging Watch backfill**;
- never allowed to overwrite an existing point-in-time canonical MA-breadth snapshot.

This makes the public CSV useful without hiding its survivorship bias.

## 6. Open point-in-time membership source for self-computation

Project:
https://github.com/chinobing/historical_sp500_constituents

The repository publishes:
- `sp_500_historical_components.csv`
- daily S&P 500 historical constituent snapshots from 1996-01-02 to present
- MIT-licensed repository code/data files

MRM supports this format directly through:

```bash
python scripts/build_ma_breadth_self_compute.py \
  --price-dir /path/to/authorized/per-ticker-prices
```

The script:
1. fetches the open historical membership CSV by default (or accepts a local file);
2. hashes the exact membership file for reproducibility;
3. loads user-authorized per-ticker price CSVs;
4. computes 20/50/200-day moving averages using point-in-time membership;
5. records eligible / above / missing-price counts per date;
6. rejects the run if missing-price coverage exceeds the configured tolerance.

This path solves the **membership survivorship** problem. It does not solve historical price licensing automatically; the user remains responsible for providing price files they are entitled to use.

## Current S5FI cross-check

Independent public pages agree on recent S5FI closes:
- Investing.com: 2026-09-18 close = 27.83
- EODData: 2026-09-18 close = 27.83

This is useful as a current-value cross-provider sanity check, while long-history licensing remains separate.


## Exact provider-style symbol cross-checks

Current public historical pages confirm the three moving-average breadth families:

- `S5TW` — S&P 500 Stocks Above 20-Day Average
- `S5FI` — S&P 500 Stocks Above 50-Day Average
- `S5TH` — S&P 500 Stocks Above 200-Day Average

Recent public reference observations:
- S5TW: 2026-09-17 = 21.07
- S5FI: 2026-09-18 = 27.83
- S5TH: 2026-09-18 = 49.50

These small fixed references are suitable for cross-provider sanity checks. They are not a substitute for a licensed historical dataset.


## Open-data point-in-time research path

To avoid making the historical study depend entirely on a paid breadth vendor, the repository also supports a self-computed research path using two public datasets.

### Point-in-time S&P 500 membership

Repository:

https://github.com/chinobing/historical_sp500_constituents

File:

`sp_500_historical_components.csv`

Properties:
- daily/snapshot-style `date,tickers` history;
- coverage from 1996-01-02 to present;
- repository license: MIT;
- maintained forward through current S&P 500 changes.

This is an **open community-maintained membership history**, not an official S&P Dow Jones Indices constituent feed. Results should therefore keep the provider/provenance visible and should be cross-checked for important historical episodes.

### Delisted-inclusive constituent prices

Dataset:

https://huggingface.co/datasets/finsaber-team/FINSABER-reproduce

File:

`data/price/all_sp500_prices_2000_2024_delisted_include.csv`

Properties:
- dataset card license: Apache-2.0;
- roughly 4.74 million daily rows;
- 2000-01-03 through 2024-12-31;
- includes delisted S&P 500 symbols;
- includes `adjusted_close`;
- price-only CSV is roughly 253–265 MB.

Using a delisted-inclusive dataset is materially better than downloading prices only for today's surviving constituents.

### Self-compute pipeline

Run:

```bash
python scripts/bootstrap_ma_breadth_open.py
```

The bootstrap:
1. downloads/caches the open membership history;
2. downloads/caches the FINSABER price CSV;
3. streams the large price file into a temporary SQLite database;
4. sorts each symbol chronologically inside SQLite;
5. calculates close > SMA20 / SMA50 / SMA200 using `adjusted_close`;
6. selects the most recent constituent snapshot whose date is <= each observation date;
7. counts eligible / above / missing-price members separately;
8. requires a configurable minimum member-price coverage (default 90%);
9. emits the same authorized-import CSV contract used by `--ma-breadth-file`.

The output is then passed through the existing canonical parser/validation:

```bash
python scripts/refresh_data.py \
  --ma-breadth-file .cache/ma-breadth-open/sp500-ma-breadth-open.csv
```

### Open-data coverage

The membership history begins in 1996, but the open delisted-inclusive price file begins in 2000.

Therefore self-computed breadth coverage can only begin once:
- the price dataset has started;
- the corresponding SMA horizon has matured;
- enough point-in-time constituents have valid price history to meet the configured coverage threshold.

The pipeline does **not** stamp an artificial 2000-01-03 start on all three horizons.

### Post-2024 limitation

The FINSABER file currently ends at 2024-12-31.

So this open path is immediately useful for historical research including the 2000, 2008, 2020 and 2022 episodes, but it does not by itself produce 2025/2026 breadth.

Current/recent 2025/2026 values still require an authorized current breadth provider/export or a separately documented recent-price supplement. That recent supplement must preserve point-in-time membership and must not silently change the price convention.

### Quality rule

The open-data path is considered:

```text
membership_mode = point_in_time
price_adjustment = adjusted_close
```

but it is still a community/open-data reconstruction. It must not be described as the official S&P Dow Jones Indices breadth series.

Cross-provider validation against S5FI/SPXA50R remains part of QA.


## Optional 2025/2026 recent-price supplement

The open FINSABER price file ends at 2024-12-31. For local research of the supplied chart's 2025/2026 episodes, the repository includes an **optional local-only** recent supplement:

```bash
python -m pip install -r requirements-research.txt
python scripts/bootstrap_ma_breadth_hybrid.py
```

The supplement:
- derives the required ticker universe from point-in-time membership snapshots, including members removed during the target period;
- requests a generous pre-2025 lookback (default 2024-01-01) so 200DMA state is mature when merged with FINSABER history;
- fetches daily prices with yfinance/Yahoo Finance;
- records unresolved/failed tickers in `.cache/ma-breadth-open/yahoo_recent_failures.json`;
- never counts an unresolved ticker as below its moving average;
- keeps raw recent prices under `.cache/`;
- merges historical FINSABER first and recent Yahoo second.

### Overlap precedence

For an identical `(symbol,date)`:

```text
historical FINSABER row
        ↓
recent supplement row
        ↓
recent supplement wins
```

This rule is deterministic and reported by the pipeline. Older non-overlapping historical rows remain untouched.

### Yahoo/yfinance rights warning

The yfinance project is open-source software, but its own documentation states that Yahoo Finance API data is intended for personal use and tells users to review Yahoo's terms for actual data rights.

Therefore the recent supplement is:
- optional;
- intended for local research;
- not automatically committed as raw data;
- marked with redistribution/data-rights caveats in provenance.

Before publishing derived recent snapshots from this supplement in a public repository, review the applicable Yahoo/data-provider terms.

### Hybrid provenance

Hybrid output is labeled as a reconstruction combining:
- point-in-time community membership history;
- Apache-2.0 FINSABER historical adjusted-close prices;
- Yahoo Finance/yfinance recent local prices.

It is not represented as an official S&P Dow Jones breadth series.
