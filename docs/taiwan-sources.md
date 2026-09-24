# Taiwan Market Regime — sources and coverage

Issue: #34

This module uses transparent first-party/public Taiwan data. It intentionally does **not** claim to reproduce MacroMicro/MM's proprietary manufacturing-cycle composite or the supplied chart author's undocumented "Breadth 1/2/3" formulas.

## Source hierarchy

1. Official first-party Taiwanese source.
2. Government open-data / official OpenAPI representation.
3. Explicit local CSV import of an official release when a stable API is unavailable.
4. Third-party data may be used for cross-checking only and is never a silent canonical substitute.

## 1. TAIEX and market trading data — TWSE

### TWSE OpenAPI
Swagger:
https://openapi.twse.com.tw/

Base:
`https://openapi.twse.com.tw/v1`

Relevant endpoints:
- `/exchangeReport/FMTQIK` — current-month daily market trading information: date, volume, value, transactions, TAIEX, change.
- `/indicesReport/MI_5MINS_HIST` — current-month TAIEX OHLC.
- `/exchangeReport/MI_INDEX` — current daily index/market statistics.
- `/opendata/twtazu_od` — up/down securities-count statistics.
- `/exchangeReport/STOCK_DAY_ALL` — listed-stock daily trading data.
- `/opendata/t187ap03_L` — listed-company master data.

TWSE's OpenAPI is publicly exposed for integration. The government open-data listing for `twtazu_od` states Government Data Open License v1.0.

### Historical TAIEX month query
TWSE's historical TAIEX endpoint accepts a month date:

`https://www.twse.com.tw/rwd/en/TAIEX/MI_5MINS_HIST?date=YYYYMM01&response=json`

The response contains daily open/high/low/close for the selected month.

### Historical individual-stock data
TWSE's public individual-stock daily trading page states daily OHLC/trading data is available from **2010-01-04**.

Reference:
https://www.twse.com.tw/en/trading/historical/stock-day.html

TWSE also exposes daily closing-price/monthly-average history back to **1999-01-05**, but the full daily OHLC/trading page starts in 2010.

That 1999-01-05 floor is enforced by the endpoint itself. A monthly
`MI_5MINS_HIST` query for any earlier month is refused:

```text
stat='Search date less then 1999/1/5, please retry!'
```

So `scripts/bootstrap_taiwan_taiex.py` defaults to `--start 1999-01`, and
`tw_taiex*` expected history starts are pinned to `1999-01-05` in
`scripts/refresh_data.py`. A verified full backfill yields **6868 daily
observations, 1999-01-05 → 2026-09-21**.

### Canonical metric ids
- `tw_taiex`
- `tw_taiex_open`
- `tw_taiex_high`
- `tw_taiex_low`
- `tw_market_trade_value`
- `tw_market_trade_volume`
- `tw_advancing_stocks`
- `tw_declining_stocks`
- `tw_unchanged_stocks`
- `tw_advance_decline_diff`
- `tw_advance_decline_pct`
- `tw_advance_decline_line`

Market scope:
`TWSE listed stocks`

Important: breadth uses the **Stocks** counts, not "Overall Market", because the overall row includes warrants/other securities.

## 2. Taiwan business-cycle indicators — National Development Council

Official:
https://www.ndc.gov.tw/en/

NDC publishes monthly:
- monitoring indicator score and light
- trend-adjusted leading index
- trend-adjusted coincident index
- trend-adjusted lagging index

NDC also documents the underlying components. Its leading index includes TAIEX, real M1B, export-order diffusion, labor/housing/semiconductor-equipment variables and the TIER manufacturing composite; its coincident index includes industrial production, electricity, manufacturing shipments, trade/food-service sales, overtime hours, exports and machinery/electrical imports.

The NDC monitoring light is **shown as its own official indicator**. MRM's derived Taiwan macro regime is a separate transparent calculation.

