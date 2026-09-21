from __future__ import annotations

import csv
import io
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TWSE_OPENAPI_BASE = "https://openapi.twse.com.tw/v1"
TWSE_FMTQIK_URL = f"{TWSE_OPENAPI_BASE}/exchangeReport/FMTQIK"
TWSE_TAIEX_MONTH_URL = "https://www.twse.com.tw/rwd/en/TAIEX/MI_5MINS_HIST"
TWSE_MI_INDEX_URL = "https://www.twse.com.tw/exchangeReport/MI_INDEX"
TWSE_UPDOWN_CSV_URL = "https://dts.twse.com.tw/opendata/twtazu_od.csv"


class TaiwanTwseError(ValueError):
    pass


def roc_date_to_iso(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise TaiwanTwseError("blank date")

    # Already-Gregorian ISO.
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        pass

    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) == 8 and int(digits[:4]) >= 1900:
        return date(
            int(digits[:4]),
            int(digits[4:6]),
            int(digits[6:8]),
        ).isoformat()

    # ROC date, e.g. 1150901 or 115/09/01.
    if len(digits) in {6, 7}:
        year_digits = len(digits) - 4
        roc_year = int(digits[:year_digits])
        month = int(digits[year_digits : year_digits + 2])
        day = int(digits[year_digits + 2 :])
        return date(roc_year + 1911, month, day).isoformat()

    raise TaiwanTwseError(f"unrecognized Taiwan/TWSE date: {value!r}")


def _number(value, *, integer: bool = False):
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "---", "N/A", "NA"}:
        return None
    number = float(text)
    if integer:
        if not number.is_integer():
            raise TaiwanTwseError(f"expected integer value, got {value!r}")
        return int(number)
    return number


def _fetch_text(url: str, *, timeout: int = 30) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Market-Risk-Monitor/0.3 "
                "(Taiwan official-data adapter; "
                "https://github.com/world4jason/Market-Risk-Monitor)"
            )
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            content_type = response.headers.get_content_charset()
            if content_type:
                return raw.decode(content_type)
            for encoding in ("utf-8-sig", "utf-8", "big5"):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue
            raise TaiwanTwseError(f"could not decode {url}")
    except Exception as exc:
        raise TaiwanTwseError(f"failed to fetch {url}: {exc}") from exc


def fetch_fmtqik_current(timeout: int = 30) -> str:
    return _fetch_text(TWSE_FMTQIK_URL, timeout=timeout)


def fetch_taiex_month(year: int, month: int, timeout: int = 30) -> str:
    params = urlencode(
        {"date": f"{year:04d}{month:02d}01", "response": "json"}
    )
    return _fetch_text(f"{TWSE_TAIEX_MONTH_URL}?{params}", timeout=timeout)


def fetch_market_breadth_day(
    day: str,
    timeout: int = 30,
) -> str:
    iso = date.fromisoformat(day).strftime("%Y%m%d")
    params = urlencode(
        {"response": "json", "date": iso, "type": "MS"}
    )
    return _fetch_text(f"{TWSE_MI_INDEX_URL}?{params}", timeout=timeout)


def parse_fmtqik_json(text: str) -> list[dict]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TaiwanTwseError("FMTQIK response is not valid JSON") from exc

    if isinstance(payload, dict):
        # Some TWSE web endpoints use fields/data rather than OpenAPI list.
        fields = payload.get("fields") or []
        data = payload.get("data") or []
        if fields and data:
            payload = [
                dict(zip(fields, row))
                for row in data
            ]
        else:
            raise TaiwanTwseError("FMTQIK JSON has no usable rows")

    if not isinstance(payload, list):
        raise TaiwanTwseError("FMTQIK JSON must be a list or fields/data object")

    rows = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_date = (
            item.get("Date")
            or item.get("日期")
        )
        if not raw_date:
            continue

        taiex = (
            item.get("TAIEX")
            or item.get("發行量加權股價指數")
            or item.get("收盤指數")
        )
        rows.append(
            {
                "date": roc_date_to_iso(raw_date),
                "close": _number(taiex),
                "trade_volume": _number(
                    item.get("TradeVolume")
                    or item.get("成交股數"),
                    integer=True,
                ),
                "trade_value": _number(
                    item.get("TradeValue")
                    or item.get("成交金額"),
                ),
                "transactions": _number(
                    item.get("Transaction")
                    or item.get("成交筆數"),
                    integer=True,
                ),
                "change": _number(
                    item.get("Change")
                    or item.get("漲跌點數"),
                ),
            }
        )

    rows.sort(key=lambda row: row["date"])
    _validate_unique_dates(rows, "FMTQIK")
    return rows


