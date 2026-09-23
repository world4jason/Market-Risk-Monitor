from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AccessibilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")

    def test_metric_cards_expose_button_equivalent_semantics(self) -> None:
        self.assertIn('role="button"', self.app)
        self.assertIn('tabindex="0"', self.app)
        self.assertIn('aria-label="Open ${escapeHtml(title)} details and history"', self.app)
        self.assertIn('event.preventDefault()', self.app)
        self.assertIn('openMetric(card.dataset.metricId, card)', self.app)

    def test_keyboard_focus_indicator_is_global_and_visible(self) -> None:
        self.assertIn(':focus-visible', self.styles)
        self.assertRegex(self.styles, r"outline:\s*3px\s+solid\s+var\(--text\)")
        self.assertIn("outline-offset: 3px", self.styles)
        self.assertIn('[role="button"]', self.styles)

    def test_dialog_is_named_and_focus_return_is_managed(self) -> None:
        self.assertIn(
            '<dialog id="metric-dialog" class="metric-dialog" aria-labelledby="dialog-title">',
            self.html,
        )
        self.assertIn('id="dialog-close"', self.html)
        self.assertIn('aria-label="Close metric details"', self.html)
        self.assertIn("function setupDialogFocusManagement()", self.app)
        self.assertIn('dialog.addEventListener("close"', self.app)
        self.assertIn('$("#dialog-close")?.focus()', self.app)

    def test_controls_keep_programmatic_labels(self) -> None:
        for control_id in (
            "theme-toggle",
            "tw-event-metric",
            "tw-event-mode",
            "history-metric",
            "history-mode",
        ):
            pattern = rf'id="{re.escape(control_id)}"[^>]*aria-label="[^"]+"'
            self.assertRegex(self.html, pattern)

        self.assertRegex(
            self.html,
            r'<label class="toggle-control">\s*<input id="ma-bands-toggle"',
        )
        self.assertRegex(
            self.html,
            r'<label class="toggle-control">\s*<input id="ma-spx-toggle"',
        )

    def test_chart_accessibility_has_names_and_nonvisual_summary(self) -> None:
        self.assertIn("function chartA11y(", self.app)
        self.assertIn("function metricChartSummary(", self.app)
        self.assertIn('class="sr-only"', self.app)
        self.assertIn("aria-describedby=", self.app)
        self.assertGreaterEqual(self.app.count("chartA11y("), 6)

    def test_color_is_not_the_only_status_channel(self) -> None:
        self.assertIn('class="badge ', self.app)
        self.assertIn('class="signal-status"', self.app)
        self.assertIn("freshnessBadge(metric)", self.app)
        self.assertIn("condition.displayStatus", self.app)


if __name__ == "__main__":
    unittest.main()
