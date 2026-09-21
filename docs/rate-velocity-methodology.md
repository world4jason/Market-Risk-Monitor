# Policy-Rate Velocity Methodology

Issue: #39

The Taiwan Market Regime module treats monetary policy as both a **level** and a **speed of change**.

## Sources

### Taiwan
Central Bank of the Republic of China (Taiwan) official discount-rate change history.

Canonical rate:
- CBC discount rate

### United States
FOMC target rate via FRED:
- `DFEDTAR` through 2008-12-15
- `DFEDTARU` target-range upper limit from 2008-12-16 onward

The two Fed series are joined at the regime change and compressed to effective-date change points.

## Step size

For policy-rate change point t:

```text
step_bp(t) = 100 × (rate_t - rate_(t-1))
```

Examples:
- +0.25 percentage point = +25 bp
- +0.50 percentage point = +50 bp
- +0.75 percentage point = +75 bp

The 25/50/75 bp differences remain visible; they are not hidden behind one generic "hiking" label.

## Cumulative velocity

For H = 3, 6, 12 months:

```text
change_Hm_bp(t)
  = 100 × [rate_t - last effective rate on/before (t-H months)]
```

This works with irregular policy change dates rather than assuming one observation per month.

## Descriptive regimes

Configured in `data/config/rates.json`.

Current defaults:

- **Easing**: 6M cumulative change <= -25 bp
- **Stable**: |6M change| < 25 bp, without an aggressive single step
- **Gradual tightening**: positive 6M change below the aggressive threshold
- **Aggressive tightening**:
  - 6M cumulative tightening >= 100 bp, or
  - a single +75 bp-or-larger step

The +75 bp rule deliberately distinguishes the 2022-style "three-notch" move in the supplied chart from normal +25 bp changes.

## Interpretation

Rate velocity is context, not a market signal by itself.

A rapid hiking cycle can affect:
- financing costs
- discount rates / valuation
- FX and liquidity conditions
- cyclicals / manufacturing demand

But the dashboard keeps it separate from:
- price
- breadth
- macro cycle

No policy-rate regime directly produces a BUY/SELL recommendation.

## Missing data

A missing rate series is `unknown`, not `stable`.

A policy rate can remain unchanged for years, so an old **effective date** is not automatically stale. The metric metadata explicitly treats the series as irregular change-date data.
