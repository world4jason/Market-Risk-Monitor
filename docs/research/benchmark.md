# Benchmark: comparable market / macro risk dashboards

Issue: #2

## What we reviewed

### 1. lauren-shih/macro-liquidity-pipeline
https://github.com/lauren-shih/macro-liquidity-pipeline

Relevant patterns:
- Treats the dashboard as the output of a data pipeline rather than as a collection of ad-hoc API calls.
- Uses FRED/ALFRED, CFTC and FINRA, including FINRA margin debt.
- Separates raw ingestion, point-in-time-safe transforms, features and dashboards.
- Includes explicit no-look-ahead tests and coverage guards.
- Keeps long-history prefetchers as a separate concern.

Takeaway for this project:
- Raw observations and derived values must be separate.
- Historical/event comparisons need point-in-time semantics.
- Coverage checks belong in validation, not only in the UI.

### 2. SecondOrderEdge/Macro-Dashboard
https://github.com/SecondOrderEdge/Macro-Dashboard

Relevant patterns:
- Makes model decomposition inspectable instead of presenting only one headline number.
- Exposes calibration, walk-forward validation and per-indicator details.
- Uses NBER/FRED recession context and historical comparisons.
- Returns explicit benchmark/context rather than pretending one model is the truth.

Takeaway:
- Avoid an opaque single risk score in v0.1.
- If a composite is added later, every component and transformation must remain auditable.
- Historical comparisons must be walk-forward / no-look-ahead where transformations use a baseline.

### 3. tduic/macro-dashboard
https://github.com/tduic/macro-dashboard

Relevant patterns:
- Compact KPI strip, sparklines, heatmap and a one-line regime summary.
- Consistent change math across multiple horizons.
- Separates market, macro and news/calendar concerns.
- Exposes data availability when FRED is unavailable.

Takeaway:
- Use compact cards plus drill-down history rather than showing full charts everywhere.
- Keep current-regime summary descriptive.
- Standardize horizon/change semantics centrally.

### 4. conradmcg/macro-dashboard
https://github.com/conradmcg/macro-dashboard

Relevant patterns:
- Uses VIX, high-yield spread and NFCI together rather than treating one series as "the market risk indicator".
- Includes yield-curve, macro and risk-sentiment sections.
- Plans recession overlays for historical context.

Takeaway:
- Financial stress, volatility, leverage and market trend belong in separate pillars.
- Cross-pillar confirmation is more useful than a single alarm.

### 5. ianlyoo/margin-ta
https://github.com/ianlyoo/margin-ta

Relevant patterns:
- Multi-horizon states.
- Reports `insufficient_data` when history is inadequate instead of inventing an answer.
- Uses public FRED CSV endpoints on a best-effort basis.
- Separates volatility, credit/rates, breadth and safe-haven inputs.

Takeaway:
- "Unknown" is a valid state and must not be treated as "safe".
- Horizon-specific context should be preserved.

Caution:
- Its 0–100 weighted market-risk score is useful for its use case, but we should not copy an opaque weighted score into v0.1.

### 6. zhamm/macro-dashboard (Watchdog)
https://github.com/zhamm/macro-dashboard

Relevant patterns:
- Clear traffic-light presentation.
- Explicit thresholds.

Anti-pattern we will not copy:
- The project can fall back to hard-coded default values when an API fails. Even if marked stale, a fallback numeric value can still be visually mistaken for a real current observation.

Rule for Market Risk Monitor:
- A failed current fetch may show the last real snapshot only with its original observation date and an explicit stale state. Never fabricate a replacement value.

### 7. essentialbit/fredai FINRA margin-debt proposal
https://github.com/essentialbit/fredai/issues/476

Relevant patterns:
- Treat FINRA margin debt as a separate monthly leverage source.
- Persist history beyond the trailing rows exposed by a current web page.
- Compute trends from stored history, excluding the current observation from the comparison baseline.

