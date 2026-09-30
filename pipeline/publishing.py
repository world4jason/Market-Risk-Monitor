from __future__ import annotations

import json
from pathlib import Path


class PublishingPolicyError(ValueError):
    pass


def load_policy(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0.0":
        raise PublishingPolicyError("unsupported publishing policy schema")
    families = payload.get("source_families")
    if not isinstance(families, list) or not families:
        raise PublishingPolicyError("publishing policy requires source_families")
    seen = {}
    for family in families:
        decision = family.get("decision")
        if decision not in {"publish", "local_only"}:
            raise PublishingPolicyError(
                f"invalid decision for {family.get('id')}: {decision}"
            )
        if not family.get("review_status") or not family.get("terms_url"):
            raise PublishingPolicyError(
                f"{family.get('id')} lacks review_status/terms_url"
            )
        for metric_id in family.get("metric_ids", []):
            if metric_id in seen:
                raise PublishingPolicyError(
                    f"metric {metric_id} appears in both {seen[metric_id]} and {family.get('id')}"
                )
            seen[metric_id] = family.get("id")
    return payload


def metric_decisions(policy: dict) -> dict[str, dict]:
    out = {}
    for family in policy["source_families"]:
        for metric_id in family.get("metric_ids", []):
            out[metric_id] = family
    return out


def _provenance_ids(payload: dict) -> set[str]:
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        return set()

    # required_inputs can include configured-but-unavailable optional metrics.
    # Publication risk comes from inputs actually consumed into this artifact.
    ids = set()
    for item in provenance.get("inputs") or []:
        if isinstance(item, dict) and item.get("id"):
            ids.add(item["id"])
    return ids


def validate_public_release(
    paths: list[Path],
    policy: dict,
) -> list[str]:
    decisions = metric_decisions(policy)
    local_only = {
        metric_id
        for metric_id, family in decisions.items()
        if family["decision"] == "local_only"
    }
    checked = []

    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        meta = payload.get("metric")
        if isinstance(meta, dict) and "observations" in payload:
            metric_id = meta.get("id")
            family = decisions.get(metric_id)
            if family is None:
                raise PublishingPolicyError(
                    f"{path.name}: metric {metric_id!r} has no publishing decision"
                )
            if family["decision"] != "publish":
                raise PublishingPolicyError(
                    f"{path.name}: {metric_id} is {family['decision']} ({family['id']})"
                )
            redistribution = payload.get("source", {}).get("redistribution")
            if redistribution == "restricted":
                raise PublishingPolicyError(
                    f"{path.name}: restricted source cannot enter a public release"
                )
            checked.append(metric_id)

        blocked_inputs = sorted(_provenance_ids(payload) & local_only)
        if blocked_inputs:
            raise PublishingPolicyError(
                f"{path.name}: provenance references local-only inputs: "
                + ", ".join(blocked_inputs)
            )

    return checked
