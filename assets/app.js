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

const I18N = globalThis.MRMI18n;
if (!I18N) throw new Error("MRM i18n runtime is not loaded");
const {
  t,
  getLocale,
  setLocale,
  initLocale,
  localeNumber,
  localeDate,
  localeOrdinal,
  localizedMetricContext,
  localizedSignalContext,
} = I18N;

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

function historyModeLabel(mode) {
  const key = {
    absolute: "research.absolute",
    pit_percentile: "research.pit_percentile",
    rolling_percentile: "research.rolling_percentile",
    rate_change: "research.rate_change",
  }[mode] || "research.absolute";
  return t(key);
}

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

function metricContext(id) {
  return localizedMetricContext(id, beginnerContext[id] || null);
}

function signalContext(id) {
  return localizedSignalContext(id, signalBeginnerContext[id] || null);
}

function pillarLabel(id) {
  return t(`pillar.${id}`) === `pillar.${id}` ? id : t(`pillar.${id}`);
}

function applyStaticTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-locale]").forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.locale === getLocale()),
    );
  });
}

function rerenderLocalizedUi() {
  applyStaticTranslations();
  if (!state.catalog && !state.metrics.size) return;
  renderOverview();
  renderMetrics();
  renderTrendParticipation();
  renderTaiwanMarket();
  renderSignals();
  renderHistorySelector();
  renderRegime();
  renderCoverage();
  updateGlobalFreshness();
}

function setupLanguage() {
  initLocale();
  applyStaticTranslations();
  document.querySelectorAll("[data-locale]").forEach((button) => {
    button.addEventListener("click", () => {
      if (button.dataset.locale === getLocale()) return;
      setLocale(button.dataset.locale);
      rerenderLocalizedUi();
    });
  });
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
    if (Math.abs(v) >= 1_000_000) {
      return `$${localeNumber(v / 1_000_000, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}T`;
    }
    if (Math.abs(v) >= 1_000) {
      return `$${localeNumber(v / 1_000, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}B`;
    }
    return `$${localeNumber(v, { maximumFractionDigits: 0 })}M`;
  }
  if (units === "percent") {
    const digits = Math.abs(v) >= 10 ? 1 : 2;
    return `${localeNumber(v, { minimumFractionDigits: digits, maximumFractionDigits: digits })}%`;
  }
  if (units === "percentile") return localeOrdinal(v);
  if (units === "ratio") return `${localeNumber(v, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}×`;
  if (units === "binary") return v ? t("common.yes") : t("common.no");
  if (units === "basis points") {
    return `${v >= 0 ? "+" : ""}${localeNumber(v, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} bp`;
  }
  return localeNumber(v, {
    maximumFractionDigits: Math.abs(v) >= 1000 ? 1 : 2,
  });
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
  const key = `common.${status}`;
  const label = t(key) === key ? status.replaceAll("_", " ") : t(key);
  return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
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
  return localeOrdinal(value);
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
    return t("percentile.last_years", {
      count: localeNumber(rounded),
      unit: t(rounded === 1 ? "percentile.year" : "percentile.years"),
    });
  }
  return t("percentile.last_observations", { count: localeNumber(window) });
}

function percentilePresentation(metric, value = rollingPercentile(metric)) {
  if (value == null) {
    return {
      value: "—",
      label: t("percentile.not_enough"),
      sentence: t("percentile.unavailable_sentence"),
    };
  }
  const rounded = Math.round(value);
  const window = rollingWindowLabel(metric);
  return {
    value: ordinal(rounded),
    label: t("percentile.vs", { window }),
    sentence: t("percentile.sentence", {
      percent: localeNumber(rounded),
      window,
    }),
  };
}

function metricDateLine(metric) {
  const context = metricContext(metric?.metric?.id);
  const asOf = metric?.latest?.as_of || "unknown";
  if (context?.date_semantics === "effective_vs_verified") {
    const verified = String(metric?.latest?.fetched_at || "").slice(0, 10) || "unknown";
    return `${t("common.effective_since", { date: localeDate(asOf) })} · ${t("common.source_verified", { date: localeDate(verified) })}`;
  }
  return t("common.as_of", { date: localeDate(asOf) });
}

