#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.publishing import load_policy, validate_public_release


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default=str(ROOT / "data" / "config" / "publishing.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "data" / "generated"),
    )
    args = parser.parse_args()

    policy = load_policy(args.policy)
    paths = sorted(Path(args.output_dir).glob("*.json"))
    if not paths:
        raise SystemExit("No generated JSON files found.")

    checked = validate_public_release(paths, policy)
    print(
        f"publish-policy OK files={len(paths)} metric_artifacts={len(checked)} "
        f"policy={args.policy}"
    )


if __name__ == "__main__":
    main()
