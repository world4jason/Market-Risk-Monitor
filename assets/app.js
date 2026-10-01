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


const SUPPORTED_LOCALES = ["en", "zh-TW"];
const LOCALE_STORAGE_KEY = "mrm-locale";

const messages = {
  en: {
    "meta.title": "Market Risk Monitor",
    "meta.description": "Explainable U.S. and Taiwan market risk, breadth, macro, and historical context dashboard.",
    "header.eyebrow": "MULTI-MARKET STRESS & BREADTH",
    "header.subtitle": "Market stress, leverage and breadth — current first, fully auditable underneath.",
    "nav.label": "Dashboard sections",
    "nav.overview": "Overview",
    "nav.us": "U.S.",
    "nav.taiwan": "Taiwan",
    "nav.research": "Research",
    "controls.language": "Language",
    "controls.theme": "Toggle theme",
    "loading.data": "Loading data…",
    "overview.eyebrow": "MARKET SNAPSHOT",
    "overview.title": "What matters now",
    "overview.meta": "Current evidence · select any card to inspect the underlying data",
    "overview.currentRead": "CURRENT READ",
    "overview.loadingConfidence": "Loading confidence",
    "overview.buildingRead": "Building the market read…",
    "overview.buildingSummary": "Combining stress, leverage and deleveraging evidence without a hidden composite score.",
    "overview.changesCall": "WHAT CHANGES THE CALL",
    "overview.waitingThresholds": "Waiting for signal thresholds…",
    "overview.kicker.stress": "U.S. stress",
    "overview.kicker.leverage": "Leverage",
    "overview.kicker.deleveraging": "Deleveraging",
    "overview.kicker.taiwan": "Taiwan",
    "overview.loading": "Loading",
    "overview.waiting.current": "Waiting for current evidence",
    "overview.waiting.finra": "Waiting for FINRA evidence",
    "overview.waiting.signal": "Waiting for signal coverage",
    "overview.waiting.taiex": "Waiting for TAIEX evidence",
    "health.label": "DATA HEALTH",
    "health.loading": "Loading snapshot health…",
    "health.checking": "Freshness and evidence coverage are being checked.",
    "health.inspect": "Inspect health →",
    "divider.us": "U.S. MARKET",
    "divider.taiwan": "TAIWAN MARKET",
    "us.eyebrow": "U.S. DETAIL",
    "us.title": "Current U.S. metrics",
    "us.reload": "Reload snapshot",
    "us.intro": "Lead conclusions are summarized above. Open any metric for the definition, reading guide, caveat, history, source, and freshness.",
    "us.unavailable": "Current U.S. snapshot is unavailable.",
    "us.unavailableDetail": "Source and freshness details will appear when a published snapshot is available.",
    "trend.eyebrow": "BREADTH / PARTICIPATION",
    "trend.title": "Trend Participation",
    "trend.customBands": "Custom heuristic bands",
    "trend.spxOverlay": "SPX overlay",
    "trend.unavailableTitle": "Trend Participation — unavailable in the public release",
    "trend.unavailableDetail": "Point-in-time S&P 500 moving-average breadth history with acceptable redistribution rights is not currently published. Missing breadth remains unknown in Deleveraging Watch.",
    "trend.historyPlaceholder": "Trend Participation history will appear here when published.",
    "trend.heuristicNote": "Heuristic bands are optional and non-canonical.",
    "trend.studyEyebrow": "THRESHOLD STUDY",
    "trend.studyTitle": "<25% / <15% historical outcomes",
    "trend.studyNotLoaded": "Study snapshot not loaded",
    "trend.noEpisodes": "No threshold-study episodes loaded.",
    "table.date": "Date",
    "table.cross": "Cross",
    "table.breadth": "Breadth",
    "table.localLow": "63d local low",
    "taiwan.eyebrow": "TAIWAN DETAIL",
    "taiwan.title": "Taiwan Market Regime",
    "taiwan.officialFirst": "Official-source first",
    "taiwan.notLoaded": "Taiwan snapshots not loaded yet.",
    "taiwan.priceContext": "Price & participation context",
    "common.coverageUnavailable": "Coverage unavailable",
    "taiwan.historyPlaceholder": "TAIEX history will appear here.",
    "taiwan.eventEyebrow": "TAIWAN EVENT WINDOWS",
    "taiwan.eventTitle": "Historical regime comparison",
    "taiwan.eventMetricAria": "Taiwan event comparison metric",
    "taiwan.eventModeAria": "Taiwan event comparison mode",
    "mode.eventNormalized": "Event-normalized",
    "mode.raw": "Raw level",
    "mode.pitPercentile": "Point-in-time percentile",
    "taiwan.eventPlaceholder": "Taiwan event comparison will appear here.",
    "taiwan.disclaimer": "Taiwan breadth uses transparent TWSE stock counts. MacroMicro/MM and proprietary Breadth 1/2/3 formulas are not reproduced or guessed.",
    "signals.eyebrow": "CONCURRENT DETERIORATION",
    "signals.title": "Deleveraging Watch",
    "signals.meta": "Transparent conditions · unknown ≠ safe",
    "signals.unavailable": "Signal snapshot not available.",
    "signals.historyEyebrow": "HISTORICAL BACKFILL",
    "signals.historyTitle": "Active and unknown conditions over time",
    "signals.publicationLag": "Publication lag is respected in historical evaluation",
    "signals.historyPlaceholder": "Historical signal state will appear here.",
    "signals.disclaimer": "This is not a crash probability or trading score. Each condition remains independently visible and auditable; no single condition creates a crisis label.",
    "research.eyebrow": "RESEARCH HISTORY",
    "research.title": "Historical context",
    "research.metricAria": "Historical metric",
    "research.modeAria": "Historical comparison mode",
    "research.noMetric": "No metric data",
    "mode.absolute": "Absolute level",
    "mode.rollingPercentile": "Rolling percentile",
    "mode.rateChange": "Rate of change",
    "research.historyPlaceholder": "Historical series will appear here.",
    "research.eventEyebrow": "EVENT WINDOWS",
    "research.eventTitle": "Cycle comparison",
    "research.eventPlaceholder": "Select a metric with sufficient event history.",
    "research.eventMeta": "Event paths are indexed to 100 at each anchor. Missing pre-history stays unavailable rather than being backfilled with a proxy.",
    "dataHealth.eyebrow": "DATA HEALTH",
    "dataHealth.title": "Snapshot health by pillar",
    "dataHealth.notLoaded": "Snapshot not loaded",
    "dataHealth.waiting": "Waiting for production snapshots.",
    "dataHealth.disclaimer": "Freshness and coverage only. This reports whether each pillar's data is current, not how risky the market is; there is no pillar-level risk score.",
    "lineage.eyebrow": "DATA LINEAGE",
    "lineage.title": "Coverage & freshness",
    "table.metric": "Metric",
    "table.pillar": "Pillar",
    "table.coverage": "Coverage",
    "table.asOf": "As of",
    "table.freshness": "Freshness",
    "table.source": "Source",
    "lineage.noMetrics": "No generated metrics yet.",
    "dialog.metric": "Metric",
    "dialog.close": "Close metric details",
    "footer.methodology": "Methodology",
    "footer.dataSources": "Data sources",
    "footer.taiwanSources": "Taiwan sources",
    "pillar.leverage": "Leverage",
    "pillar.financial_stress": "Financial stress",
    "pillar.credit_risk": "Credit / risk",
    "pillar.volatility": "Volatility",
    "pillar.breadth": "Breadth / participation",
    "pillar.market": "Market trend",
    "pillar.valuation": "Valuation",
    "pillar.context": "Context",
    "status.fresh": "fresh",
    "status.stale": "stale",
    "status.error": "error",
    "status.missing": "missing",
    "status.insufficient_data": "insufficient data",
    "status.unknown": "unknown",
    "status.active": "active",
    "status.inactive": "inactive",
    "status.loading": "Loading",
    "status.dataGap": "DATA GAP",
    "status.elevated": "ELEVATED",
    "status.clear": "CLEAR",
    "status.watch": "WATCH",
    "status.context": "CONTEXT",
    "status.partial": "PARTIAL",
    "status.current": "CURRENT",
    "window.lastYears": "last {count} year{plural}",
    "window.lastObservations": "last {count} observations",
    "percentile.notEnough": "not enough history for percentile",
    "percentile.unavailable": "Historical percentile is not available for this comparison.",
    "percentile.label": "percentile vs {window}",
    "percentile.sentence": "Higher than about {percent}% of observations in the {window} comparison window.",
    "date.effectiveVerified": "effective since {asOf} · source verified {verified}",
    "date.asOf": "as of {asOf}",
    "guide.reference": "Reference",
    "guide.why": "Why it matters",
    "guide.how": "How to read",
    "guide.direction": "Direction",
    "guide.caveat": "Caveat",
    "context.contextOnly": "context only",
    "context.retrospective": "retrospective; not PIT/backtest-safe",
    "context.riskDirection": "This rank is context only; it is not a risk direction.",
    "context.notPit": "This is a retrospective current rank and is not safe for historical PIT/backtest use.",
    "breadth.none": "No usable public breadth sessions are currently available.",
    "breadth.oneSession": "Only 1 published breadth session is available. This is a one-session participation snapshot, not a trend or percentile conclusion.",
    "breadth.historyBuilding": "{count} published breadth sessions are available. Multi-session history is accumulating, but the configured historical percentile still lacks sufficient observations.",
    "breadth.notCurrent": "Published breadth history exists, but its current freshness state is {freshness}; current trend interpretation needs caution.",
    "margin.slowing": "YoY growth slowed {value} pp over {periods} monthly observations",
    "rule.observed": "observed {value}{unit}",
    "rule.asOf": "as of {date}",
    "snapshot.noSupport": "No current supporting observation",
    "trigger.none": "No configured escalation threshold is available.",
    "overview.stress.knownCalm": "Known gauges calm",
    "overview.stress.elevated": "Stress elevated",
    "overview.stress.contained": "Stress contained",
    "overview.stress.looser": "Conditions looser than avg",
    "overview.stress.tighter": "Conditions tighter than avg",
    "overview.stress.available": "Financial conditions available",
    "overview.leverage.incomplete": "Incomplete read",
    "overview.leverage.slowing": "High, growth slowing",
    "overview.leverage.context": "Leverage context",
    "overview.deleveraging.noRead": "No signal read",
    "overview.deleveraging.notConfirmed": "Not confirmed",
    "overview.deleveraging.signs": "Deleveraging signs",
    "overview.deleveraging.noConfirmation": "No confirmation",
    "overview.taiwan.available": "Market read available",
    "overview.taiwan.noRead": "No current read",
    "overview.taiwan.noCall": "No current call",
    "overview.taiwan.priceCurrent": "Price current",
    "overview.taiwan.breadthUnavailable": "Breadth unavailable",
    "overview.marginMomentum": "Margin momentum slowing",
    "overview.usable": "{known}/{total} usable · {unknown} unknown",
    "overview.sessions": "{count} session{plural}",
    "thesis.stressAndDeleveraging": "Stress rising; deleveraging signals appearing",
    "thesis.stressNotConfirmed": "Stress rising; deleveraging not confirmed",
    "thesis.rollover": "Leverage rolling over; stress not confirmed",
    "thesis.stretched": "Leverage stretched; stress not confirmed",
    "thesis.partial": "Known stress gauges calm; read incomplete",
    "thesis.noBroadStress": "No broad stress confirmation",
    "thesis.stressElevated": "At least one current stress check is elevated.",
    "thesis.stressPartial": "Known stress gauges are not elevated, but expected stress evidence is incomplete.",
    "thesis.stressCalm": "Current NFCI/VIX stress checks are not elevated.",
    "thesis.marginSlowing": "Margin debt is still {yoy} YoY while growth momentum is slowing.",
    "thesis.marginGrowth": "Margin debt growth is {yoy} YoY.",
    "thesis.checks": "{known}/{total} deleveraging checks are usable; {active} {verb} active.",
    "thesis.confidence.high": "HIGH CONFIDENCE",
    "thesis.confidence.medium": "MEDIUM CONFIDENCE",
    "thesis.confidence.low": "LOW CONFIDENCE",
    "thesis.confidence.stale": "STALE DATA",
    "thesis.evidence.stress": "Stress: {state}",
    "thesis.evidence.stressElevated": "elevated",
    "thesis.evidence.stressPartial": "partial / known gauges calm",
    "thesis.evidence.stressCalm": "not elevated",
    "thesis.evidence.leverage": "Leverage: {rank}{yoy}",
    "thesis.evidence.deleveraging": "Deleveraging: {active} active / {known} known",
    "thesis.evidence.snapshot": "Snapshot: {date}",
    "thesis.trigger.stress": "Stress confirms",
    "thesis.trigger.rollover": "Rollover deepens",
    "thesis.trigger.breadth": "Breadth confirms",
    "thesis.trigger.stressFallback": "configured NFCI / VIX stress threshold turns active",
    "thesis.trigger.marginFallback": "margin-debt growth turns negative",
    "thesis.trigger.breadthFallback": "breadth deterioration becomes available and active",
    "health.noSnapshot": "No production snapshot",
    "health.dataCurrent": "Data current",
    "health.sourceIssues": "Source issues",
    "health.needsRefresh": "Snapshot needs refresh",
    "health.evidenceGaps": "Evidence gaps remain",
    "health.snapshotCurrent": "Snapshot current",
    "health.count.error": "{count} error",
    "health.count.missing": "{count} missing",
    "health.count.stale": "{count} stale",
    "health.count.insufficient": "{count} insufficient data",
    "health.count.unknownChecks": "{count} unknown checks",
    "health.snapshotDate": "snapshot {date}",
    "metric.openAria": "Open {title} details and history",
    "metric.lastObservation": "last observation",
    "metric.explainHistory": "Explain & view history ↗",
    "metric.openHistory": "Open history ↗",
    "metric.usUnavailable": "Current U.S. snapshot is unavailable.",
    "metric.noPlaceholder": "No fixture or placeholder value is substituted for missing published data.",
    "regime.usUnavailable": "Published U.S. metric health is unavailable.",
    "regime.notCurrent": "{count} not current",
    "regime.currentCount": "{current} of {total} {metricWord} current",
    "regime.metric.one": "metric",
    "regime.metric.many": "metrics",
    "signals.known": "{known} of {total} checks known",
    "signals.summary": "· {active} active · {unknown} unavailable/unknown",
    "signals.evaluated": "Evaluated {date} · unknown is not inactive",
    "signals.unknownCaveat": "Required public evidence is unavailable; this remains unknown rather than safe.",
    "signals.caveat": "Caveat:",
    "signals.noHistory": "Not enough historical signal states.",
    "history.selectMetric": "Select a metric to load history",
    "history.selectMetricPrompt": "Select a metric to load its full history.",
    "history.loadFailed": "This metric history could not be loaded.",
    "history.pitDisabled": "Point-in-time historical view disabled.",
    "history.pitUseAbsolute": "{reason}. Use Absolute level for retrospective history.",
    "history.usable": "{count} usable observations",
    "history.eventUnavailable": "Event definitions or history unavailable.",
    "history.eventDisabled": "Historical event comparison disabled.",
    "history.eventRawAvailable": "{reason}. Raw absolute history remains available.",
    "history.noPitEvent": "No point-in-time event history is available.",
    "history.noEventCoverage": "No event has sufficient metric history.",
    "history.notEnough": "Not enough observations for this view.",
    "dialog.loading": "Loading…",
    "dialog.fullHistory": "Full metric history",
    "dialog.loadingHistory": "Loading full metric history…",
    "dialog.loadFailed": "Detailed history could not be loaded. The overview remains available.",
    "dialog.effectiveDate": "Effective/change date",
    "dialog.sourceObservation": "Source observation",
    "dialog.currentValue": "Current value",
    "dialog.lastObservation": "Last observation"
  },
  "zh-TW": {
    "meta.title": "市場風險監測儀表板",
    "meta.description": "可解釋的美國與台灣市場風險、廣度、總經與歷史情境儀表板。",
    "header.eyebrow": "多市場壓力與廣度",
    "header.subtitle": "先看現在的市場壓力、槓桿與廣度；所有判斷都可往下追溯。",
    "nav.label": "儀表板區段",
    "nav.overview": "總覽",
    "nav.us": "美國",
    "nav.taiwan": "台灣",
    "nav.research": "研究",
    "controls.language": "語言",
    "controls.theme": "切換明暗主題",
    "loading.data": "載入資料中…",
    "overview.eyebrow": "市場快照",
    "overview.title": "現在最重要的是什麼",
    "overview.meta": "目前證據 · 點選任一卡片可查看底層資料",
    "overview.currentRead": "目前判讀",
    "overview.loadingConfidence": "計算信心中",
    "overview.buildingRead": "正在建立市場判讀…",
    "overview.buildingSummary": "綜合壓力、槓桿與去槓桿證據，不使用隱藏綜合分數。",
    "overview.changesCall": "哪些條件會改變判斷",
    "overview.waitingThresholds": "等待訊號門檻…",
    "overview.kicker.stress": "美國市場壓力",
    "overview.kicker.leverage": "槓桿",
    "overview.kicker.deleveraging": "去槓桿",
    "overview.kicker.taiwan": "台灣",
    "overview.loading": "載入中",
    "overview.waiting.current": "等待目前證據",
    "overview.waiting.finra": "等待 FINRA 資料",
    "overview.waiting.signal": "等待訊號覆蓋",
    "overview.waiting.taiex": "等待台股資料",
    "health.label": "資料健康",
    "health.loading": "檢查快照健康狀態…",
    "health.checking": "正在檢查資料新鮮度與證據覆蓋。",
    "health.inspect": "查看資料健康 →",
    "divider.us": "美國市場",
    "divider.taiwan": "台灣市場",
    "us.eyebrow": "美國詳情",
    "us.title": "目前美國市場指標",
    "us.reload": "重新載入快照",
    "us.intro": "上方先給結論。點開任何指標可查看定義、判讀方式、限制、歷史、來源與新鮮度。",
    "us.unavailable": "目前沒有可用的美國市場快照。",
    "us.unavailableDetail": "有已發布快照後，這裡會顯示來源與新鮮度細節。",
    "trend.eyebrow": "廣度 / 參與度",
    "trend.title": "趨勢參與度",
    "trend.customBands": "自訂經驗門檻",
    "trend.spxOverlay": "疊加 SPX",
    "trend.unavailableTitle": "趨勢參與度 — 公開版目前不可用",
    "trend.unavailableDetail": "目前沒有可合法公開再散布、且具時點正確性的 S&P 500 移動平均廣度歷史。缺失的廣度訊號在去槓桿監測中維持未知。",
    "trend.historyPlaceholder": "發布後會在此顯示趨勢參與度歷史。",
    "trend.heuristicNote": "經驗門檻為選配，並非正式判定標準。",
    "trend.studyEyebrow": "門檻研究",
    "trend.studyTitle": "<25% / <15% 歷史結果",
    "trend.studyNotLoaded": "尚未載入研究快照",
    "trend.noEpisodes": "尚未載入門檻研究事件。",
    "table.date": "日期",
    "table.cross": "穿越",
    "table.breadth": "廣度",
    "table.localLow": "63 日局部低點",
    "taiwan.eyebrow": "台灣詳情",
    "taiwan.title": "台灣市場狀態",
    "taiwan.officialFirst": "官方來源優先",
    "taiwan.notLoaded": "尚未載入台灣市場快照。",
    "taiwan.priceContext": "價格與參與度",
    "common.coverageUnavailable": "覆蓋資料不可用",
    "taiwan.historyPlaceholder": "TAIEX 歷史會顯示於此。",
    "taiwan.eventEyebrow": "台灣事件視窗",
    "taiwan.eventTitle": "歷史狀態比較",
    "taiwan.eventMetricAria": "台灣事件比較指標",
    "taiwan.eventModeAria": "台灣事件比較模式",
    "mode.eventNormalized": "事件標準化",
    "mode.raw": "原始數值",
    "mode.pitPercentile": "時點正確百分位",
    "taiwan.eventPlaceholder": "台灣事件比較會顯示於此。",
    "taiwan.disclaimer": "台灣廣度使用透明的 TWSE 股票家數。未重製或猜測 MacroMicro/MM 與專有 Breadth 1/2/3 公式。",
    "signals.eyebrow": "同步惡化",
    "signals.title": "去槓桿監測",
    "signals.meta": "透明條件 · 未知不等於安全",
    "signals.unavailable": "目前沒有可用的訊號快照。",
    "signals.historyEyebrow": "歷史回填",
    "signals.historyTitle": "有效與未知條件的歷史變化",
    "signals.publicationLag": "歷史評估會尊重資料發布延遲",
    "signals.historyPlaceholder": "歷史訊號狀態會顯示於此。",
    "signals.disclaimer": "這不是崩盤機率或交易分數。每個條件都獨立顯示且可稽核；單一條件不會產生危機標籤。",
    "research.eyebrow": "歷史研究",
    "research.title": "歷史情境",
    "research.metricAria": "歷史指標",
    "research.modeAria": "歷史比較模式",
    "research.noMetric": "沒有指標資料",
    "mode.absolute": "絕對數值",
    "mode.rollingPercentile": "滾動百分位",
    "mode.rateChange": "變化率",
    "research.historyPlaceholder": "歷史序列會顯示於此。",
    "research.eventEyebrow": "事件視窗",
    "research.eventTitle": "週期比較",
    "research.eventPlaceholder": "請選擇具有足夠歷史資料的指標。",
    "research.eventMeta": "每個事件路徑都以錨點標準化為 100。事件前資料不足時維持不可用，不以代理值補齊。",
    "dataHealth.eyebrow": "資料健康",
    "dataHealth.title": "各構面快照健康狀態",
    "dataHealth.notLoaded": "尚未載入快照",
    "dataHealth.waiting": "等待正式環境快照。",
    "dataHealth.disclaimer": "這裡只顯示新鮮度與覆蓋狀態，代表資料是否夠新，不代表市場風險高低；沒有構面級風險分數。",
    "lineage.eyebrow": "資料血緣",
    "lineage.title": "覆蓋範圍與新鮮度",
    "table.metric": "指標",
    "table.pillar": "構面",
    "table.coverage": "歷史覆蓋",
    "table.asOf": "截至",
    "table.freshness": "新鮮度",
    "table.source": "來源",
    "lineage.noMetrics": "尚無產生的指標。",
    "dialog.metric": "指標",
    "dialog.close": "關閉指標詳情",
    "footer.methodology": "方法論",
    "footer.dataSources": "資料來源",
    "footer.taiwanSources": "台灣資料來源",
    "pillar.leverage": "槓桿",
    "pillar.financial_stress": "金融壓力",
    "pillar.credit_risk": "信用 / 風險",
    "pillar.volatility": "波動",
    "pillar.breadth": "廣度 / 參與度",
    "pillar.market": "市場趨勢",
    "pillar.valuation": "估值",
    "pillar.context": "情境",
    "status.fresh": "最新",
    "status.stale": "過期",
    "status.error": "錯誤",
    "status.missing": "缺失",
    "status.insufficient_data": "資料不足",
    "status.unknown": "未知",
    "status.active": "觸發",
    "status.inactive": "未觸發",
    "status.loading": "載入中",
    "status.dataGap": "資料缺口",
    "status.elevated": "偏高",
    "status.clear": "未升高",
    "status.watch": "留意",
    "status.context": "情境",
    "status.partial": "部分資料",
    "status.current": "最新",
    "window.lastYears": "近 {count} 年",
    "window.lastObservations": "近 {count} 筆觀測",
    "percentile.notEnough": "歷史不足，無法計算百分位",
    "percentile.unavailable": "此比較目前無法提供歷史百分位。",
    "percentile.label": "相較{window}百分位",
    "percentile.sentence": "高於{window}比較視窗中約 {percent}% 的觀測。",
    "date.effectiveVerified": "自 {asOf} 起生效 · 來源驗證於 {verified}",
    "date.asOf": "截至 {asOf}",
    "guide.reference": "參考值",
    "guide.why": "為什麼重要",
    "guide.how": "如何判讀",
    "guide.direction": "方向",
    "guide.caveat": "限制",
    "context.contextOnly": "僅供情境參考",
    "context.retrospective": "回顧性；不可直接用於 PIT / 回測",
    "context.riskDirection": "此排名僅供情境參考，不代表風險方向。",
    "context.notPit": "這是回顧性的當前排名，不可安全地用於歷史 PIT / 回測。",
    "breadth.none": "目前沒有可用的公開廣度資料。",
    "breadth.oneSession": "目前只有 1 個已發布的廣度交易日。這只是單日參與度快照，不足以判斷趨勢或百分位。",
    "breadth.historyBuilding": "目前已有 {count} 個廣度交易日，歷史正逐步累積，但仍不足以計算設定的歷史百分位。",
    "breadth.notCurrent": "已有廣度歷史，但目前新鮮度為 {freshness}；現況趨勢判讀需保守。",
    "margin.slowing": "YoY 成長率在 {periods} 個月內下降 {value} 個百分點",
    "rule.observed": "觀測值 {value}{unit}",
    "rule.asOf": "截至 {date}",
    "snapshot.noSupport": "目前沒有可用的支持證據",
    "trigger.none": "目前沒有可用的升級門檻。",
    "overview.stress.knownCalm": "已知壓力指標平靜",
    "overview.stress.elevated": "壓力升高",
    "overview.stress.contained": "未見廣泛壓力",
    "overview.stress.looser": "金融環境較長期平均寬鬆",
    "overview.stress.tighter": "金融環境較長期平均緊",
    "overview.stress.available": "金融環境資料可用",
    "overview.leverage.incomplete": "判讀不完整",
    "overview.leverage.slowing": "高槓桿，成長動能放慢",
    "overview.leverage.context": "槓桿情境可用",
    "overview.deleveraging.noRead": "無法判讀訊號",
    "overview.deleveraging.notConfirmed": "尚未確認",
    "overview.deleveraging.signs": "出現去槓桿跡象",
    "overview.deleveraging.noConfirmation": "尚無確認訊號",
    "overview.taiwan.available": "市場判讀可用",
    "overview.taiwan.noRead": "目前無法判讀",
    "overview.taiwan.noCall": "目前不做判斷",
    "overview.taiwan.priceCurrent": "價格資料最新",
    "overview.taiwan.breadthUnavailable": "廣度不可用",
    "overview.marginMomentum": "融資槓桿動能放慢",
    "overview.usable": "{known}/{total} 可用 · {unknown} 未知",
    "overview.sessions": "{count} 個交易日",
    "thesis.stressAndDeleveraging": "壓力升高，去槓桿訊號開始出現",
    "thesis.stressNotConfirmed": "壓力升高，但去槓桿尚未確認",
    "thesis.rollover": "槓桿開始轉弱，廣泛壓力尚未確認",
    "thesis.stretched": "槓桿偏高，廣泛壓力尚未確認",
    "thesis.partial": "已知壓力指標平靜，但判讀仍不完整",
    "thesis.noBroadStress": "目前證據未確認廣泛市場壓力",
    "thesis.stressElevated": "至少一項目前壓力條件已升高。",
    "thesis.stressPartial": "已知壓力指標未升高，但部分預期壓力證據缺失。",
    "thesis.stressCalm": "目前 NFCI / VIX 壓力條件未升高。",
    "thesis.marginSlowing": "融資餘額 YoY 仍為 {yoy}，但成長動能正在放慢。",
    "thesis.marginGrowth": "融資餘額 YoY 成長為 {yoy}。",
    "thesis.checks": "{known}/{total} 項去槓桿條件可用；其中 {active} 項觸發。",
    "thesis.confidence.high": "高信心",
    "thesis.confidence.medium": "中等信心",
    "thesis.confidence.low": "低信心",
    "thesis.confidence.stale": "資料已過期",
    "thesis.evidence.stress": "壓力：{state}",
    "thesis.evidence.stressElevated": "升高",
    "thesis.evidence.stressPartial": "部分資料 / 已知指標平靜",
    "thesis.evidence.stressCalm": "未升高",
    "thesis.evidence.leverage": "槓桿：{rank}{yoy}",
    "thesis.evidence.deleveraging": "去槓桿：{active} 項觸發 / {known} 項已知",
    "thesis.evidence.snapshot": "快照：{date}",
    "thesis.trigger.stress": "壓力確認",
    "thesis.trigger.rollover": "槓桿轉弱加深",
    "thesis.trigger.breadth": "廣度確認",
    "thesis.trigger.stressFallback": "NFCI / VIX 壓力條件觸發",
    "thesis.trigger.marginFallback": "融資餘額 YoY 轉為負成長",
    "thesis.trigger.breadthFallback": "廣度惡化資料可用並觸發",
    "health.noSnapshot": "沒有正式環境快照",
    "health.dataCurrent": "資料皆為最新",
    "health.sourceIssues": "來源異常",
    "health.needsRefresh": "快照需要更新",
    "health.evidenceGaps": "仍有證據缺口",
    "health.snapshotCurrent": "快照為最新",
    "health.count.error": "{count} 錯誤",
    "health.count.missing": "{count} 缺失",
    "health.count.stale": "{count} 過期",
    "health.count.insufficient": "{count} 資料不足",
    "health.count.unknownChecks": "{count} 項未知條件",
    "health.snapshotDate": "快照 {date}",
    "metric.openAria": "開啟 {title} 的詳情與歷史",
    "metric.lastObservation": "最近一期變化",
    "metric.explainHistory": "說明與歷史 ↗",
    "metric.openHistory": "查看歷史 ↗",
    "metric.usUnavailable": "目前沒有可用的美國市場快照。",
    "metric.noPlaceholder": "缺少已發布資料時，不會用 fixture 或硬編碼數值補位。",
    "regime.usUnavailable": "目前無法取得美國指標健康狀態。",
    "regime.notCurrent": "{count} 項非最新",
    "regime.currentCount": "{current}/{total} 項指標為最新",
    "regime.metric.one": "指標",
    "regime.metric.many": "指標",
    "signals.known": "{known}/{total} 項條件已知",
    "signals.summary": "· {active} 項觸發 · {unknown} 項不可用 / 未知",
    "signals.evaluated": "評估日期 {date} · 未知不等於未觸發",
    "signals.unknownCaveat": "所需公開證據目前不可用，因此維持未知，不視為安全。",
    "signals.caveat": "限制：",
    "signals.noHistory": "歷史訊號狀態不足。",
    "history.selectMetric": "選擇指標以載入歷史",
    "history.selectMetricPrompt": "請選擇一個指標以載入完整歷史。",
    "history.loadFailed": "此指標的歷史資料無法載入。",
    "history.pitDisabled": "時點正確的歷史視圖已停用。",
    "history.pitUseAbsolute": "{reason}。若要回顧歷史，請改用絕對數值。",
    "history.usable": "{count} 筆可用觀測",
    "history.eventUnavailable": "事件定義或歷史資料不可用。",
    "history.eventDisabled": "歷史事件比較已停用。",
    "history.eventRawAvailable": "{reason}。仍可查看原始的回顧性歷史。",
    "history.noPitEvent": "目前沒有可用的時點正確事件歷史。",
    "history.noEventCoverage": "沒有事件具備足夠的指標歷史。",
    "history.notEnough": "此視圖的觀測資料不足。",
    "dialog.loading": "載入中…",
    "dialog.fullHistory": "完整指標歷史",
    "dialog.loadingHistory": "載入完整指標歷史中…",
    "dialog.loadFailed": "詳細歷史無法載入；總覽仍可使用。",
    "dialog.effectiveDate": "生效 / 變更日期",
    "dialog.sourceObservation": "來源觀測日期",
    "dialog.currentValue": "目前數值",
    "dialog.lastObservation": "最近一期"
  }
};


