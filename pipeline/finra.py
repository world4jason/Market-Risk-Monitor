from __future__ import annotations

import csv
import io
import json
import re
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .methodology import period_pct_change


SOURCE_URL = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"


class FinraError(RuntimeError):
    pass


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _parse_amount(raw):
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if not s or s.lower() in {"na", "n/a", "-"}:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.replace("$", "").replace(",", "").replace("(", "").replace(")", "")
    value = float(s)
    return -value if negative else value


def _business_month_end(value) -> str:
    if isinstance(value, datetime):
        d = value.date()
    elif isinstance(value, date):
        d = value
    else:
        s = str(value).strip()
        parsers = [
            ("%b-%y", lambda dt: dt.date()),
            ("%b %Y", lambda dt: dt.date()),
            ("%Y-%m", lambda dt: dt.date()),
            ("%Y-%m-%d", lambda dt: dt.date()),
            ("%m/%d/%Y", lambda dt: dt.date()),
        ]
        d = None
        for fmt, conv in parsers:
            try:
                d = conv(datetime.strptime(s, fmt))
                break
            except ValueError:
                continue
        if d is None:
            raise FinraError(f"Unrecognized month/date value: {value!r}")
    last = date(d.year, d.month, monthrange(d.year, d.month)[1])
    while last.weekday() >= 5:
        last -= timedelta(days=1)
    return last.isoformat()


ALIASES = {
    "month": ("month", "date", "year month"),
    "margin_debt": (
        "debit balances in customers securities margin accounts",
        "debit balances in customers margin accounts",
        "debit balances",
        "margin debt",
    ),
    "cash_free_credit": (
        "free credit balances in customers cash accounts",
        "free credit balances cash accounts",
        "cash account free credit",
    ),
    "margin_free_credit": (
        "free credit balances in customers securities margin accounts",
        "free credit balances margin accounts",
        "margin account free credit",
    ),
}


def _match_columns(headers: list[str]) -> dict[str, str]:
    normalized = {h: _norm(h) for h in headers}
    found = {}
    for key, aliases in ALIASES.items():
        for header, normed in normalized.items():
            if any(alias in normed for alias in aliases):
                found[key] = header
                break
    missing = set(ALIASES) - set(found)
    if missing:
        raise FinraError(f"Missing FINRA columns {sorted(missing)}; headers={headers}")
    return found


def parse_finra_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise FinraError("FINRA CSV has no header")
    cols = _match_columns(reader.fieldnames)
    rows = []
    for row in reader:
        if not (row.get(cols["month"]) or "").strip():
            continue
        rows.append({
            "date": _business_month_end(row[cols["month"]]),
            "margin_debt": _parse_amount(row.get(cols["margin_debt"])),
            "cash_free_credit": _parse_amount(row.get(cols["cash_free_credit"])),
            "margin_free_credit": _parse_amount(row.get(cols["margin_free_credit"])),
        })
    rows.sort(key=lambda x: x["date"])
    if len({r["date"] for r in rows}) != len(rows):
        raise FinraError("Duplicate FINRA month found")
    return rows


def parse_finra_xlsx(path: str | Path) -> list[dict]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise FinraError("openpyxl is required for XLSX import; install requirements.txt") from exc

    wb = load_workbook(path, read_only=True, data_only=True)
    best_rows = None
    for ws in wb.worksheets:
        data = list(ws.iter_rows(values_only=True))
        for header_idx, row in enumerate(data[:25]):
            headers = ["" if v is None else str(v) for v in row]
            try:
                cols = _match_columns(headers)
            except FinraError:
                continue
            indexes = {k: headers.index(v) for k, v in cols.items()}
            parsed = []
            for values in data[header_idx + 1:]:
                if not values or indexes["month"] >= len(values) or values[indexes["month"]] is None:
                    continue
                try:
                    parsed.append({
                        "date": _business_month_end(values[indexes["month"]]),
                        "margin_debt": _parse_amount(values[indexes["margin_debt"]]),
                        "cash_free_credit": _parse_amount(values[indexes["cash_free_credit"]]),
                        "margin_free_credit": _parse_amount(values[indexes["margin_free_credit"]]),
                    })
                except (ValueError, FinraError):
                    continue
            if parsed and (best_rows is None or len(parsed) > len(best_rows)):
                best_rows = parsed

    if not best_rows:
        raise FinraError("Could not locate FINRA margin-statistics table in XLSX")

    best_rows.sort(key=lambda x: x["date"])
    dedup = {}
    for row in best_rows:
        dedup[row["date"]] = row
    return [dedup[k] for k in sorted(dedup)]


def _freshness(as_of: str | None, fetched_at: datetime, max_age_days: int = 70):
    if not as_of:
        return "missing", None
    age = (fetched_at.date() - date.fromisoformat(as_of)).days
    return ("fresh" if age <= max_age_days else "stale"), max(age, 0)