Takeaway:
- FINRA history must be durable.
- Derived historical scores must use prior observations only when evaluated historically.

### 8. lukerisser-portfolio/fred-macro-recession-dashboard
https://github.com/lukerisser-portfolio/fred-macro-recession-dashboard

Relevant patterns:
- Favors interpretability over black-box output.
- Frames risk as monitoring rather than exact recession-date prediction.
- Stores cleaned data locally for reproducibility.

Takeaway:
- Language in the UI should distinguish "elevated conditions" from predictions.

## Historical coverage decisions

Do **not** force all metrics into one common short history. Preserve each valid history and expose coverage.

Initial long-history backbone:

| Metric / family | Earliest intended coverage | Role |
|---|---:|---|
| Shiller market/CAPE data | 1871 | valuation + long-run market context |
| Chicago Fed NFCI family | 1971 | financial conditions, risk, credit, leverage context |
| Cboe VIX | 1990 | volatility regime |
| FINRA margin debt | target 1997+ | investor leverage / risk appetite |
| NBER recession context | longest practical source history | event/recession overlay |

A metric unavailable for an older event must render as unavailable, not be backfilled from a proxy without clearly changing the metric identity.

## Point-in-time and revision risk

Historical charts answer two different questions:

1. **What does the latest revised dataset say happened?**
2. **What could an observer have known at the time?**

Most market-price/stress series are naturally close to point-in-time observations, while macroeconomic series can be revised.

v0.1 rule:
- For market/stress series, historical observations may use the official historical series with source metadata.
- Any derived percentile, z-score or event comparison evaluated at date T must use a baseline containing observations available up to T, not future observations.
- If later versions add revision-prone macro series to decision logic, use ALFRED/vintage data or clearly label the result as revised-history analysis.

## Reusable design patterns

1. **History-first cards**  
   Every current KPI can open a long-history view and shows its historical percentile/context when meaningful.

2. **Separate pillars**  
   Leverage, stress, volatility, credit/risk, market trend and valuation remain independently visible.

3. **Explicit data state**  
   `fresh | stale | missing | error | insufficient_data` are distinct.

4. **Source and as-of everywhere**  
   Current values carry observation date, fetch/snapshot date and source.

5. **Raw → derived lineage**  
   Derived metrics document formula and input series.

6. **No-look-ahead historical comparisons**  
   A 2008 percentile must be computed from information through 2008, not from a 2026 full-history distribution unless explicitly labeled as retrospective.

7. **Metric-specific history**  
   Do not truncate 1871/1971 series merely because FINRA begins later.

8. **Descriptive regime language**  
   Say "high leverage / low stress" or "credit stress rising"; do not turn the dashboard into a hidden trading recommendation.

## Anti-patterns

- One giant 0–100 score with undocumented weights.
- Absolute record highs displayed without normalization or historical scale.
- Red/green badges with no formula.
- Hard-coded "current" fallback values.
- Treating stale/missing as safe.
- Using future observations to normalize past events.
- Ignoring source revisions and publication lags.
- Cropping every metric to the newest common start date.
- Claiming a single indicator predicts crashes.

## v0.1 product rules derived from the benchmark

1. Dashboard headline is a **regime description**, not a trade signal.
2. Each pillar stays visible separately.
3. Each metric exposes:
   - current value
   - change
   - historical context
   - coverage start
   - as-of
   - freshness
   - source
4. Historical explorer must include Dot-com, GFC, COVID, 2022 and current where coverage permits.
5. Historical transforms must be reproducible and no-look-ahead.
6. Missing/stale values never reduce the apparent risk state.
7. FINRA margin debt is contextualized by change and history, not absolute ATH alone.
8. Long-history series keep their maximum available coverage.
9. Data contracts are stable enough that the refresh mechanism can change later without rewriting the UI.
10. v0.1 prefers transparent rules to predictive models.
