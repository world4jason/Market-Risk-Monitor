# Public cross-check: S&P 500 % Above 50DMA episodes

Issue: #26

This note records public-source corroboration before the canonical point-in-time event study is generated.

It is **not** the event-study result and must not be used to infer a buy signal.

## Indicator identity

Barchart identifies `$S5FI` as:

> S&P 500 Stocks Above 50-Day Average

Reference:
https://www.barchart.com/stocks/quotes/%24S5FI/price-history

Investing.com uses the same S5FI description:
https://www.investing.com/indices/s-p-500-stocks-above-50-day-average-historical-data

## Recent 2026 cross-check

Barchart's public 52-week statistics report:
- 52-week low: **17.69**
- low date: **2026-03-20**

So the public provider data independently confirms that 50DMA participation entered the supplied chart's custom **<25%** region during 2026.

Investing.com's public recent daily table reports:
- 2026-09-17 close: **30.81**
- 2026-09-16 close: **30.81**
- 2026-09-15 close: **34.59**
- 2026-09-01 close: **45.52**

These point observations are useful cross-provider QA facts, not a replacement for a licensed/full history.

## Coarse historical episode corroboration

WalletInvestor's public S5FI history page publishes monthly/yearly ranges. Its displayed yearly lows include:

| Year | displayed yearly low | threshold implication |
|---|---:|---|
| 2026 YTD | 17.69 | below 25; above 15 |
| 2025 | 4.17 | below 15 |
| 2024 | 16.30 | below 25 |
| 2023 | 6.36 | below 15 |
| 2022 | 0.79 | below 15 |
| 2021 | 21.78 | below 25 |
| 2020 | 0.59 | below 15 |
| 2018 | 1.19 | below 15 |
| 2015 | 4.78 | below 15 |
| 2011 | 0.60 | below 15 |
| 2008 | 0.20 | below 15 |

Reference:
https://walletinvestor.com/stock-forecast/s5fi-stock-history/

Its displayed monthly ranges also show:
- 2025 January low: **14.91**
- 2025 March low: **25.64**
- 2025 April low: **4.17**
- 2026 March low: **17.69**
- 2026 April low: **19.88**

## What this does and does not establish

It establishes that the 15% / 25% zones are **not rare one-off values** and that the supplied chart's highlighted 2022 and 2025/2026 periods are directionally plausible.

It does **not** establish:
- the exact threshold-crossing date;
- independent episode count;
- forward 1W / 1M / 3M / 6M return;
- max adverse excursion;
- whether the threshold date was the market bottom;
- statistical superiority over unconditional returns.

Those questions remain delegated to `pipeline/ma_breadth_study.py` and require the canonical daily point-in-time series.

## QA use

Small public observations may be stored as fixed QA references with source/date/value/tolerance.

Do not scrape/copy a proprietary provider's full history into the public repository merely because individual values are publicly visible.