Object.assign(messages.en, {
  "taiwan.coreUnavailable": "Core Taiwan snapshot unavailable",
  "taiwan.noPlaceholder": "No placeholder data is shown. Source and freshness details remain available when a published snapshot exists.",
  "taiwan.historyUnavailable": "TAIEX history is unavailable in the current published snapshot.",
  "taiwan.price": "Price",
  "taiwan.breadth": "Breadth",
  "taiwan.macroCycle": "Macro cycle",
  "taiwan.rates": "Rates",
  "taiwan.unavailable": "Unavailable",
  "taiwan.adNotPublished": "Official A/D breadth not published",
  "taiwan.adSnapshot": "A-D snapshot · 1 session only · no trend inference",
  "taiwan.adBuilding": "A-D % · {count} sessions · history accumulating",
  "taiwan.adHistory": "A-D history exists · {freshness}",
  "taiwan.adSessions": "A-D % · {count} sessions",
  "taiwan.lastKnown": "last known {regime} {date}",
  "taiwan.noKnownRegime": "no known regime yet",
  "taiwan.notPublished": "Not published",
  "taiwan.inputs": "{known}/{total} inputs · {lastKnown}",
  "taiwan.scoreConfidence": "score {score} · confidence {confidence}%",
  "taiwan.macroSummaryUnavailable": "{count} public macro metrics; regime summary unavailable",
  "taiwan.macroFamilyUnavailable": "Taiwan macro/regime family is not included in this public release",
  "taiwan.inputsLoaded": "Inputs loaded",
  "taiwan.cbcMetrics": "{count} CBC rate metrics",
  "taiwan.cbcNotPublished": "CBC rate history not published",
  "taiwan.observations": "{count} observations · {freshness}",
  "taiwan.historyOnDemand": "TAIEX history is available on demand.",
  "taiwan.loadHistory": "Load TAIEX history",
  "taiwan.historyLoadFailed": "TAIEX history could not be loaded. Current summary data remains available.",
  "taiwan.snapshotUnavailable": "TAIEX snapshot is unavailable in the current release.",
  "taiwan.taiexUnavailable": "TAIEX unavailable",
  "trend.notPublished": "not published",
  "trend.nonPit": "non-PIT history · {reason}",
  "trend.percentileUnavailable": "historical percentile unavailable",
  "trend.percentileContext": "{percentile} percentile vs {window}",
  "trend.studyBuild": "Build the study after loading point-in-time 50DMA breadth and SPX price history.",
  "trend.studyNonCanonical": "Event study is not canonical for this source.",
  "trend.studyCanonicalUnavailable": "Canonical episode table unavailable for this source.",
  "trend.studyStatus": "{events} events · cooldown {cooldown} sessions · descriptive only",
  "trend.noForwardWindows": "No completed forward-return windows yet.",
  "trend.studySummary": "n={n} · median {median} · positive {positive} · median MAE {mae}",
  "trend.sessions": "{count} sessions",
  "trend.noEpisodesAvailable": "No threshold-study episodes available.",
  "trend.historyOnDemand": "Trend Participation history is available on demand.",
  "trend.loadHistory": "Load breadth history",
  "trend.notEnoughHistory": "Not enough moving-average breadth history.",
  "signals.noSnapshot": "Deleveraging Watch is unavailable in the current published snapshot.",
  "signals.noHistoricalState": "Historical signal state is unavailable.",
  "history.noTaiwan": "No Taiwan history",
  "history.selectTaiwan": "Select a Taiwan metric",
  "history.taiwanLoadFailed": "This Taiwan metric history could not be loaded.",
  "history.taiwanEventUnavailable": "Taiwan event definitions or metric history unavailable.",
  "history.taiwanPitDisabled": "Point-in-time Taiwan event comparison disabled.",
  "history.taiwanRawAvailable": "{reason}. Raw retrospective history remains available.",
  "history.taiwanPitPercentileDisabled": "Point-in-time percentile mode is disabled because no eligible PIT percentile baseline is declared.",
  "history.taiwanNotEnough": "Not enough Taiwan history for this comparison mode.",
  "dialog.historyLabel": "History",
  "dialog.source": "Source",
  "dialog.coverage": "Coverage",
  "dialog.freshness": "Freshness",
  "dialog.latestFetch": "Latest fetch",
  "dialog.provider": "Provider"
});
Object.assign(messages["zh-TW"], {
  "taiwan.coreUnavailable": "台灣核心快照不可用",
  "taiwan.noPlaceholder": "不顯示替代或假資料；有已發布快照時仍可查看來源與新鮮度。",
  "taiwan.historyUnavailable": "目前發布快照中沒有可用的 TAIEX 歷史。",
  "taiwan.price": "價格",
  "taiwan.breadth": "廣度",
  "taiwan.macroCycle": "總經週期",
  "taiwan.rates": "利率",
  "taiwan.unavailable": "不可用",
  "taiwan.adNotPublished": "尚未發布官方 A/D 廣度",
  "taiwan.adSnapshot": "A-D 單日快照 · 僅 1 日 · 不推論趨勢",
  "taiwan.adBuilding": "A-D % · {count} 日 · 歷史累積中",
  "taiwan.adHistory": "A-D 歷史存在 · {freshness}",
  "taiwan.adSessions": "A-D % · {count} 日",
  "taiwan.lastKnown": "上次已知 {regime} · {date}",
  "taiwan.noKnownRegime": "尚無已知狀態",
  "taiwan.notPublished": "尚未發布",
  "taiwan.inputs": "{known}/{total} 個輸入 · {lastKnown}",
  "taiwan.scoreConfidence": "分數 {score} · 信心 {confidence}%",
  "taiwan.macroSummaryUnavailable": "已有 {count} 個公開總經指標；狀態摘要不可用",
  "taiwan.macroFamilyUnavailable": "公開版目前未包含台灣總經 / 狀態資料族",
  "taiwan.inputsLoaded": "輸入已載入",
  "taiwan.cbcMetrics": "{count} 個央行利率指標",
  "taiwan.cbcNotPublished": "尚未發布央行利率歷史",
  "taiwan.observations": "{count} 筆觀測 · {freshness}",
  "taiwan.historyOnDemand": "TAIEX 完整歷史可按需載入。",
  "taiwan.loadHistory": "載入 TAIEX 歷史",
  "taiwan.historyLoadFailed": "TAIEX 歷史載入失敗；目前摘要仍可使用。",
  "taiwan.snapshotUnavailable": "目前版本沒有可用的 TAIEX 快照。",
  "taiwan.taiexUnavailable": "TAIEX 不可用",
  "trend.notPublished": "尚未發布",
  "trend.nonPit": "非 PIT 歷史 · {reason}",
  "trend.percentileUnavailable": "歷史百分位不可用",
  "trend.percentileContext": "{percentile} · 相較{window}",
  "trend.studyBuild": "載入具時點正確性的 50DMA 廣度與 SPX 價格歷史後即可建立研究。",
  "trend.studyNonCanonical": "此來源不符合正式事件研究要求。",
  "trend.studyCanonicalUnavailable": "此來源無法提供正式事件表。",
  "trend.studyStatus": "{events} 個事件 · 冷卻 {cooldown} 個交易日 · 僅描述性",
  "trend.noForwardWindows": "尚無完成的前瞻報酬視窗。",
  "trend.studySummary": "n={n} · 中位數 {median} · 正報酬 {positive} · 中位 MAE {mae}",
  "trend.sessions": "{count} 個交易日",
  "trend.noEpisodesAvailable": "目前沒有可用的門檻研究事件。",
  "trend.historyOnDemand": "趨勢參與度完整歷史可按需載入。",
  "trend.loadHistory": "載入廣度歷史",
  "trend.notEnoughHistory": "移動平均廣度歷史不足。",
  "signals.noSnapshot": "目前發布快照中沒有可用的去槓桿監測。",
  "signals.noHistoricalState": "歷史訊號狀態不可用。",
  "history.noTaiwan": "沒有台灣歷史資料",
  "history.selectTaiwan": "選擇台灣指標",
  "history.taiwanLoadFailed": "此台灣指標歷史無法載入。",
  "history.taiwanEventUnavailable": "台灣事件定義或指標歷史不可用。",
  "history.taiwanPitDisabled": "時點正確的台灣事件比較已停用。",
  "history.taiwanRawAvailable": "{reason}。仍可查看原始回顧性歷史。",
  "history.taiwanPitPercentileDisabled": "未宣告合格的 PIT 百分位基準，因此停用時點正確百分位模式。",
  "history.taiwanNotEnough": "此比較模式的台灣歷史不足。",
  "dialog.historyLabel": "歷史",
  "dialog.source": "來源",
  "dialog.coverage": "覆蓋",
  "dialog.freshness": "新鮮度",
  "dialog.latestFetch": "最近抓取",
  "dialog.provider": "提供者"
});

