#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.finra import build_finra_metrics, parse_finra_csv, parse_finra_xlsx
from pipeline.fred import fetch_fred_csv, parse_fred_csv, build_metric
from pipeline.validate import validate_metric


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def refresh_fred(config_path: Path, output_dir: Path, selected: set[str] | None):
    config=json.loads(config_path.read_text())
    report=[]
    fetched_at=datetime.now(timezone.utc)
    for item in config["fred"]:
        if selected and item["id"] not in selected:
            continue
        dest=output_dir/f"{item['id']}.json"
        try:
            text=fetch_fred_csv(item["series_id"])
            observations=parse_fred_csv(text,item["series_id"])
            metric=build_metric(item,observations,fetched_at)
            validate_metric(metric)
            atomic_json(dest,metric)
            report.append({"metric":item["id"],"status":"updated","path":str(dest.relative_to(ROOT))})
        except Exception as exc:
            report.append({"metric":item["id"],"status":"error","error":str(exc),"preserved_previous":dest.exists()})
    return report


def refresh_finra(input_path: Path, output_dir: Path):
    if input_path.suffix.lower()==".csv":
        rows=parse_finra_csv(input_path.read_text(encoding="utf-8-sig"))
    elif input_path.suffix.lower() in {".xlsx",".xlsm"}:
        rows=parse_finra_xlsx(input_path)
    else:
        raise SystemExit("FINRA input must be CSV or XLSX")
    metrics=build_finra_metrics(rows)
    report=[]
    for metric_id, metric in metrics.items():
        validate_metric(metric)
        dest=output_dir/f"{metric_id}.json"
        atomic_json(dest,metric)
        report.append({"metric":metric_id,"status":"updated","path":str(dest.relative_to(ROOT))})
    return report


def build_catalog(output_dir: Path):
    metrics=[]
    for path in sorted(output_dir.glob("*.json")):
        if path.name in {"catalog.json","refresh-report.json"}:
            continue
        try:
            metric=json.loads(path.read_text())
            validate_metric(metric)
        except Exception:
            continue
        metrics.append({
            "id":metric["metric"]["id"],
            "name":metric["metric"]["name"],
            "pillar":metric["metric"]["pillar"],
            "frequency":metric["metric"]["frequency"],
            "history_start":metric["coverage"]["history_start"],
            "history_end":metric["coverage"]["history_end"],
            "freshness":metric["freshness"]["state"],
            "as_of":metric["latest"]["as_of"],
            "path":f"./{path.name}",
        })
    return {
        "schema_version":"1.0.0",
        "generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "metrics":metrics,
    }


def main():
    parser=argparse.ArgumentParser(description="Refresh Market Risk Monitor static snapshots without GitHub Actions.")
    parser.add_argument("--fred",action="store_true",help="Refresh configured FRED series.")
    parser.add_argument("--fred-id",action="append",default=[],help="Refresh only a configured metric id; may be repeated.")
    parser.add_argument("--finra-file",type=Path,help="Path to an official FINRA margin-statistics CSV/XLSX download.")
    parser.add_argument("--output-dir",type=Path,default=ROOT/"data"/"generated")
    args=parser.parse_args()

    if not args.fred and not args.finra_file:
        parser.error("choose --fred and/or --finra-file")

    report=[]
    if args.fred:
        report.extend(refresh_fred(ROOT/"data"/"config"/"series.json",args.output_dir,set(args.fred_id) or None))
    if args.finra_file:
        report.extend(refresh_finra(args.finra_file,args.output_dir))

    atomic_json(args.output_dir/"catalog.json",build_catalog(args.output_dir))
    atomic_json(args.output_dir/"refresh-report.json",{
        "generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "results":report,
    })

    errors=[r for r in report if r["status"]=="error"]
    print(json.dumps(report,indent=2))
    raise SystemExit(1 if errors else 0)


if __name__=="__main__":
    main()
