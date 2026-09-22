from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    async_start = source.rfind("async ", max(0, start - 8), start)
    if async_start >= 0 and source[async_start:start] == "async ":
        start = async_start
    brace = source.index("{", start)

    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    i = brace
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if line_comment:
            if char == "\n":
                line_comment = False
            i += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                i += 2
                continue
            i += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            i += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if char in ("'", '"', chr(96)):
            quote = char
            i += 1
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
        i += 1

    raise AssertionError(f"unterminated function: {name}")


class LazyLoadingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")

    def test_default_load_uses_overview_without_catalog_history_enumeration(self) -> None:
        load_data = extract_function(self.app, "loadData")
        self.assertIn("OVERVIEW_URL", load_data)
        self.assertIn("overview.metrics", load_data)

        # The old eager path iterated every catalog entry and fetched its path.
        self.assertNotIn("entries.map", load_data)
        self.assertNotIn("entry.path", load_data)
        self.assertNotIn("Promise.all(\n      entries.map", load_data)

    def test_full_metric_loader_is_single_flight_and_session_cached(self) -> None:
        loader = extract_function(self.app, "ensureMetricLoaded")
        self.assertIn("Array.isArray(existing?.observations)", loader)
        self.assertIn("state.metricLoads.has(id)", loader)
        self.assertIn("state.metricLoads.set(id, promise)", loader)
        self.assertIn("state.metrics.set(id, metric)", loader)
        self.assertIn('cache: "no-cache"', loader)

    def test_detail_and_research_paths_use_the_lazy_loader(self) -> None:
        for name in ("openMetric", "renderHistory", "renderTaiwanEventSelector"):
            with self.subTest(name=name):
                fn = extract_function(self.app, name)
                self.assertIn("ensureMetricLoaded", fn)

    def test_summary_helpers_do_not_require_full_observation_history(self) -> None:
        for name, expected in (
            ("rollingPercentile", "metric.summary.rolling_percentile"),
            ("recentChange", "metric.summary.recent_change"),
            ("usableObservationCount", "metric.summary.observation_count"),
            ("sparkline", "metric?.summary?.preview_observations"),
        ):
            with self.subTest(name=name):
                self.assertIn(expected, extract_function(self.app, name))

    def test_current_snapshot_uses_no_store_but_history_revalidates(self) -> None:
        load_data = extract_function(self.app, "loadData")
        self.assertIn('fetch(OVERVIEW_URL, { cache: "no-store" })', load_data)
        self.assertIn('fetch(CATALOG_URL, { cache: "no-store" })', load_data)
        self.assertIn('fetch(SIGNALS_URL, { cache: "no-store" })', load_data)

        loader = extract_function(self.app, "ensureMetricLoaded")
        self.assertIn('fetch(url, { cache: "no-cache" })', loader)


if __name__ == "__main__":
    unittest.main()