Canonical ids:
- `tw_ndc_monitoring_score`
- `tw_ndc_leading_index`
- `tw_ndc_coincident_index`
- `tw_ndc_lagging_index`

Current release cadence: monthly.

Because the web release/database surface is not guaranteed to be a stable machine API, v0.3 supports a normalized local CSV snapshot contract for historical ingestion.

## 3. Taiwan manufacturing PMI — CIER

Official:
https://www.cier.edu.tw/pmi-trend/

CIER publishes a monthly Taiwan Manufacturing PMI history table, including sector-level PMI series.

Canonical id:
- `tw_manufacturing_pmi`

PMI interpretation:
- >50 expansion
- <50 contraction

CIER content is publicly viewable but redistribution rights are not assumed. The repository therefore stores parser/config logic and small fixtures; a full historical snapshot is committed only if rights are verified.

### CIER rolling-window bootstrap

`scripts/bootstrap_cier_pmi.py` parses the official CIER table by its own
`月份` + `臺灣製造業PMI` headers and writes the normalized Taiwan macro CSV
contract consumed by `refresh_data.py --taiwan-macro-file`. The public table is
a rolling 12-month window, not a historical archive, so each run merges the
current window into the local CSV instead of replacing accumulated history.

The page does not expose a publication timestamp. Each parsed value therefore
uses the date it was actually verified public as its conservative
`release_date`. On the first ingest, all months in the rolling window can share
one release date; the canonical release-aware contract must treat that batch as
simultaneously available rather than as twelve historical arrivals.

For repeated observations:

- unchanged values keep their earliest verified release date;
- a revised value is accepted only when its verification/release date is
  strictly newer than the stored vintage; older or same-date conflicting
  values are rejected rather than allowed to roll canonical history backward;
- months that roll off the source page remain in the accumulated local history.

The bootstrap also requires at least 12 contiguous monthly rows from the
official rolling table. A syntactically valid but shortened/gapped response is
therefore treated as a source-shape failure instead of silently publishing a
partial window.

Run:

```bash
python scripts/bootstrap_cier_pmi.py
python scripts/refresh_data.py --taiwan-macro-file .cache/taiwan-macro/cier-pmi.csv
```

## 4. Industrial/manufacturing production — MOEA

Official:
https://www.moea.gov.tw/Mns/dos/home/Home.aspx

MOEA Department of Statistics publishes monthly:
- Industrial Production Index
- Manufacturing Production Index
- monthly/annual changes and detailed tables

Canonical ids:
- `tw_industrial_production`
- `tw_manufacturing_production`

The production indices are official statistics compiled by MOEA.

## 5. Taiwan policy rate — Central Bank of the Republic of China (Taiwan)

Official rate-history pages:
https://www.cbc.gov.tw/en/lp-695-2-2-20.html
https://www.cbc.gov.tw/en/lp-695-2-3-20.html

CBC publishes effective-date histories for:
- discount rate
- accommodations with collateral
- accommodations without collateral

Canonical ids:
- `tw_cbc_discount_rate`
- `tw_cbc_rate_change_bp`
- `tw_cbc_change_3m_bp`
- `tw_cbc_change_6m_bp`
- `tw_cbc_change_12m_bp`

## 6. Fed policy-rate overlay

Use the project's existing FRED infrastructure for first-party/FRED policy-rate series. Taiwan pages may display Fed tightening velocity as an external liquidity backdrop, but Fed data stays a separate U.S. source and is never labeled a Taiwan rate.

## Local macro/rate CSV fallback

For official sources without a stable public machine API, v0.3 accepts a normalized local file:

```csv
date,provider,series_id,value,unit,release_date,source_url
2026-08-01,CIER,tw_manufacturing_pmi,62.5,index,2026-09-01,https://www.cier.edu.tw/pmi-trend/
2026-07-01,NDC,tw_ndc_monitoring_score,41,score,2026-08-27,https://www.ndc.gov.tw/en/
```

