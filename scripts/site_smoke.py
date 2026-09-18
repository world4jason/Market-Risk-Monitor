#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    required = [
        ROOT / ".nojekyll",
        ROOT / "index.html",
        ROOT / "assets" / "app.js",
        ROOT / "assets" / "styles.css",
        ROOT / "data" / "events.json",
        ROOT / "data" / "generated" / "catalog.json",
    ]
    for path in required:
        if not path.exists():
            fail(f"required static asset missing: {path.relative_to(ROOT)}")

    workflows = ROOT / ".github" / "workflows"
    if workflows.exists() and any(workflows.iterdir()):
        fail("GitHub Actions workflow files exist, but this project is intentionally no-GHA")

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    app = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")

    root_absolute = re.findall(r'(?:src|href)=["\']/(?!/)[^"\']+', html)
    if root_absolute:
        fail(f"root-absolute asset URLs break project Pages: {root_absolute}")

    required_relative_refs = [
        './assets/styles.css',
        './assets/app.js',
        './data/generated/catalog.json',
        './data/events.json',
    ]
    combined = html + "\n" + app
    missing_refs = [ref for ref in required_relative_refs if ref not in combined]
    if missing_refs:
        fail(f"expected project-relative references missing: {missing_refs}")

    catalog_path = ROOT / "data" / "generated" / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    for metric in catalog.get("metrics", []):
        path = metric.get("path", "")
        if not path.startswith("./"):
            fail(f"catalog path is not project-relative: {metric.get('id')}={path}")

    print("OK static GitHub Pages smoke checks")
    print("Pages source must be configured manually as: main / (root)")


if __name__ == "__main__":
    main()
