const CATALOG_URL = "./data/generated/catalog.json";
const OVERVIEW_URL = "./data/generated/overview.json";
const EVENTS_URL = "./data/events.json";
const SIGNALS_URL = "./data/generated/signals.json";
const REFRESH_REPORT_URL = "./data/generated/refresh-report.json";
const MA_BREADTH_CONFIG_URL = "./data/config/ma-breadth.json";
const MA_BREADTH_STUDY_URL = "./data/generated/ma-breadth-event-study.json";
const TAIWAN_MACRO_REGIME_URL = "./data/generated/taiwan-macro-regime.json";
const TAIWAN_EVENTS_URL = "./data/taiwan-events.json";
const TAIWAN_CBC_RATE_REGIME_URL = "./data/generated/taiwan-cbc-rate-regime.json";
const FED_RATE_REGIME_URL = "./data/generated/fed-rate-regime.json";
const METRIC_BASE = new URL("./data/generated/", window.location.href);

let dialogInvoker = null;

const state = {
  catalog: null,
  metrics: new Map(),
  metricLoads: new Map(),
  deferredLoads: new Map(),
  deferredLoaded: new Set(),
  events: [],
  signals: null,
  refreshReport: null,
  refreshErrors: new Map(),
  maBreadthConfig: null,
  maBreadthStudy: null,
  taiwanMacroRegime: null,
  taiwanEvents: [],
  taiwanCbcRateRegime: null,
  fedRateRegime: null,
};

const pillarLabels = {
  leverage: "Leverage",
  financial_stress: "Financial stress",
  credit_risk: "Credit / risk",
  volatility: "Volatility",
  breadth: "Breadth / participation",
  market: "Market trend",
  valuation: "Valuation",
  context: "Context",
};

const pillarOrder = [
  "leverage",
  "financial_stress",
  "credit_risk",
  "volatility",
  "breadth",
  "market",
  "valuation",
  "context",
];

const historyModeLabels = {
  absolute: "Absolute level",
  pit_percentile: "Point-in-time percentile",
  rolling_percentile: "Rolling percentile",
  rate_change: "Rate of change",
};

const beginnerContext = {
  nfci: {
    plain_name: "Broad financial conditions",
    what_it_measures: "The Chicago Fed NFCI combines funding, credit, leverage, and risk conditions into one broad financial-conditions index.",
    why_it_matters: "Tighter financing conditions can make it harder for households, companies, and investors to borrow or take risk.",
    how_to_read: "0 is the long-run average. Negative values mean looser-than-average financial conditions; positive values mean tighter-than-average conditions.",
    higher_lower_or_contextual: "Higher is tighter and generally more stressful; lower is looser.",
    important_reference_level: "0 = the index's long-run average.",
    important_caveat: "NFCI describes current financial conditions. It does not by itself forecast market direction."
  },
  vix: {
    plain_name: "Expected equity-market volatility (VIX)",
    what_it_measures: "The VIX summarizes option-implied expected S&P 500 volatility over roughly the next 30 days.",
    why_it_matters: "Sharp increases often coincide with greater uncertainty and demand for protection.",
    how_to_read: "Higher values generally mean higher expected volatility; lower values mean lower expected volatility.",
    higher_lower_or_contextual: "Higher generally indicates more volatility stress.",
    important_reference_level: "Use its historical distribution rather than a single universal threshold.",
    important_caveat: "VIX is not a directional forecast. A high or low VIX alone does not tell you whether stocks will rise or fall."
  },
  finra_margin_debt: {
    plain_name: "Investor margin debt",
    what_it_measures: "The dollar amount customers owe in securities margin accounts reported by FINRA.",
    why_it_matters: "It is a direct measure of financed market exposure and is useful context for leverage and risk appetite.",
    how_to_read: "Read the level, year-over-year growth, and growth momentum separately. A high level can coexist with slowing growth.",
    higher_lower_or_contextual: "Contextual: a higher level means more outstanding margin borrowing, but direction and momentum matter too.",
    important_reference_level: "Compare with its own history; there is no single universal danger threshold.",
    important_caveat: "A high or rising level does not prove deleveraging. Deleveraging requires evidence that borrowing or its growth is actually rolling over."
  },
  finra_margin_debt_yoy_pct: {
    plain_name: "Margin debt year-over-year growth",
    what_it_measures: "The percentage change in FINRA margin debt from the same month one year earlier.",
    why_it_matters: "It separates the pace of leverage growth from the absolute dollar level.",
    how_to_read: "Positive means margin debt is still above a year earlier. A falling positive growth rate means growth momentum is slowing, not that margin debt has necessarily fallen.",
    higher_lower_or_contextual: "Contextual: direction and change in the growth rate matter more than a high value alone.",
    important_reference_level: "0% separates year-over-year growth from year-over-year contraction.",
    important_caveat: "Do not describe slowing positive growth as 'margin debt is falling' unless the level data also shows a decline."
  },
  tw_taiex: {
    plain_name: "Taiwan market level (TAIEX)",
    what_it_measures: "The closing level of the Taiwan Stock Exchange Capitalization Weighted Stock Index.",
    why_it_matters: "It provides the broad price backdrop for Taiwan-market risk and participation evidence.",
    how_to_read: "Use changes and historical comparisons rather than the raw index number alone.",
    higher_lower_or_contextual: "Contextual: the absolute index level is not a risk score.",
    important_reference_level: "No single index level separates safe from risky conditions.",
    important_caveat: "TAIEX price alone does not show whether gains or losses are broadly shared across stocks."
  },
  tw_advance_decline_pct: {
    plain_name: "Taiwan daily market participation",
    what_it_measures: "The balance of advancing versus declining TWSE-listed stocks, normalized by the number of stocks that moved.",
    why_it_matters: "It shows whether a day's market move is broad or concentrated.",
    how_to_read: "Positive means more stocks advanced than declined that session; negative means more declined than advanced.",
    higher_lower_or_contextual: "Lower means weaker participation for that session; trend interpretation depends on sufficient history.",
    important_reference_level: "0% = equal advancing and declining counts.",
    important_caveat: "A single daily breadth reading is only a participation snapshot. Trend and percentile conclusions require sufficient published history."
  },
  tw_cbc_rate: {
    plain_name: "Taiwan CBC policy rate",
    what_it_measures: "The effective policy-rate level from Taiwan's central bank and its change history.",
    why_it_matters: "Policy-rate changes affect financing conditions, discount rates, and the broader macro backdrop.",
    how_to_read: "The observation date is the date the current rate became effective; the source verification date shows when the project most recently checked the official source.",
    higher_lower_or_contextual: "Contextual: the level and pace of changes matter more than high versus low in isolation.",
    important_reference_level: "No single policy-rate level defines market stress.",
    important_caveat: "An old effective date is not the same as stale data when the rate has remained unchanged and the source was verified recently.",
    date_semantics: "effective_vs_verified"
  }
};

const signalBeginnerContext = {
  margin_debt_rollover: {
    plain_name: "Margin leverage momentum slowing",
    description: "Active when margin-debt YoY growth is non-positive or when that YoY growth rate slows by at least 10 percentage points over three monthly observations.",
    caveat: "An active momentum check does not mean the margin-debt level is already falling; YoY growth can remain positive."
  },
  financial_conditions_tight: {
    plain_name: "Broad financial conditions tightening",
    description: "Checks whether NFCI is above its zero reference or has tightened materially over roughly one quarter.",
    caveat: "This is one financial-conditions check, not a market-direction forecast."
  },
  risk_subindex_extreme: {
    plain_name: "Financial-risk subindex unusually high",
    description: "Checks whether the NFCI risk subindex is at or above its strict-past 90th percentile.",
    caveat: "A percentile describes historical rank, not future returns."
  },
  vix_stress: {
    plain_name: "Volatility stress unusually high",
    description: "Checks whether VIX is at or above its strict-past 90th percentile.",
    caveat: "VIX does not predict market direction by itself."
  },
  market_trend_down: {
    plain_name: "Real total-return trend deteriorating",
    description: "Checks whether Shiller real total-return price is below its level six monthly observations earlier.",
    caveat: "This is a descriptive trend check, not a timing rule."
  },
  high_low_breadth_collapse: {
    plain_name: "NYSE high/low participation unusually weak",
    description: "Checks whether normalized NYSE high-low breadth is at or below its strict-past 10th percentile.",
    caveat: "If the public artifact is unavailable, the status is unknown rather than inactive."
  },
  volume_breadth_collapse: {
    plain_name: "NYSE volume participation unusually weak",
    description: "Checks whether the McClellan Volume Summation measure is at or below its strict-past 10th percentile.",
    caveat: "If the public artifact is unavailable, the status is unknown rather than inactive."
  },
  sp500_50dma_breadth_weak: {
    plain_name: "S&P 500 50-day participation unusually weak",
    description: "Checks whether point-in-time S&P 500 50DMA breadth is at or below its strict-past 10th percentile.",
    caveat: "Unavailable or non-PIT history stays unknown; it is not interpreted as healthy participation."
  },
  sp500_200dma_breadth_weak: {
    plain_name: "S&P 500 200-day participation unusually weak",
    description: "Checks whether point-in-time S&P 500 200DMA breadth is at or below its strict-past 10th percentile.",
    caveat: "Unavailable or non-PIT history stays unknown; it is not interpreted as healthy participation."
  }
};

function $(selector) {
  return document.querySelector(selector);
}

function isTaiwanMetric(metric) {
  return String(metric?.metric?.id || "").startsWith("tw_");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatValue(value, units) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const v = Number(value);

  if (units === "USD millions") {
    if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}T`;
    if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(1)}B`;
    return `$${v.toFixed(0)}M`;
  }
  if (units === "percent") return `${v.toFixed(Math.abs(v) >= 10 ? 1 : 2)}%`;
  if (units === "percentile") return ordinal(v);
  if (units === "ratio") return `${v.toFixed(2)}×`;
  if (units === "binary") return v ? "Yes" : "No";
  if (units === "basis points") return `${v >= 0 ? "+" : ""}${v.toFixed(1)} bp`;
  if (Math.abs(v) >= 1000) {
    return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
  }
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function effectiveFreshness(metric) {
  if (!metric) return { state: "missing", reason: "metric missing" };

  const refreshError = state.refreshErrors.get(metric.metric?.id);
  if (refreshError) {
    return {
      state: "error",
      reason: refreshError.error || "latest refresh failed; previous snapshot preserved",
    };
  }

  const stored = metric.freshness?.state || "missing";
  if (["missing", "error", "insufficient_data"].includes(stored)) {
    return { state: stored, reason: metric.freshness?.reason || null };
  }

  const asOf = metric.latest?.as_of;
  const maxAge = Number(metric.freshness?.max_age_days);
  if (asOf && Number.isFinite(maxAge)) {
    const ageDays = Math.floor((Date.now() - Date.parse(`${asOf}T00:00:00Z`)) / 86400000);
    if (ageDays > maxAge) {
      return {
        state: "stale",
        reason: `source observation is ${ageDays} days old (limit ${maxAge})`,
      };
    }
  }

  return {
    state: stored === "stale" ? "stale" : "fresh",
    reason: metric.freshness?.reason || null,
  };
}

function freshnessBadge(metric) {
  const status = effectiveFreshness(metric).state;
  const cls = ["fresh", "stale", "error", "missing"].includes(status)
    ? `badge-${status}`
    : "badge-neutral";
  return `<span class="badge ${cls}">${escapeHtml(status.replaceAll("_", " "))}</span>`;
}

function percentileRank(value, baseline) {
  if (value == null || !baseline.length) return null;
  const v = Number(value);
  const less = baseline.filter((x) => x < v).length;
  const equal = baseline.filter((x) => x === v).length;
  return (100 * (less + 0.5 * equal)) / baseline.length;
}

function baselineConfig(metric, type) {
  return (metric.baselines || []).find((b) => b.type === type) || null;
}

function defaultRollingWindow(metric) {
  const frequency = metric.metric.frequency;
  if (frequency === "daily") return 2520;
  if (frequency === "weekly") return 520;
  if (frequency === "monthly") return 120;
  return 40;
}


function ordinal(value) {
  if (value == null || !Number.isFinite(Number(value))) return "—";
  const n = Math.round(Number(value));
  const mod100 = Math.abs(n) % 100;
  const mod10 = Math.abs(n) % 10;
  const suffix =
    mod100 >= 11 && mod100 <= 13
      ? "th"
      : mod10 === 1
        ? "st"
        : mod10 === 2
          ? "nd"
          : mod10 === 3
            ? "rd"
            : "th";
  return `${n}${suffix}`;
}

function rollingWindowLabel(metric) {
  const config = baselineConfig(metric, "rolling_percentile");
  const window = Number(config?.window_observations || defaultRollingWindow(metric));
  const frequency = metric?.metric?.frequency;
  let years = null;
  if (frequency === "daily") years = window / 252;
  if (frequency === "weekly") years = window / 52;
  if (frequency === "monthly") years = window / 12;
  if (years != null && Number.isFinite(years)) {
    const rounded = Math.max(1, Math.round(years));
    return `last ${rounded} year${rounded === 1 ? "" : "s"}`;
  }
  return `last ${window.toLocaleString()} observations`;
}

function percentilePresentation(metric, value = rollingPercentile(metric)) {
  if (value == null) {
    return {
      value: "—",
      label: "not enough history for percentile",
      sentence: "Historical percentile is not available for this comparison."
    };
  }
  const rounded = Math.round(value);
  const window = rollingWindowLabel(metric);
  return {
    value: ordinal(rounded),
    label: `percentile vs ${window}`,
    sentence: `Higher than about ${rounded}% of observations in the ${window} comparison window.`
  };
}

