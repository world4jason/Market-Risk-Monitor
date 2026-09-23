# Release Procedure

Issue: #46

How a published snapshot is produced. This is the authoritative version of the
command; a PR description is not documentation.

## The release command

```bash
python scripts/bootstrap_taiwan_taiex.py

python scripts/refresh_data.py --clean-output \
  --fred-id nfci --fred-id nfci_risk --fred-id nfci_credit \
  --fred-id nfci_nonfinancial_leverage --fred-id us_recession \
  --fred-id fed_target_legacy --fred-id fed_target_upper \
  --cboe-vix \
  --finra-file <margin-statistics.xlsx> \
  --shiller-file <ie_data.xls> \
  --twse-current \
  --cbc-rate-file <cbc-rates.csv>

python scripts/build_signals.py
python scripts/validate_data.py
python scripts/site_smoke.py
```

FINRA and Shiller workbooks are downloaded by `scripts/bootstrap_sources.py`.
The release does **not** use that script, because it defaults to including the
TraderMonty moving-average breadth source.

## Why `--clean-output` is not optional

A refresh is otherwise additive. An unselected source is skipped rather than
cleared, while `build_catalog()` and `build_signals()` glob the whole output
directory. So an artifact from an earlier run with different flags stays on
disk and is catalogued again:

```text
an earlier --public run leaves data/generated/sp500_index.json
  -> release command whose allowlist omits it
  -> the allowlist refreshes only what it selected
  -> sp500_index.json is untouched on disk
  -> build_catalog globs it back into the catalog
```

`sp500_index` is marked `redistribution: "restricted"`, so that path publishes
restricted data from an allowlist written specifically to exclude it. Without
`--clean-output` the allowlist looks like it worked and did not.

`--clean-output` reduces the directory to exactly what the run produced.
Artifacts a failed source deliberately preserved are kept, so it does not
change the stale/error semantics in [qa.md](./qa.md).

## Why the FRED allowlist is spelled out

`--public` includes `sp500_index`. The release names each FRED series instead.
`--fred-id` activates the FRED refresh on its own; it is an allowlist, not a
filter applied on top of `--fred`.

## What v0.1 excludes, and why

| Family | Reason |
|---|---|
| `sp500_index` | `redistribution: "restricted"`, S&P Dow Jones Indices copyright (#60) |
| TraderMonty / FMP moving-average breadth | redistribution unresolved, and fails the cross-provider tolerance check (#29) |
| NYSE breadth | no authorized source ingested (#21) |
| NDC macro | no stable machine API; history is retrospectively revised (#45) |
| CIER historical macro | 12-month rolling window, point-in-time gap (#47, #48) |

Omitted families are **not** given placeholder artifacts. They render as
unavailable, and their Deleveraging Watch conditions stay `unknown` rather than
`inactive`.

Two 404s are therefore expected on the published site, for
`ma-breadth-event-study.json` and `taiwan-macro-regime.json`. Removing them
would mean committing a placeholder.

## Acceptance checks before publishing

```text
validate_data.py   exits 0 on the exact files being published
site_smoke.py      exits 0 on the release tree
coverage.json      every metric status ok, no short_history
overview.json      lightweight summary present; no full observations
refresh-report.json  removed_artifacts records anything pruned
```

Confirm no artifact declares `redistribution: "restricted"`:

```bash
python - <<'PY'
import json, pathlib
for p in pathlib.Path("data/generated").glob("*.json"):
    d = json.loads(p.read_text())
    if isinstance(d.get("source"), dict) and d["source"].get("redistribution") == "restricted":
        print("RESTRICTED:", p.name)
PY
```

## Publishing

Pages serves `main` at `/(root)`; see
[GitHub Pages without GHA](../README.md#github-pages-without-gha). Merging the
snapshot to `main` rebuilds the site.

Refresh scheduling, snapshot retention and the long-term publishing
architecture are open in #44. v0.1 is a bootstrap release, not that
architecture: every future refresh rewrites most of these files.
