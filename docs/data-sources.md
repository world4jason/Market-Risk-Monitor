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

## Publishing and redistribution decisions — checked 2026-09-30

The operational decision is recorded in `data/config/publishing.json` and enforced
by `scripts/check_publish_policy.py`. The status below is a repository
publication decision based on the cited source terms; it is not a general legal
opinion about every possible use of the source.

| Source family | Public-repo decision | Basis |
|---|---|---|
| Chicago Fed NFCI family via FRED | Publish with attribution | FRED labels NFCI `Copyrighted: Citation Required`; FRED's legal notice permits display/publication of that class with proper attribution. |
| FRED USREC | Publish with attribution | FRED labels USREC `Copyrighted: Citation Required`; same attribution rule. |
| Board/FOMC policy-rate series via FRED | Publish with attribution | Official policy-rate data; retain Board/FRED attribution. |
| FINRA Margin Statistics | Publish normalized aggregate history with attribution | FINRA publicly publishes the aggregate statistics used here; no member-level filings are published. |
| Robert Shiller public workbook | Publish normalized research series with attribution | Public research workbook. This is a project publication decision, not a public-domain claim. |
| Cboe VIX historical download | Publish normalized daily close with attribution | Cboe exposes the 1990-present historical download publicly; proprietary DataShop feeds are separate. |
| TWSE `twtazu_od` breadth family | Publish with attribution | Taiwan Government Data Open License v1 permits reproduction, distribution and derivative use with attribution. |
| TWSE public web/OpenAPI TAIEX/current-market observations | Publish snapshot with attribution | Official public endpoint decision; paid Data E-Shop history is not covered. |
| NDC business-cycle open data | Publish with attribution | Taiwan Government Data Open License v1; revised historical vintages remain non-PIT unless separately captured. |
| CBC policy-rate history | Publish snapshot with attribution | Official public policy-rate history. |
| CIER PMI rolling public release | Publish normalized release snapshot with attribution | Only the public rolling release is normalized; no separate proprietary archive is mirrored. |
| FRED `SP500` / S&P 500 | **Local only** | FRED labels it `Copyrighted: Pre-Approval Required`; S&P DJI states index-data use/distribution requires licensing. |
| TraderMonty/FMP/Barchart/TradingView MA breadth | **Local only unless a redistribution license is supplied** | Vendor access is not treated as a redistribution grant. |
| Authorized NYSE breadth export | **Local only by default** | Ingestion authorization does not imply redistribution; public release requires source-specific redistribution rights. |

The release checker fails closed: a new metric needs an explicit source-family
decision before it can enter the public release, any artifact declaring
`redistribution: restricted` is rejected, and a derived/special artifact
cannot consume an actually-present local-only provenance input.

### Daily U.S. large-cap index replacement review (#58)

No clearly redistributable drop-in replacement for `sp500_index` was found in
the reviewed candidates. Terms were checked on 2026-09-30:

| Candidate | Terms / evidence checked | Outcome |
|---|---|---|
| S&P 500 / FRED SP500 | https://fred.stlouisfed.org/series/SP500 and https://www.spglobal.com/spdji/ | Pre-approval / index-data licensing required; local only. |
| Nasdaq Composite / Nasdaq-100 via FRED | https://fred.stlouisfed.org/tags/series?t=copyrighted%3A+pre-approval+required%3Bindexes | Same FRED pre-approval class; also wrong market universe. |
| FT Wilshire 5000 | https://www.wilshireindexes.com/wilshire-indexes-disclaimer | Written permission / appropriate license required; wrong universe. |
| Cboe SPX index feeds | https://datashop.cboe.com/main-channel-tick-data | Proprietary; external redistribution prohibited absent licensing. |
| Yahoo Finance proxy prices | https://legal.yahoo.com/us/en/yahoo/terms/otos/ | General terms do not provide a redistribution grant for a canonical public data feed. |
| ETF proxy via another vendor | Vendor-specific | Rejected before source selection because a fund price is not the index; no silent substitution. |
| Self-computed proxy | S&P constituent/data license would still be required | Deferred; not an official S&P 500 replacement without licensed PIT inputs. |
- **S&P 500 via FRED:** rejected for public release; FRED marks it
  `Copyrighted: Pre-Approval Required`, and S&P DJI requires an index-data
  license for use/distribution.
- **Nasdaq Composite / Nasdaq-100 via FRED:** rejected as a substitute and as a
  public-data shortcut; FRED places these index series in the same
  pre-approval-required class, and they are not S&P 500 large-cap beta.
- **FT Wilshire 5000:** rejected as a drop-in; Wilshire's legal notice says its
  information does not carry a use right without written permission and an
  appropriate license, and the universe is materially different.
- **Cboe SPX / DataShop:** rejected for public redistribution; Cboe labels the
  index dataset proprietary and says external redistribution is prohibited
  absent licensing.
- **ETF proxies (SPY/IVV/VOO):** rejected as a semantic substitute. A fund price
  is not the S&P 500 index, and a price vendor adds a separate license question.
- **Yahoo/Stooq/free aggregators:** rejected as the canonical public-release
  path because convenience access is not a redistribution grant.
- **Self-computed large-cap index:** not adopted. It would require licensed,
  point-in-time constituents and prices and would otherwise be a project-defined
  index rather than the S&P 500.

**Decision:** keep `sp500_index` local-only. The public event study remains
SPX-less until a suitable licensed input is available; no silent replacement is
allowed.

### Private-repository decision (#60)

As of 2026-09-30 this repository and its GitHub Pages output are public.
Therefore the preconditions for ingesting/publishing the restricted
`sp500_index` are not met. A future visibility change does not retroactively
remove data already served, cloned or cached.

The current decision is **do not include `sp500_index` in any public release**.
If the project later moves to a genuinely non-public delivery path, source terms
must be re-checked at that time. The metric keeps
`redistribution: restricted`, and the release checker prevents accidental
publication even if a local/private workflow generated the file.