function metricDateLine(metric) {
  const context = beginnerContext[metric?.metric?.id];
  const asOf = metric?.latest?.as_of || "unknown";
  if (context?.date_semantics === "effective_vs_verified") {
    const verified = String(metric?.latest?.fetched_at || "").slice(0, 10) || "unknown";
    return `effective since ${asOf} · source verified ${verified}`;
  }
  return `as of ${asOf}`;
}

function metricContextGuide(metric) {
  const context = beginnerContext[metric?.metric?.id];
  if (!context) return "";
  const reference = context.important_reference_level
    ? `<dt>Reference</dt><dd>${escapeHtml(context.important_reference_level)}</dd>`
    : "";
  const caveat = dynamicMetricCaveat(metric) || context.important_caveat;
  return `<div class="context-guide">
    <h3>${escapeHtml(context.plain_name)}</h3>
    <p>${escapeHtml(context.what_it_measures)}</p>
    <dl>
      <dt>Why it matters</dt><dd>${escapeHtml(context.why_it_matters)}</dd>
      <dt>How to read</dt><dd>${escapeHtml(context.how_to_read)}</dd>
      <dt>Direction</dt><dd>${escapeHtml(context.higher_lower_or_contextual)}</dd>
      ${reference}
      <dt>Caveat</dt><dd>${escapeHtml(caveat)}</dd>
    </dl>
  </div>`;
}

function signalCondition(id) {
  return (state.signals?.current?.conditions || []).find((condition) => condition.id === id) || null;
}


function usableObservationCount(metric) {
  if (!Array.isArray(metric?.observations) && metric?.summary) {
    return Number(metric.summary.observation_count || 0);
  }
  return (metric?.observations || []).filter((observation) => observation.value != null).length;
}

function percentileContextSuffix(metric) {
  const parts = [];
  if (metric?.metric?.polarity === "contextual") {
    parts.push("context only");
  }
  if (rollingPercentileSemantics(metric) === "retrospective") {
    parts.push("retrospective; not PIT/backtest-safe");
  }
  return parts.length ? ` · ${parts.join(" · ")}` : "";
}

function percentileCaveatSentence(metric) {
  const parts = [];
  if (metric?.metric?.polarity === "contextual") {
    parts.push("This rank is context only; it is not a risk direction.");
  }
  if (rollingPercentileSemantics(metric) === "retrospective") {
    parts.push(
      "This is a retrospective current rank and is not safe for historical PIT/backtest use.",
    );
  }
  return parts.join(" ");
}

function overviewPercentileText(metric, presentation = percentilePresentation(metric)) {
  if (!metric || presentation.value === "—") return "";
  return `${presentation.value} ${presentation.label}${percentileContextSuffix(metric)}`;
}

function ruleLeaves(rule, out = []) {
  if (!rule) return out;
  if (rule.children) {
    rule.children.forEach((child) => ruleLeaves(child, out));
    return out;
  }
  out.push(rule);
  return out;
}

function findRuleLeaf(condition, predicate) {
  return ruleLeaves(condition?.rules).find(predicate) || null;
}

function marginMomentumEvidence(condition) {
  const trigger = findRuleLeaf(
    condition,
    (rule) =>
      rule.type === "delta_periods_below" &&
      rule.metric === "finra_margin_debt_yoy_pct" &&
      rule.status === "active",
  );
  const value = trigger?.value;
  const periods = trigger?.periods;
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    typeof periods !== "number" ||
    !Number.isFinite(periods)
  ) return null;
  return `YoY growth slowed ${Math.abs(value).toFixed(1)} pp over ${periods} monthly observations`;
}

function taiwanBreadthState(metric) {
  if (!metric) return { state: "missing", observations: 0, freshness: "missing" };
  const observations = usableObservationCount(metric);
  if (observations === 0) {
    return {
      state: "missing",
      observations,
      freshness: effectiveFreshness(metric).state,
    };
  }
  const freshness = effectiveFreshness(metric).state;
  if (freshness !== "fresh") {
    return { state: "not_current", observations, freshness };
  }
  if (observations === 1) {
    return { state: "snapshot_only", observations, freshness };
  }
  if (rollingPercentile(metric) == null) {
    return { state: "history_building", observations, freshness };
  }
  return { state: "context_available", observations, freshness };
}

function dynamicMetricCaveat(metric) {
  if (metric?.metric?.id !== "tw_advance_decline_pct") return null;
  const breadth = taiwanBreadthState(metric);
  if (breadth.state === "missing") {
    return "No usable public breadth sessions are currently available.";
  }
  if (breadth.state === "snapshot_only") {
    return "Only 1 published breadth session is available. This is a one-session participation snapshot, not a trend or percentile conclusion.";
  }
  if (breadth.state === "history_building") {
    return `${breadth.observations} published breadth sessions are available. Multi-session history is accumulating, but the configured historical percentile still lacks sufficient observations.`;
  }
  if (breadth.state === "not_current") {
    return `Published breadth history exists, but its current freshness state is ${breadth.freshness}; current trend interpretation needs caution.`;
  }
  return null;
}

function formatRuleDetail(detail) {
  const parts = [`${detail.label}: ${detail.status}`];
  if (
    typeof detail.value === "number" &&
    Number.isFinite(detail.value)
  ) {
    const value = detail.value;
    const unit =
      detail.type === "delta_periods_below" && detail.metric === "finra_margin_debt_yoy_pct"
        ? " pp"
        : "";
    parts.push(`observed ${value.toFixed(2)}${unit}`);
  }
  if (detail.asOf) parts.push(`as of ${detail.asOf}`);
  const line = escapeHtml(parts.join(" · "));
  return detail.reason
    ? `${line}<br><span class="signal-rule-reason">${escapeHtml(detail.reason)}</span>`
    : line;
}


function setOverviewCard(kind, headline, evidence, note, displayState = "normal") {
  const card = document.querySelector(`[data-overview-card="${kind}"]`);
  const stateId = kind === "coverage" ? "evidence" : kind;
  const stateEl = $(`#overview-${stateId}-state`);
  const evidenceEl = $(`#overview-${stateId}-evidence`);
  const noteEl = $(`#overview-${stateId}-note`);
  const decisionEl = $(`#decision-${kind}-state`);
  if (!card || !stateEl || !evidenceEl || !noteEl) return;
  card.dataset.state = displayState;
  stateEl.textContent = headline;
  evidenceEl.innerHTML = evidence;
  noteEl.textContent = note;
  if (decisionEl) decisionEl.textContent = headline;
}


function observationAvailabilityDate(metric, observation) {
  if (observation?.availability_date) return observation.availability_date;
  const basis = metric?.source?.availability_basis || "unknown";
  if (basis === "observation_date") return observation?.date || null;
  if (basis === "release_date") return observation?.release_date || null;
  return null;
}

function pointInTimeObservationSeries(
  metric,
  observations = metric?.observations || [],
) {
  const eligibility = historicalAnalysisEligibility(metric);
  if (!eligibility.allowed) return [];

  const byAvailability = new Map();
  observations.forEach((observation) => {
    if (observation?.value == null) return;
    const available = observationAvailabilityDate(metric, observation);
    if (!available) return;

    const current = byAvailability.get(available);
    if (!current || String(observation.date) >= String(current.date)) {
      byAvailability.set(available, {
        ...observation,
        availability_date: available,
      });
    }
  });

  return [...byAvailability.values()].sort(
    (left, right) =>
      left.availability_date.localeCompare(right.availability_date) ||
      String(left.date).localeCompare(String(right.date)),
  );
}

function historicalAnalysisEligibility(metric) {
  if (metric?.source?.point_in_time_membership === false) {
    return {
      allowed: false,
      basis: metric?.source?.availability_basis || "unknown",
      reason: "historical membership is not point-in-time",
    };
  }

  const basis = metric?.source?.availability_basis || "unknown";
  if (basis === "unknown") {
    return {
      allowed: false,
      basis,
      reason: "historical observation availability timing is unknown",
    };
  }
  if (!["observation_date", "release_date"].includes(basis)) {
    return {
      allowed: false,
      basis,
      reason: `unsupported availability basis ${basis}`,
    };
  }

  if (
    basis === "release_date" &&
    Array.isArray(metric?.observations) &&
    metric.observations.some(
      (observation) =>
        observation?.value != null && !observation?.release_date,
    )
  ) {
    return {
      allowed: false,
      basis,
      reason: "release-date availability is declared but release_date is missing",
    };
  }

  return { allowed: true, basis, reason: null };
}

function historicalPercentileAllowed(metric) {
  const eligibility = historicalAnalysisEligibility(metric);
  if (!eligibility.allowed) return false;
  return (metric?.baselines || []).some(
    (baseline) =>
      ["full_history_percentile", "rolling_percentile"].includes(
        baseline?.type,
      ) && baseline?.point_in_time === true,
  );
}

function rollingPercentileSemantics(metric) {
  const config = baselineConfig(metric, "rolling_percentile");
  if (metric?.source?.point_in_time_membership === false) {
    return "unavailable";
  }

  const eligibility = historicalAnalysisEligibility(metric);
  if (config?.point_in_time === true && eligibility.allowed) {
    return "point_in_time";
  }
  return "retrospective";
}

function rollingPercentile(metric) {
  const config = baselineConfig(metric, "rolling_percentile");
  const semantics = rollingPercentileSemantics(metric);
  if (semantics === "unavailable") return null;

  if (!Array.isArray(metric?.observations) && metric?.summary) {
    const value = metric.summary.rolling_percentile;
    return value == null ? null : Number(value);
  }

  const raw = metric.observations || [];
  const present = raw.filter((observation) => observation?.value != null);
  if (present.length < 3) return null;

  if (semantics === "point_in_time") {
    const series = strictPastPercentileSeries(metric, { rolling: true });
    const value = series
      .filter((observation) => observation?.value != null)
      .at(-1)?.value;
    return value == null ? null : Number(value);
  }

  const window =
    config?.window_observations || defaultRollingWindow(metric);
  const minObs = config?.min_observations || Math.min(20, window);
  const values = present.map((observation) => Number(observation.value));
  const baseline = values.slice(
    Math.max(0, values.length - 1 - window),
    -1,
  );
  if (baseline.length < minObs) return null;
  return percentileRank(values.at(-1), baseline);
}

// Period-to-period change, in the comparison the artifact declares.
//
// A relative percent change is wrong for several metric classes: a policy rate
// going 1.75% -> 2.00% is +25 bp, not +14.29%, and an index centred on zero has
// no stable relative change at all. The artifact carries metric.comparison; see
// docs/presentation-contract.md.
function recentChange(metric) {
  if (!Array.isArray(metric?.observations) && metric?.summary) {
    const change = metric.summary.recent_change;
    return change
      ? { value: Number(change.value), comparison: change.comparison }
      : null;
  }

  const comparison = metric.metric?.comparison || "absolute";
  if (comparison === "none") return null;

  const obs = (metric.observations || []).filter((o) => o.value != null);
  if (obs.length < 2) return null;
  const prior = Number(obs.at(-2).value);
  const current = Number(obs.at(-1).value);
  if (!Number.isFinite(prior) || !Number.isFinite(current)) return null;

  const delta = current - prior;
  switch (comparison) {
    case "percent_change":
      if (prior === 0) return null;
      return { value: ((current / prior) - 1) * 100, comparison };
    case "basis_points":
      return { value: delta * 100, comparison };
    case "percentage_points":
    case "absolute":
      return { value: delta, comparison };
    default:
      return null;
  }
}

// Single formatter shared by metric cards and the detail dialog.
function formatChange(change) {
  if (change == null) return "—";
  const { value, comparison } = change;
  if (!Number.isFinite(value)) return "—";
  const sign = value >= 0 ? "+" : "";

  if (comparison === "percent_change") return `${sign}${value.toFixed(2)}%`;
  if (comparison === "basis_points") return `${sign}${value.toFixed(1)} bp`;
  if (comparison === "percentage_points") return `${sign}${value.toFixed(2)} pp`;

  // Absolute deltas span weekly NFCI moves of 0.004 and advance-decline counts
  // in the hundreds. A fixed 2 decimals renders the former as "-0", so scale
  // the precision to the magnitude and never report a non-zero change as zero.
  const abs = Math.abs(value);
  if (value === 0) return "0";
  if (abs < 0.005) return `${sign}${Number(value.toPrecision(2))}`;
  const digits = abs >= 1000 ? 0 : abs >= 1 ? 2 : 3;
  return `${sign}${value.toLocaleString(undefined, { maximumFractionDigits: digits })}`;
}

function strictPastPercentileSeries(metric, { rolling = false } = {}) {
  const raw = metric.observations || [];
  const config = baselineConfig(
    metric,
    rolling ? "rolling_percentile" : "full_history_percentile",
  );
  const eligibility = historicalAnalysisEligibility(metric);
  if (
    !eligibility.allowed ||
    !config ||
    config.point_in_time !== true
  ) {
    return raw.map((obs) => ({
      date: obs.date,
      value: null,
      status: obs.value == null ? "missing" : "insufficient_data",
    }));
  }

  const window = rolling
    ? (config.window_observations || defaultRollingWindow(metric))
    : null;
  const minObs = config.min_observations || 20;
  const history = [];
  const out = raw.map((obs) => ({
    date: obs.date,
    value: null,
    status: obs.value == null ? "missing" : "insufficient_data",
  }));
  const groups = new Map();

  raw.forEach((obs, index) => {
    if (obs.value == null) return;
    const available = observationAvailabilityDate(metric, obs);
    if (!available) return;
    out[index].availability_date = available;
    if (!groups.has(available)) groups.set(available, []);
    groups.get(available).push({ index, obs });
  });

  [...groups.keys()].sort().forEach((available) => {
    const baseline = window ? history.slice(-window) : [...history];
    const batch = groups.get(available);

    batch.forEach(({ index, obs }) => {
      if (baseline.length < minObs) return;
      out[index] = {
        date: obs.date,
        value: percentileRank(Number(obs.value), baseline),
        status: "observed",
        availability_date: available,
      };
    });

    batch.forEach(({ obs }) => {
      history.push(Number(obs.value));
    });
  });

  return out;
}

