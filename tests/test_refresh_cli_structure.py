import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFRESH = ROOT / "scripts" / "refresh_data.py"


class RefreshCliStructureTests(unittest.TestCase):
    def setUp(self):
        self.source = REFRESH.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_refresh_ma_breadth_defined_once(self):
        definitions = [
            node
            for node in self.tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "refresh_ma_breadth"
        ]
        self.assertEqual(len(definitions), 1)

    def test_fred_id_allowlist_activates_the_fred_refresh(self):
        # A command built only out of --fred-id must actually refresh FRED.
        # When it did not, the allowlist silently refreshed nothing while
        # previously generated series stayed on disk and were still catalogued,
        # so an allowlist meant to exclude a restricted series looked like it
        # had worked.
        self.assertIn(
            "run_fred = args.fred or args.public or bool(args.fred_id)",
            self.source,
        )

    def test_ma_breadth_cli_option_declared_once(self):
        self.assertEqual(self.source.count('"--ma-breadth-file"'), 1)

    def test_ma_breadth_execution_branch_declared_once(self):
        self.assertEqual(self.source.count("if args.ma_breadth_file:"), 1)

    def test_special_artifacts_not_loaded_as_metrics(self):
        for filename in [
            "catalog.json",
            "refresh-report.json",
            "signals.json",
            "coverage.json",
            "ma-breadth-audit.json",
            "ma-breadth-event-study.json",
        ]:
            self.assertIn(filename, self.source)

    def test_taiwan_cli_options_declared_once(self):
        for option in [
            '"--twse-current"',
            '"--twse-breadth-file"',
            '"--taiwan-trend-panel"',
            '"--taiwan-macro-file"',
            '"--cbc-rate-file"',
        ]:
            self.assertEqual(self.source.count(option), 1)

    def test_taiwan_refresh_functions_defined_once(self):
        expected = [
            "refresh_twse_current",
            "refresh_twse_breadth_file",
            "refresh_taiwan_trend_panel",
            "refresh_taiwan_macro_file",
            "refresh_cbc_rate_file",
        ]
        for name in expected:
            definitions = [
                node
                for node in self.tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == name
            ]
            self.assertEqual(len(definitions), 1, name)


if __name__ == "__main__":
    unittest.main()