const beginnerContextZhTW = {
  nfci: {
    plain_name: "廣義金融環境",
    what_it_measures: "Chicago Fed NFCI 將資金、信用、槓桿與風險條件整合為一個廣義金融環境指數。",
    why_it_matters: "金融環境轉緊時，家庭、企業與投資人取得資金或承擔風險的難度通常會上升。",
    how_to_read: "0 是長期平均。負值代表金融環境比平均寬鬆；正值代表比平均緊。",
    higher_lower_or_contextual: "越高通常代表金融環境越緊、壓力越大；越低則越寬鬆。",
    important_reference_level: "0 = 指數長期平均。",
    important_caveat: "NFCI 描述目前金融環境，本身不預測市場方向。"
  },
  vix: {
    plain_name: "美股預期波動（VIX）",
    what_it_measures: "VIX 反映選擇權市場對 S&P 500 未來約 30 天波動度的隱含預期。",
    why_it_matters: "VIX 急升通常伴隨不確定性與避險需求提高。",
    how_to_read: "數值越高通常代表預期波動越大；越低代表預期波動較小。",
    higher_lower_or_contextual: "越高通常代表波動壓力較大。",
    important_reference_level: "應與自身歷史分布比較，而不是只看單一固定門檻。",
    important_caveat: "VIX 不是方向預測。單看 VIX 高低無法判斷股市接下來漲跌。"
  },
  finra_margin_debt: {
    plain_name: "投資人融資負債",
    what_it_measures: "FINRA 公布的證券融資帳戶客戶欠款總額。",
    why_it_matters: "這是市場融資曝險的直接衡量，可作為槓桿與風險偏好的重要情境。",
    how_to_read: "應分開看絕對水位、YoY 成長與成長動能。高水位可以同時伴隨成長放慢。",
    higher_lower_or_contextual: "屬於情境指標：更高代表融資借款更多，但方向與動能也很重要。",
    important_reference_level: "與自身歷史比較；沒有單一通用危險門檻。",
    important_caveat: "融資水位高或仍在上升，不代表已經去槓桿。需要看到借款或其成長真正轉弱。"
  },
  finra_margin_debt_yoy_pct: {
    plain_name: "融資餘額年增率",
    what_it_measures: "FINRA 融資餘額相較一年前同月的百分比變化。",
    why_it_matters: "可將槓桿成長速度與絕對金額水位分開觀察。",
    how_to_read: "正值代表融資餘額仍高於一年前；正成長下降代表成長放慢，不代表融資餘額本身一定下降。",
    higher_lower_or_contextual: "屬於情境指標：成長率的方向與變化比單純高低更重要。",
    important_reference_level: "0% 是 YoY 成長與 YoY 衰退的分界。",
    important_caveat: "若絕對水位沒有下降，不應把正成長放慢描述成『融資餘額正在下降』。"
  },
  tw_taiex: {
    plain_name: "台灣加權指數（TAIEX）",
    what_it_measures: "台灣證券交易所發行量加權股價指數的收盤水位。",
    why_it_matters: "提供台灣市場風險與參與度判讀的整體價格背景。",
    how_to_read: "應看變化與歷史比較，而不是只看指數絕對點位。",
    higher_lower_or_contextual: "屬於情境指標：絕對點位本身不是風險分數。",
    important_reference_level: "沒有單一點位能區分安全與危險。",
    important_caveat: "只看 TAIEX 無法知道漲跌是否由多數股票共同參與。"
  },
  tw_advance_decline_pct: {
    plain_name: "台股每日市場參與度",
    what_it_measures: "TWSE 上漲家數與下跌家數的差異，並以有漲跌的股票數標準化。",
    why_it_matters: "可觀察當日市場漲跌是廣泛參與，還是集中在少數股票。",
    how_to_read: "正值代表上漲家數多於下跌；負值代表下跌家數較多。",
    higher_lower_or_contextual: "越低代表當日參與度越弱；趨勢判讀仍需要足夠歷史。",
    important_reference_level: "0% = 上漲與下跌家數相同。",
    important_caveat: "單日廣度只是一個參與度快照；趨勢與百分位需要足夠的已發布歷史。"
  },
  tw_cbc_rate: {
    plain_name: "台灣央行政策利率",
    what_it_measures: "台灣央行政策利率的有效水位與歷次變動。",
    why_it_matters: "政策利率會影響融資環境、折現率與整體總經背景。",
    how_to_read: "觀測日期代表目前利率何時生效；來源驗證日期代表系統最近何時重新確認官方來源。",
    higher_lower_or_contextual: "屬於情境指標：利率水位與調整速度通常比單純高低更重要。",
    important_reference_level: "沒有單一政策利率水位能定義市場壓力。",
    important_caveat: "若利率長期未調整，生效日期很舊不代表資料過期；應同時看最近來源驗證日期。",
    date_semantics: "effective_vs_verified"
  }
};

