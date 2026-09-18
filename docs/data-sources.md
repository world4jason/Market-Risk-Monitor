# Data sources and historical coverage

Related issues: #5, #6

This document records the v0.1 historical backbone, source hierarchy, coverage, and caveats.

## Coverage ladder

| Pillar | Series / source | Intended coverage | Frequency | Notes |
|---|---|---:|---|---|
| Valuation / market context | Robert Shiller live U.S. stock market / CAPE workbook | 1871–present | Monthly | Long-run price, real total-return, and CAPE context. Current partial month is intentionally excluded. |
| Financial conditions | Chicago Fed NFCI via FRED | 1971–present | Weekly | Positive values mean tighter-than-average financial conditions. |
| Financial risk | Chicago Fed NFCIRISK via FRED | 1971–present | Weekly | Risk/volatility/funding-risk component of NFCI. |
| Credit | Chicago Fed NFCICREDIT via FRED | 1971–present | Weekly | Credit-condition component of NFCI. |
| Nonfinancial leverage | Chicago Fed NFCINONFINLEVERAGE via FRED | 1971–present | Weekly | Long-run leverage context complementary to FINRA customer margin debt. |
| Volatility | Cboe official VIX history | 1990–present | Daily | Primary source is Cboe's own daily CSV, not the FRED redistribution. |
| Customer leverage | FINRA Margin Statistics | Jan 1997–present | Monthly | Margin debt plus free credit. Legacy free-credit schema changes in Feb 2010. |
| Recession context | NBER/FRED USREC | longest practical official history | Monthly | Context/shading only; not a leading trading signal. |
| Optional credit proxy | Moody's Baa minus 10Y Treasury via FRED (BAA10YM) | 1953–present | Monthly | Useful long history, but not bundled until redistribution/licensing review is explicit. |

## Why there is no single common start date

The product is meant to answer "where does today sit relative to history?"

Cropping every series to FINRA's 1997 start would discard:
- more than a century of Shiller market/valuation history;
- the 1970s–1990s NFCI financial-condition history;
- the early 1990s VIX history.

Each metric therefore owns:
- `history_start`
- `history_end`
- source frequency
- publication lag
- freshness threshold
- valid historical baselines

If a historical event predates a metric, the explorer displays `unavailable`. It does not silently replace that metric with a different proxy.

## Source hierarchy

v0.1 preference order:

1. first-party canonical source;
2. first-party data distributed by FRED where direct automation is less stable;
3. third-party sources only for independent verification, never as silent production replacements.

A network failure does not trigger a third-party fallback.

---

## FINRA margin statistics

Landing page:

https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics

Canonical historical workbook:

https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx

FINRA states that member firms report, on a settlement-date basis as of the last business day of each month:
- total debit balances in securities margin accounts;
- total free credit balances in cash and securities margin accounts.

FINRA also states:
- historical downloadable data begins in January 1997;
- updates are generally published in the third week of the following month;
- there is no FINRA data feed for this dataset;
- monthly changes can partly reflect reporting-method changes.

### Legacy free-credit schema

Through January 2010, FINRA/NYSE-era data combines free credit in cash and margin accounts rather than reporting the two components separately.

Therefore the pipeline preserves four concepts:

- `finra_margin_debt`
- `finra_total_free_credit` — valid across the full usable history
- `finra_cash_free_credit` — separate component from Feb 2010 onward
- `finra_margin_free_credit` — separate component from Feb 2010 onward

The derived `margin_debt_to_free_credit` ratio uses:
- combined free credit for legacy observations;
- cash + margin free credit for modern observations.

The pipeline must never mislabel a legacy combined balance as the cash-only or margin-only component.

### Reference date

FINRA reports as of the **last business day of the month**, so the normalized observation date uses business month-end.

---

## Chicago Fed NFCI family

Primary automated endpoint: FRED CSV, with methodology/source attribution to the Federal Reserve Bank of Chicago.

Series:
- `NFCI`
- `NFCIRISK`
- `NFCICREDIT`
- `NFCINONFINLEVERAGE`

