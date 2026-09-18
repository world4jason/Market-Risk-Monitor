# Historical comparison methodology

Issue: #7

The dashboard is designed to answer "where are we relative to history?" without accidentally using future data to score past events.

## 1. Raw level is not enough

A current number is shown with historical context where meaningful:

- raw level;
- period-over-period change;
- YoY change for monthly series where defined;
- strict-past percentile;
- rolling strict-past percentile;
- robust z-score when enough history exists;
- event-window normalized path.

No transformation replaces the raw series. Users can always inspect the source level.

## 2. Point-in-time rule

For an observation at time t, any statistic intended to represent what an observer could have known at t uses only observations strictly before t.

For a value x_t and history H_t = {x_1, ..., x_(t-1)}:

    P_t = 100 * (N(x < x_t) + 0.5 * N(x = x_t)) / |H_t|

This is a mid-rank percentile.

The current observation is excluded from its own baseline, and future observations are never included.

Implementation: `pipeline.methodology.point_in_time_percentiles`.

## 3. Full-history vs rolling history

Two historical questions are useful and should not be conflated.

### Expanding point-in-time percentile

Uses all valid prior observations. It answers:

> Relative to everything observed up to then, how unusual was this value?

### Rolling percentile

Uses only the last N observations before t. It answers:

> Relative to the recent regime, how unusual was this value?

This matters because some financial series are structurally non-stationary. Margin debt in nominal dollars is the clearest example: a full-history percentile will naturally drift upward over decades.

The UI must label the baseline explicitly.

## 4. Robust z-score

When a standardized distance is useful, use a median/MAD robust z-score:

    z_r = 0.67448975 * (x_t - median(H_t)) / MAD(H_t)

where:

    MAD(H_t) = median(|x - median(H_t)|)

If MAD is zero or too little history exists, return `insufficient_data`; do not substitute an arbitrary score.

## 5. Period changes

For fixed-frequency series:

    change_(k,t) = (x_t / x_(t-k) - 1) * 100

Examples:
- monthly MoM: k = 1;
- monthly YoY: k = 12.

If the earlier value is zero/missing or the required history is absent, the result is unavailable.

## 6. Event comparison

Historical event overlays are data-driven in `data/events.json`.

Initial anchors:
- Dot-com peak / unwind;
- Global Financial Crisis;
- COVID shock;
- 2022 tightening / bear market;
- current period.

For path comparison, the event-anchor value is indexed to 100:

    I_(t+k) = 100 * x_(t+k) / x_t

This normalization does not imply a forecast. It is a retrospective path comparison.

Metric coverage is respected. If a metric begins after an event, that event/metric cell is `unavailable`.

## 7. Direction / polarity

Each metric declares one of:

- `higher_is_riskier`
- `lower_is_riskier`
- `contextual`
- `neutral`

Polarity affects presentation, not raw mathematics.

Examples:
- VIX: `higher_is_riskier`
- NFCI: `higher_is_riskier`
- nominal margin debt: `contextual` because a high absolute level alone is not a crash signal
- recession shading: `neutral`

## 8. Structural-shift caution

The dashboard must never imply that the same raw level has identical meaning across all eras.

Examples:
- nominal margin debt grows with market size and inflation;
- market structure changed across decades;
- volatility and credit markets can have different structural regimes.

For such metrics, the preferred view is a combination of:
- change rate;
- rolling percentile;
- normalized ratio when a defensible denominator exists;
- current-vs-event path.

## 9. Missing history

If a transform requires at least m historical observations and fewer exist:

    status = insufficient_data
    value = null

Missing, stale, error and insufficient history are not "safe".

## 10. Revision risk

Historical market-price and stress series are often close to point-in-time values, but macroeconomic datasets can be revised.

v0.1 rule:
- point-in-time transforms never use future rows;
- if a future feature depends on revision-prone macro data for "what was known then", use vintages/ALFRED or label it explicitly as revised-history analysis.

## 11. Deterministic tests

Tests cover:
- percentile tie handling;
- no-look-ahead behavior;
- rolling-window behavior;
- robust z-score edge cases;
- fixed-period percentage changes;
- event normalization.

Run:

    python -m unittest discover -s tests -v