const signalBeginnerContextZhTW = {
  margin_debt_rollover: {
    plain_name: "融資槓桿動能放慢",
    description: "當融資餘額 YoY 成長不再為正，或 YoY 成長率在三個月內下降至少 10 個百分點時觸發。",
    caveat: "動能條件觸發不代表融資餘額絕對水位已經下降；YoY 仍可能維持正成長。"
  },
  financial_conditions_tight: {
    plain_name: "廣義金融環境轉緊",
    description: "檢查 NFCI 是否高於 0，或約一季內出現明顯收緊。",
    caveat: "這只是金融環境的一項檢查，不是市場方向預測。"
  },
  risk_subindex_extreme: {
    plain_name: "金融風險子指數異常偏高",
    description: "檢查 NFCI risk 子指數是否達到嚴格歷史時點的第 90 百分位以上。",
    caveat: "百分位只描述歷史排名，不代表未來報酬。"
  },
  vix_stress: {
    plain_name: "波動壓力異常偏高",
    description: "檢查 VIX 是否達到嚴格歷史時點的第 90 百分位以上。",
    caveat: "VIX 本身不預測市場方向。"
  },
  market_trend_down: {
    plain_name: "實質總報酬趨勢惡化",
    description: "檢查 Shiller 實質總報酬價格是否低於六個月前。",
    caveat: "這是描述性趨勢條件，不是進出場時點規則。"
  },
  high_low_breadth_collapse: {
    plain_name: "NYSE 高低點廣度異常偏弱",
    description: "檢查標準化 NYSE 高低點廣度是否低於嚴格歷史時點的第 10 百分位。",
    caveat: "若公開資料不可用，狀態維持未知，不會當作未觸發。"
  },
  volume_breadth_collapse: {
    plain_name: "NYSE 成交量廣度異常偏弱",
    description: "檢查 McClellan Volume Summation 是否低於嚴格歷史時點的第 10 百分位。",
    caveat: "若公開資料不可用，狀態維持未知，不會當作未觸發。"
  },
  sp500_50dma_breadth_weak: {
    plain_name: "S&P 500 50 日線參與度異常偏弱",
    description: "檢查具時點正確性的 S&P 500 50DMA 廣度是否低於嚴格歷史時點的第 10 百分位。",
    caveat: "資料不可用或非 PIT 歷史時維持未知，不會被解讀為健康參與度。"
  },
  sp500_200dma_breadth_weak: {
    plain_name: "S&P 500 200 日線參與度異常偏弱",
    description: "檢查具時點正確性的 S&P 500 200DMA 廣度是否低於嚴格歷史時點的第 10 百分位。",
    caveat: "資料不可用或非 PIT 歷史時維持未知，不會被解讀為健康參與度。"
  }
};