function rateOfChangePeriods(metric) {
  const frequency = metric.metric.frequency;
  if (frequency === "daily") return { periods: 20, label: "20-observation change" };
  if (frequency === "weekly") return { periods: 13, label: "13-week change" };
  if (frequency === "monthly") return { periods: 12, label: "12-month change" };
  return { periods: 4, label: "4-observation change" };
}

function rateOfChangeSeries(metric) {
  const raw = (metric.observations || []).filter((o) => o.value != null);
  const { periods } = rateOfChangePeriods(metric);
  return raw.map((obs, index) => {
    if (index < periods) {
      return { date: obs.date, value: null, status: "insufficient_data" };
    }
    const prior = Number(raw[index - periods].value);
    const current = Number(obs.value);
    if (!prior) return { date: obs.date, value: null, status: "insufficient_data" };
    return {
      date: obs.date,
      value: ((current / prior) - 1) * 100,
      status: "observed",
    };
  });
}

function knowledgeTimelineSeries(metric, observations) {
  return observations
    .map((observation) => {
      const referenceDate =
        observation.reference_date || observation.date || null;
      const availabilityDate =
        observation.availability_date ||
        observationAvailabilityDate(metric, observation);

      return {
        ...observation,
        date: availabilityDate || referenceDate,
        reference_date: referenceDate,
        availability_date: availabilityDate,
      };
    })
    .sort((left, right) =>
      String(left.date || "").localeCompare(String(right.date || "")) ||
      String(left.reference_date || "").localeCompare(
        String(right.reference_date || ""),
      ),
    );
}

function historyView(metric, mode) {
  if (mode === "pit_percentile") {
    return {
      ...metric,
      metric: {
        ...metric.metric,
        name: `${metric.metric.name} — point-in-time percentile`,
        units: "percentile",
      },
      observations: knowledgeTimelineSeries(
        metric,
        strictPastPercentileSeries(metric),
      ),
    };
  }

  if (mode === "rolling_percentile") {
    return {
      ...metric,
      metric: {
        ...metric.metric,
        name: `${metric.metric.name} — rolling percentile`,
        units: "percentile",
      },
      observations: knowledgeTimelineSeries(
        metric,
        strictPastPercentileSeries(metric, { rolling: true }),
      ),
    };
  }

  if (mode === "rate_change") {
    const { label } = rateOfChangePeriods(metric);
    return {
      ...metric,
      metric: {
        ...metric.metric,
        name: `${metric.metric.name} — ${label}`,
        units: "percent",
      },
      observations: rateOfChangeSeries(metric),
    };
  }

  return metric;
}

function svgPath(observations, width = 320, height = 64, pad = 4) {
  const points = observations.filter((o) => o.value != null);
  if (points.length < 2) return null;

  const vals = points.map((o) => Number(o.value));
  let min = Math.min(...vals);
  let max = Math.max(...vals);
  if (min === max) {
    min -= 1;
    max += 1;
  }

  const x = (i) => pad + (i / (points.length - 1)) * (width - 2 * pad);
  const y = (v) => pad + ((max - v) / (max - min)) * (height - 2 * pad);
  const line = points
    .map((p, i) => `${i ? "L" : "M"} ${x(i).toFixed(2)} ${y(Number(p.value)).toFixed(2)}`)
    .join(" ");
  const area = `${line} L ${x(points.length - 1).toFixed(2)} ${height - pad} L ${x(0).toFixed(2)} ${height - pad} Z`;

  return { line, area };
}

function sparkline(metric) {
  const source = Array.isArray(metric?.observations)
    ? metric.observations
    : (metric?.summary?.preview_observations || []);
  const obs = source
    .filter((o) => o.value != null)
    .slice(-120);
  const path = svgPath(obs);

  if (!path) {
    return '<svg class="spark" viewBox="0 0 320 64" aria-hidden="true"><line class="baseline" x1="0" y1="32" x2="320" y2="32"/></svg>';
  }

  return `<svg class="spark" viewBox="0 0 320 64" preserveAspectRatio="none" aria-hidden="true">
    <path class="area" d="${path.area}"></path>
    <path class="line" d="${path.line}"></path>
  </svg>`;
}

function metricCard(metric) {
  const pct = rollingPercentile(metric);
  const p = percentilePresentation(metric, pct);
  const change = recentChange(metric);
  const cText = formatChange(change);
  const context = beginnerContext[metric.metric.id];
  const title = context?.plain_name || metric.metric.name;
  const contextOnly = pct != null ? percentileContextSuffix(metric) : "";

  return `<article class="panel metric-card" data-metric-id="${escapeHtml(metric.metric.id)}" role="button" tabindex="0" aria-label="Open ${escapeHtml(title)} details and history">
    <div class="metric-card-top">
      <div>
        <p class="eyebrow">${escapeHtml(pillarLabels[metric.metric.pillar] || metric.metric.pillar)}</p>
        <h3>${escapeHtml(title)}</h3>
      </div>
      ${freshnessBadge(metric)}
    </div>
    <div class="metric-value">${formatValue(metric.latest?.value, metric.metric.units)}</div>
    <div class="metric-unit">${escapeHtml(metricDateLine(metric))} · ${escapeHtml(metric.metric.units)}</div>
    <div class="metric-context">
      <div class="context-chip"><strong>${cText}</strong><span>last observation</span></div>
      <div class="context-chip"><strong>${p.value}</strong><span>${escapeHtml(p.label)}${contextOnly}</span></div>
    </div>
    ${sparkline(metric)}
    <div class="metric-card-bottom">
      <span class="meta">${escapeHtml(metric.coverage?.history_start || "—")} → ${escapeHtml(metric.coverage?.history_end || "—")}</span>
      <span class="meta">${context ? "Explain & view history ↗" : "Open history ↗"}</span>
    </div>
  </article>`;
}


function renderOverview() {
  const nfci = state.metrics.get("nfci");
  const vix = state.metrics.get("vix");
  const margin = state.metrics.get("finra_margin_debt");
  const marginYoy = state.metrics.get("finra_margin_debt_yoy_pct");
  const taiex = state.metrics.get("tw_taiex");
  const twBreadth = state.metrics.get("tw_advance_decline_pct");
  const cbc = state.metrics.get("tw_cbc_rate");

  const financialCondition = signalCondition("financial_conditions_tight");
  const vixStress = signalCondition("vix_stress");
  const expectedStressConditions = [financialCondition, vixStress];
  const stressStatuses = expectedStressConditions
    .filter(Boolean)
    .map((condition) => effectiveConditionStatus(condition));
  const stressUnknown =
    expectedStressConditions.some((condition) => !condition) ||
    stressStatuses.some((status) => status === "unknown");
  const stressActive = stressStatuses.some((status) => status === "active");
  const stressHeadline = stressUnknown
    ? "U.S. stress evidence is incomplete"
    : stressActive
      ? "One or more current U.S. stress checks are elevated"
      : "Current U.S. stress checks are not broadly elevated";

  const stressEvidence = [];
  if (nfci) {
    stressEvidence.push(`<strong>NFCI ${formatValue(nfci.latest?.value, nfci.metric.units)}</strong> · 0 is the historical-average reference; negative is looser than average.`);
  }
  if (vix) {
    const p = percentilePresentation(vix);
    stressEvidence.push(`<strong>VIX ${formatValue(vix.latest?.value, vix.metric.units)}</strong> · ${escapeHtml(overviewPercentileText(vix, p))}.`);
  }
  setOverviewCard(
    "stress",
    stressHeadline,
    stressEvidence.join("<br>") || "Current NFCI/VIX evidence is unavailable.",
    stressUnknown
      ? "At least one expected stress check is missing, unknown, stale, or errored; the overview does not convert partial evidence into a reassuring conclusion."
      : "These measures describe current conditions; VIX and NFCI do not forecast market direction by themselves.",
    stressUnknown ? "attention" : "normal"
  );

  const marginPct = margin ? percentilePresentation(margin) : null;
  const marginSignal = signalCondition("margin_debt_rollover");
  const marginStatus = marginSignal ? effectiveConditionStatus(marginSignal) : "unknown";
  const momentumEvidence = marginMomentumEvidence(marginSignal);
  const yoy = Number(marginYoy?.latest?.value);
  const leverageHeadline = margin && marginYoy
    ? (marginStatus === "active" && Number.isFinite(yoy) && yoy > 0
        ? "Leverage growth remains positive; its growth momentum is slowing"
        : "Leverage level and growth are available for historical comparison")
    : "Leverage evidence is incomplete";
  const leverageEvidence = [];
  if (margin) {
    const percentileText = marginPct ? overviewPercentileText(margin, marginPct) : "";
    leverageEvidence.push(`<strong>${formatValue(margin.latest?.value, margin.metric.units)}</strong>${percentileText ? ` · ${escapeHtml(percentileText)}` : ""}.`);
  }
  if (marginYoy) {
    leverageEvidence.push(`<strong>YoY growth ${formatValue(marginYoy.latest?.value, "percent")}</strong>.`);
  }
  if (momentumEvidence) {
    leverageEvidence.push(`<strong>${escapeHtml(momentumEvidence)}</strong> · this is the active rollover evidence.`);
  }
  setOverviewCard(
    "leverage",
    leverageHeadline,
    leverageEvidence.join("<br>") || "FINRA margin data is unavailable.",
    marginStatus === "active" && Number.isFinite(yoy) && yoy > 0
      ? "The level is not described as falling: the active condition is the deceleration in YoY growth."
      : "Level, year-over-year growth, and momentum are separate facts; no one of them is a BUY/SELL signal.",
    margin && marginYoy ? (marginStatus === "active" ? "attention" : "normal") : "missing"
  );

  const conditions = (state.signals?.current?.conditions || []).map((condition) => ({
    ...condition,
    displayStatus: effectiveConditionStatus(condition)
  }));
  const known = conditions.filter((c) => c.displayStatus !== "unknown").length;
  const active = conditions.filter((c) => c.displayStatus === "active").length;
  const unknown = conditions.filter((c) => c.displayStatus === "unknown").length;
  const total = conditions.length;
  const activeNames = conditions
    .filter((c) => c.displayStatus === "active")
    .map((c) => signalBeginnerContext[c.id]?.plain_name || c.name);
  const deleveragingHeadline = total
    ? `${active} active / ${known} known / ${unknown} unknown`
    : "Deleveraging checks are unavailable";
  const deleveragingEvidence = total
    ? `Known evidence: <strong>${known}/${total}</strong> · Active: <strong>${active}</strong> · Unknown: <strong>${unknown}</strong>${activeNames.length ? `.<br>Active now: ${escapeHtml(activeNames.join(", "))}.` : "."}`
    : "No signal snapshot is available.";
  setOverviewCard(
    "deleveraging",
    deleveragingHeadline,
    deleveragingEvidence,
    unknown
      ? "Unavailable breadth checks remain unknown; they are not counted as inactive or safe."
      : "Every check is shown independently; this is not a crash probability.",
    total ? (unknown ? "attention" : "normal") : "missing"
  );

  const taiexFreshness = effectiveFreshness(taiex).state;
  const breadth = taiwanBreadthState(twBreadth);
  const taiexChange = taiex ? formatChange(recentChange(taiex)) : "—";
  let taiwanHeadline;
  if (!taiex) {
    taiwanHeadline = "TAIEX price evidence is unavailable";
  } else if (taiexFreshness !== "fresh") {
    taiwanHeadline = `TAIEX data is ${taiexFreshness}; current-price evidence needs attention`;
  } else if (breadth.state === "missing") {
    taiwanHeadline = "TAIEX is current; breadth is unavailable";
  } else if (breadth.state === "not_current") {
    taiwanHeadline = `TAIEX is current; breadth data is ${breadth.freshness}`;
  } else if (breadth.state === "snapshot_only") {
    taiwanHeadline = "TAIEX is current; breadth has one published session";
  } else if (breadth.state === "history_building") {
    taiwanHeadline = "TAIEX is current; breadth history is accumulating";
  } else {
    taiwanHeadline = "Taiwan price and participation context are available";
  }

  const taiwanEvidence = [];
  if (taiex) {
    const freshnessText = taiexFreshness === "fresh" ? "current" : taiexFreshness;
    taiwanEvidence.push(`<strong>TAIEX ${formatValue(taiex.latest?.value, taiex.metric.units)}</strong> · last observation ${escapeHtml(taiexChange)} · ${escapeHtml(freshnessText)}.`);
  }
  if (breadth.state === "missing") {
    taiwanEvidence.push("TWSE A/D breadth is not available in the current published snapshot.");
  } else if (twBreadth) {
    taiwanEvidence.push(`<strong>A/D ${formatValue(twBreadth.latest?.value, "percent")}</strong> · ${breadth.observations} published session${breadth.observations === 1 ? "" : "s"} · ${escapeHtml(breadth.freshness)}.`);
  }
  if (cbc) {
    const verified = String(cbc.latest?.fetched_at || "").slice(0, 10) || "unknown";
    taiwanEvidence.push(`CBC rate <strong>${formatValue(cbc.latest?.value, "percent")}</strong> · effective since ${escapeHtml(cbc.latest?.as_of || "unknown")} · source verified ${escapeHtml(verified)}.`);
  }

  let taiwanNote = "Price, participation, and policy context are shown separately.";
  if (breadth.state === "snapshot_only") {
    taiwanNote = "The breadth reading is a one-session participation snapshot; no breadth trend or percentile conclusion is supported yet.";
  } else if (breadth.state === "history_building") {
    taiwanNote = `${breadth.observations} breadth sessions are published, but the configured historical percentile still lacks sufficient observations.`;
  } else if (breadth.state === "missing") {
    taiwanNote = "Missing breadth is different from insufficient history: no participation conclusion is shown.";
  } else if (breadth.state === "not_current") {
    taiwanNote = "Breadth history exists, but its freshness problem is surfaced rather than treated as current.";
  }

  const taiwanDisplayState =
    !taiex || taiexFreshness === "missing" || taiexFreshness === "error"
      ? "missing"
      : (taiexFreshness !== "fresh" || ["missing", "not_current", "snapshot_only", "history_building"].includes(breadth.state))
        ? "attention"
        : "normal";
  setOverviewCard(
    "taiwan",
    taiwanHeadline,
    taiwanEvidence.join("<br>") || "Taiwan market evidence is unavailable.",
    taiwanNote,
    taiwanDisplayState
  );

  const metrics = [...state.metrics.values()];
  const notCurrent = metrics.filter((metric) => effectiveFreshness(metric).state !== "fresh");
  const comparisonParts = [];
  for (const metric of [nfci, vix, margin]) {
    if (!metric) continue;
    const p = percentilePresentation(metric);
    if (p.value !== "—") {
      const label = beginnerContext[metric.metric.id]?.plain_name || metric.metric.name;
      comparisonParts.push(`${escapeHtml(label)}: <strong>${escapeHtml(p.value)}</strong> ${escapeHtml(p.label)}${escapeHtml(percentileContextSuffix(metric))}`);
    }
  }
  const coverageHeadline = total
    ? `${unknown} of ${total} deleveraging checks unavailable; ${notCurrent.length} loaded metrics need health attention`
    : (metrics.length
        ? `${metrics.length} published metrics loaded; signal coverage unavailable`
        : "Evidence coverage is unavailable");
  setOverviewCard(
    "coverage",
    coverageHeadline,
    comparisonParts.join("<br>") || "Historical comparison becomes available when sufficient published history exists.",
    unknown
      ? `Research views retain full history and event windows. ${unknown} of ${total} Deleveraging Watch checks are currently unavailable.`
      : "Research views retain full history, event windows, source, coverage, and freshness.",
    (notCurrent.length || unknown) ? "attention" : (metrics.length ? "normal" : "missing")
  );
}


