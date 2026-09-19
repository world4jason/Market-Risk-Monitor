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


if __name__ == "__main__":
    unittest.main()
