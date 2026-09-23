import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const APP_PATH = path.join(ROOT, "assets", "app.js");
const FIXTURE_PATH = path.join(ROOT, "tests", "fixtures", "ui_behavior.json");
const APP_SOURCE = fs.readFileSync(APP_PATH, "utf8");
const FIXTURE = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8"));

class FakeClassList {
  constructor() {
    this.values = new Set();
  }
  add(...names) {
    names.forEach((name) => this.values.add(name));
  }
  remove(...names) {
    names.forEach((name) => this.values.delete(name));
  }
  contains(name) {
    return this.values.has(name);
  }
}
class FakeElement {
  constructor(id = "") {
    this.id = id;
    this.textContent = "";
    this.innerHTML = "";
    this.className = "";
    this.hidden = false;
    this.dataset = {};
    this.classList = new FakeClassList();
    this.listeners = new Map();
    this.metricCards = [];
    this.open = false;
    this.disabled = false;
    this.focused = false;
    this.isConnected = true;
  }
  addEventListener(type, handler) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(handler);
  }
  removeEventListener(type, handler) {
    const current = this.listeners.get(type) || [];
    this.listeners.set(type, current.filter((item) => item !== handler));
  }
  dispatch(type, event = {}) {
    const dispatched = {
      defaultPrevented: false,
      preventDefault() {
        this.defaultPrevented = true;
      },
      ...event,
      currentTarget: this,
    };
    for (const handler of this.listeners.get(type) || []) {
      handler(dispatched);
    }
    return dispatched;
  }
  focus() {
    this.focused = true;
  }
  querySelectorAll(selector) {
    if (selector === ".metric-card") return this.metricCards;
    return [];
  }
  showModal() {
    this.open = true;
  }
}