function bindMetricCardInteractions(grid) {
  grid.querySelectorAll(".metric-card").forEach((card) => {
    const open = () => openMetric(card.dataset.metricId, card);
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      open();
    });
  });
}

function renderMetrics() {
  const grid = $("#metric-grid");
  const metrics = [...state.metrics.values()]
    .filter((m) => m.metric.pillar !== "context" && !isTaiwanMetric(m))
    .sort(
      (a, b) =>
        pillarOrder.indexOf(a.metric.pillar) -
        pillarOrder.indexOf(b.metric.pillar),
    );

  if (!metrics.length) {
    grid.innerHTML =
      '<div class="panel empty-state"><strong>Current U.S. snapshot is unavailable.</strong><span>No fixture or placeholder value is substituted for missing published data.</span></div>';
    return;
  }

  grid.innerHTML = metrics.map(metricCard).join("");
  bindMetricCardInteractions(grid);
}

function renderTaiwanMarket() {
  const grid = $("#tw-metric-grid");
  const stateGrid = $("#tw-state-grid");
  const chart = $("#tw-taiex-chart");
  const status = $("#tw-history-status");
  if (!grid || !stateGrid || !chart || !status) return;

  const metrics = [...state.metrics.values()]
    .filter(isTaiwanMetric)
    .sort(
      (a, b) =>
        pillarOrder.indexOf(a.metric.pillar) -
        pillarOrder.indexOf(b.metric.pillar),
    );

  if (!metrics.length) {
    stateGrid.innerHTML =
      '<div class="optional-state"><strong>Core Taiwan snapshot unavailable</strong><span>No placeholder data is shown. Source and freshness details remain available when a published snapshot exists.</span></div>';
    grid.innerHTML = "";
    chart.innerHTML =
      '<div class="empty-state compact">TAIEX history is unavailable in the current published snapshot.</div>';
    status.textContent = "Coverage unavailable";
    return;
  }

  const taiex = state.metrics.get("tw_taiex");
  const adPct = state.metrics.get("tw_advance_decline_pct");
  const taiexFreshness = effectiveFreshness(taiex).state;
  const breadth = taiwanBreadthState(adPct);
  const macroMetrics = metrics.filter((m) =>
    ["tw_ndc_", "tw_manufacturing_pmi", "tw_industrial_", "tw_manufacturing_production"]
      .some((prefix) => m.metric.id.startsWith(prefix)),
  );
  const macroCurrent = state.taiwanMacroRegime?.current || null;
  const macroLastKnown = state.taiwanMacroRegime?.latest_known || null;
  const macroLastKnownNote = macroLastKnown
    ? `last known ${macroLastKnown.regime} ${macroLastKnown.date}`
    : "no known regime yet";
  const rateMetrics = metrics.filter((m) =>
    m.metric.id.startsWith("tw_cbc_"),
  );

  const statusCell = (label, value, note) => `<div class="regime-cell">
    <p class="eyebrow">${escapeHtml(label)}</p>
    <div class="regime-value">${escapeHtml(value)}</div>
    <div class="regime-note">${escapeHtml(note)}</div>
  </div>`;

  let breadthValue = "Unavailable";
  let breadthNote = "Official A/D breadth not published";
  if (adPct && breadth.state !== "missing") {
    breadthValue = formatValue(adPct.latest?.value, "percent");
    if (breadth.state === "snapshot_only") {
      breadthNote = "A-D snapshot · 1 session only · no trend inference";
    } else if (breadth.state === "history_building") {
      breadthNote = `A-D % · ${breadth.observations.toLocaleString()} sessions · history accumulating`;
    } else if (breadth.state === "not_current") {
      breadthNote = `A-D history exists · ${breadth.freshness}`;
    } else {
      breadthNote = `A-D % · ${breadth.observations.toLocaleString()} sessions`;
    }
  }

  stateGrid.innerHTML = [
    statusCell(
      "Price",
      taiex ? formatValue(taiex.latest?.value, taiex.metric.units) : "Unavailable",
      taiex
        ? `TAIEX · ${taiex.latest?.as_of || "—"} · ${taiexFreshness}`
        : "TAIEX not published",
    ),
    statusCell("Breadth", breadthValue, breadthNote),
    statusCell(
      "Macro cycle",
      macroCurrent ? String(macroCurrent.regime || "Unknown") : "Not published",
      macroCurrent
        ? (macroCurrent.score === null || macroCurrent.score === undefined
            ? `${macroCurrent.known_components}/${macroCurrent.total_components} inputs · ${macroLastKnownNote}`
            : `score ${Number(macroCurrent.score).toFixed(2)} · confidence ${Math.round(Number(macroCurrent.confidence) * 100)}%`)
        : (macroMetrics.length
            ? `${macroMetrics.length} public macro metrics; regime summary unavailable`
            : "Taiwan macro/regime family is not included in this public release"),
    ),
    statusCell(
      "Rates",
      state.taiwanCbcRateRegime?.current?.regime
        ? String(state.taiwanCbcRateRegime.current.regime)
        : (rateMetrics.length ? "Inputs loaded" : "Unknown"),
      state.taiwanCbcRateRegime?.current
        ? `CBC ${formatValue(state.taiwanCbcRateRegime.current.rate, "percent")} · 6M ${formatValue(state.taiwanCbcRateRegime.current.change_6m_bp, "basis points")} · Fed ${state.fedRateRegime?.current?.regime || "unknown"}`
        : (rateMetrics.length ? `${rateMetrics.length} CBC rate metrics` : "CBC rate history not published"),
    ),
  ].join("");

  const preferredIds = [
    "tw_taiex",
    "tw_advance_decline_pct",
    "tw_advance_decline_diff",
    "tw_advancing_stocks",
    "tw_declining_stocks",
    "tw_market_trade_value",
    "tw_manufacturing_pmi",
    "tw_ndc_monitoring_score",
    "tw_above_50dma_pct",
    "tw_high_low_pct",
    "tw_cbc_rate",
    "tw_cbc_change_6m_bp",
  ];
  const preferred = preferredIds
    .map((id) => state.metrics.get(id))
    .filter(Boolean);

  grid.innerHTML = preferred.map(metricCard).join("");
  bindMetricCardInteractions(grid);

  if (taiex) {
    const observationCount = usableObservationCount(taiex);
    status.textContent =
      `${taiex.coverage.history_start} → ${taiex.coverage.history_end} · ${observationCount.toLocaleString()} observations · ${taiexFreshness}`;
    if (Array.isArray(taiex.observations)) {
      fullChart(taiex, chart);
    } else {
      chart.innerHTML =
        '<div class="empty-state compact"><strong>TAIEX history is available on demand.</strong><button id="tw-load-history" class="text-button" type="button">Load TAIEX history</button></div>';
      $("#tw-load-history")?.addEventListener("click", async (event) => {
        event.currentTarget.disabled = true;
        event.currentTarget.textContent = "Loading…";
        try {
          await ensureMetricLoaded("tw_taiex");
          renderTaiwanMarket();
        } catch (error) {
          console.warn("TAIEX history load failed", error);
          chart.innerHTML =
            '<div class="empty-state compact">TAIEX history could not be loaded. Current summary data remains available.</div>';
        }
      });
    }
  } else {
    chart.innerHTML =
      '<div class="empty-state compact">TAIEX snapshot is unavailable in the current release.</div>';
    status.textContent = "TAIEX unavailable";
  }

  renderTaiwanEventSelector();
}

function maBreadthMetrics() {
  return {
    20: state.metrics.get("sp500_above_20dma_pct"),
    50: state.metrics.get("sp500_above_50dma_pct"),
    200: state.metrics.get("sp500_above_200dma_pct"),
  };
}

function renderTrendParticipation() {
  const section = $("#trend-participation-section");
  const controls = $("#trend-controls");
  const summaryEl = $("#ma-summary");
  const chartEl = $("#ma-chart");
  const legend = $("#trend-legend");
  const studyBlock = $("#ma-study-block");
  const metrics = maBreadthMetrics();
  const loaded = Object.entries(metrics).filter(([, metric]) => metric);

  if (!loaded.length) {
    section?.classList.add("compact-optional");
    if (controls) controls.hidden = true;
    if (chartEl) chartEl.hidden = true;
    if (legend) legend.hidden = true;
    if (studyBlock) studyBlock.hidden = true;
    summaryEl.innerHTML =
      '<div class="optional-state"><strong>Trend Participation — unavailable in the public release</strong><span>Point-in-time S&P 500 moving-average breadth history with acceptable redistribution rights is not currently published. Missing breadth remains unknown in Deleveraging Watch.</span></div>';
    return;
  }

  section?.classList.remove("compact-optional");
  if (controls) controls.hidden = false;
  if (chartEl) chartEl.hidden = false;
  if (legend) legend.hidden = false;
  if (studyBlock) studyBlock.hidden = false;

  summaryEl.innerHTML = [20, 50, 200]
    .map((horizon) => {
      const metric = metrics[horizon];
      if (!metric) {
        return `<div class="trend-stat missing"><span>${horizon}DMA</span><strong>—</strong><small>not published</small></div>`;
      }
      const pct = rollingPercentile(metric);
      const eligibility = historicalAnalysisEligibility(metric);
      const context = !eligibility.allowed
        ? `non-PIT history · ${eligibility.reason}`
        : (pct == null
            ? "historical percentile unavailable"
            : `${ordinal(pct)} percentile vs ${rollingWindowLabel(metric)}`);
      return `<button class="trend-stat" type="button" data-ma-metric="${metric.metric.id}">
        <span>${horizon}DMA</span>
        <strong>${formatValue(metric.latest?.value, "percent")}</strong>
        <small>${escapeHtml(context)} · ${escapeHtml(metric.latest?.as_of || "—")}</small>
      </button>`;
    })
    .join("");

  summaryEl.querySelectorAll("[data-ma-metric]").forEach((button) => {
    button.addEventListener("click", () => openMetric(button.dataset.maMetric));
  });

  renderTrendParticipationChart();
  renderMaBreadthStudy();
}

