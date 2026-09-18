# Deleveraging Watch methodology

Issue: #10

Deleveraging Watch is a set of independently visible confirmation conditions.

It is **not**:
- a crash probability;
- a BUY / SELL score;
- a forecast;
- a weighted black-box index.

The UI reports:

```text
active conditions / known conditions · unknown conditions · total conditions
```

Unknown inputs are never counted as inactive/safe.

## Configuration

All production thresholds live in:

`data/config/signals.json`

The evaluation engine is:

`pipeline/signals.py`

The static snapshot is written to:

`data/generated/signals.json`

## v0.1 conditions

### 1. Margin leverage rolling over

Inputs:
- `finra_margin_debt_yoy_pct`

Active if either:
- year-over-year margin-debt growth is at or below 0%; or
- the YoY growth rate has fallen by at least 10 percentage points over three monthly observations.

Purpose:
A high absolute margin-debt level is not treated as a crash signal. This condition looks for a meaningful rollover/deceleration instead.

### 2. Financial conditions tightening

Input:
- `nfci`

Active if either:
- NFCI is at or above 0; or
- NFCI has increased at least 0.5 over 13 weekly observations.

The zero threshold has a source-level interpretation: the Chicago Fed defines positive NFCI values as tighter-than-average financial conditions and negative values as looser-than-average.

The 13-week / 0.5 change rule is a transparent acceleration check. It is configurable, not embedded in UI code.

### 3. Financial risk unusually high

Input:
- `nfci_risk`

Active when the latest observation is at or above its strict-past 90th percentile.

The percentile baseline excludes the current observation and all future observations.

### 4. Volatility stress unusually high

Input:
- `vix`

Active when the latest VIX close is at or above its strict-past 90th percentile.

This avoids hard-coding one absolute VIX number across all market eras.

### 5. Market trend deteriorating

Input:
- `shiller_real_tr_price`

Active when the latest real total-return price is at or below its level six monthly observations earlier.

This is a slow market-trend confirmation, not a daily timing rule.

## Rule states

Each condition is one of:

- `active`
- `inactive`
- `unknown`

For current conditions, a referenced metric must be `fresh`. If it is stale, missing, or errored, the condition becomes `unknown`.

For nested rules:

### any

- if any child is active → active;
- otherwise if any child is unknown → unknown;
- otherwise → inactive.

### all

- if any child is inactive → inactive;
- otherwise if any child is unknown → unknown;
- otherwise → active.

This prevents a missing input from making the dashboard look safer.

## Historical backfill

The signal engine generates a monthly history beginning at the configured historical start.

Historical evaluation differs from the current snapshot in one important way: source publication lag is respected.

For an observation dated `D` with configured lag `L`, it is only available to the historical evaluator on or after:

```text
D + L days
```

This is intentionally conservative. It avoids giving a historical observer a monthly FINRA value before that monthly report would reasonably have been published.

For percentile rules, the current historical observation is compared only with earlier available observations. Future observations are never used.

## Why no composite score

Five active conditions are not automatically "100% crash risk", and one active condition is not "20% risk".

The conditions measure different phenomena:
- leverage rollover;
- financial conditions;
- financial-system risk;
- equity volatility;
- market trend.

Their usefulness is in simultaneous deterioration and historical comparison, not a pseudo-precise aggregate probability.

## Historical event use

`data/generated/signals.json` contains monthly active/known/unknown counts and per-condition states.

The UI overlays the same event anchors used by the Historical Explorer:
- Dot-com;
- Global Financial Crisis;
- COVID shock;
- 2022 tightening/bear market;
- current period.

This lets a viewer inspect how many conditions were active or unknown around previous episodes without turning those episodes into a forecast template.

## Threshold changes

Changing a threshold requires:
1. editing `data/config/signals.json`;
2. documenting the rationale here;
3. rebuilding historical signal history;
4. checking whether the new threshold materially changes historical interpretation.

Thresholds must not be tuned solely to make known crises look visually perfect.
