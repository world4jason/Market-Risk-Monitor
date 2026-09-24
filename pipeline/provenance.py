from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Iterable


PROVENANCE_CONTRACT_VERSION = "1.0.0"


def canonical_json_bytes(payload) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def content_digest(payload) -> str:
    return "sha256:" + hashlib.sha256(
        canonical_json_bytes(payload)
    ).hexdigest()


def _as_utc_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if len(text) == 10:
            text = f"{text}T00:00:00+00:00"
        elif text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso_datetime(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc_datetime(value).isoformat().replace("+00:00", "Z")


def metric_input(metric: dict) -> dict:
    metric_id = metric.get("metric", {}).get("id")
    if not metric_id:
        raise ValueError("provenance metric input requires metric.id")
    latest = metric.get("latest", {})
    present = [
        obs
        for obs in metric.get("observations", [])
        if obs.get("value") is not None
    ]
    as_of = (
        latest.get("as_of")
        or (present[-1].get("date") if present else None)
    )
    snapshot_at = (
        latest.get("fetched_at")
        or (f"{as_of}T00:00:00Z" if as_of else None)
    )
    return {
        "id": metric_id,
        "as_of": as_of,
        "snapshot_at": _iso_datetime(snapshot_at),
        "content_digest": content_digest(metric),
    }


def records_input(
    input_id: str,
    records,
    *,
    as_of: str | None,
    snapshot_at: str | datetime | None,
) -> dict:
    if not input_id:
        raise ValueError("provenance input id is required")
    return {
        "id": input_id,
        "as_of": as_of,
        "snapshot_at": _iso_datetime(snapshot_at),
        "content_digest": content_digest(records),
    }


def _default_generated_at(inputs: list[dict]) -> str:
    snapshots = [
        _as_utc_datetime(item["snapshot_at"])
        for item in inputs
        if item.get("snapshot_at")
    ]
    if snapshots:
        return max(snapshots).isoformat().replace("+00:00", "Z")

    as_of = [
        item.get("as_of")
        for item in inputs
        if item.get("as_of")
    ]
    if as_of:
        return f"{max(as_of)}T00:00:00Z"
    return "1970-01-01T00:00:00Z"


def build_provenance(
    *,
    methodology_id: str,
    methodology_version: str,
    config_id: str,
    config: dict,
    inputs: Iterable[dict],
    required_input_ids: Iterable[str] | None = None,
    generated_at: str | datetime | None = None,
    build_revision: str | None = None,
) -> dict:
    manifest = []
    for item in inputs:
        normalized = dict(item)
        if normalized.get("snapshot_at") is not None:
            normalized["snapshot_at"] = _iso_datetime(
                normalized["snapshot_at"]
            )
        manifest.append(normalized)
    manifest.sort(key=lambda item: item["id"])
    required = sorted(
        set(required_input_ids or [item["id"] for item in manifest])
    )
    if not methodology_id or not methodology_version:
        raise ValueError("methodology id/version are required")
    if not config_id:
        raise ValueError("config id is required")
    if not required:
        raise ValueError("at least one required provenance input is required")
    provenance = {
        "contract_version": PROVENANCE_CONTRACT_VERSION,
        "methodology": {
            "id": methodology_id,
            "version": methodology_version,
        },
        "config": {
            "id": config_id,
            "content_digest": content_digest(config),
        },
        "required_inputs": required,
        "inputs": manifest,
        "generated_at": (
            _iso_datetime(generated_at)
            or _default_generated_at(manifest)
        ),
    }
    if build_revision:
        provenance["build_revision"] = build_revision
    return provenance
