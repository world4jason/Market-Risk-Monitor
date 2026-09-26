from __future__ import annotations

import json
import math
import re
from datetime import date
from http.cookiejar import CookieJar
from urllib.request import HTTPCookieProcessor, Request, build_opener


class NDCBusinessCycleError(ValueError):
    pass


NDC_ROOT = "https://index.ndc.gov.tw"
NDC_PAGE_URL = f"{NDC_ROOT}/n/zh_tw/lightscore"
SERIES = {
    "lightscore": {
        "series_id": "tw_ndc_monitoring_score",
        "unit": "score",
        "page_url": f"{NDC_ROOT}/n/zh_tw/lightscore",
    },
    "leading": {
        "series_id": "tw_ndc_leading_index",
        "unit": "index",
        "page_url": f"{NDC_ROOT}/n/zh_tw/leading",
    },
    "coincident": {
        "series_id": "tw_ndc_coincident_index",
        "unit": "index",
        "page_url": f"{NDC_ROOT}/n/zh_tw/coincident",
    },
    "lagged": {
        "series_id": "tw_ndc_lagging_index",
        "unit": "index",
        "page_url": f"{NDC_ROOT}/n/zh_tw/lagged",
    },
}


def _parse_month(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{6}", value):
        raise NDCBusinessCycleError(f"invalid NDC month {value!r}")
    year = int(value[:4])
    month = int(value[4:])
    if year < 1900 or not 1 <= month <= 12:
        raise NDCBusinessCycleError(f"invalid NDC month {value!r}")
    return f"{year:04d}-{month:02d}-01"


def _month_number(value: str) -> int:
    return int(value[:4]) * 12 + int(value[5:7]) - 1


def parse_ndc_snapshot_json(text: str) -> dict:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NDCBusinessCycleError("NDC snapshot is not valid JSON") from exc
    validate_ndc_snapshot(payload)
    return payload


def validate_ndc_snapshot(payload: object) -> None:
    if not isinstance(payload, dict):
        raise NDCBusinessCycleError("NDC snapshot must be an object")

    missing = sorted(set(SERIES) - set(payload))
    if missing:
        raise NDCBusinessCycleError(
            f"NDC snapshot missing required series: {', '.join(missing)}"
        )

    expected_months: list[str] | None = None
    expected_next: str | None = None
    for source_key, spec in SERIES.items():
        block = payload.get(source_key)
        if not isinstance(block, dict):
            raise NDCBusinessCycleError(f"NDC {source_key}: payload must be an object")
        line = block.get("line")
        if not isinstance(line, list) or len(line) != 12:
            raise NDCBusinessCycleError(
                f"NDC {source_key}: expected exactly 12 monthly line points"
            )

        months: list[str] = []
        seen: set[str] = set()
        for index, point in enumerate(line):
            if not isinstance(point, dict):
                raise NDCBusinessCycleError(
                    f"NDC {source_key}: point {index} must be an object"
                )
            obs_date = _parse_month(point.get("x"))
            if obs_date in seen:
                raise NDCBusinessCycleError(
                    f"NDC {source_key}: duplicate month {obs_date}"
                )
            seen.add(obs_date)
            months.append(obs_date)

            value = point.get("y")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise NDCBusinessCycleError(
                    f"NDC {source_key}: non-numeric value at {obs_date}"
                )
            if not math.isfinite(float(value)):
                raise NDCBusinessCycleError(
                    f"NDC {source_key}: non-finite value at {obs_date}"
                )
            if source_key == "lightscore":
                if float(value) != int(value) or not 9 <= int(value) <= 45:
                    raise NDCBusinessCycleError(
                        f"NDC lightscore: score outside canonical 9..45 at {obs_date}"
                    )

        if months != sorted(months):
            raise NDCBusinessCycleError(f"NDC {source_key}: months not ascending")
        for left, right in zip(months, months[1:]):
            if _month_number(right) != _month_number(left) + 1:
                raise NDCBusinessCycleError(
                    f"NDC {source_key}: rolling window is not contiguous"
                )

        if expected_months is None:
            expected_months = months
        elif months != expected_months:
            raise NDCBusinessCycleError(
                f"NDC {source_key}: month window differs from other series"
            )

        next_update = block.get("next")
        if not isinstance(next_update, str) or not next_update.strip():
            raise NDCBusinessCycleError(f"NDC {source_key}: next update missing")
        if expected_next is None:
            expected_next = next_update
        elif next_update != expected_next:
            raise NDCBusinessCycleError(
                f"NDC {source_key}: next update differs from other series"
            )


def to_macro_rows(payload: dict, *, observed_at: date) -> list[dict]:
    validate_ndc_snapshot(payload)
    rows: list[dict] = []
    for source_key, spec in SERIES.items():
        for point in payload[source_key]["line"]:
            rows.append(
                {
                    "date": _parse_month(point["x"]),
                    "provider": "NDC",
                    "series_id": spec["series_id"],
                    "value": point["y"],
                    "unit": spec["unit"],
                    "release_date": observed_at.isoformat(),
                    "source_url": spec["page_url"],
                }
            )
    rows.sort(key=lambda row: (row["series_id"], row["date"]))
    return rows


def merge_current_vintage_rows(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Retain older months while replacing overlap with the newest verified snapshot.

    Retained months are latest-observed vintages, not PIT history. The verification
    watermark must never move backwards.
    """
    if not incoming:
        raise NDCBusinessCycleError("incoming NDC snapshot is empty")
    incoming_watermarks = {row["release_date"] for row in incoming}
    if len(incoming_watermarks) != 1:
        raise NDCBusinessCycleError("incoming NDC snapshot has mixed verification dates")
    incoming_watermark = next(iter(incoming_watermarks))

    existing_watermarks = [row["release_date"] for row in existing]
    if existing_watermarks and incoming_watermark < max(existing_watermarks):
        raise NDCBusinessCycleError(
            "refusing stale NDC snapshot replay: incoming verification date "
            f"{incoming_watermark} < stored {max(existing_watermarks)}"
        )

    merged = {
        (row["series_id"], row["date"]): dict(row)
        for row in existing
    }
    for row in incoming:
        merged[(row["series_id"], row["date"])] = dict(row)
    return sorted(merged.values(), key=lambda row: (row["series_id"], row["date"]))


def fetch_ndc_snapshot(*, timeout: int = 30) -> dict:
    """Fetch the four public NDC chart JSON payloads through a browser-like session."""
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    page_request = Request(
        NDC_PAGE_URL,
        headers={"User-Agent": "Market-Risk-Monitor/1.0"},
    )
    with opener.open(page_request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="replace")

    token_match = re.search(
        r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)',
        html,
        flags=re.IGNORECASE,
    )
    if token_match is None:
        token_match = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']csrf-token["\']',
            html,
            flags=re.IGNORECASE,
        )
    if token_match is None:
        raise NDCBusinessCycleError("NDC page did not expose a CSRF token")
    csrf = token_match.group(1)

    payload: dict[str, dict] = {}
    for source_key in SERIES:
        endpoint = f"{NDC_ROOT}/n/json/{source_key}"
        request = Request(
            endpoint,
            data=b"",
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": NDC_PAGE_URL,
                "User-Agent": "Market-Risk-Monitor/1.0",
                "X-CSRF-TOKEN": csrf,
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        with opener.open(request, timeout=timeout) as response:
            try:
                payload[source_key] = json.loads(response.read().decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise NDCBusinessCycleError(
                    f"NDC {source_key} endpoint returned invalid JSON"
                ) from exc

    validate_ndc_snapshot(payload)
    return payload