function createDom() {
  const byId = new Map();
  const overviewCards = new Map();
  const register = (id, element = new FakeElement(id)) => {
    byId.set(id, element);
    return element;
  };
  const registerOverviewCard = (kind) => {
    const element = new FakeElement(`overview-card-${kind}`);
    overviewCards.set(kind, element);
    return element;
  };
  const document = {
    documentElement: { dataset: {} },
    querySelector(selector) {
      if (selector.startsWith("#")) return byId.get(selector.slice(1)) || null;
      const match = selector.match(/^\[data-overview-card="([^"]+)"\]$/);
      if (match) return overviewCards.get(match[1]) || null;
      return null;
    },
  };
  return { byId, overviewCards, register, registerOverviewCard, document };
}
function buildRuntime(fetchImpl = async () => {
  throw new Error("unexpected fetch");
}) {
  const dom = createDom();
  const logs = { errors: [], warnings: [] };
  const bootstrap = APP_SOURCE.lastIndexOf("\ninitTheme();");
  assert.notEqual(bootstrap, -1, "app bootstrap marker missing");
  const exports = `
globalThis.__MRM__ = {
  state,
  effectiveFreshness,
  globalFreshnessSummary,
  formatValue,
  formatChange,
  defaultRollingWindow,
  historicalPercentileAllowed,
  rollingPercentile,
  historyView,
  taiwanBreadthState,
  marginMomentumEvidence,
  renderOverview,
  renderMetrics,
  renderTrendParticipation,
  renderTaiwanEvents,
  updateGlobalFreshness,
  setupDialogFocusManagement,
  openMetric,
  fullChart,
  loadData,
  setOpenMetricForTest(fn) { openMetric = fn; },
  setRenderStubsForTest(stubs) {
    renderOverview = stubs.renderOverview || renderOverview;
    renderMetrics = stubs.renderMetrics || renderMetrics;
    renderTrendParticipation = stubs.renderTrendParticipation || renderTrendParticipation;
    renderTaiwanMarket = stubs.renderTaiwanMarket || renderTaiwanMarket;
    renderSignals = stubs.renderSignals || renderSignals;
    renderHistorySelector = stubs.renderHistorySelector || renderHistorySelector;
    renderRegime = stubs.renderRegime || renderRegime;
    renderCoverage = stubs.renderCoverage || renderCoverage;
    setupDeferredContextLoading = stubs.setupDeferredContextLoading || setupDeferredContextLoading;
  }
};`;
  const sandbox = {
    URL,
    fetch: fetchImpl,
    document: dom.document,
    localStorage: {
      values: new Map(),
      getItem(key) { return this.values.get(key) ?? null; },
      setItem(key, value) { this.values.set(key, String(value)); },
    },
    window: {
      location: { href: "https://example.test/" },
      matchMedia: () => ({ matches: false }),
    },
    console: {
      error: (...args) => logs.errors.push(args.map(String).join(" ")),
      warn: (...args) => logs.warnings.push(args.map(String).join(" ")),
      log: () => {},
    },
    setTimeout,
    clearTimeout,
  };
  vm.createContext(sandbox);
  vm.runInContext(APP_SOURCE.slice(0, bootstrap) + exports, sandbox, {
    filename: "assets/app.js",
  });
  return { api: sandbox.__MRM__, dom, logs };
}
function summaryMetric({
  id,
  freshness = "fresh",
  observations = 30,
  percentile = 50,
  units = "index",
  frequency = "daily",
  pillar = "market",
  polarity = "contextual",
  comparison = "percent_change",
  latest = 100,
  pointInTime = true,
}) {
  const preview = observations
    ? [
        { date: "2026-01-01", value: latest - 1, status: "observed" },
        { date: "2026-01-02", value: latest, status: "observed" },
      ].slice(-Math.min(observations, 2))
    : [];
  return {
    metric: { id, name: id, pillar, units, frequency, polarity, comparison },
    source: {
      provider: "fixture",
      dataset: "fixture",
      url: "https://example.test/source",
      point_in_time_membership: pointInTime,
    },
    coverage: { history_start: "2020-01-01", history_end: "2026-01-02" },
    freshness: {
      state: freshness,
      max_age_days: 100000,
      reason: freshness === "fresh" ? null : `fixture ${freshness}`,
    },
    latest: {
      as_of: "2026-01-02",
      fetched_at: "2026-01-03T00:00:00Z",
      value: latest,
    },
    baselines: [
      {
        type: "rolling_percentile",
        window_observations: frequency === "monthly" ? 120 : frequency === "weekly" ? 520 : 2520,
        min_observations: 2,
      },
    ],
    summary: {
      observation_count: observations,
      rolling_percentile: percentile,
      recent_change:
        comparison === "none"
          ? null
          : { value: 1, comparison },
      preview_observations: preview,
    },
  };
}

function fullMetricFromSummary(summary, values = [10, 11, 12, 13, 14]) {
  return {
    ...summary,
    observations: values.map((value, index) => ({
      date: `2026-01-${String(index + 1).padStart(2, "0")}`,
      value,
      status: "observed",
    })),
  };
}
function registerOverviewDom(runtime) {
  const kinds = ["stress", "leverage", "deleveraging", "taiwan", "coverage"];
  for (const kind of kinds) {
    runtime.dom.registerOverviewCard(kind);
    const stateId = kind === "coverage" ? "evidence" : kind;
    runtime.dom.register(`overview-${stateId}-state`);
    runtime.dom.register(`overview-${stateId}-evidence`);
    runtime.dom.register(`overview-${stateId}-note`);
    runtime.dom.register(`decision-${kind}-state`);
  }
}

