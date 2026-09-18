const CATALOG_URL = "./data/generated/catalog.json";
const EVENTS_URL = "./data/events.json";
const METRIC_BASE = new URL("./data/generated/", window.location.href);

const state = {
  catalog: null,
  metrics: new Map(),
  events: [],
};

const pillarLabels = {
  leverage: "Leverage",
  financial_stress: "Financial stress",
  credit_risk: "Credit / risk",
  volatility: "Volatility",
  market: "Market trend",
  valuation: "Valuation",
  context: "Context",
};

const pillarOrder = ["leverage", "financial_stress", "credit_risk", "volatility", "market", "valuation", "context"];

function $(selector) { return document.querySelector(selector); }

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
  if (units === "ratio") return `${v.toFixed(2)}×`;
  if (units === "binary") return v ? "Yes" : "No";
  if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, {maximumFractionDigits: 1});
  return v.toLocaleString(undefined, {maximumFractionDigits: 2});
}

function freshnessBadge(metric) {
  const s = metric?.freshness?.state || "missing";
  const cls = ["fresh","stale","error","missing"].includes(s) ? `badge-${s}` : "badge-neutral";
  return `<span class="badge ${cls}">${escapeHtml(s.replaceAll("_"," "))}</span>`;
}

function percentileRank(value, baseline) {
  if (value == null || !baseline.length) return null;
  const v = Number(value);
  const less = baseline.filter(x => x < v).length;
  const equal = baseline.filter(x => x === v).length;
  return 100 * (less + 0.5 * equal) / baseline.length;
}

function rollingPercentile(metric) {
  const obs = (metric.observations || []).filter(o => o.value != null);
  if (obs.length < 3) return null;
  const current = Number(obs.at(-1).value);
  const frequency = metric.metric.frequency;
  const window = frequency === "daily" ? 2520 : frequency === "weekly" ? 520 : frequency === "monthly" ? 120 : 40;
  const baseline = obs.slice(Math.max(0, obs.length - 1 - window), -1).map(o => Number(o.value));
  if (!baseline.length) return null;
  return percentileRank(current, baseline);
}

function recentChange(metric) {
  const obs = (metric.observations || []).filter(o => o.value != null);
  if (obs.length < 2) return null;
  const a = Number(obs.at(-2).value);
  const b = Number(obs.at(-1).value);
  if (a === 0) return null;
  return (b / a - 1) * 100;
}

function svgPath(observations, width = 320, height = 64, pad = 4) {
  const points = observations.filter(o => o.value != null);
  if (points.length < 2) return null;
  const vals = points.map(o => Number(o.value));
  let min = Math.min(...vals), max = Math.max(...vals);
  if (min === max) { min -= 1; max += 1; }
  const x = i => pad + i / (points.length - 1) * (width - 2 * pad);
  const y = v => pad + (max - v) / (max - min) * (height - 2 * pad);
  const line = points.map((p,i) => `${i ? "L" : "M"} ${x(i).toFixed(2)} ${y(Number(p.value)).toFixed(2)}`).join(" ");
  const area = `${line} L ${x(points.length-1).toFixed(2)} ${height-pad} L ${x(0).toFixed(2)} ${height-pad} Z`;
  return { line, area, min, max, points };
}

function sparkline(metric) {
  const obs = (metric.observations || []).filter(o => o.value != null).slice(-120);
  const p = svgPath(obs);
  if (!p) return `<svg class="spark" viewBox="0 0 320 64" aria-hidden="true"><line class="baseline" x1="0" y1="32" x2="320" y2="32"/></svg>`;
  return `<svg class="spark" viewBox="0 0 320 64" preserveAspectRatio="none" aria-hidden="true">
    <path class="area" d="${p.area}"></path>
    <path class="line" d="${p.line}"></path>
  </svg>`;
}

function metricCard(metric) {
  const pct = rollingPercentile(metric);
  const change = recentChange(metric);
  const pText = pct == null ? "—" : `${pct.toFixed(0)}th`;
  const cText = change == null ? "—" : `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`;
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
    .filter(m => m.metric.pillar !== "context")
    .sort((a,b) => pillarOrder.indexOf(a.metric.pillar) - pillarOrder.indexOf(b.metric.pillar));

  if (!metrics.length) {
    grid.innerHTML = `<div class="panel empty-state"><strong>No production snapshot loaded.</strong><span>Run the refresh command, validate the generated files, and commit them. This page never substitutes fixture values as current data.</span></div>`;
    return;
  }
  grid.innerHTML = metrics.map(metricCard).join("");
  grid.querySelectorAll(".metric-card").forEach(card => {
    const open = () => openMetric(card.dataset.metricId);
    card.addEventListener("click", open);
    card.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") open(); });
  });
}

