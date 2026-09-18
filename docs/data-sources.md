# Data sources and historical coverage

Related issues: #5, #6

This document records the intended historical backbone and the reason each series is included.

## Coverage ladder

| Pillar | Series / source | Intended coverage | Frequency | Notes |
|---|---|---:|---|---|
| Valuation / market context | Robert Shiller U.S. stock market / CAPE dataset | 1871–present | Monthly | Long-run valuation and price context. Keep separate from short-history market-price feeds. |
| Financial conditions | Chicago Fed NFCI | 1971–present | Weekly | Broad financial-conditions index. Positive values mean tighter-than-average conditions. |
| Financial risk | Chicago Fed NFCIRISK | 1971–present | Weekly | Risk subindex; useful for separating risk from the headline NFCI. |
| Credit | Chicago Fed NFCICREDIT | 1971–present | Weekly | Long-history credit subindex with consistent family methodology. |
| Nonfinancial leverage | Chicago Fed NFCINONFINLEVERAGE | 1971–present | Weekly | Long-run leverage context complementary to FINRA customer margin debt. |
| Volatility | Cboe VIX | 1990–present | Daily | Official VIX history; Cboe publishes 1990–present and updates daily. |
| Customer leverage | FINRA Margin Statistics | 1997–present | Monthly | Debit balances plus free credit balances. Official historical Excel begins Jan 1997. |
| Recession context | NBER/FRED recession indicator | longest practical official history | Monthly | Used as context/shading, not as a market-timing signal. |
| Optional credit proxy | Moody's Baa minus 10Y Treasury via FRED (BAA10YM) | 1953–present | Monthly | Useful long history, but redistribution/licensing must be reviewed before bundling full observations. |

## Why we do not use one common start date

The dashboard's purpose is historical context. Cropping every series to FINRA's 1997 start would discard decades (or more than a century) of useful information.

Each metric therefore declares its own:
- `history_start`
- `history_end`
- source frequency
- valid historical baselines

The historical explorer must display `unavailable` if an event predates a metric.

## Official source references

### FINRA margin statistics
https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics

FINRA reports:
- debit balances in customers' securities margin accounts;
- free credit balances in customers' cash accounts;
- free credit balances in customers' securities margin accounts.

FINRA states that the downloadable historical dataset starts in January 1997 and that updates are generally published in the third week of the month following the reference month.

### Chicago Fed NFCI family via FRED
https://fred.stlouisfed.org/series/NFCI

Related series:
- NFCI
- NFCIRISK
- NFCICREDIT
- NFCINONFINLEVERAGE

The NFCI family begins in January 1971 and is weekly.

### Cboe VIX
https://www.cboe.com/tradable_products/vix/vix_historical_data

Cboe publishes VIX daily closing history from 1990 to present.

### Robert Shiller long-run data
https://www.econ.yale.edu/~shiller/data.htm

Shiller publishes U.S. stock-market price, dividend, earnings, CPI and CAPE-related history from 1871 to present.

### Long-run credit-spread candidate
https://fred.stlouisfed.org/series/BAA10YM

Monthly Baa corporate bond yield minus 10Y Treasury history begins in 1953. Because Moody's rights are noted by FRED, treat this as a source to review rather than automatically republishing full history in the repository.

## Initial production-source policy

Preferred for v0.1:
1. Official first-party source where practical.
2. Preserve the source's full valid history.
3. Keep source provenance in every generated metric file.
4. Do not bundle restricted full-history datasets without a redistribution review.
5. Keep a last valid snapshot only when clearly marked with original `as_of` and freshness state.
6. Derived historical transforms must be reproducible from their declared inputs.

## Historical event set

The first historical explorer should support, where each metric has coverage:
- Dot-com / 2000–2002
- Global Financial Crisis / 2007–2009
- COVID shock / 2020
- 2022 tightening / bear-market period
- current period

Older long-run views can additionally use the Shiller / NFCI datasets without pretending FINRA or VIX existed before their actual start dates.