test("freshness matrix and preserved-refresh errors use production semantics", () => {
  const runtime = buildRuntime();
  const { state, effectiveFreshness, globalFreshnessSummary } = runtime.api;
  const metrics = FIXTURE.freshness_states.map(({ id, state: freshness }) =>
    summaryMetric({ id, freshness }),
  );

  for (const metric of metrics) {
    assert.equal(effectiveFreshness(metric).state, metric.freshness.state);
  }

  const preserved = summaryMetric({ id: "preserved", freshness: "fresh" });
  state.refreshErrors.set("preserved", {
    status: "error",
    error: "temporary source failure",
    preserved_previous: true,
  });
  assert.equal(effectiveFreshness(preserved).state, "error");
  assert.match(effectiveFreshness(preserved).reason, /temporary source failure/);

  state.refreshErrors.clear();
  const summary = globalFreshnessSummary(metrics);
  assert.equal(summary.counts.fresh, 1);
  assert.equal(summary.counts.stale, 1);
  assert.equal(summary.counts.missing, 1);
  assert.equal(summary.counts.error, 1);
  assert.equal(summary.counts.insufficient_data, 1);
  assert.equal(summary.text, "1 error · 1 missing · 1 stale · 1 insufficient data");
  assert.equal(summary.className, "badge badge-error");

  const badge = runtime.dom.register("global-freshness");
  metrics.forEach((metric) => state.metrics.set(metric.metric.id, metric));
  runtime.api.updateGlobalFreshness();
  assert.equal(badge.textContent, summary.text);
  assert.equal(badge.className, summary.className);
});
test("unit-aware values, deltas, and frequency windows are executable", () => {
  const { api } = buildRuntime();

  for (const item of FIXTURE.delta_cases) {
    assert.equal(
      api.formatChange({ value: item.value, comparison: item.comparison }),
      item.expected,
    );
  }

  for (const item of FIXTURE.value_cases) {
    assert.equal(api.formatValue(item.value, item.units), item.expected);
  }

  for (const item of FIXTURE.frequency_windows) {
    const metric = summaryMetric({
      id: `frequency-${item.frequency}`,
      frequency: item.frequency,
    });
    assert.equal(api.defaultRollingWindow(metric), item.expected);
  }
});

test("Taiwan breadth state machine executes the production classifier", () => {
  const runtime = buildRuntime();

  for (const item of FIXTURE.taiwan_breadth_cases) {
    const metric = item.present
      ? summaryMetric({
          id: "tw_advance_decline_pct",
          pillar: "breadth",
          units: "percent",
          freshness: item.state,
          observations: item.observations,
          percentile: item.percentile,
        })
      : null;
    assert.equal(runtime.api.taiwanBreadthState(metric).state, item.expected);
  }
});
test("non-PIT historical percentile and event modes stay blocked", () => {
  const runtime = buildRuntime();
  const summary = summaryMetric({
    id: FIXTURE.non_pit_metric.id,
    pillar: FIXTURE.non_pit_metric.pillar,
    units: FIXTURE.non_pit_metric.units,
    frequency: FIXTURE.non_pit_metric.frequency,
    polarity: FIXTURE.non_pit_metric.polarity,
    comparison: FIXTURE.non_pit_metric.comparison,
    pointInTime: false,
  });
  const metric = fullMetricFromSummary(summary);

  assert.equal(runtime.api.historicalPercentileAllowed(metric), false);
  const view = runtime.api.historyView(metric, "pit_percentile");
  assert.ok(view.observations.every((item) => item.value === null));
  assert.ok(
    view.observations.every((item) => item.status === "insufficient_data"),
  );

  const list = runtime.dom.register("tw-event-list");
  const chart = runtime.dom.register("tw-event-chart");
  runtime.api.state.taiwanEvents = [
    { id: "fixture-event", name: "Fixture event", anchor_date: "2026-01-03" },
  ];
  runtime.api.renderTaiwanEvents(metric, "normalized");
  assert.equal(list.innerHTML, "");
  assert.match(chart.innerHTML, /non-point-in-time/);

  const pitMetric = fullMetricFromSummary(
    summaryMetric({
      id: FIXTURE.non_pit_metric.id,
      pillar: "breadth",
      units: "percent",
      pointInTime: true,
    }),
  );
  pitMetric.baselines.push({
    type: "full_history_percentile",
    min_observations: 2,
  });
  assert.equal(runtime.api.historicalPercentileAllowed(pitMetric), true);
  const pitView = runtime.api.historyView(pitMetric, "pit_percentile");
  assert.ok(pitView.observations.some((item) => item.value !== null));
});
test("optional MA family renders compact unavailable state", () => {
  const runtime = buildRuntime();
  const section = runtime.dom.register("trend-participation-section");
  const controls = runtime.dom.register("trend-controls");
  const summary = runtime.dom.register("ma-summary");
  const chart = runtime.dom.register("ma-chart");
  const legend = runtime.dom.register("trend-legend");
  const study = runtime.dom.register("ma-study-block");

  runtime.api.renderTrendParticipation();

  assert.equal(section.classList.contains("compact-optional"), true);
  assert.equal(controls.hidden, true);
  assert.equal(chart.hidden, true);
  assert.equal(legend.hidden, true);
  assert.equal(study.hidden, true);
  assert.match(summary.innerHTML, /unavailable in the public release/);
});

