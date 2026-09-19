# Breadth / Participation methodology

Issues: #15, #16, #17, #18

## 1. 52-week price strength

Raw:

```text
H_t = NYSE new 52-week highs
L_t = NYSE new 52-week lows
```

Net new highs:

```text
NetHL_t = H_t - L_t
```

When a consistent total-active-issues denominator exists:

```text
HighLowPct_t = 100 * (H_t - L_t) / TotalIssues_t
```

The normalized percentage is preferable for cross-era comparison because the number of listed/active issues changes over time.

If `TotalIssues_t` is unavailable, `HighLowPct_t` is missing. The pipeline never fabricates the denominator.

## 2. Advance / decline participation

Raw:

```text
A_t = advancing issues
D_t = declining issues
```

Daily difference:

```text
ADDiff_t = A_t - D_t
```

Normalized ratio where A+D > 0:

```text
ADPct_t = 100 * (A_t - D_t) / (A_t + D_t)
```

Cumulative A/D line:

```text
ADLine_0 = ADDiff_0
ADLine_t = ADLine_(t-1) + ADDiff_t
```

Its absolute level depends on initialization, so event/percentile views are more portable than comparing arbitrary raw levels from different source histories.

## 3. Volume breadth

Raw:

```text
UV_t = NYSE up volume
DV_t = NYSE down volume
UDV_t = UV_t - DV_t
```

No forward-fill is allowed when UV or DV is missing.

## 4. McClellan Volume Oscillator

McClellan Financial documents the classic trend formulas:

```text
T10_t = 0.10 * UDV_t + 0.90 * T10_(t-1)
T05_t = 0.05 * UDV_t + 0.95 * T05_(t-1)

VolumeOsc_t = T10_t - T05_t
```

The 10% and 5% trends correspond to what modern software often calls 19-day and 39-day EMAs.

Reference:
https://www.mcoscillator.com/learning_center/kb/market_data/exponential_moving_averages_calculation/

Initialization in this project:

```text
T10_0 = UDV_0
T05_0 = UDV_0
```

The trends are mathematically defined from the first row, but the public oscillator is marked `insufficient_data` until 39 valid observations have accumulated.

This prevents the initialization seed from being treated as a mature signal.

## 5. McClellan Volume Summation Index

McClellan describes the volume version as the same oscillator/summation framework driven by NYSE Up Volume minus Down Volume.

Reference:
https://www.mcoscillator.com/learning_center/weekly_chart/a_subtle_message_in_the_volume_summation_index/

For a reproducible project-local series:

```text
VolumeSum_first_valid = 1000 + VolumeOsc_first_valid
VolumeSum_t = VolumeSum_(t-1) + VolumeOsc_t
```

The `1000` base makes the series visually comparable to the traditional calibrated Summation Index convention; it is explicitly part of this project's lineage.

Because vendor/CNN implementations can differ in initialization, universe adjustments, and recent proprietary calculation changes, the series is labeled:

**MRM Classic McClellan Volume Summation**

It is not claimed to exactly equal CNN's displayed value.

## 6. Missing-data rule

Any missing UV/DV day breaks the McClellan recurrence.

After a missing day:
- the current oscillator/summation observation is missing;
- trend state is reset;
- another 39 consecutive valid observations are required before the public oscillator/summation becomes mature again.

This is intentionally conservative.

## 7. Historical comparison

Breadth metrics support the same dashboard modes as other metrics:

- absolute
- strict-past percentile
- rolling percentile
- rate of change
- event-window normalization

No historical percentile can use future observations.

## 8. Cross-era comparison

Raw counts such as 250 new lows in 1995 and 250 new lows in 2026 are not assumed equivalent.

Preferred cross-era views:
1. `HighLowPct` using total active issues when available;
2. strict-past or rolling percentile of `NetHL`;
3. strict-past or rolling percentile of the McClellan Volume Summation Index;
4. event-normalized paths.

## 9. CNN-style sentiment labels

CNN labels are not canonical metrics.

If a future UI adds CNN-style labels, they must:
- be explicitly labeled "CNN-style / approximate";
- use only historical data available at that date;
- expose the chosen trailing window and thresholds;
- never hide the underlying raw breadth series.

v0.2 initially ships the underlying metrics without a fake CNN-equivalent score.