function renderRegime() {
  const grid = $("#regime-grid");
  const metrics = [...state.metrics.values()].filter(m => m.metric.pillar !== "context");
  if (!metrics.length) {
    grid.innerHTML = `<div class="empty-state compact">Waiting for production snapshots.</div>`;
    return;
  }

  const byPillar = new Map();
  for (const metric of metrics) {
    if (!byPillar.has(metric.metric.pillar)) byPillar.set(metric.metric.pillar, []);
    byPillar.get(metric.metric.pillar).push(metric);
  }

  grid.innerHTML = pillarOrder
    .filter(p => byPillar.has(p))
    .slice(0, 6)
    .map(pillar => {
      const ms = byPillar.get(pillar);
      const stale = ms.filter(m => m.freshness.state !== "fresh").length;
      const pct = ms.map(rollingPercentile).filter(v => v != null);
      const median = pct.length ? pct.sort((a,b)=>a-b)[Math.floor(pct.length/2)] : null;
      const summary = median == null ? "Context available" : `Median ${median.toFixed(0)}th pct`;
      return `<div class="regime-cell">
        <p class="eyebrow">${escapeHtml(pillarLabels[pillar] || pillar)}</p>
        <div class="regime-value">${stale ? `${stale} stale / missing` : "Data current"}</div>
        <div class="regime-note">${summary} · ${ms.length} metric${ms.length === 1 ? "" : "s"}</div>
      </div>`;
    }).join("");
}

function renderCoverage() {
  const tbody = $("#coverage-body");
  const metrics = [...state.metrics.values()].sort((a,b) => a.metric.name.localeCompare(b.metric.name));
  if (!metrics.length) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-cell">No generated metrics yet.</td></tr>`;
    return;
  }
  tbody.innerHTML = metrics.map(m => `<tr>
    <td>${escapeHtml(m.metric.name)}</td>
    <td>${escapeHtml(pillarLabels[m.metric.pillar] || m.metric.pillar)}</td>
    <td>${escapeHtml(m.coverage.history_start || "—")} → ${escapeHtml(m.coverage.history_end || "—")}</td>
    <td>${escapeHtml(m.latest.as_of || "—")}</td>
    <td>${freshnessBadge(m)}</td>
    <td><a class="source-link" href="${escapeHtml(m.source.url)}" target="_blank" rel="noopener">${escapeHtml(m.source.provider)}</a></td>
  </tr>`).join("");
}

function fullChart(metric, element, opts = {}) {
  const obs = (metric.observations || []).filter(o => o.value != null);
  if (obs.length < 2) {
    element.innerHTML = `<div class="empty-state compact">Not enough observations.</div>`;
    return;
  }
  const width = 1000, height = opts.height || 360, left = 58, right = 20, top = 22, bottom = 42;
  const vals = obs.map(o => Number(o.value));
  let min = Math.min(...vals), max = Math.max(...vals);
  if (min === max) { min -= 1; max += 1; }
  const innerW = width - left - right, innerH = height - top - bottom;
  const x = i => left + i/(obs.length-1)*innerW;
  const y = v => top + (max-v)/(max-min)*innerH;
  const path = obs.map((o,i)=>`${i ? "L":"M"} ${x(i).toFixed(1)} ${y(Number(o.value)).toFixed(1)}`).join(" ");
  const grids=[0,.25,.5,.75,1].map(t=>{
    const yy=top+t*innerH;
    const val=max-t*(max-min);
    return `<line class="gridline" x1="${left}" y1="${yy}" x2="${width-right}" y2="${yy}"/><text x="${left-9}" y="${yy+4}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${escapeHtml(formatValue(val, metric.metric.units))}</text>`;
  }).join("");
  const first=obs[0].date, last=obs.at(-1).date;
  element.innerHTML=`<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${escapeHtml(metric.metric.name)} history">
    ${grids}
    <path class="line" d="${path}"></path>
    <text x="${left}" y="${height-12}" fill="currentColor" opacity=".55" font-size="11">${escapeHtml(first)}</text>
    <text x="${width-right}" y="${height-12}" text-anchor="end" fill="currentColor" opacity=".55" font-size="11">${escapeHtml(last)}</text>
  </svg>`;
}