def _raw_metric(metric_id: str, name: str, units: str, rows: list[dict], field: str, fetched_at: datetime) -> dict:
    obs = [{"date": r["date"], "value": r[field], "status": "observed" if r[field] is not None else "missing"} for r in rows]
    present = [o for o in obs if o["value"] is not None]
    latest = present[-1] if present else None
    as_of = latest["date"] if latest else None
    state, age = _freshness(as_of, fetched_at)
    return {
        "schema_version":"1.0.0","environment":"production",
        "metric":{"id":metric_id,"name":name,"description":"FINRA monthly margin-statistics series.","pillar":"leverage","units":units,"frequency":"monthly","polarity":"contextual"},
        "source":{"provider":"FINRA","dataset":"Margin Statistics","series_id":None,"url":SOURCE_URL,"license_note":"Official FINRA monthly margin-statistics source.","redistribution":"unknown"},
        "coverage":{"history_start":obs[0]["date"] if obs else None,"history_end":obs[-1]["date"] if obs else None,"timezone":"America/New_York","expected_observation_lag_days":25},
        "freshness":{"state":state,"max_age_days":70,"age_days":age,"evaluated_at":fetched_at.isoformat().replace("+00:00","Z"),"reason":None},
        "lineage":{"kind":"raw","inputs":[],"formula":None,"transform_version":"finra-raw-v1"},
        "baselines":[
            {"id":"expanding-pit","type":"full_history_percentile","window_observations":None,"min_observations":36,"point_in_time":True,"notes":"Strict-past expanding baseline."},
            {"id":"rolling-120m","type":"rolling_percentile","window_observations":120,"min_observations":36,"point_in_time":True,"notes":"Trailing 10-year monthly baseline."}
        ],
        "latest":{"as_of":as_of,"fetched_at":fetched_at.isoformat().replace("+00:00","Z"),"value":latest["value"] if latest else None,"revision_tag":None},
        "observations":obs,
    }


def _derived_pct(metric_id: str, name: str, source_metric: dict, periods: int, formula: str) -> dict:
    derived_obs = period_pct_change(source_metric["observations"], periods)
    present = [o for o in derived_obs if o["value"] is not None]
    latest = present[-1] if present else None
    result = json.loads(json.dumps(source_metric))
    result["metric"].update({"id":metric_id,"name":name,"units":"percent","polarity":"contextual"})
    result["lineage"] = {"kind":"derived","inputs":[source_metric["metric"]["id"]],"formula":formula,"transform_version":"pct-change-v1"}
    result["latest"]["as_of"] = latest["date"] if latest else None
    result["latest"]["value"] = latest["value"] if latest else None
    result["observations"] = derived_obs
    return result


def _ratio_metric(rows: list[dict], base_metric: dict) -> dict:
    obs=[]
    for row in rows:
        fc = None
        if row["cash_free_credit"] is not None and row["margin_free_credit"] is not None:
            fc = row["cash_free_credit"] + row["margin_free_credit"]
        value = None if fc in (None, 0) or row["margin_debt"] is None else row["margin_debt"] / fc
        obs.append({"date":row["date"],"value":value,"status":"observed" if value is not None else "missing"})
    present=[o for o in obs if o["value"] is not None]
    latest=present[-1] if present else None
    result=json.loads(json.dumps(base_metric))
    result["metric"].update({
        "id":"margin_debt_to_free_credit",
        "name":"Margin Debt / Total Free Credit",
        "units":"ratio",
        "polarity":"higher_is_riskier",
    })
    result["lineage"]={
        "kind":"derived",
        "inputs":["finra_margin_debt","finra_cash_free_credit","finra_margin_free_credit"],
        "formula":"margin_debt / (cash_free_credit + margin_free_credit)",
        "transform_version":"ratio-v1",
    }
    result["latest"]["as_of"]=latest["date"] if latest else None
    result["latest"]["value"]=latest["value"] if latest else None
    result["observations"]=obs
    return result


def build_finra_metrics(rows: list[dict], fetched_at: datetime | None = None) -> dict[str, dict]:
    fetched_at = fetched_at or datetime.now(timezone.utc)
    debt = _raw_metric("finra_margin_debt","FINRA Margin Debt","USD millions",rows,"margin_debt",fetched_at)
    cash = _raw_metric("finra_cash_free_credit","FINRA Cash Account Free Credit","USD millions",rows,"cash_free_credit",fetched_at)
    margin = _raw_metric("finra_margin_free_credit","FINRA Margin Account Free Credit","USD millions",rows,"margin_free_credit",fetched_at)
    mom = _derived_pct("finra_margin_debt_mom_pct","FINRA Margin Debt MoM",debt,1,"(x_t / x_t-1 - 1) * 100")
    yoy = _derived_pct("finra_margin_debt_yoy_pct","FINRA Margin Debt YoY",debt,12,"(x_t / x_t-12 - 1) * 100")
    ratio = _ratio_metric(rows,debt)
    return {m["metric"]["id"]:m for m in [debt,cash,margin,mom,yoy,ratio]}