let currentLocale = "en";

function normalizeLocale(locale) {
  const value = String(locale || "").trim();
  if (value.toLowerCase().startsWith("zh")) return "zh-TW";
  return "en";
}

function interpolate(message, values = {}) {
  return String(message).replace(/\{(\w+)\}/g, (_, key) =>
    values[key] === undefined || values[key] === null ? "" : String(values[key]),
  );
}

function t(key, values = {}) {
  const table = messages[currentLocale] || messages.en;
  const fallback = messages.en[key] || key;
  return interpolate(table[key] || fallback, values);
}

function getLocale() {
  return currentLocale;
}

function localNumber(value) {
  return Number(value).toLocaleString(currentLocale === "zh-TW" ? "zh-TW" : "en-US");
}

function localizedBeginnerContext(id) {
  const base = beginnerContext[id];
  if (!base) return null;
  if (currentLocale !== "zh-TW") return base;
  return { ...base, ...(beginnerContextZhTW[id] || {}) };
}

function localizedSignalContext(id) {
  const base = signalBeginnerContext[id] || {};
  if (currentLocale !== "zh-TW") return base;
  return { ...base, ...(signalBeginnerContextZhTW[id] || {}) };
}

function pillarLabel(pillar) {
  return t("pillar." + pillar) || pillar;
}