function renderHistorySelector() {
  const select = $("#history-metric");
  const metrics=[...state.metrics.values()].filter(m => (m.observations || []).length > 1 && m.metric.pillar !== "context");
  if (!metrics.length) {
    select.innerHTML = `<option value="">No metric data</option>`;
    $("#history-chart").innerHTML = `<div class="empty-state compact">Historical series will appear here.</div>`;
    return;
  }
  select.innerHTML=metrics.map(m=>`<option value="${escapeHtml(m.metric.id)}">${escapeHtml(m.metric.name)}</option>`).join("");
  select.onchange=()=>renderHistory(select.value);
  renderHistory(select.value);
}

function renderHistory(id) {
  const metric=state.metrics.get(id);
  if (!metric) return;
  fullChart(metric,$("#history-chart"));
  $("#history-coverage").textContent=`${metric.coverage.history_start} → ${metric.coverage.history_end} · ${metric.observations.length.toLocaleString()} observations`;
  renderEvents(metric);
}

function monthsBetween(a,b) {
  return (b.getUTCFullYear()-a.getUTCFullYear())*12 + (b.getUTCMonth()-a.getUTCMonth());
}

function nearestObservationIndex(obs, anchor) {
  const target=Date.parse(anchor);
  let best=-1, dist=Infinity;
  obs.forEach((o,i)=>{
    if (o.value == null) return;
    const d=Math.abs(Date.parse(o.date)-target);
    if (d<dist){best=i;dist=d;}
  });
  return best;
}

