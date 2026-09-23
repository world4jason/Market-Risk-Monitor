from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class UiBehaviorRunnerTests(unittest.TestCase):
    def test_node_behavior_suite(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "test_ui_behavior.py")],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode:
            self.fail(
                "UI behavior suite failed.\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