def parse_taiex_month_json(text: str) -> list[dict]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TaiwanTwseError("TAIEX month response is not valid JSON") from exc

    if payload.get("stat") not in {None, "OK"}:
        raise TaiwanTwseError(
            f"TAIEX month response stat={payload.get('stat')!r}"
        )
    data = payload.get("data") or []
    rows = []
    for row in data:
        if len(row) < 5:
            continue
        rows.append(
            {
                "date": roc_date_to_iso(row[0]),
                "open": _number(row[1]),
                "high": _number(row[2]),
                "low": _number(row[3]),
                "close": _number(row[4]),
            }
        )
    rows.sort(key=lambda row: row["date"])
    _validate_unique_dates(rows, "TAIEX month")
    return rows


def merge_taiex_rows(*groups: list[dict]) -> list[dict]:
    by_date: dict[str, dict] = {}
    for group in groups:
        for row in group:
            target = by_date.setdefault(row["date"], {"date": row["date"]})
            for key, value in row.items():
                if key == "date" or value is None:
                    continue
                target[key] = value
    return [by_date[key] for key in sorted(by_date)]


def _parse_count_and_limit(value) -> tuple[int | None, int | None]:
    if value is None:
        return None, None
    text = str(value).strip().replace(",", "")
    match = re.fullmatch(r"(-?\d+)(?:\((-?\d+)\))?", text)
    if not match:
        raise TaiwanTwseError(f"unexpected breadth count {value!r}")
    count = int(match.group(1))
    limit = int(match.group(2)) if match.group(2) is not None else None
    return count, limit