test("core overview artifact failure is visible and does not fake a snapshot", async () => {
  const responses = new Map([
    ["./data/generated/catalog.json", { ok: true, status: 200, payload: { metrics: [] } }],
    ["./data/generated/overview.json", { ok: false, status: 404, payload: {} }],
    ["./data/generated/signals.json", { ok: true, status: 200, payload: {} }],
    ["./data/generated/refresh-report.json", { ok: true, status: 200, payload: { results: [] } }],
  ]);
  const runtime = buildRuntime(async (url) => {
    const item = responses.get(String(url));
    if (!item) throw new Error(`unexpected fetch: ${url}`);
    return { ok: item.ok, status: item.status, json: async () => item.payload };
  });
  const generated = runtime.dom.register("data-generated");
  const badge = runtime.dom.register("global-freshness");
  const noop = () => {};
  runtime.api.setRenderStubsForTest({
    renderOverview: noop,
    renderMetrics: noop,
    renderTrendParticipation: noop,
    renderTaiwanMarket: noop,
    renderSignals: noop,
    renderHistorySelector: noop,
    renderRegime: noop,
    renderCoverage: noop,
    setupDeferredContextLoading: noop,
  });

  await runtime.api.loadData();

  assert.equal(generated.textContent, "Snapshot load failed");
  assert.equal(badge.textContent, "No production snapshot");
  assert.equal(badge.className, "badge badge-missing");
  assert.equal(runtime.api.state.metrics.size, 0);
  assert.equal(runtime.logs.errors.length, 1);
});
test("metric cards open from click, Enter, and Space at interaction level", () => {
  const runtime = buildRuntime();
  const grid = runtime.dom.register("metric-grid");
  const card = new FakeElement("metric-card-fixture");
  card.dataset.metricId = "fixture-index";
  grid.metricCards = [card];

  runtime.api.state.metrics.set(
    "fixture-index",
    summaryMetric({ id: "fixture-index", pillar: "market" }),
  );

  const opened = [];
  runtime.api.setOpenMetricForTest((id) => opened.push(id));
  runtime.api.renderMetrics();

  card.dispatch("click");
  const enter = card.dispatch("keydown", { key: "Enter" });
  const space = card.dispatch("keydown", { key: " " });
  const escape = card.dispatch("keydown", { key: "Escape" });

  assert.deepEqual(opened, [
    "fixture-index",
    "fixture-index",
    "fixture-index",
  ]);
  assert.equal(enter.defaultPrevented, true);
  assert.equal(space.defaultPrevented, true);
  assert.equal(escape.defaultPrevented, false);
  assert.match(grid.innerHTML, /role="button"/);
  assert.match(grid.innerHTML, /tabindex="0"/);
  assert.match(grid.innerHTML, /aria-label="Open fixture-index details and history"/);
});
test("overview executes partial-stress and positive-YoY rollover semantics", () => {
  const runtime = buildRuntime();
  registerOverviewDom(runtime);

  runtime.api.state.metrics.set(
    "nfci",
    summaryMetric({
      id: "nfci",
      pillar: "financial_stress",
      polarity: "higher_is_riskier",
      latest: -0.56,
    }),
  );
  runtime.api.state.metrics.set(
    "vix",
    summaryMetric({
      id: "vix",
      pillar: "volatility",
      polarity: "higher_is_riskier",
      latest: 14.87,
    }),
  );
  runtime.api.state.metrics.set(
    "finra_margin_debt",
    summaryMetric({
      id: "finra_margin_debt",
      pillar: "leverage",
      units: "USD millions",
      polarity: "contextual",
      latest: 1453832,
      percentile: 100,
    }),
  );
  runtime.api.state.metrics.set(
    "finra_margin_debt_yoy_pct",
    summaryMetric({
      id: "finra_margin_debt_yoy_pct",
      pillar: "leverage",
      units: "percent",
      polarity: "contextual",
      comparison: "percentage_points",
      latest: 37.2,
    }),
  );

  runtime.api.state.signals = {
    current: {
      conditions: [
        {
          id: "vix_stress",
          name: "VIX stress",
          status: "inactive",
          metrics: ["vix"],
        },
        FIXTURE.margin_condition,
      ],
    },
  };

  runtime.api.renderOverview();

  assert.equal(
    runtime.dom.byId.get("overview-stress-state").textContent,
    "U.S. stress evidence is incomplete",
  );
  assert.equal(
    runtime.dom.byId.get("overview-leverage-state").textContent,
    "Leverage growth remains positive; its growth momentum is slowing",
  );
  assert.match(
    runtime.dom.byId.get("overview-leverage-evidence").innerHTML,
    /YoY growth slowed 16\.5 pp over 3 monthly observations/,
  );
  assert.match(
    runtime.dom.byId.get("overview-leverage-evidence").innerHTML,
    /context only/,
  );
  assert.match(
    runtime.dom.byId.get("overview-leverage-note").textContent,
    /not described as falling/,
  );
});