function renderEvents(metric) {
  const list=$("#event-list");
  const obs=(metric.observations||[]).filter(o=>o.value!=null);
  if (!state.events.length || !obs.length) {
    list.innerHTML="";
    $("#event-chart").innerHTML=`<div class="empty-state compact">Event definitions or history unavailable.</div>`;
    return;
  }
  const coverageStart=Date.parse(metric.coverage.history_start);
  list.innerHTML=state.events.map(event=>{
    const anchor=event.anchor_date || metric.latest.as_of;
    const unavailable=!anchor || Date.parse(anchor)<coverageStart;
    return `<span class="event-pill ${unavailable ? "unavailable":""}" title="${escapeHtml(event.notes || "")}">${escapeHtml(event.name)}</span>`;
  }).join("");

  const lines=[];
  const colors=["#5dc2aa","#e7b75f","#ff8278","#7c9cff","#b58cff"];
  state.events.forEach((event,idx)=>{
    const anchor=event.anchor_date || metric.latest.as_of;
    if (!anchor || Date.parse(anchor)<coverageStart) return;
    const anchorIdx=nearestObservationIndex(obs,anchor);
    if (anchorIdx<0) return;
    const anchorValue=Number(obs[anchorIdx].value);
    if (!anchorValue) return;
    const anchorDate=new Date(obs[anchorIdx].date+"T00:00:00Z");
    const points=[];
    obs.forEach(o=>{
      const dt=new Date(o.date+"T00:00:00Z");
      const offset=monthsBetween(anchorDate,dt);
      if (offset < -12 || offset > 24) return;
      points.push({offset,value:Number(o.value)/anchorValue*100});
    });
    if (points.length>1) lines.push({name:event.name,points,color:colors[idx%colors.length]});
  });

  const el=$("#event-chart");
  if (!lines.length){
    el.innerHTML=`<div class="empty-state compact">No event has sufficient metric history.</div>`;
    return;
  }

  const width=720,height=250,left=42,right=16,top=18,bottom=34;
  const all=lines.flatMap(l=>l.points.map(p=>p.value));
  let min=Math.min(...all),max=Math.max(...all);
  if(min===max){min-=1;max+=1;}
  const x=o=>left+(o+12)/36*(width-left-right);
  const y=v=>top+(max-v)/(max-min)*(height-top-bottom);
  const zeroX=x(0);
  const paths=lines.map(l=>{
    const sorted=l.points.sort((a,b)=>a.offset-b.offset);
    const d=sorted.map((p,i)=>`${i?"L":"M"} ${x(p.offset).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ");
    return `<path d="${d}" fill="none" stroke="${l.color}" stroke-width="2" vector-effect="non-scaling-stroke"><title>${escapeHtml(l.name)}</title></path>`;
  }).join("");
  el.innerHTML=`<svg class="history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
    <line class="gridline" x1="${left}" y1="${y(100)}" x2="${width-right}" y2="${y(100)}"/>
    <line class="gridline" x1="${zeroX}" y1="${top}" x2="${zeroX}" y2="${height-bottom}"/>
    ${paths}
    <text x="${left}" y="${height-10}" fill="currentColor" opacity=".55" font-size="10">T-12m</text>
    <text x="${zeroX}" y="${height-10}" text-anchor="middle" fill="currentColor" opacity=".55" font-size="10">Anchor</text>
    <text x="${width-right}" y="${height-10}" text-anchor="end" fill="currentColor" opacity=".55" font-size="10">T+24m</text>
  </svg>`;
}

function openMetric(id) {
  const metric=state.metrics.get(id);
  if(!metric) return;
  $("#dialog-pillar").textContent=pillarLabels[metric.metric.pillar] || metric.metric.pillar;
  $("#dialog-title").textContent=metric.metric.name;
  const pct=rollingPercentile(metric);
  const change=recentChange(metric);
  $("#dialog-summary").innerHTML=`
    <div class="detail-stat"><strong>${formatValue(metric.latest.value,metric.metric.units)}</strong><span>Current value</span></div>
    <div class="detail-stat"><strong>${change==null?"—":`${change>=0?"+":""}${change.toFixed(2)}%`}</strong><span>Last observation</span></div>
    <div class="detail-stat"><strong>${pct==null?"—":`${pct.toFixed(0)}th`}</strong><span>Rolling percentile</span></div>
    <div class="detail-stat"><strong>${escapeHtml(metric.latest.as_of || "—")}</strong><span>Source observation</span></div>`;
  fullChart(metric,$("#dialog-chart"),{height:390});
  $("#dialog-source").innerHTML=`Source: <a class="source-link" href="${escapeHtml(metric.source.url)}" target="_blank" rel="noopener">${escapeHtml(metric.source.provider)} — ${escapeHtml(metric.source.dataset)}</a><br>
    Snapshot fetched: ${escapeHtml(metric.latest.fetched_at || "—")} · freshness: ${escapeHtml(metric.freshness.state)} · history starts: ${escapeHtml(metric.coverage.history_start || "—")}`;
  $("#metric-dialog").showModal();
}

function updateGlobalFreshness() {
  const badge=$("#global-freshness");
  const metrics=[...state.metrics.values()];
  if(!metrics.length){
    badge.className="badge badge-missing";
    badge.textContent="No production snapshot";
    return;
  }
  const bad=metrics.filter(m=>m.freshness.state!=="fresh");
  if(bad.length){
    badge.className="badge badge-stale";
    badge.textContent=`${bad.length} stale / missing`;
  }else{
    badge.className="badge badge-fresh";
    badge.textContent="All loaded data current";
  }
}

function applyTheme(theme){
  document.documentElement.dataset.theme=theme;
  localStorage.setItem("mrm-theme",theme);
}
function initTheme(){
  const saved=localStorage.getItem("mrm-theme");
  const system=window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark":"light";
  applyTheme(saved || system);
  $("#theme-toggle").onclick=()=>applyTheme(document.documentElement.dataset.theme==="dark"?"light":"dark");
}

async function loadData(){
  state.metrics.clear();
  try{
    const [catalogResp,eventsResp]=await Promise.all([fetch(CATALOG_URL,{cache:"no-store"}),fetch(EVENTS_URL,{cache:"no-store"})]);
    if(!catalogResp.ok) throw new Error(`catalog HTTP ${catalogResp.status}`);
    state.catalog=await catalogResp.json();
    state.events=eventsResp.ok ? (await eventsResp.json()).events || [] : [];
    $("#data-generated").textContent=state.catalog.generated_at ? `Generated ${state.catalog.generated_at}` : "No production refresh committed";

    const entries=state.catalog.metrics || [];
    const results=await Promise.all(entries.map(async entry=>{
      try{
        const url=new URL(entry.path.replace(/^\.\//,""),METRIC_BASE);
        const resp=await fetch(url,{cache:"no-store"});
        if(!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
      }catch(err){
        console.warn("metric load failed",entry.id,err);
        return null;
      }
    }));
    results.filter(Boolean).forEach(metric=>state.metrics.set(metric.metric.id,metric));
  }catch(err){
    console.error(err);
    $("#data-generated").textContent="Snapshot load failed";
  }

  renderMetrics();
  renderRegime();
  renderCoverage();
  renderHistorySelector();
  updateGlobalFreshness();
}

initTheme();
$("#refresh-view").addEventListener("click",loadData);
loadData();
