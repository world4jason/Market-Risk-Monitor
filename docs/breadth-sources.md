# Breadth data sources

Issue: #14

## What the product needs

The Breadth / Participation pillar requires a consistent **NYSE** daily universe for:

- 52-week new highs
- 52-week new lows
- advancing issues
- declining issues
- unchanged issues where available
- up volume
- down volume
- unchanged volume where available
- total active issues where available

The dashboard must not mix an NYSE numerator with an all-U.S. or Nasdaq denominator.

## Candidate sources

### 1. NYSE Daily TAQ — first-party, paid/raw

NYSE Daily TAQ is the most authoritative raw source. NYSE describes it as a comprehensive history of daily trades/quotes across NYSE, Nasdaq and regional exchanges, with history available from 1993.

Source:
https://www.nyse.com/data-products/catalog/daily-taq

Pros:
- first-party / exchange-operated source;
- sufficient raw trades/quotes to reconstruct many breadth measures;
- explicit long historical availability.

Cons:
- paid product;
- raw TAQ is much heavier than this project needs;
- 52-week-high/low counts still require a carefully defined eligible-security universe and rolling price history;
- redistribution of derived history must follow the applicable license.

v0.2 status: **authoritative raw candidate, not the default public-repo snapshot source**.

### 2. StockCharts market indicators — derived, long history, proprietary

StockCharts publishes a clear dictionary of NYSE breadth symbols, including:

- `$NYHGH` — NYSE new 52-week highs
- `$NYLOW` — NYSE new 52-week lows
- `$NYHL` — new highs minus new lows
- `$NYADV` — advancing issues
- `$NYDEC` — declining issues
- `$NYAD` — advance-decline issues
- `$NYUPV` — advancing volume
- `$NYDNV` — declining volume
- `$NYUD` — advance-decline volume
- `$NYTOT` — total active symbols

Its dictionary reports history generally beginning in 1992 for these raw NYSE breadth series.

Source:
https://chartschool.stockcharts.com/table-of-contents/market-indicators/introduction-to-market-indicators/market-indicator-dictionary

Pros:
- directly matches the metrics needed;
- consistent market scope;
- long history;
- convenient for validating calculations.

Cons:
- proprietary service/data;
- public GitHub redistribution rights must not be assumed;
- automated export access can depend on subscription/product terms.

v0.2 status: **strong authorized-export candidate and independent verification source**.

### 3. Barchart special symbols / OnDemand API — derived/API, proprietary

Barchart publishes special symbols for:
- NYSE new highs/lows;
- advance/decline by exchange;
- advance/decline volume by exchange;
- total highs/lows and multiple time windows.

Its OnDemand Highs & Lows API also accepts exchange filters such as NYSE.

Sources:
https://www.barchart.com/education/special-symbols
https://www.barchart.com/ondemand/api/getHighsLows

Pros:
- explicit NYSE filtering;
- breadth-oriented products;
- API/export route exists.

Cons:
- proprietary symbols/API;
- API requires credentials/product access;
- inclusion rules differ from other providers, so it must never be mixed silently with StockCharts/NYSE universes.

v0.2 status: **authorized API/export candidate, not a hard-coded public dependency**.

## Canonical v0.2 ingest path

Because the public repository cannot assume redistribution rights for the long-history vendor datasets, v0.2 uses an **authorized local CSV contract**.

The source can be an export from NYSE/StockCharts/Barchart or another authorized provider, but one CSV snapshot must represent one consistent market scope.

Required CSV columns:

```text
date
market_scope
provider
new_52w_highs
new_52w_lows
advancing_issues
declining_issues
unchanged_issues
up_volume
down_volume
unchanged_volume
total_issues
```

Optional fields may be blank, but:
- `date`, `market_scope`, and `provider` are mandatory;
- at least one complete feature family must exist;
- `market_scope` must remain constant throughout the file;
- the production v0.2 target scope is exactly `NYSE`;
- no derived metric invents a missing denominator.

Example:

```csv
date,market_scope,provider,new_52w_highs,new_52w_lows,advancing_issues,declining_issues,unchanged_issues,up_volume,down_volume,unchanged_volume,total_issues
2026-09-18,NYSE,authorized-export,42,188,1012,1711,74,1423000000,2612000000,82000000,2797
```

## History targets

When an authorized source is available:

| Input family | Desired start | Notes |
|---|---:|---|
| New highs/lows | 1992 or earliest licensed history | StockCharts dictionary reports NYSE breadth history from 1992 |
| Advance/decline | 1992 or earliest licensed history | Keep same source/scope as high/low when possible |
| Up/down volume | 1992 or earliest licensed history | Same scope required for McClellan Volume calculations |

The implementation does not pretend history exists before the actual imported file.

## CNN is not the raw source

CNN's Fear & Greed page describes:
- Stock Price Strength as net new 52-week highs/lows on NYSE;
- Stock Price Breadth as the McClellan Volume Summation Index.

CNN also states that its breadth calculation received a minor calculation change.

Therefore:
- CNN is a **product/reference definition**, not the canonical raw dataset;
- this project preserves its own raw inputs and formulas;
- any future "CNN-style" label must be explicitly labeled approximate unless exact current methodology is documented and reproducible.

## Redistribution policy

For breadth snapshots:
- public-domain/open data may be committed when terms allow;
- paid/vendor history is **not** committed merely because the user can view/export it;
- authorized local imports can generate local dashboard snapshots;
- before committing vendor-derived history to the public repo, verify redistribution terms separately.

## Source-scope invariant

A single generated breadth snapshot carries:

```text
market_scope = NYSE
provider = <one provider/export family>
```

A source-scope mismatch is a validation failure.

Examples that must fail:
- NYSE new highs + all-U.S. total issues;
- NYSE up volume + Nasdaq down volume;
- StockCharts numerator + Barchart denominator without an explicitly documented reconciliation layer.