function historyModeLabel(mode) {
  const key = {
    absolute: "mode.absolute",
    pit_percentile: "mode.pitPercentile",
    rolling_percentile: "mode.rollingPercentile",
    rate_change: "mode.rateChange",
  }[mode] || "mode.absolute";
  return t(key);
}

function statusLabel(status) {
  return t("status." + String(status || "unknown").replaceAll(" ", "_"));
}

function applyStaticTranslations() {
  if (!document?.documentElement) return;
  document.documentElement.lang = currentLocale;
  document.title = t("meta.title");
  const description = document.querySelector?.('meta[name="description"]');
  if (description) description.setAttribute("content", t("meta.description"));

  document.querySelectorAll?.("[data-i18n]").forEach((element) => {
    element.textContent = t(element.dataset.i18n);
  });
  document.querySelectorAll?.("[data-i18n-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
  });

  const selector = $("#language-select");
  if (selector) selector.value = currentLocale;
}

function rerenderLocalizedUi() {
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

function setLocale(locale, { persist = true, rerender = true } = {}) {
  currentLocale = normalizeLocale(locale);
  if (persist) localStorage.setItem(LOCALE_STORAGE_KEY, currentLocale);
  applyStaticTranslations();
  if (rerender) rerenderLocalizedUi();
  if (typeof CustomEvent !== "undefined") {
    window.dispatchEvent?.(new CustomEvent("mrm:localechange", {
      detail: { locale: currentLocale },
    }));
  }
}

function initLocale() {
  const saved = localStorage.getItem(LOCALE_STORAGE_KEY);
  const browserLocale = window.navigator?.language || window.navigator?.languages?.[0] || "en";
  currentLocale = normalizeLocale(saved || browserLocale);
  applyStaticTranslations();
  $("#language-select")?.addEventListener("change", (event) => {
    setLocale(event.currentTarget.value);
  });
}

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
  const locale = currentLocale === "zh-TW" ? "zh-TW" : "en-US";

  if (units === "USD millions") {
    if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}T`;
    if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(1)}B`;
    return `$${v.toFixed(0)}M`;
  }
  if (units === "percent") return `${v.toFixed(Math.abs(v) >= 10 ? 1 : 2)}%`;
  if (units === "percentile") return ordinal(v);
  if (units === "ratio") return `${v.toFixed(2)}×`;
  if (units === "binary") return currentLocale === "zh-TW" ? (v ? "是" : "否") : (v ? "Yes" : "No");
  if (units === "basis points") return `${v >= 0 ? "+" : ""}${v.toFixed(1)} bp`;
  if (Math.abs(v) >= 1000) {
    return v.toLocaleString(locale, { maximumFractionDigits: 1 });
  }
  return v.toLocaleString(locale, { maximumFractionDigits: 2 });
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
  return `<span class="badge ${cls}">${escapeHtml(statusLabel(status))}</span>`;
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
  if (currentLocale === "zh-TW") return `第 ${n} 百分位`;
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
    return t("window.lastYears", {
      count: localNumber(rounded),
      plural: currentLocale === "en" && rounded !== 1 ? "s" : "",
    });
  }
  return t("window.lastObservations", { count: localNumber(window) });
}