Reference page:

https://fred.stlouisfed.org/series/NFCI

All four series begin in January 1971 and are weekly.

Interpretation:
- NFCI > 0: financial conditions tighter than historical average;
- NFCI < 0: conditions looser than historical average;
- subindexes decompose risk, credit, and leverage-related components.

FRED pages mark these data as copyrighted / citation-required. The repository therefore records source/attribution metadata and does not assume unrestricted redistribution rights.

---

## Cboe VIX

Landing page:

https://www.cboe.com/tradable_products/vix/vix_historical_data

Official daily CSV:

https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv

Cboe publishes daily VIX history from 1990 to present and updates it daily.

The pipeline uses Cboe directly rather than the FRED `VIXCLS` redistribution so provenance remains first-party.

Only the daily close is promoted to the canonical dashboard metric in v0.1; raw OHLC columns remain a source-level detail.

---

## Robert Shiller long-run market data

Live landing page:

https://shillerdata.com/

The live `ie_data.xls` workbook contains monthly U.S. stock-market data beginning January 1871, including:
- stock price;
- dividends;
- earnings;
- CPI;
- interest rates;
- real-price / real-total-return series;
- CAPE.

### Important source correction

The long-standing Yale mirror:

http://www.econ.yale.edu/~shiller/data/ie_data.xls

has been observed by recent reproducibility projects to lag the live workbook. v0.1 therefore treats **shillerdata.com as the live source** and imports a locally downloaded `ie_data.xls`.

### Date parsing

The workbook's `Date` cell is numeric. October values such as `2025.10` can become indistinguishable from `2025.1` if parsed naïvely.

The pipeline therefore derives the calendar month from the workbook's **Date Fraction** column and cross-checks the strict monthly sequence from 1871-01 onward.

### Partial current month

The workbook can include a current partial month with estimated/revisable inputs. v0.1 drops the final partial row before creating production snapshots.

This makes event comparisons reproducible rather than allowing an in-progress month to silently change later.

---

## Recession context

`USREC` is used for chart shading/context.

It is never interpreted as a leading market signal and never contributes directly to Deleveraging Watch.

---

## Optional long-run credit spread

Candidate:

https://fred.stlouisfed.org/series/BAA10YM

The monthly Moody's Baa corporate yield minus 10-year Treasury series extends back to 1953.

Because the source chain includes Moody's and FRED notes rights restrictions, v0.1 does **not** automatically bundle the full series until redistribution terms are reviewed.

The NFCI credit subindex already gives the core dashboard a long-run credit-condition view without requiring this optional series.

---

## Independent verification sources

Third-party dashboards may be used to detect parser mistakes or stale source assumptions, but not to replace canonical production data.

Examples found during research:
- US Margin Dashboard — FINRA-derived history with the same pre-2010 combined-free-credit caveat.
- The Trading Tools margin-debt page — FINRA-derived history and rate-of-change views.

If a cross-check disagrees with the first-party source, the first-party source wins unless the discrepancy is documented as a source revision.

---

## Historical event set

Initial event anchors are stored in `data/events.json`, not chart code:

- Dot-com peak / unwind
- Global Financial Crisis
- COVID shock
- 2022 tightening / bear-market period
- current period

Event windows support:
- raw level;
- point-in-time percentile;
- rolling percentile;
- rate of change;
- normalized path indexed to 100 at the anchor.

A metric is unavailable for an event if its source history did not yet exist.

---

## Production-source policy

1. Prefer official first-party sources.
2. Preserve each metric's maximum valid history.
3. Keep provenance in every generated metric file.
4. Do not silently substitute a proxy.
5. Do not silently treat missing/stale data as "safe."
6. Derived historical transforms must be reproducible.
7. Historical point-in-time statistics must not use future observations.
8. Source format changes fail validation rather than producing guessed values.
9. Previous valid snapshots remain visible only with their original `as_of` and explicit stale state.
10. Redistribution/licensing caveats stay machine-readable in metric metadata.
