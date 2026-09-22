from __future__ import annotations

import json
from pathlib import Path

from .presentation import apply_presentation

"""
The single write path for generated artifacts.

Four separate copies of an atomic_json() helper used to exist -- in
scripts/refresh_data.py, scripts/bootstrap_taiwan_taiex.py,
scripts/build_ma_breadth_self_compute.py and inline in
pipeline/taiwan_trend_breadth.py. Copies do not receive changes: when
metric.comparison became required by the JSON schema, only the refresh_data
copy learned to stamp it, and the other three silently produced artifacts that
scripts/validate_data.py rejects.

Everything that writes a canonical artifact goes through here, so a change to
what "finished artifact" means reaches every producer.
"""


def write_json_artifact(path: Path, payload: dict) -> dict:
    """
    Finalize and atomically write an artifact. Returns what was written.

    Finalizing declares presentation semantics on metric artifacts; non-metric
    payloads pass through untouched.
    """
    payload = apply_presentation(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)
    return payload