function renderMaBreadthStudy() {
  const statusEl = $("#ma-study-status");
  const summaryEl = $("#ma-study-summary");
  const bodyEl = $("#ma-study-body");
  const study = state.maBreadthStudy;

  if (!statusEl || !summaryEl || !bodyEl) return;

  if (!study) {
    statusEl.textContent = "Study snapshot not loaded";
    summaryEl.innerHTML =
      '<div class="empty-state compact">Build the study after loading point-in-time 50DMA breadth and SPX price history.</div>';
    bodyEl.innerHTML =
      '<tr><td colspan="9" class="empty-cell">No threshold-study episodes loaded.</td></tr>';
    return;
  }

  if (study.status !== "ready") {
    statusEl.textContent = study.status.replaceAll("_", " ");
    summaryEl.innerHTML = `<div class="empty-state compact">${escapeHtml(study.reason || "Event study is not canonical for this source.")}</div>`;
    bodyEl.innerHTML =
      '<tr><td colspan="9" class="empty-cell">Canonical episode table unavailable for this source.</td></tr>';
    return;
  }

  statusEl.textContent =
    `${study.events?.length || 0} events · cooldown ${study.cooldown_sessions} sessions · descriptive only`;

  const preferred = (study.summaries || []).filter(
    (row) =>
      row.direction === "down" &&
      [15, 25].includes(Number(row.threshold)) &&
      ["1M", "3M"].includes(row.horizon),
  );

  summaryEl.innerHTML = preferred.length
    ? preferred
        .map((row) => {
          const medianText =
            row.median_return_pct == null
              ? "—"
              : `${row.median_return_pct >= 0 ? "+" : ""}${row.median_return_pct.toFixed(2)}%`;
          const hitText =
            row.positive_hit_rate_pct == null
              ? "—"
              : `${row.positive_hit_rate_pct.toFixed(0)}%`;
          const maeText =
            row.median_max_adverse_excursion_pct == null
              ? "—"
              : `${row.median_max_adverse_excursion_pct.toFixed(2)}%`;
          return `<div class="ma-study-card">
            <strong>Cross &lt; ${row.threshold}% · ${row.horizon}</strong>
            <span>n=${row.sample_count} · median ${medianText} · positive ${hitText} · median MAE ${maeText}</span>
          </div>`;
        })
        .join("")
    : '<div class="empty-state compact">No completed forward-return windows yet.</div>';

  const formatReturn = (value) =>
    value == null ? "—" : `${value >= 0 ? "+" : ""}${Number(value).toFixed(2)}%`;

  const events = [...(study.events || [])].sort((a, b) =>
    a.date.localeCompare(b.date),
  );

  bodyEl.innerHTML = events.length
    ? events
        .map((event) => `<tr>
          <td>${escapeHtml(event.date)}</td>
          <td>${escapeHtml(event.direction)} ${Number(event.threshold).toFixed(0)}%</td>
          <td>${Number(event.breadth_value).toFixed(2)}%</td>
          <td>${formatValue(event.price, "index")}</td>
          <td>${formatReturn(event.forward_returns_pct?.["1W"])}</td>
          <td>${formatReturn(event.forward_returns_pct?.["1M"])}</td>
          <td>${formatReturn(event.forward_returns_pct?.["3M"])}</td>
          <td>${formatReturn(event.forward_returns_pct?.["6M"])}</td>
          <td>${event.sessions_to_63d_low == null ? "—" : `${event.sessions_to_63d_low} sessions`}</td>
        </tr>`)
        .join("")
    : '<tr><td colspan="9" class="empty-cell">No threshold-study episodes available.</td></tr>';
}

function renderTrendParticipationChart() {
  const element = $("#ma-chart");
  const metrics = maBreadthMetrics();
  const summaryOnly = Object.values(metrics).filter(
    (metric) => metric && !Array.isArray(metric.observations),
  );
  if (summaryOnly.length) {
    element.innerHTML =
      '<div class="empty-state compact"><strong>Trend Participation history is available on demand.</strong><button id="ma-load-history" class="text-button" type="button">Load breadth history</button></div>';
    $("#ma-load-history")?.addEventListener("click", async (event) => {
      event.currentTarget.disabled = true;
      event.currentTarget.textContent = "Loading…";
      const ids = summaryOnly.map((metric) => metric.metric.id);
      const results = await Promise.allSettled(ids.map(ensureMetricLoaded));
      const failed = results.filter((result) => result.status === "rejected").length;
      if (failed) {
        console.warn("moving-average breadth history load failed", failed);
      }
      renderTrendParticipationChart();
    });
    return;
  }
  const lines = [20, 50, 200]
    .map((horizon) => ({
      horizon,
      metric: metrics[horizon],
      observations: (metrics[horizon]?.observations || []).filter((o) => o.value != null),
    }))
    .filter((line) => line.observations.length > 1);

  if (!lines.length) {
    element.innerHTML =
      '<div class="empty-state compact">Not enough moving-average breadth history.</div>';
    return;
  }

  const width = 1000;
  const height = 360;
  const left = 58;
  const right = 74;
  const top = 24;
  const bottom = 42;
  const allDates = lines.flatMap((line) => line.observations.map((o) => Date.parse(o.date)));
  const firstTs = Math.min(...allDates);
  const lastTs = Math.max(...allDates);
  const span = Math.max(lastTs - firstTs, 1);
  const innerW = width - left - right;
  const innerH = height - top - bottom;
  const x = (dateValue) => left + ((Date.parse(dateValue) - firstTs) / span) * innerW;
  const y = (value) => top + ((100 - value) / 100) * innerH;

  const grids = [0, 25, 50, 75, 100]
    .map((value) => {
      const yy = y(value);
      return `<line class="gridline" x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}"/>
        <text x="${left - 9}" y="${yy + 4}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${value}%</text>`;
    })
    .join("");

  const classes = { 20: "ma-line-20", 50: "ma-line-50", 200: "ma-line-200" };
  const paths = lines
    .map((line) => {
      const d = line.observations
        .map((obs, index) => `${index ? "L" : "M"} ${x(obs.date).toFixed(1)} ${y(Number(obs.value)).toFixed(1)}`)
        .join(" ");
      return `<path class="${classes[line.horizon]}" d="${d}"><title>S&P 500 % above ${line.horizon}DMA</title></path>`;
    })
    .join("");

  let bands = "";
  if ($("#ma-bands-toggle")?.checked) {
    const config = state.maBreadthConfig?.custom_heuristics?.supplied_chart;
    if (config) {
      const values = [
        ["Euphoria", config.euphoria_above],
        ["Greed", config.greed_above],
        ["Fear", config.fear_below],
        ["Capitulation", config.capitulation_below],
      ];
      bands = values
        .filter(([, value]) => Number.isFinite(Number(value)))
        .map(([label, value]) => {
          const yy = y(Number(value));
          return `<line class="ma-heuristic-line" x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}"/>
            <text x="${width - right - 5}" y="${yy - 5}" text-anchor="end" fill="currentColor" opacity=".55" font-size="10">${escapeHtml(label)} ${value}% · 50DMA custom</text>`;
        })
        .join("");
    }
  }

  let spxPath = "";
  let spxAxis = "";
  if ($("#ma-spx-toggle")?.checked) {
    const spx = state.metrics.get("sp500_index");
    const obs = (spx?.observations || [])
      .filter((o) => o.value != null)
      .filter((o) => Date.parse(o.date) >= firstTs && Date.parse(o.date) <= lastTs);
    if (obs.length > 1) {
      const values = obs.map((o) => Number(o.value));
      let min = Math.min(...values);
      let max = Math.max(...values);
      if (min === max) {
        min -= 1;
        max += 1;
      }
      const ySpx = (value) => top + ((max - value) / (max - min)) * innerH;
      const d = obs
        .map((item, index) => `${index ? "L" : "M"} ${x(item.date).toFixed(1)} ${ySpx(Number(item.value)).toFixed(1)}`)
        .join(" ");
      spxPath = `<path class="ma-spx-line" d="${d}"><title>S&P 500 index overlay</title></path>`;
      spxAxis = `<text x="${width - 5}" y="${top + 10}" text-anchor="end" fill="currentColor" opacity=".5" font-size="10">SPX ${formatValue(max, "index")}</text>
        <text x="${width - 5}" y="${height - bottom}" text-anchor="end" fill="currentColor" opacity=".5" font-size="10">SPX ${formatValue(min, "index")}</text>`;
    }
  }

  const coverageStart = new Date(firstTs).toISOString().slice(0, 10);
  const coverageEnd = new Date(lastTs).toISOString().slice(0, 10);
  const latestBreadth = lines
    .map((line) => {
      const latest = line.observations.at(-1);
      return `${line.horizon}DMA ${formatValue(latest.value, "percent")} on ${latest.date}`;
    })
    .join("; ");
  const a11y = chartA11y(
    element,
    "S&P 500 moving-average breadth",
    `S&P 500 moving-average breadth from ${coverageStart} to ${coverageEnd}. Latest: ${latestBreadth}.`,
  );
  element.innerHTML = `${a11y.summaryHtml}<svg class="history-svg ma-breadth-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" ${a11y.svgAttrs}>
    ${grids}
    ${bands}
    ${paths}
    ${spxPath}
    ${spxAxis}
    <text x="${left}" y="${height - 12}" fill="currentColor" opacity=".55" font-size="11">${coverageStart}</text>
    <text x="${width - right}" y="${height - 12}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${coverageEnd}</text>
  </svg>`;
}

function renderRegime() {
  const grid = $("#regime-grid");
  const details = $("#data-health-details");
  const metrics = [...state.metrics.values()].filter(
    (m) => m.metric.pillar !== "context" && !isTaiwanMetric(m),
  );

  if (!metrics.length) {
    grid.innerHTML =
      '<div class="empty-state compact">Published U.S. metric health is unavailable.</div>';
    if (details) details.open = true;
    return;
  }

  const byPillar = new Map();
  for (const metric of metrics) {
    if (!byPillar.has(metric.metric.pillar)) {
      byPillar.set(metric.metric.pillar, []);
    }
    byPillar.get(metric.metric.pillar).push(metric);
  }

  const bad = metrics.filter((metric) => effectiveFreshness(metric).state !== "fresh");
  if (details) details.open = bad.length > 0;

  grid.innerHTML = pillarOrder
    .filter((pillar) => byPillar.has(pillar))
    .slice(0, 6)
    .map((pillar) => {
      const metricsForPillar = byPillar.get(pillar);
      const notCurrent = metricsForPillar.filter(
        (m) => effectiveFreshness(m).state !== "fresh",
      ).length;
      const current = metricsForPillar.length - notCurrent;

      return `<div class="regime-cell">
        <p class="eyebrow">${escapeHtml(pillarLabels[pillar] || pillar)}</p>
        <div class="regime-value">${notCurrent ? `${notCurrent} not current` : "Data current"}</div>
        <div class="regime-note">${current} of ${metricsForPillar.length} metric${metricsForPillar.length === 1 ? "" : "s"} current</div>
      </div>`;
    })
    .join("");
}

function renderCoverage() {
  const tbody = $("#coverage-body");
  const metrics = [...state.metrics.values()].sort((a, b) =>
    a.metric.name.localeCompare(b.metric.name),
  );

  if (!metrics.length) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="empty-cell">No generated metrics yet.</td></tr>';
    return;
  }

  tbody.innerHTML = metrics
    .map(
      (m) => `<tr>
        <td>${escapeHtml(m.metric.name)}</td>
        <td>${escapeHtml(pillarLabels[m.metric.pillar] || m.metric.pillar)}</td>
        <td>${escapeHtml(m.coverage.history_start || "—")} → ${escapeHtml(m.coverage.history_end || "—")}</td>
        <td>${escapeHtml(m.latest.as_of || "—")}</td>
        <td>${freshnessBadge(m)}</td>
        <td><a class="source-link" href="${escapeHtml(m.source.url)}" target="_blank" rel="noopener">${escapeHtml(m.source.provider)}</a></td>
      </tr>`,
    )
    .join("");
}

function recessionIntervals() {
  const recession = state.metrics.get("us_recession");
  if (!recession) return [];

  const obs = (recession.observations || []).filter((o) => o.value != null);
  const intervals = [];
  let start = null;

  for (const item of obs) {
    const isRecession = Number(item.value) >= 0.5;
    if (isRecession && start == null) start = Date.parse(item.date);
    if (!isRecession && start != null) {
      intervals.push([start, Date.parse(item.date)]);
      start = null;
    }
  }

  if (start != null) {
    intervals.push([start, Date.parse(obs.at(-1).date)]);
  }
  return intervals;
}

function chartA11y(element, label, summary) {
  const base = element?.id || "chart";
  const summaryId = `${base}-a11y-summary`;
  return {
    summaryId,
    summaryHtml: `<p id="${escapeHtml(summaryId)}" class="sr-only">${escapeHtml(summary)}</p>`,
    svgAttrs: `role="img" aria-label="${escapeHtml(label)}" aria-describedby="${escapeHtml(summaryId)}"`,
  };
}

function metricChartSummary(metric, observations) {
  const obs = observations.filter((item) => item.value != null);
  if (!obs.length) return `${metric.metric.name}. No usable observations.`;
  const values = obs.map((item) => Number(item.value)).filter(Number.isFinite);
  const first = obs[0];
  const last = obs.at(-1);
  const range = values.length
    ? ` Range ${formatValue(Math.min(...values), metric.metric.units)} to ${formatValue(Math.max(...values), metric.metric.units)}.`
    : "";
  const usesKnowledgeTimeline = obs.some(
    (item) =>
      item.reference_date &&
      item.date &&
      item.reference_date !== item.date,
  );
  if (usesKnowledgeTimeline) {
    const reference = last.reference_date || last.date;
    return `${metric.metric.name}. ${obs.length} point-in-time observations on knowledge dates from ${first.date} to ${last.date}. Latest knowledge date ${last.date}, reference period ${reference}: ${formatValue(last.value, metric.metric.units)}.${range}`;
  }
  return `${metric.metric.name}. ${obs.length} observations from ${first.date} to ${last.date}. Latest ${last.date}: ${formatValue(last.value, metric.metric.units)}.${range}`;
}

