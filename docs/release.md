# Release Procedure

Issue: #46

How a published snapshot is produced. This is the authoritative version of the
command; a PR description is not documentation.

## The release command

```bash
python scripts/refresh_public_snapshot.py
```

This is the authoritative command used both locally and by `.github/workflows/refresh-public-snapshot.yml`. It prefetches every file-based dependency before mutating tracked outputs, rehydrates rolling CIER/NDC source windows from the committed macro audit, runs the explicit public-source allowlist with `--clean-output`, executes tests/validation/publishing-policy/site-smoke gates, and restores the previous generated tree on failure.

The workflow exposes `workflow_dispatch` and runs twice on weekdays: ~15:30 and ~06:30 Asia/Taipei. It commits only changed `data/generated/` files after every gate succeeds.

FINRA and Shiller workbooks are downloaded by `scripts/bootstrap_sources.py`.
The release does **not** use that script, because it defaults to including the
TraderMonty moving-average breadth source.

The NDC bootstrap uses the public chart JSON surface used by the official site.
Because it is undocumented, a fetch failure must stop the macro refresh rather
than silently relabel an old snapshot. For reproducibility of the first committed
snapshot, use:

```bash
python scripts/bootstrap_ndc_business_cycle.py \
  --snapshot-file tests/fixtures/ndc_business_cycle_snapshot.json \
  --observed-at 2026-09-26 \
  --output /tmp/ndc-business-cycle.csv
```

That command reproduces the committed `data/source/ndc-business-cycle-2026-09-26.csv`
exactly, but it must not be used to pretend the snapshot is fresh on a later date.

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

## What the public release still excludes, and why

| Family | Reason |
|---|---|
| `sp500_index` | `redistribution: "restricted"`, S&P Dow Jones Indices copyright (#60) |
| TraderMonty / FMP moving-average breadth | redistribution unresolved, and fails the cross-provider tolerance check (#29) |
| NYSE breadth | no authorized source ingested (#21) |
| NDC historical PIT backtest | the public NDC chart JSON is current-vintage and revision-prone; only retrospective current context is published |
| CIER pre-window history | the official table is a rolling 12-month window; coverage accumulates only from verified snapshots forward |

Omitted families are **not** given placeholder artifacts. They render as
unavailable, and their Deleveraging Watch conditions stay `unknown` rather than
`inactive`.

`taiwan-macro-regime.json` is now part of the public release when the CIER + NDC
bootstrap succeeds. `ma-breadth-event-study.json` may still be absent when its
source family is not included; absence remains preferable to a placeholder.

## Acceptance checks before publishing

```text
validate_data.py   exits 0 on the exact files being published
site_smoke.py      exits 0 on the release tree
coverage.json      every metric status ok, no short_history
overview.json      lightweight summary present; no full observations
refresh-report.json  removed_artifacts records anything pruned
```

Enforce the reviewed source-by-source publication policy:

```bash
python scripts/check_publish_policy.py
```

This is stronger than grepping for `redistribution: "restricted"`: it also rejects unclassified new metrics, source families marked local-only, and derived/special artifacts that actually consumed a local-only provenance input. The machine-readable decisions live in `data/config/publishing.json`.

## Publishing

Pages serves `main` at `/(root)`; see
[GitHub Pages + scheduled data refresh](../README.md#github-pages--scheduled-data-refresh). Merging the
snapshot to `main` rebuilds the site.

## Retention and subsequent refreshes

The long-term decision from #44 is **tracked snapshots on `main`** for source families explicitly approved by `data/config/publishing.json`.

- `data/generated/*.json` is release output **and intentionally versioned**.
- Every release regenerates the complete public set with `--clean-output`; there is no second downsampled representation.
- `validate_data.py`, `check_publish_policy.py`, and `site_smoke.py` must pass before generated files are committed.
- Restricted/local-only inputs may exist in a developer's separate local output directory, but never in the tracked public release tree.
- Each accepted refresh replaces the tracked snapshot set on `main`; Git history is the retention/audit trail.
- Pages deliberately remains branch-based at `main/(root)`. GitHub Actions is a refresh runner only; it does not build or deploy the site.
- If repository/Pages visibility or a source license changes, update the dated policy review and machine-readable config before publishing.