function metricContextGuide(metric) {
  const context = metricContext(metric?.metric?.id);
  if (!context) return "";
  const reference = context.important_reference_level
    ? `<dt>${escapeHtml(t("guide.reference"))}</dt><dd>${escapeHtml(context.important_reference_level)}</dd>`
    : "";
  const caveat = dynamicMetricCaveat(metric) || context.important_caveat;
  return `<div class="context-guide">
    <h3>${escapeHtml(context.plain_name)}</h3>
    <p>${escapeHtml(context.what_it_measures)}</p>
    <dl>
      <dt>${escapeHtml(t("guide.why"))}</dt><dd>${escapeHtml(context.why_it_matters)}</dd>
      <dt>${escapeHtml(t("guide.how"))}</dt><dd>${escapeHtml(context.how_to_read)}</dd>
      <dt>${escapeHtml(t("guide.direction"))}</dt><dd>${escapeHtml(context.higher_lower_or_contextual)}</dd>
      ${reference}
      <dt>${escapeHtml(t("guide.caveat"))}</dt><dd>${escapeHtml(caveat)}</dd>
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
    parts.push(t("context.only"));
  }
  if (rollingPercentileSemantics(metric) === "retrospective") {
    parts.push(t("context.retrospective"));
  }
  return parts.length ? ` · ${parts.join(" · ")}` : "";
}

function percentileCaveatSentence(metric) {
  const parts = [];
  if (metric?.metric?.polarity === "contextual") {
    parts.push(
      getLocale() === "zh-TW"
        ? "這個排名只供情境參考，不代表風險方向。"
        : "This rank is context only; it is not a risk direction.",
    );
  }
  if (rollingPercentileSemantics(metric) === "retrospective") {
    parts.push(
      getLocale() === "zh-TW"
        ? "這是回溯性的目前排名，不適合歷史 PIT / 回測使用。"
        : "This is a retrospective current rank and is not safe for historical PIT/backtest use.",
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
  return t("margin.slowed_evidence", {
    value: localeNumber(Math.abs(value), { minimumFractionDigits: 1, maximumFractionDigits: 1 }),
    periods: localeNumber(periods),
  });
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
  if (breadth.state === "missing") return t("breadth.no_sessions");
  if (breadth.state === "snapshot_only") return t("breadth.one_session");
  if (breadth.state === "history_building") {
    return t("breadth.history_building", { count: localeNumber(breadth.observations) });
  }
  if (breadth.state === "not_current") {
    return t("breadth.not_current", {
      state: t(`common.${breadth.freshness}`),
    });
  }
  return null;
}

function formatRuleDetail(detail) {
  const statusKey = `common.${String(detail.status || "unknown").replaceAll(" ", "_")}`;
  const status = t(statusKey) === statusKey ? detail.status : t(statusKey);
  const parts = [`${detail.label}: ${status}`];
  if (typeof detail.value === "number" && Number.isFinite(detail.value)) {
    const unit =
      detail.type === "delta_periods_below" && detail.metric === "finra_margin_debt_yoy_pct"
        ? " pp"
        : "";
    parts.push(
      t("rule.observed", {
        value: localeNumber(detail.value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
        unit,
      }),
    );
  }
  if (detail.asOf) parts.push(t("rule.as_of", { date: localeDate(detail.asOf) }));
  const line = escapeHtml(parts.join(" · "));
  return detail.reason
    ? `${line}<br><span class="signal-rule-reason">${escapeHtml(detail.reason)}</span>`
    : line;
}

function setSnapshotCard(kind, status, headline, facts = [], displayState = "normal") {
  const card = document.querySelector(`[data-overview-card="${kind}"]`);
  const statusEl = $(`#overview-${kind}-status`);
  const valueEl = $(`#overview-${kind}-value`);
  const factsEl = $(`#overview-${kind}-sub`);
  if (!card || !statusEl || !valueEl || !factsEl) return;

  card.dataset.state = displayState;
  statusEl.textContent = status;
  valueEl.textContent = headline;

  const compactFacts = facts.filter(Boolean).slice(0, 2);
  factsEl.innerHTML = compactFacts.length
    ? compactFacts.map((fact) => `<span>${escapeHtml(fact)}</span>`).join("")
    : `<span>${escapeHtml(t("metric.no_support"))}</span>`;
}

function setOverviewHealth(headline, detail, displayState = "normal") {
  const strip = $("#overview-health-strip");
  const stateEl = $("#overview-health-state");
  const detailEl = $("#overview-health-detail");
  if (!strip || !stateEl || !detailEl) return;

  strip.dataset.state = displayState;
  stateEl.textContent = headline;
  detailEl.textContent = detail;
}