function fullChart(metric, element, opts = {}) {
  const obs = (metric.observations || []).filter((o) => o.value != null);
  if (obs.length < 2) {
    element.innerHTML =
      '<div class="empty-state compact">Not enough observations for this view.</div>';
    return;
  }

  const width = 1000;
  const height = opts.height || 360;
  const left = 66;
  const right = 20;
  const top = 22;
  const bottom = 42;

  const values = obs.map((o) => Number(o.value));
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  }

  const firstTs = Date.parse(obs[0].date);
  const lastTs = Date.parse(obs.at(-1).date);
  const innerW = width - left - right;
  const innerH = height - top - bottom;
  const span = Math.max(lastTs - firstTs, 1);

  const xTs = (ts) => left + ((ts - firstTs) / span) * innerW;
  const y = (v) => top + ((max - v) / (max - min)) * innerH;

  const path = obs
    .map(
      (o, i) =>
        `${i ? "L" : "M"} ${xTs(Date.parse(o.date)).toFixed(1)} ${y(Number(o.value)).toFixed(1)}`,
    )
    .join(" ");

  const grids = [0, 0.25, 0.5, 0.75, 1]
    .map((t) => {
      const yy = top + t * innerH;
      const val = max - t * (max - min);
      return `<line class="gridline" x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}"/>
        <text x="${left - 9}" y="${yy + 4}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${escapeHtml(formatValue(val, metric.metric.units))}</text>`;
    })
    .join("");

  const bands = recessionIntervals()
    .filter(([start, end]) => end >= firstTs && start <= lastTs)
    .map(([start, end]) => {
      const x1 = xTs(Math.max(start, firstTs));
      const x2 = xTs(Math.min(end, lastTs));
      return `<rect class="recession-band" x="${x1.toFixed(1)}" y="${top}" width="${Math.max(x2 - x1, 1).toFixed(1)}" height="${innerH}"><title>NBER recession context</title></rect>`;
    })
    .join("");

  const a11y = chartA11y(
    element,
    `${metric.metric.name} history`,
    metricChartSummary(metric, obs),
  );
  element.innerHTML = `${a11y.summaryHtml}<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" ${a11y.svgAttrs}>
    ${bands}
    ${grids}
    <path class="line" d="${path}"></path>
    <text x="${left}" y="${height - 12}" fill="currentColor" opacity=".55" font-size="11">${escapeHtml(obs[0].date)}</text>
    <text x="${width - right}" y="${height - 12}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${escapeHtml(obs.at(-1).date)}</text>
  </svg>`;
}

function renderHistorySelector() {
  const select = $("#history-metric");
  const mode = $("#history-mode");
  const metrics = [...state.metrics.values()].filter(
    (m) =>
      usableObservationCount(m) > 1 &&
      m.metric.pillar !== "context" &&
      !isTaiwanMetric(m),
  );

  if (!metrics.length) {
    select.innerHTML = '<option value="">No metric data</option>';
    $("#history-chart").innerHTML =
      '<div class="empty-state compact">Historical series will appear here.</div>';
    return;
  }

  select.innerHTML = [
    '<option value="">Select a metric to load history</option>',
    ...metrics.map(
      (m) =>
        `<option value="${escapeHtml(m.metric.id)}">${escapeHtml(m.metric.name)}</option>`,
    ),
  ].join("");

  const rerender = async () => {
    if (!select.value) {
      $("#history-chart").innerHTML =
        '<div class="empty-state compact">Select a metric to load its full history.</div>';
      return;
    }
    await renderHistory(select.value, mode.value);
  };
  select.onchange = rerender;
  mode.onchange = rerender;
  $("#history-chart").innerHTML =
    '<div class="empty-state compact">Select a metric to load its full history.</div>';
}

async function renderHistory(id, mode = "absolute") {
  let metric;
  try {
    [metric] = await Promise.all([
      ensureMetricLoaded(id),
      ensureDeferredContext("events"),
    ]);
  } catch (error) {
    console.warn("history load failed", id, error);
    $("#history-chart").innerHTML =
      '<div class="empty-state compact">This metric history could not be loaded.</div>';
    return;
  }

  const percentileMode =
    mode === "pit_percentile" || mode === "rolling_percentile";
  const eligibility = historicalAnalysisEligibility(metric);
  const baselineType =
    mode === "rolling_percentile"
      ? "rolling_percentile"
      : "full_history_percentile";
  const baseline = percentileMode
    ? baselineConfig(metric, baselineType)
    : null;
  const percentileBlocked =
    percentileMode &&
    (
      !eligibility.allowed ||
      !baseline ||
      baseline.point_in_time !== true
    );

  const view = historyView(metric, mode);
  if (percentileBlocked) {
    const reason = !eligibility.allowed
      ? eligibility.reason
      : "the selected baseline is not declared point-in-time";
    $("#history-chart").innerHTML =
      `<div class="empty-state compact"><strong>Point-in-time historical view disabled.</strong><span>${escapeHtml(reason)}. Use Absolute level for retrospective history.</span></div>`;
  } else {
    fullChart(view, $("#history-chart"));
  }

  const available = (view.observations || []).filter((o) => o.value != null);
  const modeLabel =
    mode === "rate_change"
      ? rateOfChangePeriods(metric).label
      : historyModeLabels[mode] || historyModeLabels.absolute;

  $("#history-mode-label").innerHTML =
    `<i class="legend-dot"></i> ${escapeHtml(modeLabel)}`;
  $("#history-coverage").textContent =
    `${metric.coverage.history_start} → ${metric.coverage.history_end} · ${available.length.toLocaleString()} usable observations`;

  renderEvents(metric);
}

function monthOffset(anchorDate, targetDate) {
  return (targetDate.getTime() - anchorDate.getTime()) / (30.4375 * 86400000);
}

function observationOnOrBeforeIndex(obs, anchor) {
  const target = Date.parse(anchor);
  let best = -1;
  for (let i = 0; i < obs.length; i += 1) {
    if (obs[i].value == null) continue;
    const available = obs[i].availability_date || obs[i].date;
    if (Date.parse(available) <= target) best = i;
    else break;
  }
  return best;
}

function renderEvents(metric) {
  const list = $("#event-list");
  const el = $("#event-chart");
  const rawObs = (metric.observations || []).filter((o) => o.value != null);

  if (!state.events.length || !rawObs.length) {
    list.innerHTML = "";
    el.innerHTML =
      '<div class="empty-state compact">Event definitions or history unavailable.</div>';
    return;
  }

  const eligibility = historicalAnalysisEligibility(metric);
  if (!eligibility.allowed) {
    list.innerHTML = "";
    el.innerHTML =
      `<div class="empty-state compact"><strong>Historical event comparison disabled.</strong><span>${escapeHtml(eligibility.reason)}. Raw absolute history remains available.</span></div>`;
    return;
  }

  const obs = pointInTimeObservationSeries(metric, rawObs);
  if (!obs.length) {
    list.innerHTML = "";
    el.innerHTML =
      '<div class="empty-state compact">No point-in-time event history is available.</div>';
    return;
  }

  const coverageStart = Date.parse(obs[0].availability_date);
  const colors = [
    "#5dc2aa",
    "#e7b75f",
    "#ff8278",
    "#7c9cff",
    "#b58cff",
    "#63b3ed",
    "#d98bc6",
    "#8fbf62",
  ];

  list.innerHTML = state.events
    .map((event, index) => {
      const anchor = event.anchor_date || metric.latest.as_of;
      const unavailable = !anchor || Date.parse(anchor) < coverageStart;
      const color = colors[index % colors.length];
      return `<span class="event-pill ${unavailable ? "unavailable" : ""}" title="${escapeHtml(event.notes || "")}"><i class="event-dot" style="background:${color}"></i>${escapeHtml(event.name)}</span>`;
    })
    .join("");
  const lines = [];

  state.events.forEach((event, index) => {
    const anchor = event.anchor_date || metric.latest.as_of;
    if (!anchor || Date.parse(anchor) < coverageStart) return;

    // Historical comparison is strict-on-or-before: never choose a future
    // observation merely because it is closer to the event date.
    const anchorIdx = observationOnOrBeforeIndex(obs, anchor);
    if (anchorIdx < 0) return;

    const anchorValue = Number(obs[anchorIdx].value);
    if (!anchorValue) return;

    const anchorDate = new Date(
      `${obs[anchorIdx].availability_date || obs[anchorIdx].date}T00:00:00Z`,
    );
    const pre = Number(event.window?.pre_months ?? 12);
    const post = Number(event.window?.post_months ?? 24);
    const points = [];

    for (const item of obs) {
      const dt = new Date(
        `${item.availability_date || item.date}T00:00:00Z`,
      );
      const offset = monthOffset(anchorDate, dt);
      if (offset < -pre || offset > post) continue;
      points.push({
        offset,
        value: (Number(item.value) / anchorValue) * 100,
      });
    }

    if (points.length > 1) {
      lines.push({
        name: event.name,
        points,
        color: colors[index % colors.length],
        pre,
        post,
      });
    }
  });

  if (!lines.length) {
    el.innerHTML =
      '<div class="empty-state compact">No event has sufficient metric history.</div>';
    return;
  }

  const width = 720;
  const height = 250;
  const left = 42;
  const right = 16;
  const top = 18;
  const bottom = 34;
  const minOffset = Math.min(...lines.map((line) => -line.pre));
  const maxOffset = Math.max(...lines.map((line) => line.post));
  const allValues = lines.flatMap((line) => line.points.map((p) => p.value));

  let min = Math.min(...allValues);
  let max = Math.max(...allValues);
  if (min === max) {
    min -= 1;
    max += 1;
  }

  const x = (offset) =>
    left +
    ((offset - minOffset) / Math.max(maxOffset - minOffset, 1)) *
      (width - left - right);
  const y = (value) =>
    top + ((max - value) / (max - min)) * (height - top - bottom);

  const zeroX = x(0);
  const paths = lines
    .map((line) => {
      const sorted = [...line.points].sort((a, b) => a.offset - b.offset);
      const d = sorted
        .map(
          (point, i) =>
            `${i ? "L" : "M"} ${x(point.offset).toFixed(1)} ${y(point.value).toFixed(1)}`,
        )
        .join(" ");
      return `<path d="${d}" fill="none" stroke="${line.color}" stroke-width="2" vector-effect="non-scaling-stroke"><title>${escapeHtml(line.name)}</title></path>`;
    })
    .join("");

  const eventEndpoints = lines
    .map((line) => {
      const endpoint = [...line.points].sort((a, b) => a.offset - b.offset).at(-1);
      return `${line.name}: ${endpoint.value.toFixed(1)} at T${endpoint.offset >= 0 ? "+" : ""}${endpoint.offset}m`;
    })
    .join("; ");
  const a11y = chartA11y(
    el,
    `${metric.metric.name} historical event comparison`,
    `${metric.metric.name} event comparison. ${lines.length} event paths indexed to 100 at the anchor, covering T${minOffset} to T+${maxOffset} months. Endpoints: ${eventEndpoints}.`,
  );
  el.innerHTML = `${a11y.summaryHtml}<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" ${a11y.svgAttrs}>
    <line class="gridline" x1="${left}" y1="${y(100)}" x2="${width - right}" y2="${y(100)}"/>
    <line class="gridline" x1="${zeroX}" y1="${top}" x2="${zeroX}" y2="${height - bottom}"/>
    ${paths}
    <text x="${left}" y="${height - 10}" fill="currentColor" opacity=".55" font-size="10">T${minOffset}m</text>
    <text x="${zeroX}" y="${height - 10}" text-anchor="middle" fill="currentColor" opacity=".55" font-size="10">Anchor</text>
    <text x="${width - right}" y="${height - 10}" text-anchor="end" fill="currentColor" opacity=".55" font-size="10">T+${maxOffset}m</text>
  </svg>`;
}


function renderTaiwanEventSelector() {
  const select = $("#tw-event-metric");
  const mode = $("#tw-event-mode");
  if (!select || !mode) return;

  const metrics = [...state.metrics.values()]
    .filter(
      (metric) =>
        isTaiwanMetric(metric) &&
        usableObservationCount(metric) > 1,
    )
    .sort((a, b) => a.metric.name.localeCompare(b.metric.name));

  if (!metrics.length) {
    select.innerHTML = '<option value="">No Taiwan history</option>';
    renderTaiwanEvents(null, mode.value);
    return;
  }

  const previous = select.dataset.initialized === "true" ? select.value : "";
  select.innerHTML = [
    '<option value="">Select a Taiwan metric</option>',
    ...metrics.map(
      (metric) =>
        `<option value="${escapeHtml(metric.metric.id)}">${escapeHtml(metric.metric.name)}</option>`,
    ),
  ].join("");
  select.dataset.initialized = "true";
  if (previous && metrics.some((m) => m.metric.id === previous)) {
    select.value = previous;
  }

  const rerender = async () => {
    if (!select.value) {
      renderTaiwanEvents(null, mode.value);
      return;
    }
    try {
      const [metric] = await Promise.all([
        ensureMetricLoaded(select.value),
        ensureDeferredContext("taiwan"),
      ]);
      renderTaiwanEvents(metric, mode.value);
    } catch (error) {
      console.warn("Taiwan history load failed", select.value, error);
      $("#tw-event-list").innerHTML = "";
      $("#tw-event-chart").innerHTML =
        '<div class="empty-state compact">This Taiwan metric history could not be loaded.</div>';
    }
  };
  select.onchange = rerender;
  mode.onchange = rerender;

  if (previous && select.value) rerender();
  else renderTaiwanEvents(null, mode.value);
}