function percentilePresentation(metric, value = rollingPercentile(metric)) {
  if (value == null) {
    return {
      value: "—",
      label: t("percentile.notEnough"),
      sentence: t("percentile.unavailable"),
    };
  }
  const rounded = Math.round(value);
  const window = rollingWindowLabel(metric);
  const displayRank = currentLocale === "zh-TW" ? `第 ${rounded} 百分位` : ordinal(rounded);
  return {
    value: displayRank,
    label: t("percentile.label", { window }),
    sentence: t("percentile.sentence", { percent: rounded, window }),
  };
}

function metricDateLine(metric) {
  const context = localizedBeginnerContext(metric?.metric?.id);
  const asOf = metric?.latest?.as_of || "unknown";
  if (context?.date_semantics === "effective_vs_verified") {
    const verified = String(metric?.latest?.fetched_at || "").slice(0, 10) || "unknown";
    return t("date.effectiveVerified", { asOf, verified });
  }
  return t("date.asOf", { asOf });
}

function metricContextGuide(metric) {
  const context = localizedBeginnerContext(metric?.metric?.id);
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
    parts.push(t("context.contextOnly"));
  }
  if (rollingPercentileSemantics(metric) === "retrospective") {
    parts.push(t("context.retrospective"));
  }
  return parts.length ? ` · ${parts.join(" · ")}` : "";
}