function setDecisionThesis(title, summary, confidence, evidence = [], triggers = [], displayState = "normal") {
  const thesis = $("#decision-thesis");
  const titleEl = $("#overview-thesis-title");
  const summaryEl = $("#overview-thesis-summary");
  const confidenceEl = $("#overview-thesis-confidence");
  const evidenceEl = $("#overview-thesis-evidence");
  const triggersEl = $("#overview-thesis-triggers");
  if (!thesis || !titleEl || !summaryEl || !confidenceEl || !evidenceEl || !triggersEl) return;

  thesis.dataset.confidence = displayState;
  titleEl.textContent = title;
  summaryEl.textContent = summary;
  confidenceEl.textContent = confidence;
  evidenceEl.innerHTML = evidence
    .filter(Boolean)
    .slice(0, 4)
    .map((item) => `<span class="thesis-chip">${escapeHtml(item)}</span>`)
    .join("");

  triggersEl.innerHTML = triggers
    .filter((item) => item?.text)
    .slice(0, 3)
    .map((item) => `<div class="trigger-item"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.text)}</strong></div>`)
    .join("") || `<span class="trigger-item">${escapeHtml(t("rule.no_threshold"))}</span>`;
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
  const context = metricContext(metric.metric.id);
  const title = context?.plain_name || metric.metric.name;
  const contextOnly = pct != null ? percentileContextSuffix(metric) : "";

  return `<article class="panel metric-card" data-metric-id="${escapeHtml(metric.metric.id)}" role="button" tabindex="0" aria-label="${escapeHtml(t("metric.open_aria", { name: title }))}">
    <div class="metric-card-top">
      <div>
        <p class="eyebrow">${escapeHtml(pillarLabel(metric.metric.pillar))}</p>
        <h3>${escapeHtml(title)}</h3>
      </div>
      ${freshnessBadge(metric)}
    </div>
    <div class="metric-value">${formatValue(metric.latest?.value, metric.metric.units)}</div>
    <div class="metric-unit">${escapeHtml(metricDateLine(metric))} · ${escapeHtml(metric.metric.units)}</div>
    <div class="metric-context">
      <div class="context-chip"><strong>${cText}</strong><span>${escapeHtml(t("metric.last_observation"))}</span></div>
      <div class="context-chip"><strong>${p.value}</strong><span>${escapeHtml(p.label)}${contextOnly}</span></div>
    </div>
    ${sparkline(metric)}
    <div class="metric-card-bottom">
      <span class="meta">${escapeHtml(localeDate(metric.coverage?.history_start))} → ${escapeHtml(localeDate(metric.coverage?.history_end))}</span>
      <span class="meta">${escapeHtml(t(context ? "metric.open_explain" : "metric.open_history"))}</span>
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

  const stressFacts = [];
  if (nfci) {
    const nfciValue = Number(nfci.latest?.value);
    stressFacts.push(
      Number.isFinite(nfciValue)
        ? t(nfciValue > 0 ? "overview.conditions_tighter" : "overview.conditions_looser")
        : t("overview.financial_available"),
    );
  }
  if (vix) {
    const percentile = percentilePresentation(vix);
    stressFacts.push(
      `VIX ${formatValue(vix.latest?.value, vix.metric.units)}${percentile.value !== "—" ? ` · ${t("common.percentile_short", { value: percentile.value })}` : ""}`,
    );
  }
  setSnapshotCard(
    "stress",
    t(stressUnknown ? "common.data_gap" : stressActive ? "common.elevated" : "common.clear"),
    t(stressUnknown ? "overview.known_gauges_calm" : stressActive ? "overview.stress_elevated" : "overview.stress_contained"),
    stressFacts,
    stressUnknown ? "gap" : stressActive ? "watch" : "normal",
  );

  const marginSignal = signalCondition("margin_debt_rollover");
  const marginStatus = marginSignal ? effectiveConditionStatus(marginSignal) : "unknown";
  const yoy = Number(marginYoy?.latest?.value);
  const marginPct = margin ? percentilePresentation(margin) : null;
  const leverageReady = Boolean(margin && marginYoy);
  const leverageFacts = [];
  if (margin) {
    leverageFacts.push(
      `${formatValue(margin.latest?.value, margin.metric.units)}${marginPct?.value && marginPct.value !== "—" ? ` · ${t("common.percentile_context", { value: marginPct.value })}` : ""}`,
    );
  }
  if (marginYoy) {
    leverageFacts.push(t("overview.yoy", { value: formatValue(marginYoy.latest?.value, "percent") }));
  }
  const slowing = marginStatus === "active" && Number.isFinite(yoy) && yoy > 0;
  setSnapshotCard(
    "leverage",
    t(!leverageReady ? "common.data_gap" : slowing ? "common.watch" : "common.context"),
    t(!leverageReady ? "overview.incomplete_read" : slowing ? "overview.high_growth_slowing" : "overview.leverage_context"),
    leverageFacts,
    !leverageReady ? "gap" : slowing ? "watch" : "normal",
  );

  const conditions = (state.signals?.current?.conditions || []).map((condition) => ({
    ...condition,
    displayStatus: effectiveConditionStatus(condition),
  }));
  const known = conditions.filter((condition) => condition.displayStatus !== "unknown").length;
  const activeConditions = conditions.filter((condition) => condition.displayStatus === "active");
  const active = activeConditions.length;
  const unknown = conditions.filter((condition) => condition.displayStatus === "unknown").length;
  const total = conditions.length;
  const activeName = activeConditions[0]
    ? (activeConditions[0].id === "margin_debt_rollover"
        ? t("overview.margin_momentum")
        : signalContext(activeConditions[0].id)?.plain_name || activeConditions[0].name)
    : null;

  const deleveragingFacts = [];
  if (activeName) deleveragingFacts.push(activeName);
  if (total) {
    deleveragingFacts.push(t("overview.usable_unknown", {
      known: localeNumber(known),
      total: localeNumber(total),
      unknown: localeNumber(unknown),
    }));
  }
  setSnapshotCard(
    "deleveraging",
    !total
      ? t("common.data_gap")
      : active
        ? `${localeNumber(active)} ${t("common.active").toUpperCase()}`
        : unknown
          ? t("common.partial")
          : t("common.clear"),
    t(!total
      ? "overview.no_signal_read"
      : (active && unknown)
        ? "overview.not_confirmed"
        : active
          ? "overview.delev_signs"
          : "overview.no_confirmation"),
    deleveragingFacts,
    !total ? "gap" : active ? "watch" : unknown ? "gap" : "normal",
  );

  const taiexFreshness = effectiveFreshness(taiex).state;
  const breadth = taiwanBreadthState(twBreadth);
  const taiwanFacts = [];
  if (taiex) {
    taiwanFacts.push(`TAIEX ${formatValue(taiex.latest?.value, taiex.metric.units)}`);
  }
  if (twBreadth && breadth.state !== "missing") {
    const unit = t(breadth.observations === 1 ? "overview.session" : "overview.sessions_plural");
    taiwanFacts.push(t("overview.ad_sessions", {
      value: formatValue(twBreadth.latest?.value, "percent"),
      count: localeNumber(breadth.observations),
      unit,
    }));
  } else {
    taiwanFacts.push(t("overview.breadth_unavailable"));
  }

  const taiwanMissing = !taiex || ["missing", "error"].includes(taiexFreshness);
  const taiwanNeedsAttention =
    !taiwanMissing &&
    (taiexFreshness !== "fresh" ||
      ["missing", "not_current", "snapshot_only", "history_building"].includes(breadth.state));
  let taiwanStatus = t("common.current");
  let taiwanHeadline = t("overview.market_read");
  let taiwanState = "normal";
  if (taiwanMissing) {
    taiwanStatus = t("common.data_gap");
    taiwanHeadline = t("overview.no_current_call");
    taiwanState = "gap";
  } else if (taiexFreshness !== "fresh") {
    const freshnessKey = `common.${taiexFreshness}`;
    taiwanStatus = t(freshnessKey) === freshnessKey ? taiexFreshness : t(freshnessKey);
    taiwanHeadline = t("overview.no_current_call");
    taiwanState = "watch";
  } else if (taiwanNeedsAttention) {
    taiwanStatus = t("common.partial");
    taiwanHeadline = t("overview.price_current");
    taiwanState = "watch";
  }
  setSnapshotCard("taiwan", taiwanStatus, taiwanHeadline, taiwanFacts, taiwanState);

  const metrics = [...state.metrics.values()];
  const health = globalFreshnessSummary(metrics);
  const snapshotDate = String(
    state.catalog?.generated_at || state.refreshReport?.generated_at || "",
  ).slice(0, 10);
  const healthParts = [];
  if (health.counts.error) healthParts.push(t("health.error_count", { count: localeNumber(health.counts.error) }));
  if (health.counts.missing) healthParts.push(t("health.missing_count", { count: localeNumber(health.counts.missing) }));
  if (health.counts.stale) healthParts.push(t("health.stale_count", { count: localeNumber(health.counts.stale) }));
  if (health.counts.insufficient_data) {
    healthParts.push(t("health.insufficient_count", { count: localeNumber(health.counts.insufficient_data) }));
  }
  if (unknown) healthParts.push(t("health.unknown_checks", { count: localeNumber(unknown) }));
  if (snapshotDate) healthParts.push(t("health.snapshot", { date: localeDate(snapshotDate) }));

  const healthHasHardGap = Boolean(health.counts.error || health.counts.missing);
  const healthNeedsRefresh = Boolean(health.counts.stale);
  const healthHasEvidenceGap = Boolean(unknown);
  const marginRank = margin ? rollingPercentile(margin) : null;
  const leverageElevated = Number.isFinite(marginRank) && marginRank >= 90;

  let thesisTitle;
  if (stressActive) {
    thesisTitle = t(active ? "thesis.stress_rising_delev" : "thesis.stress_rising_no_delev");
  } else if (slowing) {
    thesisTitle = t("thesis.leverage_rollover");
  } else if (leverageElevated) {
    thesisTitle = t("thesis.leverage_stretched");
  } else if (stressUnknown) {
    thesisTitle = t("thesis.known_calm_incomplete");
  } else {
    thesisTitle = t("thesis.no_stress_confirmation");
  }

  const thesisParts = [];
  thesisParts.push(
    t(stressActive
      ? "thesis.stress_elevated"
      : stressUnknown
        ? "thesis.stress_known_calm_partial"
        : "thesis.stress_not_elevated"),
  );
  if (Number.isFinite(yoy)) {
    thesisParts.push(
      t(slowing ? "thesis.margin_slowing" : "thesis.margin_growth", {
        yoy: formatValue(yoy, "percent"),
      }),
    );
  }
  if (total) {
    thesisParts.push(t("thesis.delev_coverage", {
      known: localeNumber(known),
      total: localeNumber(total),
      active: localeNumber(active),
      verb: t(active === 1 ? "thesis.is" : "thesis.are"),
    }).replace(/\s+([。,.])/g, "$1").trim());
  }

  let thesisConfidence = t("thesis.high");
  let thesisState = "normal";
  if (!total || unknown >= Math.ceil(Math.max(total, 1) / 2) || stressUnknown) {
    thesisConfidence = t("thesis.low");
    thesisState = "gap";
  } else if (unknown || healthNeedsRefresh) {
    thesisConfidence = t("thesis.medium");
    thesisState = "watch";
  }
  if (healthNeedsRefresh) {
    thesisConfidence += ` · ${t("thesis.stale")}`;
    if (thesisState === "normal") thesisState = "watch";
  }

  const stressState = t(stressActive
    ? "thesis.state_elevated"
    : stressUnknown
      ? "thesis.state_partial_calm"
      : "thesis.state_not_elevated");
  const leverageRank = Number.isFinite(marginRank)
    ? formatValue(marginRank, "percentile")
    : t("overview.available");
  const thesisEvidence = [
    t("thesis.evidence_stress", { state: stressState }),
    margin
      ? t("thesis.evidence_leverage", {
          rank: leverageRank,
          yoy: Number.isFinite(yoy) ? ` · ${t("overview.yoy", { value: formatValue(yoy, "percent") })}` : "",
        })
      : `${t("card.leverage")}: ${t("overview.unavailable")}`,
    total
      ? t("thesis.evidence_delev", { active: localeNumber(active), known: localeNumber(known) })
      : `${t("card.deleveraging")}: ${t("overview.unavailable")}`,
    snapshotDate ? t("thesis.evidence_snapshot", { date: localeDate(snapshotDate) }) : null,
  ];

  const nfciTrigger = findRuleLeaf(financialCondition, (rule) => rule.type === "latest_above");
  const vixTrigger = findRuleLeaf(vixStress, (rule) => rule.type === "percentile_above");
  const marginTrigger = findRuleLeaf(marginSignal, (rule) => rule.type === "latest_below");
  const breadthCondition = signalCondition("high_low_breadth_collapse");
  const breadthTrigger = findRuleLeaf(breadthCondition, (rule) => rule.type === "percentile_below");
  const breadthThreshold = Number(breadthTrigger?.threshold);
  const thesisTriggers = [
    {
      label: t("trigger.stress"),
      text: nfciTrigger && vixTrigger
        ? t("trigger.stress_rule", { nfci: nfciTrigger.threshold, vix: vixTrigger.threshold })
        : t("trigger.stress_fallback"),
    },
    {
      label: t("trigger.rollover"),
      text: marginTrigger
        ? t("trigger.margin_rule", { value: marginTrigger.threshold })
        : t("trigger.margin_fallback"),
    },
    {
      label: t("trigger.breadth"),
      text: Number.isFinite(breadthThreshold)
        ? t("trigger.breadth_rule", { value: breadthThreshold })
        : (breadthTrigger?.label || t("trigger.breadth_fallback")),
    },
  ];

  setDecisionThesis(
    thesisTitle,
    thesisParts.join(" "),
    thesisConfidence,
    thesisEvidence,
    thesisTriggers,
    thesisState,
  );

  setOverviewHealth(
    t(healthHasHardGap
      ? "health.source_issues"
      : healthNeedsRefresh
        ? "health.needs_refresh"
        : healthHasEvidenceGap
          ? "health.evidence_gaps"
          : "health.current"),
    healthParts.join(" · ") || t("health.no_snapshot"),
    healthHasHardGap ? "gap" : (healthNeedsRefresh || healthHasEvidenceGap) ? "watch" : "normal",
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
      `<div class="panel empty-state"><strong>${escapeHtml(t("us.unavailable"))}</strong><span>${escapeHtml(t("metrics.no_placeholder"))}</span></div>`;
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

  const regimeLabel = (value) => {
    const raw = String(value || "unknown");
    const key = `regime.${raw.toLowerCase()}`;
    const translated = t(key);
    return translated === key ? raw : translated;
  };
  const freshnessLabel = (value) => {
    const key = `common.${value || "unknown"}`;
    const translated = t(key);
    return translated === key ? String(value || t("common.unknown")) : translated;
  };

  const metrics = [...state.metrics.values()]
    .filter(isTaiwanMetric)
    .sort(
      (a, b) =>
        pillarOrder.indexOf(a.metric.pillar) -
        pillarOrder.indexOf(b.metric.pillar),
    );

  if (!metrics.length) {
    stateGrid.innerHTML =
      `<div class="optional-state"><strong>${escapeHtml(t("taiwan.core_unavailable"))}</strong><span>${escapeHtml(t("taiwan.no_placeholder"))}</span></div>`;
    grid.innerHTML = "";
    chart.innerHTML =
      `<div class="empty-state compact">${escapeHtml(t("taiwan.history_unavailable"))}</div>`;
    status.textContent = t("taiwan.coverage_unavailable");
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
    ? t("taiwan.last_known", {
        regime: regimeLabel(macroLastKnown.regime),
        date: localeDate(macroLastKnown.date),
      })
    : t("taiwan.no_known_regime");
  const rateMetrics = metrics.filter((m) => m.metric.id.startsWith("tw_cbc_"));

  const statusCell = (label, value, note) => `<div class="regime-cell">
    <p class="eyebrow">${escapeHtml(label)}</p>
    <div class="regime-value">${escapeHtml(value)}</div>
    <div class="regime-note">${escapeHtml(note)}</div>
  </div>`;

  let breadthValue = t("taiwan.unavailable");
  let breadthNote = t("taiwan.ad_not_published");
  if (adPct && breadth.state !== "missing") {
    breadthValue = formatValue(adPct.latest?.value, "percent");
    if (breadth.state === "snapshot_only") {
      breadthNote = t("taiwan.ad_snapshot");
    } else if (breadth.state === "history_building") {
      breadthNote = t("taiwan.ad_building", { count: localeNumber(breadth.observations) });
    } else if (breadth.state === "not_current") {
      breadthNote = t("taiwan.ad_history_state", { state: freshnessLabel(breadth.freshness) });
    } else {
      breadthNote = t("taiwan.ad_sessions", { count: localeNumber(breadth.observations) });
    }
  }

  stateGrid.innerHTML = [
    statusCell(
      t("taiwan.price"),
      taiex ? formatValue(taiex.latest?.value, taiex.metric.units) : t("taiwan.unavailable"),
      taiex
        ? `TAIEX · ${localeDate(taiex.latest?.as_of || "—")} · ${freshnessLabel(taiexFreshness)}`
        : t("taiwan.not_published"),
    ),
    statusCell(t("taiwan.breadth"), breadthValue, breadthNote),
    statusCell(
      t("taiwan.macro_cycle"),
      macroCurrent ? regimeLabel(macroCurrent.regime) : t("taiwan.not_published"),
      macroCurrent
        ? (macroCurrent.score === null || macroCurrent.score === undefined
            ? t("taiwan.inputs", {
                known: localeNumber(macroCurrent.known_components),
                total: localeNumber(macroCurrent.total_components),
                note: macroLastKnownNote,
              })
            : t("taiwan.score_confidence", {
                score: localeNumber(Number(macroCurrent.score), { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
                confidence: localeNumber(Math.round(Number(macroCurrent.confidence) * 100)),
              }))
        : (macroMetrics.length
            ? t("taiwan.public_macro", { count: localeNumber(macroMetrics.length) })
            : t("taiwan.macro_not_in_release")),
    ),
    statusCell(
      t("taiwan.rates"),
      state.taiwanCbcRateRegime?.current?.regime
        ? regimeLabel(state.taiwanCbcRateRegime.current.regime)
        : (rateMetrics.length ? t("taiwan.inputs_loaded") : t("regime.unknown")),
      state.taiwanCbcRateRegime?.current
        ? `CBC ${formatValue(state.taiwanCbcRateRegime.current.rate, "percent")} · 6M ${formatValue(state.taiwanCbcRateRegime.current.change_6m_bp, "basis points")} · Fed ${regimeLabel(state.fedRateRegime?.current?.regime)}`
        : (rateMetrics.length
            ? t("taiwan.cbc_metrics", { count: localeNumber(rateMetrics.length) })
            : t("taiwan.cbc_not_published")),
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
  const preferred = preferredIds.map((id) => state.metrics.get(id)).filter(Boolean);
  grid.innerHTML = preferred.map(metricCard).join("");
  bindMetricCardInteractions(grid);

  if (taiex) {
    const observationCount = usableObservationCount(taiex);
    status.textContent = t("history.usable_observations", {
      start: localeDate(taiex.coverage.history_start),
      end: localeDate(taiex.coverage.history_end),
      count: localeNumber(observationCount),
    }) + ` · ${freshnessLabel(taiexFreshness)}`;
    if (Array.isArray(taiex.observations)) {
      fullChart(taiex, chart);
    } else {
      chart.innerHTML =
        `<div class="empty-state compact"><strong>${escapeHtml(t("taiwan.history_on_demand"))}</strong><button id="tw-load-history" class="text-button" type="button">${escapeHtml(t("taiwan.load_history"))}</button></div>`;
      $("#tw-load-history")?.addEventListener("click", async (event) => {
        event.currentTarget.disabled = true;
        event.currentTarget.textContent = t("metric.loading");
        try {
          await ensureMetricLoaded("tw_taiex");
          renderTaiwanMarket();
        } catch (error) {
          console.warn("TAIEX history load failed", error);
          chart.innerHTML =
            `<div class="empty-state compact">${escapeHtml(t("taiwan.history_failed"))}</div>`;
        }
      });
    }
  } else {
    chart.innerHTML =
      `<div class="empty-state compact">${escapeHtml(t("taiwan.snapshot_unavailable"))}</div>`;
    status.textContent = t("taiwan.unavailable_short");
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
    grid.innerHTML = `<div class="empty-state compact">${escapeHtml(t("regime.us_unavailable"))}</div>`;
    if (details) details.open = true;
    return;
  }
  const byPillar = new Map();
  for (const metric of metrics) {
    if (!byPillar.has(metric.metric.pillar)) byPillar.set(metric.metric.pillar, []);
    byPillar.get(metric.metric.pillar).push(metric);
  }
  const bad = metrics.filter((metric) => effectiveFreshness(metric).state !== "fresh");
  if (details) details.open = bad.length > 0;
  grid.innerHTML = pillarOrder
    .filter((pillar) => byPillar.has(pillar))
    .slice(0, 6)
    .map((pillar) => {
      const metricsForPillar = byPillar.get(pillar);
      const notCurrent = metricsForPillar.filter((m) => effectiveFreshness(m).state !== "fresh").length;
      const current = metricsForPillar.length - notCurrent;
      const unit = t(metricsForPillar.length === 1 ? "regime.metric" : "regime.metrics");
      return `<div class="regime-cell">
        <p class="eyebrow">${escapeHtml(pillarLabel(pillar))}</p>
        <div class="regime-value">${escapeHtml(notCurrent ? t("regime.not_current", { count: localeNumber(notCurrent) }) : t("regime.current"))}</div>
        <div class="regime-note">${escapeHtml(t("regime.current_count", {
          current: localeNumber(current),
          total: localeNumber(metricsForPillar.length),
          unit,
        }))}</div>
      </div>`;
    }).join("");
}

function renderCoverage() {
  const tbody = $("#coverage-body");
  const metrics = [...state.metrics.values()].sort((a, b) =>
    a.metric.name.localeCompare(b.metric.name),
  );
  if (!metrics.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">${escapeHtml(t("lineage.empty"))}</td></tr>`;
    return;
  }
  tbody.innerHTML = metrics.map((m) => `<tr>
    <td>${escapeHtml(metricContext(m.metric.id)?.plain_name || m.metric.name)}</td>
    <td>${escapeHtml(pillarLabel(m.metric.pillar))}</td>
    <td>${escapeHtml(localeDate(m.coverage.history_start))} → ${escapeHtml(localeDate(m.coverage.history_end))}</td>
    <td>${escapeHtml(localeDate(m.latest.as_of))}</td>
    <td>${freshnessBadge(m)}</td>
    <td><a class="source-link" href="${escapeHtml(m.source.url)}" target="_blank" rel="noopener">${escapeHtml(m.source.provider)}</a></td>
  </tr>`).join("");
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
  const context = metricContext(id);
  $("#dialog-pillar").textContent = pillarLabel(summary.metric.pillar);
  $("#dialog-title").textContent = context?.plain_name || summary.metric.name;
  $("#dialog-summary").innerHTML =
    `<div class="detail-stat"><strong>${escapeHtml(t("metric.loading"))}</strong><span>${escapeHtml(t("dialog.full_history"))}</span></div>`;
  $("#dialog-chart").innerHTML =
    `<div class="empty-state compact">${escapeHtml(t("dialog.loading_history"))}</div>`;
  $("#dialog-source").innerHTML = "";
  if (invoker && typeof invoker.focus === "function") dialogInvoker = invoker;
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
      `<div class="empty-state compact">${escapeHtml(t("dialog.history_failed"))}</div>`;
    $("#dialog-source").textContent = String(error?.message || error);
    return;
  }

  const pct = rollingPercentile(metric);
  const p = percentilePresentation(metric, pct);
  const change = recentChange(metric);
  const related = relatedBreadthStats(metric);
  const dateLabel = context?.date_semantics === "effective_vs_verified"
    ? t("dialog.effective_date")
    : t("dialog.source_observation");
  const baseStats = [
    { value: formatValue(metric.latest.value, metric.metric.units), label: t("dialog.current_value") },
    { value: formatChange(change), label: t("dialog.last_observation") },
    { value: p.value, label: p.label },
    { value: escapeHtml(localeDate(metric.latest.as_of || "—")), label: dateLabel },
  ];
  const stats = related.length
    ? related.map((item) => ({
        value: item.value,
        label: `${item.label} · ${localeDate(item.asOf)}`,
      }))
    : baseStats;
  $("#dialog-summary").innerHTML = stats
    .map((item) => `<div class="detail-stat"><strong>${item.value}</strong><span>${escapeHtml(item.label)}</span></div>`)
    .join("");

  fullChart(metric, $("#dialog-chart"), { height: 390 });
  const membershipContext =
    metric.source?.membership_mode
      ? ` · ${escapeHtml(t("dialog.membership"))}: ${escapeHtml(metric.source.membership_mode)}`
      : "";
  const verifiedLabel = context?.date_semantics === "effective_vs_verified"
    ? t("dialog.source_verified")
    : t("dialog.snapshot_fetched");
  const freshnessState = effectiveFreshness(metric).state;
  const freshnessKey = `common.${freshnessState}`;
  const freshnessLabel = t(freshnessKey) === freshnessKey ? freshnessState : t(freshnessKey);
  $("#dialog-source").innerHTML =
    `${metricContextGuide(metric)}
     ${pct == null ? "" : `<p class="meta">${escapeHtml(p.sentence)} ${escapeHtml(percentileCaveatSentence(metric))}</p>`}
     <div class="source-meta">${escapeHtml(t("dialog.source"))}: <a class="source-link" href="${escapeHtml(metric.source.url)}" target="_blank" rel="noopener">${escapeHtml(metric.source.provider)} — ${escapeHtml(metric.source.dataset)}</a><br>
     ${escapeHtml(verifiedLabel)}: ${escapeHtml(metric.latest.fetched_at || "—")} · ${escapeHtml(t("lineage.freshness"))}: ${escapeHtml(freshnessLabel)} · ${escapeHtml(t("dialog.history_starts"))}: ${escapeHtml(localeDate(metric.coverage.history_start || "—"))}${membershipContext}</div>`;
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
    summaryEl.innerHTML = `<div class="empty-state compact">${escapeHtml(t("signals.current_unavailable"))}</div>`;
    grid.innerHTML = "";
    chart.innerHTML = `<div class="empty-state compact">${escapeHtml(t("signals.history_unavailable"))}</div>`;
    return;
  }
  const displayConditions = (snapshot.current.conditions || []).map((condition) => ({
    ...condition,
    displayStatus: effectiveConditionStatus(condition),
  }));
  const summary = {
    active: displayConditions.filter((item) => item.displayStatus === "active").length,
    inactive: displayConditions.filter((item) => item.displayStatus === "inactive").length,
    unknown: displayConditions.filter((item) => item.displayStatus === "unknown").length,
    total: displayConditions.length,
  };
  summary.known = summary.active + summary.inactive;
  summaryEl.innerHTML = `
    <div class="signal-summary-main">
      <strong>${escapeHtml(t("signal.known_summary", { known: localeNumber(summary.known), total: localeNumber(summary.total) }))}</strong>
      <span class="meta">${escapeHtml(t("signal.summary_meta", { active: localeNumber(summary.active), unknown: localeNumber(summary.unknown) }))}</span>
    </div>
    <span class="meta">${escapeHtml(t("signal.evaluated", { date: localeDate(snapshot.current.as_of || "—") }))}</span>
  `;
  grid.innerHTML = displayConditions.map((condition) => {
    const beginner = signalContext(condition.id) || {};
    const details = flattenRuleDetails(condition.rules);
    const detailText = details.map(formatRuleDetail).join("<br>");
    const caveat = condition.displayStatus === "unknown" ? t("signal.caveat_unknown") : (beginner.caveat || "");
    const statusKey = `common.${condition.displayStatus}`;
    const statusLabel = t(statusKey) === statusKey ? condition.displayStatus : t(statusKey);
    return `<article class="signal-card" data-status="${escapeHtml(condition.displayStatus)}">
      <span class="signal-status">${escapeHtml(statusLabel)}</span>
      <h3>${escapeHtml(beginner.plain_name || condition.name)}</h3>
      <p>${escapeHtml(beginner.description || condition.description || "")}</p>
      ${caveat ? `<p><strong>${escapeHtml(t("signal.caveat_label"))}</strong> ${escapeHtml(caveat)}</p>` : ""}
      <div class="signal-rule">${detailText}</div>
    </article>`;
  }).join("");
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
  const counts = { fresh: 0, stale: 0, missing: 0, error: 0, insufficient_data: 0 };
  for (const metric of metrics) {
    const freshness = effectiveFreshness(metric).state;
    if (freshness in counts) counts[freshness] += 1;
    else counts.error += 1;
  }
  if (!metrics.length) {
    return { counts, className: "badge badge-missing", text: t("health.no_snapshot") };
  }
  const parts = [
    counts.error ? t("health.error_count", { count: localeNumber(counts.error) }) : "",
    counts.missing ? t("health.missing_count", { count: localeNumber(counts.missing) }) : "",
    counts.stale ? t("health.stale_count", { count: localeNumber(counts.stale) }) : "",
    counts.insufficient_data ? t("health.insufficient_count", { count: localeNumber(counts.insufficient_data) }) : "",
  ].filter(Boolean);
  if (!parts.length) return { counts, className: "health-passive", text: t("health.data_current") };
  return {
    counts,
    className: counts.error || counts.missing ? "badge badge-error" : "badge badge-stale",
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
