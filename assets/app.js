const CATALOG_URL = "./data/generated/catalog.json";
const EVENTS_URL = "./data/events.json";
const SIGNALS_URL = "./data/generated/signals.json";
const REFRESH_REPORT_URL = "./data/generated/refresh-report.json";
const METRIC_BASE = new URL("./data/generated/", window.location.href);

const state = {
  catalog: null,
  metrics: new Map(),
  events: [],
  signals: null,
  refreshReport: null,
  refreshErrors: new Map(),
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

function rollingPercentile(metric) {
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
    .filter((m) => m.metric.pillar !== "context")
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

function renderRegime() {
  const grid = $("#regime-grid");
  const metrics = [...state.metrics.values()].filter(
    (m) => m.metric.pillar !== "context",
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
    (m) => (m.observations || []).length > 1 && m.metric.pillar !== "context",
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

function openMetric(id) {
  const metric = state.metrics.get(id);
  if (!metric) return;

  $("#dialog-pillar").textContent =
    pillarLabels[metric.metric.pillar] || metric.metric.pillar;
  $("#dialog-title").textContent = metric.metric.name;

  const pct = rollingPercentile(metric);
  const change = recentChange(metric);
  $("#dialog-summary").innerHTML = `
    <div class="detail-stat"><strong>${formatValue(metric.latest.value, metric.metric.units)}</strong><span>Current value</span></div>
    <div class="detail-stat"><strong>${change == null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`}</strong><span>Last observation</span></div>
    <div class="detail-stat"><strong>${pct == null ? "—" : `${pct.toFixed(0)}th`}</strong><span>Rolling percentile</span></div>
    <div class="detail-stat"><strong>${escapeHtml(metric.latest.as_of || "—")}</strong><span>Source observation</span></div>`;

  fullChart(metric, $("#dialog-chart"), { height: 390 });
  $("#dialog-source").innerHTML =
    `Source: <a class="source-link" href="${escapeHtml(metric.source.url)}" target="_blank" rel="noopener">${escapeHtml(metric.source.provider)} — ${escapeHtml(metric.source.dataset)}</a><br>
     Snapshot fetched: ${escapeHtml(metric.latest.fetched_at || "—")} · freshness: ${escapeHtml(effectiveFreshness(metric).state)} · history starts: ${escapeHtml(metric.coverage.history_start || "—")}`;

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
    const [catalogResp, eventsResp, signalsResp, refreshResp] = await Promise.all([
      fetch(CATALOG_URL, { cache: "no-store" }),
      fetch(EVENTS_URL, { cache: "no-store" }),
      fetch(SIGNALS_URL, { cache: "no-store" }).catch(() => null),
      fetch(REFRESH_REPORT_URL, { cache: "no-store" }).catch(() => null),
    ]);
    if (!catalogResp.ok) throw new Error(`catalog HTTP ${catalogResp.status}`);

    state.catalog = await catalogResp.json();
    state.events = eventsResp.ok
      ? (await eventsResp.json()).events || []
      : [];
    state.signals = signalsResp?.ok ? await signalsResp.json() : null;
    state.refreshReport = refreshResp?.ok ? await refreshResp.json() : null;
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

  renderMetrics();
  renderRegime();
  renderCoverage();
  renderSignals();
  renderHistorySelector();
  updateGlobalFreshness();
}

initTheme();
$("#refresh-view").addEventListener("click", loadData);
loadData();