test("metric dialog moves focus to close and returns it to the invoker", async () => {
  const runtime = buildRuntime();
  const dialog = runtime.dom.register("metric-dialog");
  const close = runtime.dom.register("dialog-close");
  runtime.dom.register("dialog-pillar");
  runtime.dom.register("dialog-title");
  runtime.dom.register("dialog-summary");
  runtime.dom.register("dialog-chart");
  runtime.dom.register("dialog-source");

  const invoker = new FakeElement("metric-card-invoker");
  const summary = summaryMetric({ id: "fixture-dialog", pillar: "market" });
  runtime.api.state.metrics.set(
    "fixture-dialog",
    fullMetricFromSummary(summary, [10, 11, 12, 13, 14]),
  );

  runtime.api.setupDialogFocusManagement();
  await runtime.api.openMetric("fixture-dialog", invoker);

  assert.equal(dialog.open, true);
  assert.equal(close.focused, true);
  assert.equal(invoker.focused, false);

  dialog.dispatch("close");
  assert.equal(invoker.focused, true);
});

test("full history chart exposes a non-visual key-value summary", () => {
  const runtime = buildRuntime();
  const chart = runtime.dom.register("history-chart");
  const metric = fullMetricFromSummary(
    summaryMetric({ id: "fixture-history", pillar: "market", units: "index" }),
    [10, 12, 11, 14, 13],
  );

  runtime.api.fullChart(metric, chart);

  assert.match(chart.innerHTML, /class="sr-only"/);
  assert.match(chart.innerHTML, /aria-describedby="history-chart-a11y-summary"/);
  assert.match(chart.innerHTML, /5 observations from 2026-01-01 to 2026-01-05/);
  assert.match(chart.innerHTML, /Latest 2026-01-05: 13/);
  assert.match(chart.innerHTML, /Range 10 to 14/);
});