function renderTaiwanEvents(metric, mode = "normalized") {
  const list = $("#tw-event-list");
  const el = $("#tw-event-chart");
  if (!list || !el) return;

  if (!metric || !state.taiwanEvents.length) {
    list.innerHTML = "";
    el.innerHTML =
      '<div class="empty-state compact">Taiwan event definitions or metric history unavailable.</div>';
    return;
  }

  const eligibility = historicalAnalysisEligibility(metric);
  if (!eligibility.allowed && mode !== "raw") {
    list.innerHTML = "";
    el.innerHTML =
      `<div class="empty-state compact"><strong>Point-in-time Taiwan event comparison disabled.</strong><span>${escapeHtml(eligibility.reason)}. Raw retrospective history remains available.</span></div>`;
    return;
  }
  if (
    mode === "pit_percentile" &&
    !historicalPercentileAllowed(metric)
  ) {
    list.innerHTML = "";
    el.innerHTML =
      '<div class="empty-state compact">Point-in-time percentile mode is disabled because no eligible PIT percentile baseline is declared.</div>';
    return;
  }

  let eventMetric = metric;
  if (mode === "pit_percentile") {
    eventMetric = {
      ...metric,
      metric: {
        ...metric.metric,
        units: "percentile",
      },
      observations: strictPastPercentileSeries(metric),
    };
  }

  const retrospectiveObs = (eventMetric.observations || []).filter(
    (observation) => observation.value != null,
  );
  const obs =
    mode === "raw"
      ? retrospectiveObs
      : pointInTimeObservationSeries(eventMetric, retrospectiveObs);
  if (obs.length < 2) {
    list.innerHTML = "";
    el.innerHTML =
      '<div class="empty-state compact">Not enough Taiwan history for this comparison mode.</div>';
    return;
  }

  const coverageStart = Date.parse(
    mode === "raw"
      ? metric.coverage.history_start
      : (obs[0].availability_date || obs[0].date),
  );
  const colors = [
    "#5dc2aa",
    "#e7b75f",
    "#ff8278",
    "#7c9cff",
    "#b58cff",
    "#63b3ed",
    "#d98bc6",
    "#8fbf62",
  ];

  list.innerHTML = state.taiwanEvents
    .map((event, index) => {
      const anchorDate = event.anchor_date || metric.latest.as_of;
      const unavailable =
        !anchorDate || Date.parse(anchorDate) < coverageStart;
      return `<span class="event-pill ${unavailable ? "unavailable" : ""}" title="${escapeHtml(event.notes || "")}"><i class="event-dot" style="background:${colors[index % colors.length]}"></i>${escapeHtml(event.name)}</span>`;
    })
    .join("");

  const lines = [];
  state.taiwanEvents.forEach((event, index) => {
    const anchor = event.anchor_date || metric.latest.as_of;
    if (!anchor || Date.parse(anchor) < coverageStart) return;

    const anchorIdx = observationOnOrBeforeIndex(obs, anchor);
    if (anchorIdx < 0) return;

    const anchorValue = Number(obs[anchorIdx].value);
    if (!Number.isFinite(anchorValue)) return;
    if (mode === "normalized" && anchorValue === 0) return;

    const anchorDate = new Date(
      `${obs[anchorIdx].availability_date || obs[anchorIdx].date}T00:00:00Z`,
    );
    const pre = Number(event.window?.pre_months ?? 12);
    const post = Number(event.window?.post_months ?? 24);
    const points = [];

    for (const item of obs) {
      const offset = monthOffset(
        anchorDate,
        new Date(
          `${item.availability_date || item.date}T00:00:00Z`,
        ),
      );
      if (offset < -pre || offset > post) continue;

      const raw = Number(item.value);
      points.push({
        offset,
        value:
          mode === "normalized"
            ? (raw / anchorValue) * 100
            : raw,
      });
    }

    if (points.length > 1) {
      lines.push({
        name: event.name,
        points,
        pre,
        post,
        color: colors[index % colors.length],
      });
    }
  });

  if (!lines.length) {
    el.innerHTML =
      '<div class="empty-state compact">This Taiwan metric has no usable coverage for the configured events.</div>';
    return;
  }

  const width = 720;
  const height = 250;
  const left = 52;
  const right = 16;
  const top = 18;
  const bottom = 34;
  const minOffset = Math.min(...lines.map((line) => -line.pre));
  const maxOffset = Math.max(...lines.map((line) => line.post));
  const values = lines.flatMap((line) => line.points.map((point) => point.value));
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  }

  const x = (offset) =>
    left +
    ((offset - minOffset) / Math.max(maxOffset - minOffset, 1)) *
      (width - left - right);
  const y = (value) =>
    top + ((max - value) / (max - min)) * (height - top - bottom);

  const paths = lines
    .map((line) => {
      const d = [...line.points]
        .sort((a, b) => a.offset - b.offset)
        .map(
          (point, index) =>
            `${index ? "L" : "M"} ${x(point.offset).toFixed(1)} ${y(point.value).toFixed(1)}`,
        )
        .join(" ");
      return `<path d="${d}" fill="none" stroke="${line.color}" stroke-width="2" vector-effect="non-scaling-stroke"><title>${escapeHtml(line.name)}</title></path>`;
    })
    .join("");

  const referenceValue = mode === "normalized" ? 100 : null;
  const referenceLine =
    referenceValue != null && referenceValue >= min && referenceValue <= max
      ? `<line class="gridline" x1="${left}" y1="${y(referenceValue)}" x2="${width - right}" y2="${y(referenceValue)}"/>`
      : "";

  const unit =
    mode === "normalized"
      ? "index=100"
      : mode === "pit_percentile"
        ? "percentile"
        : eventMetric.metric.units;

  const taiwanEndpoints = lines
    .map((line) => {
      const endpoint = [...line.points].sort((a, b) => a.offset - b.offset).at(-1);
      return `${line.name}: ${endpoint.value.toFixed(1)} ${unit} at T${endpoint.offset >= 0 ? "+" : ""}${endpoint.offset}m`;
    })
    .join("; ");
  const a11y = chartA11y(
    el,
    `${metric.metric.name} Taiwan historical event comparison`,
    `${metric.metric.name} Taiwan event comparison in ${unit}. ${lines.length} event paths from T${minOffset} to T+${maxOffset} months. Endpoints: ${taiwanEndpoints}.`,
  );
  el.innerHTML = `${a11y.summaryHtml}<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" ${a11y.svgAttrs}>
    ${referenceLine}
    <line class="gridline" x1="${x(0)}" y1="${top}" x2="${x(0)}" y2="${height - bottom}"/>
    ${paths}
    <text x="${left - 5}" y="${top + 10}" text-anchor="end" fill="currentColor" opacity=".55" font-size="9">${escapeHtml(unit)}</text>
    <text x="${left}" y="${height - 10}" fill="currentColor" opacity=".55" font-size="10">T${minOffset}m</text>
    <text x="${x(0)}" y="${height - 10}" text-anchor="middle" fill="currentColor" opacity=".55" font-size="10">Anchor</text>
    <text x="${width - right}" y="${height - 10}" text-anchor="end" fill="currentColor" opacity=".55" font-size="10">T+${maxOffset}m</text>
  </svg>`;
}


function relatedBreadthStats(metric) {
  const id = metric.metric.id;
  const stats = [];

  const add = (metricId, label) => {
    const related = state.metrics.get(metricId);
    if (!related) return;
    stats.push({
      label,
      value: formatValue(related.latest?.value, related.metric.units),
      asOf: related.latest?.as_of || "—",
    });
  };

  if ([
    "nyse_new_52w_highs",
    "nyse_new_52w_lows",
    "nyse_net_new_52w_highs",
    "nyse_high_low_pct",
  ].includes(id)) {
    add("nyse_new_52w_highs", "52W highs");
    add("nyse_new_52w_lows", "52W lows");
    add("nyse_net_new_52w_highs", "Net highs");
    add("nyse_high_low_pct", "High-Low %");
  } else if ([
    "nyse_up_volume",
    "nyse_down_volume",
    "nyse_up_down_volume",
    "mrm_mcclellan_volume_oscillator",
    "mrm_mcclellan_volume_summation",
  ].includes(id)) {
    add("nyse_up_volume", "Up volume");
    add("nyse_down_volume", "Down volume");
    add("nyse_up_down_volume", "Up-Down volume");
    add("mrm_mcclellan_volume_oscillator", "McClellan oscillator");
    add("mrm_mcclellan_volume_summation", "Volume summation");
  } else if ([
    "sp500_above_20dma_pct",
    "sp500_above_50dma_pct",
    "sp500_above_200dma_pct",
  ].includes(id)) {
    add("sp500_above_20dma_pct", "% > 20DMA");
    add("sp500_above_50dma_pct", "% > 50DMA");
    add("sp500_above_200dma_pct", "% > 200DMA");
  } else if ([
    "tw_above_20dma_pct",
    "tw_above_50dma_pct",
    "tw_above_200dma_pct",
  ].includes(id)) {
    add("tw_above_20dma_pct", "TWSE % > 20DMA");
    add("tw_above_50dma_pct", "TWSE % > 50DMA");
    add("tw_above_200dma_pct", "TWSE % > 200DMA");
  } else if ([
    "tw_new_52w_highs",
    "tw_new_52w_lows",
    "tw_net_new_52w_highs",
    "tw_high_low_pct",
  ].includes(id)) {
    add("tw_new_52w_highs", "TWSE 52W highs");
    add("tw_new_52w_lows", "TWSE 52W lows");
    add("tw_net_new_52w_highs", "TWSE net highs");
    add("tw_high_low_pct", "TWSE High-Low %");
  } else if ([
    "nyse_advancing_issues",
    "nyse_declining_issues",
    "nyse_advance_decline_diff",
    "nyse_advance_decline_pct",
    "nyse_advance_decline_line",
  ].includes(id)) {
    add("nyse_advancing_issues", "Advancing");
    add("nyse_declining_issues", "Declining");
    add("nyse_advance_decline_diff", "A-D difference");
    add("nyse_advance_decline_pct", "A-D %");
  }

  return stats;
}