function percentileCaveatSentence(metric) {
  const parts = [];
  if (metric?.metric?.polarity === "contextual") {
    parts.push(t("context.riskDirection"));
  }
  if (rollingPercentileSemantics(metric) === "retrospective") {
    parts.push(t("context.notPit"));
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
  return t("margin.slowing", {
    value: Math.abs(value).toFixed(1),
    periods,
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
  if (breadth.state === "missing") {
    return t("breadth.none");
  }
  if (breadth.state === "snapshot_only") {
    return t("breadth.oneSession");
  }
  if (breadth.state === "history_building") {
    return t("breadth.historyBuilding", { count: localNumber(breadth.observations) });
  }
  if (breadth.state === "not_current") {
    return t("breadth.notCurrent", { freshness: statusLabel(breadth.freshness) });
  }
  return null;
}

function formatRuleDetail(detail) {
  const parts = [`${detail.label}: ${statusLabel(detail.status)}`];
  if (
    typeof detail.value === "number" &&
    Number.isFinite(detail.value)
  ) {
    const value = detail.value;
    const unit =
      detail.type === "delta_periods_below" && detail.metric === "finra_margin_debt_yoy_pct"
        ? (currentLocale === "zh-TW" ? " 個百分點" : " pp")
        : "";
    parts.push(t("rule.observed", { value: value.toFixed(2), unit }));
  }
  if (detail.asOf) parts.push(t("rule.asOf", { date: detail.asOf }));
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
    : `<span>${escapeHtml(t("snapshot.noSupport"))}</span>`;
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
    .join("") || `<span class="trigger-item">${escapeHtml(t("trigger.none"))}</span>`;
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
  const context = localizedBeginnerContext(metric.metric.id);
  const title = context?.plain_name || metric.metric.name;
  const contextOnly = pct != null ? percentileContextSuffix(metric) : "";

  return `<article class="panel metric-card" data-metric-id="${escapeHtml(metric.metric.id)}" role="button" tabindex="0" aria-label="${escapeHtml(t("metric.openAria", { title }))}">
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
      <div class="context-chip"><strong>${cText}</strong><span>${escapeHtml(t("metric.lastObservation"))}</span></div>
      <div class="context-chip"><strong>${p.value}</strong><span>${escapeHtml(p.label)}${contextOnly}</span></div>
    </div>
    ${sparkline(metric)}
    <div class="metric-card-bottom">
      <span class="meta">${escapeHtml(metric.coverage?.history_start || "—")} → ${escapeHtml(metric.coverage?.history_end || "—")}</span>
      <span class="meta">${escapeHtml(context ? t("metric.explainHistory") : t("metric.openHistory"))}</span>
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
        ? t(nfciValue > 0 ? "overview.stress.tighter" : "overview.stress.looser")
        : t("overview.stress.available"),
    );
  }
  if (vix) {
    const percentile = percentilePresentation(vix);
    stressFacts.push(
      `VIX ${formatValue(vix.latest?.value, vix.metric.units)}${percentile.value !== "—" ? ` · ${percentile.value}` : ""}`,
    );
  }
  setSnapshotCard(
    "stress",
    stressUnknown ? t("status.dataGap") : stressActive ? t("status.elevated") : t("status.clear"),
    stressUnknown ? t("overview.stress.knownCalm") : stressActive ? t("overview.stress.elevated") : t("overview.stress.contained"),
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
      `${formatValue(margin.latest?.value, margin.metric.units)}${marginPct?.value && marginPct.value !== "—" ? ` · ${marginPct.value} (${t("context.contextOnly")})` : ""}`,
    );
  }
  if (marginYoy) {
    leverageFacts.push(`YoY ${formatValue(marginYoy.latest?.value, "percent")}`);
  }
  const slowing = marginStatus === "active" && Number.isFinite(yoy) && yoy > 0;
  setSnapshotCard(
    "leverage",
    !leverageReady ? t("status.dataGap") : slowing ? t("status.watch") : t("status.context"),
    !leverageReady ? t("overview.leverage.incomplete") : slowing ? t("overview.leverage.slowing") : t("overview.leverage.context"),
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
        ? t("overview.marginMomentum")
        : localizedSignalContext(activeConditions[0].id)?.plain_name || activeConditions[0].name)
    : null;

  const deleveragingFacts = [];
  if (activeName) deleveragingFacts.push(activeName);
  if (total) {
    deleveragingFacts.push(t("overview.usable", { known, total, unknown }));
  }
  setSnapshotCard(
    "deleveraging",
    !total
      ? t("status.dataGap")
      : active
        ? `${active} ${currentLocale === "zh-TW" ? "項觸發" : "ACTIVE"}`
        : unknown
          ? t("status.partial")
          : t("status.clear"),
    !total
      ? t("overview.deleveraging.noRead")
      : (active && unknown)
        ? t("overview.deleveraging.notConfirmed")
        : active
          ? t("overview.deleveraging.signs")
          : t("overview.deleveraging.noConfirmation"),
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
    taiwanFacts.push(
      `A/D ${formatValue(twBreadth.latest?.value, "percent")} · ${t("overview.sessions", {
        count: localNumber(breadth.observations),
        plural: currentLocale === "en" && breadth.observations !== 1 ? "s" : "",
      })}`,
    );
  } else {
    taiwanFacts.push(t("overview.taiwan.breadthUnavailable"));
  }

  const taiwanMissing = !taiex || ["missing", "error"].includes(taiexFreshness);
  const taiwanNeedsAttention =
    !taiwanMissing &&
    (taiexFreshness !== "fresh" ||
      ["missing", "not_current", "snapshot_only", "history_building"].includes(breadth.state));
  let taiwanStatus = t("status.current");
  let taiwanHeadline = t("overview.taiwan.available");
  let taiwanState = "normal";
  if (taiwanMissing) {
    taiwanStatus = t("status.dataGap");
    taiwanHeadline = t("overview.taiwan.noRead");
    taiwanState = "gap";
  } else if (taiexFreshness !== "fresh") {
    taiwanStatus = statusLabel(taiexFreshness).toUpperCase();
    taiwanHeadline = t("overview.taiwan.noCall");
    taiwanState = "watch";
  } else if (taiwanNeedsAttention) {
    taiwanStatus = t("status.partial");
    taiwanHeadline = t("overview.taiwan.priceCurrent");
    taiwanState = "watch";
  }
  setSnapshotCard(
    "taiwan",
    taiwanStatus,
    taiwanHeadline,
    taiwanFacts,
    taiwanState,
  );

  const metrics = [...state.metrics.values()];
  const health = globalFreshnessSummary(metrics);
  const snapshotDate = String(
    state.catalog?.generated_at || state.refreshReport?.generated_at || "",
  ).slice(0, 10);
  const healthParts = [];
  if (health.counts.error) healthParts.push(t("health.count.error", { count: health.counts.error }));
  if (health.counts.missing) healthParts.push(t("health.count.missing", { count: health.counts.missing }));
  if (health.counts.stale) healthParts.push(t("health.count.stale", { count: health.counts.stale }));
  if (health.counts.insufficient_data) {
    healthParts.push(t("health.count.insufficient", { count: health.counts.insufficient_data }));
  }
  if (unknown) healthParts.push(t("health.count.unknownChecks", { count: unknown }));
  if (snapshotDate) healthParts.push(t("health.snapshotDate", { date: snapshotDate }));

  const healthHasHardGap = Boolean(health.counts.error || health.counts.missing);
  const healthNeedsRefresh = Boolean(health.counts.stale);
  const healthHasEvidenceGap = Boolean(unknown);
  const marginRank = margin ? rollingPercentile(margin) : null;
  const leverageElevated = Number.isFinite(marginRank) && marginRank >= 90;

  let thesisTitle;
  if (stressActive) {
    thesisTitle = active
      ? t("thesis.stressAndDeleveraging")
      : t("thesis.stressNotConfirmed");
  } else if (slowing) {
    thesisTitle = t("thesis.rollover");
  } else if (leverageElevated) {
    thesisTitle = t("thesis.stretched");
  } else if (stressUnknown) {
    thesisTitle = t("thesis.partial");
  } else {
    thesisTitle = t("thesis.noBroadStress");
  }

  const thesisParts = [];
  if (stressActive) {
    thesisParts.push(t("thesis.stressElevated"));
  } else if (stressUnknown) {
    thesisParts.push(t("thesis.stressPartial"));
  } else {
    thesisParts.push(t("thesis.stressCalm"));
  }
  if (Number.isFinite(yoy)) {
    thesisParts.push(
      slowing
        ? t("thesis.marginSlowing", { yoy: formatValue(yoy, "percent") })
        : t("thesis.marginGrowth", { yoy: formatValue(yoy, "percent") }),
    );
  }
  if (total) {
    thesisParts.push(t("thesis.checks", {
      known,
      total,
      active,
      verb: active === 1 ? "is" : "are",
    }));
  }

  let thesisConfidence = t("thesis.confidence.high");
  let thesisState = "normal";
  if (!total || unknown >= Math.ceil(Math.max(total, 1) / 2) || stressUnknown) {
    thesisConfidence = t("thesis.confidence.low");
    thesisState = "gap";
  } else if (unknown || healthNeedsRefresh) {
    thesisConfidence = t("thesis.confidence.medium");
    thesisState = "watch";
  }
  if (healthNeedsRefresh) {
    thesisConfidence += ` · ${t("thesis.confidence.stale")}`;
    if (thesisState === "normal") thesisState = "watch";
  }

  const stressEvidenceState = stressActive
    ? t("thesis.evidence.stressElevated")
    : stressUnknown
      ? t("thesis.evidence.stressPartial")
      : t("thesis.evidence.stressCalm");
  const leverageRank = Number.isFinite(marginRank)
    ? (currentLocale === "zh-TW"
        ? `${formatValue(marginRank, "percentile")}（近 10 年）`
        : `${formatValue(marginRank, "percentile")} vs 10y`)
    : (currentLocale === "zh-TW" ? "資料可用" : "available");
  const leverageYoy = Number.isFinite(yoy)
    ? ` · YoY ${formatValue(yoy, "percent")}`
    : "";

  const thesisEvidence = [
    t("thesis.evidence.stress", { state: stressEvidenceState }),
    margin ? t("thesis.evidence.leverage", { rank: leverageRank, yoy: leverageYoy }) : null,
    total ? t("thesis.evidence.deleveraging", { active, known }) : null,
    snapshotDate ? t("thesis.evidence.snapshot", { date: snapshotDate }) : null,
  ];

  const nfciTrigger = findRuleLeaf(financialCondition, (rule) => rule.type === "latest_above");
  const vixTrigger = findRuleLeaf(vixStress, (rule) => rule.type === "percentile_above");
  const marginTrigger = findRuleLeaf(marginSignal, (rule) => rule.type === "latest_below");
  const breadthCondition = signalCondition("high_low_breadth_collapse");
  const breadthTrigger = findRuleLeaf(breadthCondition, (rule) => rule.type === "percentile_below");
  const breadthThreshold = Number(breadthTrigger?.threshold);
  const thesisTriggers = [
    {
      label: t("thesis.trigger.stress"),
      text: nfciTrigger && vixTrigger
        ? (currentLocale === "zh-TW"
            ? `NFCI ≥ ${nfciTrigger.threshold} 或 VIX ≥ 第 ${vixTrigger.threshold} 百分位`
            : `NFCI ≥ ${nfciTrigger.threshold} or VIX ≥ ${vixTrigger.threshold}th percentile`)
        : t("thesis.trigger.stressFallback"),
    },
    {
      label: t("thesis.trigger.rollover"),
      text: marginTrigger
        ? `Margin-debt YoY ≤ ${marginTrigger.threshold}%`
        : t("thesis.trigger.marginFallback"),
    },
    {
      label: t("thesis.trigger.breadth"),
      text: Number.isFinite(breadthThreshold)
        ? (currentLocale === "zh-TW"
            ? `NYSE 高低點廣度 ≤ 第 ${breadthThreshold} 百分位`
            : `NYSE High-Low breadth ≤ ${breadthThreshold}th percentile`)
        : t("thesis.trigger.breadthFallback"),
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
    healthHasHardGap
      ? t("health.sourceIssues")
      : healthNeedsRefresh
        ? t("health.needsRefresh")
        : healthHasEvidenceGap
          ? t("health.evidenceGaps")
          : t("health.snapshotCurrent"),
    healthParts.join(" · ") || t("health.noSnapshot"),
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
      `<div class="panel empty-state"><strong>${escapeHtml(t("metric.usUnavailable"))}</strong><span>${escapeHtml(t("metric.noPlaceholder"))}</span></div>`;
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
        <p class="eyebrow">${escapeHtml(pillarLabel(pillar))}</p>
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
        <td>${escapeHtml(pillarLabel(m.metric.pillar))}</td>
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
      : historyModeLabel(mode);

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
  const context = localizedBeginnerContext(id);
  $("#dialog-pillar").textContent =
    pillarLabel(summary.metric.pillar);
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
      const beginner = localizedSignalContext(condition.id) || {};
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
      text: t("health.noSnapshot"),
    };
  }

  const parts = [
    counts.error ? t("health.count.error", { count: counts.error }) : "",
    counts.missing ? t("health.count.missing", { count: counts.missing }) : "",
    counts.stale ? t("health.count.stale", { count: counts.stale }) : "",
    counts.insufficient_data ? t("health.count.insufficient", { count: counts.insufficient_data }) : "",
  ].filter(Boolean);

  if (!parts.length) {
    return {
      counts,
      className: "health-passive",
      text: t("health.dataCurrent"),
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

initLocale();
initTheme();
setupDialogFocusManagement();
$("#refresh-view").addEventListener("click", loadData);
$("#ma-bands-toggle")?.addEventListener("change", renderTrendParticipationChart);
$("#ma-spx-toggle")?.addEventListener("change", renderTrendParticipationChart);
loadData();
