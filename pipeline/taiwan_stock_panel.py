from __future__ import annotations

import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen

from .taiwan_twse import roc_date_to_iso


STOCK_DAY_ALL_URL = (
    "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
)
COMPANY_MASTER_URL = (
    "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
)
MARKET_SCOPE = "TWSE listed common stocks"


class TaiwanStockPanelError(ValueError):
    pass


def _fetch_json(url: str, timeout: int = 30):
    req = Request(
        url,
        headers={
            "User-Agent": (
                "Market-Risk-Monitor/0.3 "
                "(TWSE daily common-stock breadth collector)"
            )
        },
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8-sig"))
    except Exception as exc:
        raise TaiwanStockPanelError(
            f"failed to fetch/parse {url}: {exc}"
        ) from exc


def fetch_stock_day_all(timeout: int = 30):
    return _fetch_json(STOCK_DAY_ALL_URL, timeout=timeout)


def fetch_company_master(timeout: int = 30):
    return _fetch_json(COMPANY_MASTER_URL, timeout=timeout)


def parse_company_codes(payload) -> set[str]:
    if not isinstance(payload, list):
        raise TaiwanStockPanelError(
            "company master payload must be a list"
        )
    codes = set()
    for row in payload:
        if not isinstance(row, dict):
            continue
        code = str(
            row.get("公司代號")
            or row.get("Code")
            or row.get("SecuritiesCompanyCode")
            or ""
        ).strip()
        if code:
            codes.add(code)
    if not codes:
        raise TaiwanStockPanelError(
            "company master contains no company codes"
        )
    return codes


def _number(value):
    text = str(value or "").strip().replace(",", "")
    if text in {"", "--", "---", "N/A", "NA"}:
        return None
    return float(text)


def build_daily_panel_rows(
    stock_payload,
    company_payload,
) -> list[dict]:
    if not isinstance(stock_payload, list):
        raise TaiwanStockPanelError(
            "STOCK_DAY_ALL payload must be a list"
        )
    company_codes = parse_company_codes(company_payload)

    rows = []
    dates = set()
    for raw in stock_payload:
        if not isinstance(raw, dict):
            continue
        symbol = str(raw.get("Code") or "").strip()
        if symbol not in company_codes:
            # ETFs, warrants, ETNs and other non-company securities are
            # intentionally excluded by the listed-company master.
            continue

        raw_date = str(raw.get("Date") or "").strip()
        if not raw_date:
            continue
        obs_date = roc_date_to_iso(raw_date)
        dates.add(obs_date)

        rows.append(
            {
                "date": obs_date,
                "symbol": symbol,
                "high": _number(raw.get("HighestPrice")),
                "low": _number(raw.get("LowestPrice")),
                "close": _number(raw.get("ClosingPrice")),
                "market_scope": MARKET_SCOPE,
                "provider": "Taiwan Stock Exchange (TWSE) OpenAPI",
                "membership_mode": "official_daily_snapshot",
                "price_adjustment": "unadjusted_close",
            }
        )

    if not rows:
        raise TaiwanStockPanelError(
            "no listed-company rows matched STOCK_DAY_ALL"
        )
    if len(dates) != 1:
        raise TaiwanStockPanelError(
            f"expected one trade date in current snapshot; got {sorted(dates)}"
        )

    rows.sort(key=lambda row: (row["date"], row["symbol"]))
    return rows


FIELDS = [
    "date",
    "symbol",
    "high",
    "low",
    "close",
    "market_scope",
    "provider",
    "membership_mode",
    "price_adjustment",
]


def append_snapshot(
    panel_path: Path,
    rows: list[dict],
) -> dict:
    """
    Append a point-in-time official daily snapshot.

    Re-running the same trade date replaces that date atomically instead of
    creating duplicate rows.
    """
    existing = []
    if panel_path.exists():
        with panel_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)
            existing = list(reader)

    snapshot_date = rows[0]["date"]
    kept = [
        row for row in existing
        if (row.get("date") or "").strip() != snapshot_date
    ]
    combined = kept + rows
    combined.sort(
        key=lambda row: (
            (row.get("date") or "").strip(),
            (row.get("symbol") or "").strip(),
        )
    )

    panel_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = panel_path.with_suffix(panel_path.suffix + ".tmp")
    with tmp.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(combined)
    tmp.replace(panel_path)

    return {
        "date": snapshot_date,
        "rows": len(rows),
        "total_panel_rows": len(combined),
        "panel": str(panel_path),
    }