async function ensureMetricLoaded(id) {
  const existing = state.metrics.get(id);
  if (Array.isArray(existing?.observations)) return existing;

  if (state.metricLoads.has(id)) {
    return state.metricLoads.get(id);
  }

  const entry = (state.catalog?.metrics || []).find((item) => item.id === id);
  if (!entry) throw new Error(`metric ${id} is not present in the catalog`);

  const promise = (async () => {
    const url = new URL(entry.path.replace(/^\.\//, ""), METRIC_BASE);
    const response = await fetch(url, { cache: "no-cache" });
    if (!response.ok) throw new Error(`${id} HTTP ${response.status}`);
    const metric = await response.json();
    state.metrics.set(id, metric);
    return metric;
  })();

  state.metricLoads.set(id, promise);
  try {
    return await promise;
  } finally {
    state.metricLoads.delete(id);
  }
}

function setupDialogFocusManagement() {
  const dialog = $("#metric-dialog");
  if (!dialog || dialog.dataset.focusManaged === "true") return;
  dialog.dataset.focusManaged = "true";
  dialog.addEventListener("close", () => {
    const invoker = dialogInvoker;
    dialogInvoker = null;
    if (invoker && invoker.isConnected !== false && typeof invoker.focus === "function") {
      invoker.focus();
    }
  });
}

async function openMetric(id, invoker = document.activeElement) {
  const summary = state.metrics.get(id);
  if (!summary) return;

  const dialog = $("#metric-dialog");
  const context = beginnerContext[id];
  $("#dialog-pillar").textContent =
    pillarLabels[summary.metric.pillar] || summary.metric.pillar;
  $("#dialog-title").textContent = context?.plain_name || summary.metric.name;
  $("#dialog-summary").innerHTML =
    '<div class="detail-stat"><strong>Loading…</strong><span>Full metric history</span></div>';
  $("#dialog-chart").innerHTML =
    '<div class="empty-state compact">Loading full metric history…</div>';
  $("#dialog-source").innerHTML = "";
  if (invoker && typeof invoker.focus === "function") {
    dialogInvoker = invoker;
  }
  if (!dialog.open) {
    dialog.showModal();
    $("#dialog-close")?.focus();
  }

  let metric;
  try {
    metric = await ensureMetricLoaded(id);
  } catch (error) {
    console.warn("metric detail load failed", id, error);
    $("#dialog-chart").innerHTML =
      '<div class="empty-state compact">Detailed history could not be loaded. The overview remains available.</div>';
    $("#dialog-source").textContent = String(error?.message || error);
    return;
  }

  const pct = rollingPercentile(metric);
  const p = percentilePresentation(metric, pct);
  const change = recentChange(metric);
  const related = relatedBreadthStats(metric);
  const dateLabel = context?.date_semantics === "effective_vs_verified"
    ? "Effective/change date"
    : "Source observation";
  const baseStats = [
    { value: formatValue(metric.latest.value, metric.metric.units), label: "Current value" },
    { value: formatChange(change), label: "Last observation" },
    { value: p.value, label: p.label },
    { value: escapeHtml(metric.latest.as_of || "—"), label: dateLabel },
  ];
  const stats = related.length
    ? related.map((item) => ({ value: item.value, label: `${item.label} · ${item.asOf}` }))
    : baseStats;
  $("#dialog-summary").innerHTML = stats
    .map((item) => `<div class="detail-stat"><strong>${item.value}</strong><span>${escapeHtml(item.label)}</span></div>`)
    .join("");

  fullChart(metric, $("#dialog-chart"), { height: 390 });
  const membershipContext =
    metric.source?.membership_mode
      ? ` · membership: ${escapeHtml(metric.source.membership_mode)}`
      : "";
  const verifiedLabel = context?.date_semantics === "effective_vs_verified"
    ? "Source verified"
    : "Snapshot fetched";
  $("#dialog-source").innerHTML =
    `${metricContextGuide(metric)}
     ${pct == null ? "" : `<p class="meta">${escapeHtml(p.sentence)} ${escapeHtml(percentileCaveatSentence(metric))}</p>`}
     <div class="source-meta">Source: <a class="source-link" href="${escapeHtml(metric.source.url)}" target="_blank" rel="noopener">${escapeHtml(metric.source.provider)} — ${escapeHtml(metric.source.dataset)}</a><br>
     ${verifiedLabel}: ${escapeHtml(metric.latest.fetched_at || "—")} · freshness: ${escapeHtml(effectiveFreshness(metric).state)} · history starts: ${escapeHtml(metric.coverage.history_start || "—")}${membershipContext}</div>`;
}


function flattenRuleDetails(rule, out = []) {
  if (!rule) return out;
  if (rule.children) {
    rule.children.forEach((child) => flattenRuleDetails(child, out));
    return out;
  }
  out.push({
    type: rule.type || null,
    metric: rule.metric || null,
    label: rule.label || rule.type || "rule",
    reason: rule.reason || "",
    value: rule.value ?? null,
    threshold: rule.threshold ?? null,
    periods: rule.periods ?? null,
    asOf: rule.as_of || null,
    status: rule.status || "unknown",
  });
  return out;
}

function effectiveConditionStatus(condition) {
  const staleInputs = (condition.metrics || [])
    .map((id) => state.metrics.get(id))
    .filter(Boolean)
    .filter((metric) => effectiveFreshness(metric).state !== "fresh");

  const missingInputs = (condition.metrics || []).filter(
    (id) => !state.metrics.has(id),
  );

  if (staleInputs.length || missingInputs.length) return "unknown";
  return condition.status || "unknown";
}

function renderSignals() {
  const summaryEl = $("#signal-summary");
  const grid = $("#signal-grid");
  const chart = $("#signal-history-chart");
  const snapshot = state.signals;

  if (!snapshot?.current) {
    summaryEl.innerHTML =
      '<div class="empty-state compact">Deleveraging Watch is unavailable in the current published snapshot.</div>';
    grid.innerHTML = "";
    chart.innerHTML =
      '<div class="empty-state compact">Historical signal state is unavailable.</div>';
    return;
  }

  const displayConditions = (snapshot.current.conditions || []).map((condition) => ({
    ...condition,
    displayStatus: effectiveConditionStatus(condition),
  }));
  const summary = {
    active: displayConditions.filter((c) => c.displayStatus === "active").length,
    inactive: displayConditions.filter((c) => c.displayStatus === "inactive").length,
    unknown: displayConditions.filter((c) => c.displayStatus === "unknown").length,
    total: displayConditions.length,
  };
  summary.known = summary.active + summary.inactive;

  summaryEl.innerHTML = `
    <div class="signal-summary-main">
      <strong>${summary.known} of ${summary.total} checks known</strong>
      <span class="meta">· ${summary.active} active · ${summary.unknown} unavailable/unknown</span>
    </div>
    <span class="meta">Evaluated ${escapeHtml(snapshot.current.as_of || "—")} · unknown is not inactive</span>
  `;

  grid.innerHTML = displayConditions
    .map((condition) => {
      const beginner = signalBeginnerContext[condition.id] || {};
      const details = flattenRuleDetails(condition.rules);
      const detailText = details.map(formatRuleDetail).join("<br>");
      const caveat = condition.displayStatus === "unknown"
        ? "Required public evidence is unavailable; this remains unknown rather than safe."
        : (beginner.caveat || "");
      return `<article class="signal-card" data-status="${escapeHtml(condition.displayStatus)}">
        <span class="signal-status">${escapeHtml(condition.displayStatus)}</span>
        <h3>${escapeHtml(beginner.plain_name || condition.name)}</h3>
        <p>${escapeHtml(beginner.description || condition.description || "")}</p>
        ${caveat ? `<p><strong>Caveat:</strong> ${escapeHtml(caveat)}</p>` : ""}
        <div class="signal-rule">${detailText}</div>
      </article>`;
    })
    .join("");

  renderSignalHistory(snapshot, chart);
}

function renderSignalHistory(snapshot, element) {
  const history = snapshot.history || [];
  if (history.length < 2) {
    element.innerHTML =
      '<div class="empty-state compact">Not enough historical signal states.</div>';
    return;
  }

  const width = 1000;
  const height = 250;
  const left = 48;
  const right = 22;
  const top = 20;
  const bottom = 38;
  const firstTs = Date.parse(history[0].date);
  const lastTs = Date.parse(history.at(-1).date);
  const span = Math.max(lastTs - firstTs, 1);
  const total = Math.max(...history.map((point) => point.summary.total || 0), 1);

  const x = (dateValue) =>
    left + ((Date.parse(dateValue) - firstTs) / span) * (width - left - right);
  const y = (value) =>
    top + ((total - value) / total) * (height - top - bottom);

  const activePath = history
    .map(
      (point, index) =>
        `${index ? "L" : "M"} ${x(point.date).toFixed(1)} ${y(point.summary.active).toFixed(1)}`,
    )
    .join(" ");
  const unknownPath = history
    .map(
      (point, index) =>
        `${index ? "L" : "M"} ${x(point.date).toFixed(1)} ${y(point.summary.unknown).toFixed(1)}`,
    )
    .join(" ");

  const grids = Array.from({ length: total + 1 }, (_, value) => {
    const yy = y(value);
    return `<line class="gridline" x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}"/>
      <text x="${left - 8}" y="${yy + 4}" text-anchor="end" fill="currentColor" opacity=".5" font-size="10">${value}</text>`;
  }).join("");

  const eventLines = state.events
    .filter((event) => event.anchor_date)
    .filter((event) => {
      const ts = Date.parse(event.anchor_date);
      return ts >= firstTs && ts <= lastTs;
    })
    .map((event) => {
      const xx = x(event.anchor_date);
      return `<line class="signal-event-line" x1="${xx}" y1="${top}" x2="${xx}" y2="${height - bottom}">
        <title>${escapeHtml(event.name)}</title>
      </line>`;
    })
    .join("");

  const latest = history.at(-1);
  const a11y = chartA11y(
    element,
    "Historical Deleveraging Watch condition counts",
    `Deleveraging Watch history from ${history[0].date} to ${latest.date}. Latest: ${latest.summary.active} active, ${latest.summary.unknown} unknown, ${latest.summary.total} total conditions.`,
  );
  element.innerHTML = `${a11y.summaryHtml}<svg class="history-svg signal-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" ${a11y.svgAttrs}>
    ${grids}
    ${eventLines}
    <path class="active-line" d="${activePath}"><title>Active conditions</title></path>
    <path class="unknown-line" d="${unknownPath}"><title>Unknown conditions</title></path>
    <text x="${left}" y="${height - 11}" fill="currentColor" opacity=".55" font-size="10">${escapeHtml(history[0].date)}</text>
    <text x="${width - right}" y="${height - 11}" text-anchor="end" fill="currentColor" opacity=".55" font-size="10">${escapeHtml(latest.date)}</text>
  </svg>`;
}

function globalFreshnessSummary(metrics) {
  const counts = {
    fresh: 0,
    stale: 0,
    missing: 0,
    error: 0,
    insufficient_data: 0,
  };

  for (const metric of metrics) {
    const freshness = effectiveFreshness(metric).state;
    if (freshness in counts) counts[freshness] += 1;
    else counts.error += 1;
  }

  if (!metrics.length) {
    return {
      counts,
      className: "badge badge-missing",
      text: "No production snapshot",
    };
  }

  const parts = [
    counts.error ? `${counts.error} error` : "",
    counts.missing ? `${counts.missing} missing` : "",
    counts.stale ? `${counts.stale} stale` : "",
    counts.insufficient_data
      ? `${counts.insufficient_data} insufficient data`
      : "",
  ].filter(Boolean);

  if (!parts.length) {
    return {
      counts,
      className: "health-passive",
      text: "Data current",
    };
  }

  return {
    counts,
    className:
      counts.error || counts.missing
        ? "badge badge-error"
        : "badge badge-stale",
    text: parts.join(" · "),
  };
}

function updateGlobalFreshness() {
  const badge = $("#global-freshness");
  const summary = globalFreshnessSummary([...state.metrics.values()]);
  badge.className = summary.className;
  badge.textContent = summary.text;
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("mrm-theme", theme);
}

function initTheme() {
  const saved = localStorage.getItem("mrm-theme");
  const system = window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
  applyTheme(saved || system);

  $("#theme-toggle").onclick = () =>
    applyTheme(
      document.documentElement.dataset.theme === "dark" ? "light" : "dark",
    );
}


async function fetchDeferredJson(url, options = null) {
  const optionalNotFound = options?.optionalNotFound === true;
  const response = await fetch(url);
  if (response.ok) return await response.json();
  if (optionalNotFound && response.status === 404) return null;
  throw new Error(`${url} HTTP ${response.status}`);
}

async function ensureDeferredContext(kind) {
  if (state.deferredLoaded.has(kind)) return;
  if (state.deferredLoads.has(kind)) return state.deferredLoads.get(kind);

  const promise = (async () => {
    if (kind === "events") {
      const payload = await fetchDeferredJson(EVENTS_URL);
      state.events = payload?.events || [];
    } else if (kind === "trend") {
      const [config, study] = await Promise.all([
        fetchDeferredJson(MA_BREADTH_CONFIG_URL),
        fetchDeferredJson(MA_BREADTH_STUDY_URL, { optionalNotFound: true }),
      ]);
      state.maBreadthConfig = config;
      state.maBreadthStudy = study;
    } else if (kind === "taiwan") {
      const [macro, taiwanEvents, cbcRate, fedRate] = await Promise.all([
        fetchDeferredJson(TAIWAN_MACRO_REGIME_URL, { optionalNotFound: true }),
        fetchDeferredJson(TAIWAN_EVENTS_URL),
        fetchDeferredJson(TAIWAN_CBC_RATE_REGIME_URL, { optionalNotFound: true }),
        fetchDeferredJson(FED_RATE_REGIME_URL, { optionalNotFound: true }),
      ]);
      state.taiwanMacroRegime = macro;
      state.taiwanEvents = taiwanEvents?.events || [];
      state.taiwanCbcRateRegime = cbcRate;
      state.fedRateRegime = fedRate;
    } else {
      throw new Error(`unknown deferred context kind: ${kind}`);
    }

    // Mark loaded only after every required request for this kind succeeds.
    // Optional 404s are represented as null and still count as a successful load.
    state.deferredLoaded.add(kind);
  })();

  state.deferredLoads.set(kind, promise);
  try {
    return await promise;
  } finally {
    // A rejected request is intentionally not added to deferredLoaded, so the
    // next call can retry within the same page session.
    state.deferredLoads.delete(kind);
  }
}

function observeSectionOnce(selector, onVisible) {
  const element = $(selector);
  if (!element) return;

  let complete = false;
  let inFlight = false;
  let observer = null;

  const attempt = async () => {
    if (complete || inFlight) return;
    inFlight = true;
    try {
      await onVisible();
      complete = true;
      observer?.disconnect();
      element.removeEventListener("pointerenter", attempt);
      element.removeEventListener("focusin", attempt);
    } catch (error) {
      // Keep the observer/listeners active. Scrolling away/back or interacting
      // again retries the deferred load instead of caching a transient failure.
      console.warn("deferred context load failed", selector, error);
    } finally {
      inFlight = false;
    }
  };

  if (!("IntersectionObserver" in window)) {
    element.addEventListener("pointerenter", attempt);
    element.addEventListener("focusin", attempt);
    return;
  }

  observer = new IntersectionObserver(
    (entries) => {
      if (entries.some((entry) => entry.isIntersecting)) attempt();
    },
    { rootMargin: "200px 0px" },
  );
  observer.observe(element);
}

function setupDeferredContextLoading() {
  observeSectionOnce("#trend-participation-section", async () => {
    await ensureDeferredContext("trend");
    renderTrendParticipation();
  });
  observeSectionOnce("#taiwan-detail", async () => {
    await ensureDeferredContext("taiwan");
    renderTaiwanMarket();
  });
  observeSectionOnce("#signals-detail", async () => {
    await ensureDeferredContext("events");
    renderSignals();
  });
  observeSectionOnce("#research", () => ensureDeferredContext("events"));
}


async function loadData() {
  state.metrics.clear();
  state.metricLoads.clear();
  state.deferredLoads.clear();
  state.deferredLoaded.clear();
  state.events = [];
  state.maBreadthConfig = null;
  state.maBreadthStudy = null;
  state.taiwanMacroRegime = null;
  state.taiwanEvents = [];
  state.taiwanCbcRateRegime = null;
  state.fedRateRegime = null;

  try {
    const [catalogResp, overviewResp, signalsResp, refreshResp] = await Promise.all([
      fetch(CATALOG_URL, { cache: "no-store" }),
      fetch(OVERVIEW_URL, { cache: "no-store" }),
      fetch(SIGNALS_URL, { cache: "no-store" }).catch(() => null),
      fetch(REFRESH_REPORT_URL, { cache: "no-store" }).catch(() => null),
    ]);
    if (!catalogResp.ok) throw new Error(`catalog HTTP ${catalogResp.status}`);
    if (!overviewResp.ok) throw new Error(`overview HTTP ${overviewResp.status}`);

    state.catalog = await catalogResp.json();
    const overview = await overviewResp.json();
    for (const metric of overview.metrics || []) {
      state.metrics.set(metric.metric.id, metric);
    }

    state.signals = signalsResp?.ok ? await signalsResp.json() : null;
    state.refreshReport = refreshResp?.ok ? await refreshResp.json() : null;
    state.refreshErrors.clear();
    for (const result of state.refreshReport?.results || []) {
      if (result.status === "error" && result.metric) {
        state.refreshErrors.set(result.metric, result);
      }
    }

    $("#data-generated").textContent = overview.generated_at
      ? `Overview generated ${overview.generated_at}`
      : "Overview snapshot loaded";
  } catch (error) {
    console.error(error);
    $("#data-generated").textContent = "Snapshot load failed";
  }

  renderOverview();
  renderMetrics();
  renderTrendParticipation();
  renderTaiwanMarket();
  renderSignals();
  renderHistorySelector();
  renderRegime();
  renderCoverage();
  updateGlobalFreshness();
  setupDeferredContextLoading();
}

initTheme();
setupDialogFocusManagement();
$("#refresh-view").addEventListener("click", loadData);
$("#ma-bands-toggle")?.addEventListener("change", renderTrendParticipationChart);
$("#ma-spx-toggle")?.addEventListener("change", renderTrendParticipationChart);
loadData();
