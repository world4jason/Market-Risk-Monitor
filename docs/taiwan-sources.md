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
