const CATALOG_URL = "./data/generated/catalog.json";
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

const state = {
  catalog: null,
  metrics: new Map(),
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
  if (units === "percentile") return `${v.toFixed(0)}th`;
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

function historicalPercentileAllowed(metric) {
  const id = String(metric?.metric?.id || "");
  const membershipSensitive =
    id.startsWith("sp500_above_") ||
    id.startsWith("tw_above_") ||
    id.startsWith("tw_new_52w_") ||
    id === "tw_net_new_52w_highs" ||
    id === "tw_high_low_pct";

  return !(
    membershipSensitive &&
    metric?.source?.point_in_time_membership === false
  );
}

function rollingPercentile(metric) {
  if (!historicalPercentileAllowed(metric)) return null;
  const obs = (metric.observations || []).filter((o) => o.value != null);
  if (obs.length < 3) return null;

  const config = baselineConfig(metric, "rolling_percentile");
  const window = config?.window_observations || defaultRollingWindow(metric);
  const minObs = config?.min_observations || Math.min(20, window);
  const baseline = obs
    .slice(Math.max(0, obs.length - 1 - window), -1)
    .map((o) => Number(o.value));

  if (baseline.length < minObs) return null;
  return percentileRank(Number(obs.at(-1).value), baseline);
}

function recentChange(metric) {
  const obs = (metric.observations || []).filter((o) => o.value != null);
  if (obs.length < 2) return null;
  const prior = Number(obs.at(-2).value);
  const current = Number(obs.at(-1).value);
  if (prior === 0) return null;
  return ((current / prior) - 1) * 100;
}

function strictPastPercentileSeries(metric, { rolling = false } = {}) {
  const raw = metric.observations || [];
  if (!historicalPercentileAllowed(metric)) {
    return raw.map((obs) => ({
      date: obs.date,
      value: null,
      status: "insufficient_data",
    }));
  }
  const config = baselineConfig(
    metric,
    rolling ? "rolling_percentile" : "full_history_percentile",
  );
  const window = rolling
    ? (config?.window_observations || defaultRollingWindow(metric))
    : null;
  const minObs = config?.min_observations || 20;

  const history = [];
  const out = [];

  for (const obs of raw) {
    const baseline = window ? history.slice(-window) : history;
    let value = null;
    let status = "insufficient_data";

    if (obs.value == null) {
      status = "missing";
    } else if (baseline.length >= minObs) {
      value = percentileRank(Number(obs.value), baseline);
      status = "observed";
    }

    out.push({ date: obs.date, value, status });
    if (obs.value != null) history.push(Number(obs.value));
  }
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

function historyView(metric, mode) {
  if (mode === "pit_percentile") {
    return {
      ...metric,
      metric: {
        ...metric.metric,
        name: `${metric.metric.name} — point-in-time percentile`,
        units: "percentile",
      },
      observations: strictPastPercentileSeries(metric),
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
      observations: strictPastPercentileSeries(metric, { rolling: true }),
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
  const obs = (metric.observations || [])
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
  const change = recentChange(metric);
  const pText = pct == null ? "—" : `${pct.toFixed(0)}th`;
  const cText =
    change == null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;

  return `<article class="panel metric-card" data-metric-id="${escapeHtml(metric.metric.id)}" tabindex="0">
    <div class="metric-card-top">
      <div>
        <p class="eyebrow">${escapeHtml(pillarLabels[metric.metric.pillar] || metric.metric.pillar)}</p>
        <h3>${escapeHtml(metric.metric.name)}</h3>
      </div>
      ${freshnessBadge(metric)}
    </div>
    <div class="metric-value">${formatValue(metric.latest?.value, metric.metric.units)}</div>
    <div class="metric-unit">as of ${escapeHtml(metric.latest?.as_of || "unknown")} · ${escapeHtml(metric.metric.units)}</div>
    <div class="metric-context">
      <div class="context-chip"><strong>${cText}</strong><span>last observation</span></div>
      <div class="context-chip"><strong>${pText}</strong><span>rolling history percentile</span></div>
    </div>
    ${sparkline(metric)}
    <div class="metric-card-bottom">
      <span class="meta">${escapeHtml(metric.coverage?.history_start || "—")} → ${escapeHtml(metric.coverage?.history_end || "—")}</span>
      <span class="meta">Open history ↗</span>
    </div>
  </article>`;
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
      '<div class="panel empty-state"><strong>No production snapshot loaded.</strong><span>Run the refresh command, validate the generated files, and commit them. This page never substitutes fixture values as current data.</span></div>';
    return;
  }

  grid.innerHTML = metrics.map(metricCard).join("");
  grid.querySelectorAll(".metric-card").forEach((card) => {
    const open = () => openMetric(card.dataset.metricId);
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") open();
    });
  });
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
      '<div class="empty-state compact">Taiwan snapshots not loaded yet.</div>';
    grid.innerHTML = "";
    chart.innerHTML =
      '<div class="empty-state compact">Run <code>python scripts/refresh_data.py --twse-current</code> to populate current TAIEX and TWSE breadth.</div>';
    status.textContent = "Coverage unavailable";
    return;
  }

  const taiex = state.metrics.get("tw_taiex");
  const adPct = state.metrics.get("tw_advance_decline_pct");
  const macroMetrics = metrics.filter((m) =>
    ["tw_ndc_", "tw_manufacturing_pmi", "tw_industrial_", "tw_manufacturing_production"]
      .some((prefix) => m.metric.id.startsWith(prefix)),
  );
  const macroCurrent = state.taiwanMacroRegime?.current || null;
  const rateMetrics = metrics.filter((m) =>
    m.metric.id.startsWith("tw_cbc_"),
  );

  const statusCell = (label, value, note) => `<div class="regime-cell">
    <p class="eyebrow">${escapeHtml(label)}</p>
    <div class="regime-value">${escapeHtml(value)}</div>
    <div class="regime-note">${escapeHtml(note)}</div>
  </div>`;

  stateGrid.innerHTML = [
    statusCell(
      "Price",
      taiex ? formatValue(taiex.latest?.value, taiex.metric.units) : "Unknown",
      taiex ? `TAIEX · ${taiex.latest?.as_of || "—"}` : "TAIEX not loaded",
    ),
    statusCell(
      "Breadth",
      adPct ? formatValue(adPct.latest?.value, "percent") : "Unknown",
      adPct ? "A-D % · TWSE listed stocks" : "Official A/D not loaded",
    ),
    statusCell(
      "Macro cycle",
      macroCurrent ? String(macroCurrent.regime || "Unknown") : "Unknown",
      macroCurrent
        ? `score ${Number(macroCurrent.score).toFixed(2)} · confidence ${Math.round(Number(macroCurrent.confidence) * 100)}%`
        : (macroMetrics.length ? `${macroMetrics.length} public macro metrics` : "NDC / PMI / production pending"),
    ),
    statusCell(
      "Rates",
      state.taiwanCbcRateRegime?.current?.regime
        ? String(state.taiwanCbcRateRegime.current.regime)
        : (rateMetrics.length ? "Inputs loaded" : "Unknown"),
      state.taiwanCbcRateRegime?.current
        ? `CBC ${formatValue(state.taiwanCbcRateRegime.current.rate, "percent")} · 6M ${formatValue(state.taiwanCbcRateRegime.current.change_6m_bp, "basis points")} · Fed ${state.fedRateRegime?.current?.regime || "unknown"}`
        : (rateMetrics.length ? `${rateMetrics.length} CBC rate metrics` : "CBC rate history pending"),
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
    "tw_cbc_rate",
    "tw_cbc_change_6m_bp",
  ];
  const preferred = preferredIds
    .map((id) => state.metrics.get(id))
    .filter(Boolean);

  grid.innerHTML = preferred.map(metricCard).join("");
  grid.querySelectorAll(".metric-card").forEach((card) => {
    const open = () => openMetric(card.dataset.metricId);
    card.addEventListener("click", open);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") open();
    });
  });

  if (taiex) {
    fullChart(taiex, chart);
    status.textContent =
      `${taiex.coverage.history_start} → ${taiex.coverage.history_end} · ${taiex.observations.length.toLocaleString()} observations`;
  } else {
    chart.innerHTML =
      '<div class="empty-state compact">TAIEX snapshot not loaded.</div>';
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
  const summaryEl = $("#ma-summary");
  const chartEl = $("#ma-chart");
  const metrics = maBreadthMetrics();
  const loaded = Object.entries(metrics).filter(([, metric]) => metric);

  if (!loaded.length) {
    summaryEl.innerHTML =
      '<div class="empty-state compact">20/50/200DMA breadth snapshots not loaded yet.</div>';
    chartEl.innerHTML =
      '<div class="empty-state compact">Import an authorized S&P 500 moving-average breadth file to populate this view.</div>';
    return;
  }

  summaryEl.innerHTML = [20, 50, 200]
    .map((horizon) => {
      const metric = metrics[horizon];
      if (!metric) {
        return `<div class="trend-stat missing"><span>${horizon}DMA</span><strong>—</strong><small>not loaded</small></div>`;
      }
      const pct = rollingPercentile(metric);
      const pit = metric?.source?.point_in_time_membership;
      const context = pit === false
        ? "non-PIT history · percentile disabled"
        : (pct == null ? "percentile —" : `${pct.toFixed(0)}th rolling pct`);
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

  element.innerHTML = `<svg class="history-svg ma-breadth-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="S&P 500 moving-average breadth">
    ${grids}
    ${bands}
    ${paths}
    ${spxPath}
    ${spxAxis}
    <text x="${left}" y="${height - 12}" fill="currentColor" opacity=".55" font-size="11">${new Date(firstTs).toISOString().slice(0, 10)}</text>
    <text x="${width - right}" y="${height - 12}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${new Date(lastTs).toISOString().slice(0, 10)}</text>
  </svg>`;
}

function renderRegime() {
  const grid = $("#regime-grid");
  const metrics = [...state.metrics.values()].filter(
    (m) => m.metric.pillar !== "context" && !isTaiwanMetric(m),
  );

  if (!metrics.length) {
    grid.innerHTML =
      '<div class="empty-state compact">Waiting for production snapshots.</div>';
    return;
  }

  const byPillar = new Map();
  for (const metric of metrics) {
    if (!byPillar.has(metric.metric.pillar)) {
      byPillar.set(metric.metric.pillar, []);
    }
    byPillar.get(metric.metric.pillar).push(metric);
  }

  grid.innerHTML = pillarOrder
    .filter((pillar) => byPillar.has(pillar))
    .slice(0, 6)
    .map((pillar) => {
      const metricsForPillar = byPillar.get(pillar);
      const stale = metricsForPillar.filter(
        (m) => effectiveFreshness(m).state !== "fresh",
      ).length;
      const percentiles = metricsForPillar
        .map(rollingPercentile)
        .filter((v) => v != null)
        .sort((a, b) => a - b);
      const median = percentiles.length
        ? percentiles[Math.floor(percentiles.length / 2)]
        : null;

      return `<div class="regime-cell">
        <p class="eyebrow">${escapeHtml(pillarLabels[pillar] || pillar)}</p>
        <div class="regime-value">${stale ? `${stale} stale / missing` : "Data current"}</div>
        <div class="regime-note">${median == null ? "Historical context available" : `Median ${median.toFixed(0)}th pct`} · ${metricsForPillar.length} metric${metricsForPillar.length === 1 ? "" : "s"}</div>
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

  element.innerHTML = `<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${escapeHtml(metric.metric.name)} history">
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
      (m.observations || []).length > 1 &&
      m.metric.pillar !== "context" &&
      !isTaiwanMetric(m),
  );

  if (!metrics.length) {
    select.innerHTML = '<option value="">No metric data</option>';
    $("#history-chart").innerHTML =
      '<div class="empty-state compact">Historical series will appear here.</div>';
    return;
  }

  select.innerHTML = metrics
    .map(
      (m) =>
        `<option value="${escapeHtml(m.metric.id)}">${escapeHtml(m.metric.name)}</option>`,
    )
    .join("");

  const rerender = () => renderHistory(select.value, mode.value);
  select.onchange = rerender;
  mode.onchange = rerender;
  renderHistory(select.value, mode.value);
}

function renderHistory(id, mode = "absolute") {
  const metric = state.metrics.get(id);
  if (!metric) return;

  const view = historyView(metric, mode);
  fullChart(view, $("#history-chart"));

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
    if (Date.parse(obs[i].date) <= target) best = i;
    else break;
  }
  return best;
}

function renderEvents(metric) {
  const list = $("#event-list");
  const obs = (metric.observations || []).filter((o) => o.value != null);

  if (!state.events.length || !obs.length) {
    list.innerHTML = "";
    $("#event-chart").innerHTML =
      '<div class="empty-state compact">Event definitions or history unavailable.</div>';
    return;
  }

  const coverageStart = Date.parse(metric.coverage.history_start);
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

    const anchorDate = new Date(`${obs[anchorIdx].date}T00:00:00Z`);
    const pre = Number(event.window?.pre_months ?? 12);
    const post = Number(event.window?.post_months ?? 24);
    const points = [];

    for (const item of obs) {
      const dt = new Date(`${item.date}T00:00:00Z`);
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

  const el = $("#event-chart");
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

  el.innerHTML = `<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
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
        (metric.observations || []).filter((o) => o.value != null).length > 1,
    )
    .sort((a, b) => a.metric.name.localeCompare(b.metric.name));

  if (!metrics.length) {
    select.innerHTML = '<option value="">No Taiwan history</option>';
    renderTaiwanEvents(null, mode.value);
    return;
  }

  const previous = select.value;
  select.innerHTML = metrics
    .map(
      (metric) =>
        `<option value="${escapeHtml(metric.metric.id)}">${escapeHtml(metric.metric.name)}</option>`,
    )
    .join("");

  if (previous && metrics.some((m) => m.metric.id === previous)) {
    select.value = previous;
  } else if (metrics.some((m) => m.metric.id === "tw_taiex")) {
    select.value = "tw_taiex";
  }

  const rerender = () =>
    renderTaiwanEvents(
      state.metrics.get(select.value) || null,
      mode.value,
    );
  select.onchange = rerender;
  mode.onchange = rerender;
  rerender();
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

  if (!historicalPercentileAllowed(metric) && mode !== "raw") {
    list.innerHTML = "";
    el.innerHTML =
      '<div class="empty-state compact">This membership-sensitive Taiwan breadth series is non-point-in-time, so canonical historical normalization/percentiles are disabled.</div>';
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

  const obs = (eventMetric.observations || []).filter((o) => o.value != null);
  if (obs.length < 2) {
    list.innerHTML = "";
    el.innerHTML =
      '<div class="empty-state compact">Not enough Taiwan history for this comparison mode.</div>';
    return;
  }

  const coverageStart = Date.parse(metric.coverage.history_start);
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

    const anchorDate = new Date(`${obs[anchorIdx].date}T00:00:00Z`);
    const pre = Number(event.window?.pre_months ?? 12);
    const post = Number(event.window?.post_months ?? 24);
    const points = [];

    for (const item of obs) {
      const offset = monthOffset(
        anchorDate,
        new Date(`${item.date}T00:00:00Z`),
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

  el.innerHTML = `<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Taiwan historical event comparison">
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

function openMetric(id) {
  const metric = state.metrics.get(id);
  if (!metric) return;

  $("#dialog-pillar").textContent =
    pillarLabels[metric.metric.pillar] || metric.metric.pillar;
  $("#dialog-title").textContent = metric.metric.name;

  const pct = rollingPercentile(metric);
  const change = recentChange(metric);
  const related = relatedBreadthStats(metric);
  const baseStats = [
    { value: formatValue(metric.latest.value, metric.metric.units), label: "Current value" },
    { value: change == null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`, label: "Last observation" },
    { value: pct == null ? "—" : `${pct.toFixed(0)}th`, label: "Rolling percentile" },
    { value: escapeHtml(metric.latest.as_of || "—"), label: "Source observation" },
  ];
  const stats = related.length ? related.map((item) => ({ value: item.value, label: `${item.label} · ${item.asOf}` })) : baseStats;
  $("#dialog-summary").innerHTML = stats
    .map((item) => `<div class="detail-stat"><strong>${item.value}</strong><span>${escapeHtml(item.label)}</span></div>`)
    .join("");

  fullChart(metric, $("#dialog-chart"), { height: 390 });
  const membershipContext =
    metric.source?.membership_mode
      ? ` · membership: ${escapeHtml(metric.source.membership_mode)}`
      : "";
  $("#dialog-source").innerHTML =
    `Source: <a class="source-link" href="${escapeHtml(metric.source.url)}" target="_blank" rel="noopener">${escapeHtml(metric.source.provider)} — ${escapeHtml(metric.source.dataset)}</a><br>
     Snapshot fetched: ${escapeHtml(metric.latest.fetched_at || "—")} · freshness: ${escapeHtml(effectiveFreshness(metric).state)} · history starts: ${escapeHtml(metric.coverage.history_start || "—")}${membershipContext}`;

  $("#metric-dialog").showModal();
}


function flattenRuleDetails(rule, out = []) {
  if (!rule) return out;
  if (rule.children) {
    rule.children.forEach((child) => flattenRuleDetails(child, out));
    return out;
  }
  out.push({
    label: rule.label || rule.type || "rule",
    reason: rule.reason || "",
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
      '<div class="empty-state compact">Signal snapshot not built yet. Run <code>python scripts/build_signals.py</code> after refreshing metrics.</div>';
    grid.innerHTML = "";
    chart.innerHTML =
      '<div class="empty-state compact">Historical signal state will appear here.</div>';
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
      <strong>${summary.active} active</strong>
      <span class="meta">/ ${summary.known} known · ${summary.unknown} unknown · ${summary.total} total</span>
    </div>
    <span class="meta">Evaluated ${escapeHtml(snapshot.current.as_of || "—")}</span>
  `;

  grid.innerHTML = displayConditions
    .map((condition) => {
      const details = flattenRuleDetails(condition.rules);
      const detailText = details
        .map((detail) => {
          const asOf = detail.asOf ? ` · as of ${detail.asOf}` : "";
          return `${detail.label}: ${detail.status}${asOf}`;
        })
        .join("<br>");
      return `<article class="signal-card" data-status="${escapeHtml(condition.displayStatus)}">
        <span class="signal-status">${escapeHtml(condition.displayStatus)}</span>
        <h3>${escapeHtml(condition.name)}</h3>
        <p>${escapeHtml(condition.description || "")}</p>
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

  element.innerHTML = `<svg class="history-svg signal-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Historical Deleveraging Watch condition counts">
    ${grids}
    ${eventLines}
    <path class="active-line" d="${activePath}"><title>Active conditions</title></path>
    <path class="unknown-line" d="${unknownPath}"><title>Unknown conditions</title></path>
    <text x="${left}" y="${height - 11}" fill="currentColor" opacity=".55" font-size="10">${escapeHtml(history[0].date)}</text>
    <text x="${width - right}" y="${height - 11}" text-anchor="end" fill="currentColor" opacity=".55" font-size="10">${escapeHtml(history.at(-1).date)}</text>
  </svg>`;
}

function updateGlobalFreshness() {
  const badge = $("#global-freshness");
  const metrics = [...state.metrics.values()];

  if (!metrics.length) {
    badge.className = "badge badge-missing";
    badge.textContent = "No production snapshot";
    return;
  }

  const bad = metrics.filter((m) => effectiveFreshness(m).state !== "fresh");
  if (bad.length) {
    badge.className = "badge badge-stale";
    badge.textContent = `${bad.length} stale / missing`;
  } else {
    badge.className = "badge badge-fresh";
    badge.textContent = "All loaded data current";
  }
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

async function loadData() {
  state.metrics.clear();

  try {
    const [catalogResp, eventsResp, signalsResp, refreshResp, maConfigResp, maStudyResp, twMacroResp, twEventsResp, twCbcRateResp, fedRateResp] = await Promise.all([
      fetch(CATALOG_URL, { cache: "no-store" }),
      fetch(EVENTS_URL, { cache: "no-store" }),
      fetch(SIGNALS_URL, { cache: "no-store" }).catch(() => null),
      fetch(REFRESH_REPORT_URL, { cache: "no-store" }).catch(() => null),
      fetch(MA_BREADTH_CONFIG_URL, { cache: "no-store" }).catch(() => null),
      fetch(MA_BREADTH_STUDY_URL, { cache: "no-store" }).catch(() => null),
      fetch(TAIWAN_MACRO_REGIME_URL, { cache: "no-store" }).catch(() => null),
      fetch(TAIWAN_EVENTS_URL, { cache: "no-store" }).catch(() => null),
      fetch(TAIWAN_CBC_RATE_REGIME_URL, { cache: "no-store" }).catch(() => null),
      fetch(FED_RATE_REGIME_URL, { cache: "no-store" }).catch(() => null),
    ]);
    if (!catalogResp.ok) throw new Error(`catalog HTTP ${catalogResp.status}`);

    state.catalog = await catalogResp.json();
    state.events = eventsResp.ok
      ? (await eventsResp.json()).events || []
      : [];
    state.signals = signalsResp?.ok ? await signalsResp.json() : null;
    state.refreshReport = refreshResp?.ok ? await refreshResp.json() : null;
    state.maBreadthConfig = maConfigResp?.ok ? await maConfigResp.json() : null;
    state.maBreadthStudy = maStudyResp?.ok ? await maStudyResp.json() : null;
    state.taiwanMacroRegime = twMacroResp?.ok ? await twMacroResp.json() : null;
    state.taiwanEvents = twEventsResp?.ok ? (await twEventsResp.json()).events || [] : [];
    state.taiwanCbcRateRegime = twCbcRateResp?.ok ? await twCbcRateResp.json() : null;
    state.fedRateRegime = fedRateResp?.ok ? await fedRateResp.json() : null;
    state.refreshErrors.clear();
    for (const result of state.refreshReport?.results || []) {
      if (result.status === "error" && result.metric) {
        state.refreshErrors.set(result.metric, result);
      }
    }

    $("#data-generated").textContent = state.catalog.generated_at
      ? `Generated ${state.catalog.generated_at}`
      : "No production refresh committed";

    const entries = state.catalog.metrics || [];
    const results = await Promise.all(
      entries.map(async (entry) => {
        try {
          const url = new URL(entry.path.replace(/^\.\//, ""), METRIC_BASE);
          const resp = await fetch(url, { cache: "no-store" });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          return await resp.json();
        } catch (error) {
          console.warn("metric load failed", entry.id, error);
          return null;
        }
      }),
    );

    results
      .filter(Boolean)
      .forEach((metric) => state.metrics.set(metric.metric.id, metric));
  } catch (error) {
    console.error(error);
    $("#data-generated").textContent = "Snapshot load failed";
  }

  renderTaiwanMarket();
  renderMetrics();
  renderTrendParticipation();
  renderRegime();
  renderCoverage();
  renderSignals();
  renderHistorySelector();
  updateGlobalFreshness();
}

initTheme();
$("#refresh-view").addEventListener("click", loadData);
$("#ma-bands-toggle")?.addEventListener("change", renderTrendParticipationChart);
$("#ma-spx-toggle")?.addEventListener("change", renderTrendParticipationChart);
loadData();