def parse_mi_index_market_summary_json(text: str) -> dict:
    """
    Parse TWSE MI_INDEX type=MS.

    TWSE's market-summary table contains both overall securities and a Stocks
    column. We deliberately use the Stocks column to avoid warrants/ETFs/etc.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TaiwanTwseError("MI_INDEX response is not valid JSON") from exc

    if payload.get("stat") != "OK":
        raise TaiwanTwseError(
            f"MI_INDEX response stat={payload.get('stat')!r}"
        )
    rows = payload.get("data8") or payload.get("data") or []
    if len(rows) < 5:
        raise TaiwanTwseError("MI_INDEX market summary missing breadth rows")

    values = []
    for row in rows[:5]:
        if len(row) < 3:
            raise TaiwanTwseError("MI_INDEX market-summary row too short")
        values.append(row[2])  # Stocks column.

    up, limit_up = _parse_count_and_limit(values[0])
    down, limit_down = _parse_count_and_limit(values[1])
    unchanged, _ = _parse_count_and_limit(values[2])
    unmatched, _ = _parse_count_and_limit(values[3])
    not_applicable, _ = _parse_count_and_limit(values[4])

    raw_date = (
        payload.get("date")
        or payload.get("Date")
        or payload.get("日期")
    )
    if not raw_date:
        title = str(payload.get("title") or "")
        match = re.search(r"(\d{3})年(\d{2})月(\d{2})日", title)
        if match:
            raw_date = "".join(match.groups())
    if not raw_date:
        raise TaiwanTwseError("MI_INDEX response missing date")

    return {
        "date": roc_date_to_iso(raw_date),
        "advancing": up,
        "limit_up": limit_up,
        "declining": down,
        "limit_down": limit_down,
        "unchanged": unchanged,
        "unmatched": (unmatched or 0) + (not_applicable or 0),
    }


def parse_twtazu_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise TaiwanTwseError("twtazu CSV has no header")

    rows = []
    for raw in reader:
        raw_type = str(
            raw.get("類型")
            or raw.get("Type")
            or ""
        ).strip()
        if raw_type not in {"股票", "Stocks", "Stock"}:
            continue

        rows.append(
            {
                "date": roc_date_to_iso(
                    raw.get("資料日期")
                    or raw.get("日期")
                    or raw.get("Date")
                ),
                "advancing": _number(
                    raw.get("上漲") or raw.get("Up"),
                    integer=True,
                ),
                "limit_up": _number(
                    raw.get("漲停") or raw.get("Limit Up"),
                    integer=True,
                ),
                "declining": _number(
                    raw.get("下跌") or raw.get("Down"),
                    integer=True,
                ),
                "limit_down": _number(
                    raw.get("跌停") or raw.get("Limit Down"),
                    integer=True,
                ),
                "unchanged": _number(
                    raw.get("持平") or raw.get("Unchanged"),
                    integer=True,
                ),
                "unmatched": (
                    _number(
                        raw.get("未成交") or raw.get("Unmatched"),
                        integer=True,
                    )
                    or 0
                )
                + (
                    _number(
                        raw.get("無比價") or raw.get("N/A"),
                        integer=True,
                    )
                    or 0
                ),
            }
        )

    rows.sort(key=lambda row: row["date"])
    _validate_unique_dates(rows, "twtazu")
    return rows


def parse_taiwan_breadth_csv(text: str) -> list[dict]:
    """
    Local normalized history contract:
    date,advancing,declining,unchanged,limit_up,limit_down,unmatched
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise TaiwanTwseError("Taiwan breadth CSV has no header")
    required = {"date", "advancing", "declining"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise TaiwanTwseError(
            f"Taiwan breadth CSV missing {sorted(missing)}"
        )

    rows = []
    previous = None
    for line_no, raw in enumerate(reader, start=2):
        obs_date = date.fromisoformat(raw["date"].strip()).isoformat()
        if previous is not None and obs_date <= previous:
            raise TaiwanTwseError(
                f"row {line_no}: dates must be strictly increasing"
            )
        previous = obs_date

        row = {"date": obs_date}
        for field in (
            "advancing",
            "declining",
            "unchanged",
            "limit_up",
            "limit_down",
            "unmatched",
        ):
            value = _number(raw.get(field), integer=True)
            if value is not None and value < 0:
                raise TaiwanTwseError(
                    f"row {line_no}: {field} must be non-negative"
                )
            row[field] = value
        rows.append(row)
    return rows


def derive_taiwan_breadth(rows: list[dict]) -> list[dict]:
    cumulative = 0.0
    output = []
    for row in rows:
        advancing = row.get("advancing")
        declining = row.get("declining")
        diff = (
            None
            if advancing is None or declining is None
            else advancing - declining
        )
        denom = (
            None
            if advancing is None or declining is None
            else advancing + declining
        )
        pct = (
            None
            if diff is None or not denom
            else 100.0 * diff / denom
        )
        if diff is not None:
            cumulative += diff
            ad_line = cumulative
        else:
            ad_line = None

        output.append(
            {
                **row,
                "advance_decline_diff": diff,
                "advance_decline_pct": pct,
                "advance_decline_line": ad_line,
            }
        )
    return output


def _validate_unique_dates(rows: list[dict], label: str) -> None:
    dates = [row["date"] for row in rows]
    if dates != sorted(dates):
        raise TaiwanTwseError(f"{label}: dates not monotonic")
    if len(dates) != len(set(dates)):
        raise TaiwanTwseError(f"{label}: duplicate dates")


def _freshness(
    as_of: str | None,
    fetched_at: datetime,
    max_age_days: int,
) -> tuple[str, int | None]:
    if not as_of:
        return "missing", None
    age = max(
        (fetched_at.date() - date.fromisoformat(as_of)).days,
        0,
    )
    return ("fresh" if age <= max_age_days else "stale"), age


def _build_metric(
    rows: list[dict],
    *,
    metric_id: str,
    name: str,
    field: str,
    pillar: str,
    units: str,
    polarity: str,
    description: str,
    source_url: str,
    fetched_at: datetime,
    frequency: str = "daily",
    max_age_days: int = 5,
    lineage: dict | None = None,
) -> dict | None:
    observations = [
        {
            "date": row["date"],
            "value": row.get(field),
            "status": (
                "observed"
                if row.get(field) is not None
                else "missing"
            ),
        }
        for row in rows
    ]
    present = [
        obs for obs in observations
        if obs["value"] is not None
    ]
    if not present:
        return None

    latest = present[-1]
    state, age = _freshness(
        latest["date"],
        fetched_at,
        max_age_days,
    )

    return {
        "schema_version": "1.0.0",
        "environment": "production",
        "metric": {
            "id": metric_id,
            "name": name,
            "description": description,
            "pillar": pillar,
            "units": units,
            "frequency": frequency,
            "polarity": polarity,
        },
        "source": {
            "provider": "Taiwan Stock Exchange (TWSE)",
            "dataset": "TWSE official market data",
            "series_id": None,
            "url": source_url,
            "license_note": (
                "Official TWSE source. Government open-data items such as "
                "twtazu_od are published under Taiwan Government Data Open "
                "License v1.0; other web/OpenAPI data retain source attribution."
            ),
            "redistribution": "unknown",
            "market_scope": "TWSE listed stocks",
            "membership_mode": None,
            "membership_snapshot": None,
            "price_adjustment": None,
            "point_in_time_membership": None,
        },
        "coverage": {
            "history_start": observations[0]["date"],
            "history_end": observations[-1]["date"],
            "timezone": "Asia/Taipei",
            "expected_observation_lag_days": 1,
        },
        "freshness": {
            "state": state,
            "max_age_days": max_age_days,
            "age_days": age,
            "evaluated_at": (
                fetched_at.isoformat().replace("+00:00", "Z")
            ),
            "reason": None,
        },
        "lineage": lineage
        or {
            "kind": "raw",
            "inputs": [],
            "formula": None,
            "transform_version": "twse-raw-v1",
        },
        "baselines": [
            {
                "id": "expanding-pit",
                "type": "full_history_percentile",
                "window_observations": None,
                "min_observations": 60,
                "point_in_time": True,
                "notes": "Strict-past expanding baseline.",
            },
            {
                "id": "rolling-1260d",
                "type": "rolling_percentile",
                "window_observations": 1260,
                "min_observations": 252,
                "point_in_time": True,
                "notes": "Approximate trailing five trading years.",
            },
        ],
        "latest": {
            "as_of": latest["date"],
            "fetched_at": (
                fetched_at.isoformat().replace("+00:00", "Z")
            ),
            "value": latest["value"],
            "revision_tag": None,
        },
        "observations": observations,
    }


def build_taiex_metrics(
    rows: list[dict],
    fetched_at: datetime | None = None,
) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    specs = [
        (
            "tw_taiex",
            "TAIEX",
            "close",
            "index",
            "contextual",
            "Taiwan Stock Exchange Capitalization Weighted Stock Index close.",
        ),
        (
            "tw_taiex_open",
            "TAIEX Open",
            "open",
            "index",
            "contextual",
            "TAIEX daily opening index.",
        ),
        (
            "tw_taiex_high",
            "TAIEX High",
            "high",
            "index",
            "contextual",
            "TAIEX daily high index.",
        ),
        (
            "tw_taiex_low",
            "TAIEX Low",
            "low",
            "index",
            "contextual",
            "TAIEX daily low index.",
        ),
        (
            "tw_market_trade_value",
            "TWSE Market Trade Value",
            "trade_value",
            "TWD",
            "contextual",
            "TWSE daily aggregate market trade value.",
        ),
        (
            "tw_market_trade_volume",
            "TWSE Market Trade Volume",
            "trade_volume",
            "shares",
            "contextual",
            "TWSE daily aggregate market trade volume.",
        ),
    ]
    metrics = {}
    for metric_id, name, field, units, polarity, desc in specs:
        metric = _build_metric(
            rows,
            metric_id=metric_id,
            name=name,
            field=field,
            pillar="market",
            units=units,
            polarity=polarity,
            description=desc,
            source_url=TWSE_FMTQIK_URL,
            fetched_at=fetched_at,
        )
        if metric:
            metrics[metric_id] = metric
    return metrics


def build_taiwan_breadth_metrics(
    rows: list[dict],
    fetched_at: datetime | None = None,
) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    derived = derive_taiwan_breadth(rows)

    specs = [
        (
            "tw_advancing_stocks",
            "TWSE Advancing Stocks",
            "advancing",
            "count",
            "contextual",
            "Number of TWSE-listed stocks closing above the prior close.",
            None,
        ),
        (
            "tw_declining_stocks",
            "TWSE Declining Stocks",
            "declining",
            "count",
            "higher_is_riskier",
            "Number of TWSE-listed stocks closing below the prior close.",
            None,
        ),
        (
            "tw_unchanged_stocks",
            "TWSE Unchanged Stocks",
            "unchanged",
            "count",
            "neutral",
            "Number of TWSE-listed stocks unchanged versus the prior close.",
            None,
        ),
        (
            "tw_advance_decline_diff",
            "TWSE Advance-Decline Difference",
            "advance_decline_diff",
            "count",
            "lower_is_riskier",
            "Advancing TWSE stocks minus declining TWSE stocks.",
            {
                "kind": "derived",
                "inputs": [
                    "tw_advancing_stocks",
                    "tw_declining_stocks",
                ],
                "formula": "advancing - declining",
                "transform_version": "tw-ad-v1",
            },
        ),
        (
            "tw_advance_decline_pct",
            "TWSE Advance-Decline %",
            "advance_decline_pct",
            "percent",
            "lower_is_riskier",
            "100 × (advancing - declining) / (advancing + declining).",
            {
                "kind": "derived",
                "inputs": [
                    "tw_advancing_stocks",
                    "tw_declining_stocks",
                ],
                "formula": (
                    "100 * (advancing - declining) "
                    "/ (advancing + declining)"
                ),
                "transform_version": "tw-ad-v1",
            },
        ),
        (
            "tw_advance_decline_line",
            "TWSE Advance-Decline Line",
            "advance_decline_line",
            "index",
            "contextual",
            "Cumulative TWSE advancing-minus-declining stock count.",
            {
                "kind": "derived",
                "inputs": ["tw_advance_decline_diff"],
                "formula": "cumsum(advancing - declining)",
                "transform_version": "tw-ad-v1",
            },
        ),
    ]

    metrics = {}
    for (
        metric_id,
        name,
        field,
        units,
        polarity,
        desc,
        lineage,
    ) in specs:
        metric = _build_metric(
            derived,
            metric_id=metric_id,
            name=name,
            field=field,
            pillar="breadth",
            units=units,
            polarity=polarity,
            description=desc,
            source_url=TWSE_UPDOWN_CSV_URL,
            fetched_at=fetched_at,
            lineage=lineage,
        )
        if metric:
            metrics[metric_id] = metric
    return metrics


def write_metrics(
    metrics: dict[str, dict],
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for metric_id, metric in metrics.items():
        dest = output_dir / f"{metric_id}.json"
        tmp = dest.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(metric, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(dest)
        paths.append(dest)
    return paths