Rules:
- one `series_id` has one unit;
- observation date and release date are distinct;
- historical no-look-ahead analysis uses `release_date` when it matters;
- missing releases remain missing.

## Replacing the supplied chart's layers

The supplied chart is treated as an architecture reference:

- "MM cycle" → transparent NDC + PMI + production regime
- "Breadth 1" → official A/D participation
- "Breadth 2" → High/Low extreme breadth
- "Breadth 3" → % above 20/50/200DMA
- "FED hikes" → explicit Fed/CBC rate velocity
- "TAIEX" → official TWSE TAIEX

No undocumented formula is guessed or presented as the author's exact indicator.


## Taiwan trend / extreme breadth panel

The reproducible Taiwan Breadth 2/3 replacement is built from **TWSE-listed common stocks only**.

### Forward point-in-time collection

Official current sources:
- `/exchangeReport/STOCK_DAY_ALL` — current daily listed-security OHLC/trading rows
- `/opendata/t187ap03_L` — listed-company master

The collector intersects the current trading rows with the listed-company master. This excludes ETFs, ETNs, warrants and other non-company securities without relying on ticker-length heuristics.

Run:

```bash
python scripts/collect_taiwan_stock_snapshot.py
```

This appends the current official snapshot to:

`.cache/taiwan-stocks/twse-common-stock-panel.csv`

Re-running the same trade date replaces that date rather than creating duplicate rows.

Each row carries:

```text
date
symbol
high
low
close
market_scope = TWSE listed common stocks
provider
membership_mode = official_daily_snapshot
price_adjustment = unadjusted_close
```

Because each day's listed-company master is collected at that date, forward-collected history is point-in-time by construction.

### Historical import contract

For an authorized/bulk historical panel:

```csv
date,symbol,high,low,close,market_scope,provider,membership_mode,price_adjustment
2022-01-03,2330,688,680,684,TWSE listed common stocks,authorized-history,point_in_time,unadjusted_close
```

The historical panel must be sorted by `date,symbol`.

If historical rows were created using today's surviving constituents, they must be labeled:

`membership_mode = current_constituents_retroactive`

Such series may be viewed as experiments but are blocked from canonical historical percentiles/event interpretation.

### Public-history limit

TWSE's public individual-stock daily trading page states history is available from **2010-01-04**. This gives a practical public-price starting point, but reconstructing a historically accurate common-stock universe also requires listing/delisting history.

TWSE Data E-Shop offers list/delist and ex-right/dividend datasets for deeper institutional use. Redistribution rules for paid E-Shop data must be respected.

### Corporate actions

The free current/daily panel uses `unadjusted_close`.

This is explicit because ex-right/ex-dividend and capital changes can create mechanical price discontinuities. TWSE separately publishes ex-right/ex-dividend reference data, with public ex-right price data from 2003-05-05 and paid historical/reference products.

Therefore:
- current/forward MA breadth is transparent but unadjusted;
- a future adjusted historical reconstruction must declare its adjustment formula/source;
- the pipeline never silently labels raw close as adjusted close.

### Derived metrics

`pipeline/taiwan_trend_breadth.py` produces:

- `tw_above_20dma_pct`
- `tw_above_50dma_pct`
- `tw_above_200dma_pct`
- `tw_new_52w_highs`
- `tw_new_52w_lows`
- `tw_net_new_52w_highs`
- `tw_high_low_pct`

Moving averages:
- include the current close;
- require the full 20/50/200 valid-session window for each stock;
- missing/newly listed stocks remain explicit missing members.

52-week highs/lows:
- require 252 valid symbol observations;
- new high = current daily high >= previous 251-session maximum;
- new low = current daily low <= previous 251-session minimum.

Build:

```bash
python scripts/build_taiwan_trend_breadth.py \
  --panel-file .cache/taiwan-stocks/twse-common-stock-panel.csv
```
