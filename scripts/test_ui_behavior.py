#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    node = shutil.which("node")
    if not node:
        print(
            "FAIL Node.js is required for executable UI behavior tests.",
            file=sys.stderr,
        )
        return 2

    command = [
        node,
        "--test",
        str(ROOT / "tests" / "ui_behavior.test.mjs"),
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
