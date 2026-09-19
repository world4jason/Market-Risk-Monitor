# Moving-Average Breadth Sources

Issue: #23

## Target metrics

The v0.2b Trend Participation module tracks the percentage of S&P 500 constituents above:

- 20-day moving average
- 50-day moving average
- 200-day moving average

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

Its public historical page states:
- site visitors can view recent daily history;
- members may access longer downloadable history;
- Historical Data Download / API products provide deeper history, with availability depending on product/symbol.

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
