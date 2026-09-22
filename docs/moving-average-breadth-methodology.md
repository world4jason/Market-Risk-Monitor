# Moving-Average Breadth Methodology

Issue: #25

## Canonical metrics

For horizon N in {20, 50, 200}:

```text
Breadth_N(t) =
100 * Above_N(t) / Eligible_N(t)
```

where eligible constituents belong to the documented S&P 500 universe for date t.

The canonical metric is the percentage itself. Raw numerator/denominator are audit metadata when available.

## Historical views

Each horizon supports:

- absolute percentage
- strict-past expanding percentile
- strict-past rolling percentile
- rate of change
- event-window normalization

Historical percentile calculations exclude the current observation and all future observations.

## Survivorship rule

Historical event studies are canonical only when:

```text
source.point_in_time_membership = true
```

A series generated from today's S&P 500 constituents backfilled into history may be displayed only as a non-canonical experiment and is excluded from official event-study and historical signal backfill.

## Interpretation bands

### Common generic interpretation

StockCharts documents a common rule of thumb for percent-above-moving-average breadth:

- above 70%: often considered overbought
- below 30%: often considered oversold

StockCharts also explicitly cautions that becoming oversold is not automatically a buy signal.

### Supplied-chart custom heuristic

The supplied chart uses:

- >85% Euphoria
- >75% Greed
- <25% Fear
- <15% Capitulation

These thresholds are retained only as a configurable **custom heuristic**:

```json
{
  "name": "supplied-chart",
  "bands": {
    "euphoria_above": 85,
    "greed_above": 75,
    "fear_below": 25,
    "capitulation_below": 15
  }
}
```

They do not alter the raw metric, historical percentile, or Deleveraging Watch unless a separate signal explicitly references them.

## Threshold crossing definitions

A downward crossing below threshold K occurs at date t if:

```text
Breadth_(t-1) >= K
Breadth_t < K
```

An upward recross above K occurs if:

```text
Breadth_(t-1) <= K
Breadth_t > K
```

Consecutive days remaining below/above K are not new events.

## Episode de-duplication

For event studies, a crossing starts an episode.

Default cooldown:

```text
20 trading sessions
```

The cooldown window is anchored on the crossing that opened the episode, not on
the previous crossing.

Inside that window:

- at most one opposite-side recross is recorded, and it closes the episode;
- every further crossing is ignored.

Once the window has elapsed, the next crossing anchors a new episode.

Anchoring is what makes this rule work. Chaining the cooldown off the previous
crossing instead lets breadth oscillating across K emit one event per session,
because each crossing is the opposite of the one before it — exactly the choppy
multi-day oversold period this rule exists to collapse.

Only past observations are used, so whether an event exists at time T never
depends on future data.

## Forward-return windows

Default trading-session horizons:

- 1W: 5 sessions
- 1M: 21 sessions
- 3M: 63 sessions
- 6M: 126 sessions

For each event:

```text
forward_return_h =
100 * (SPX_(t+h) / SPX_t - 1)
```

If the target session is unavailable, use the first valid session on/after the target index only when the source calendar gap is <= 3 calendar days; otherwise the result is unavailable.

## Max adverse excursion

For event t and horizon h:

```text
MAE_h =
100 * (min(SPX_t ... SPX_(t+h)) / SPX_t - 1)
```

MAE is descriptive downside experienced after the event. It is not a stop-loss recommendation.

## Local low timing

A "local low" is not used to decide whether an event existed.

Optional retrospective context:

- find the minimum SPX close over the next 63 sessions;
- report sessions-to-low;
- clearly label it retrospective.

This field must never be used to filter or select historical events.

## Unconditional comparison

For each forward horizon, compare event returns with all eligible daily SPX starting dates over the same source coverage.

Report:

- event sample count
- median event return
- positive-return hit rate
- median unconditional return
- unconditional positive-return hit rate
- difference in medians

No claim of predictive significance is made without adequate sample size/statistical testing.

## Required event-study caveats

Every output must expose:

- breadth source/provider
- membership mode
- breadth coverage
- SPX source/coverage
- threshold
- crossing direction
- cooldown
- sample count

Small samples are displayed as such rather than converted into confident labels.
