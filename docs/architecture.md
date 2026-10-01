# Architecture: Static GitHub Pages + scheduled data refresh

Issue: #3

## Constraint

The website must remain a publish-ready static application served directly from `main/(root)`. Pages deployment therefore does **not** depend on a custom GitHub Actions build.

GitHub Actions is used only as a data-refresh runner. The scheduled/manual workflow executes the same Python release command available locally, validates the resulting snapshots, and commits approved `data/generated/` changes back to `main`.

References:
- https://docs.github.com/en/pages/quickstart
- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll

## Deployment topology

```text
                 refresh_data.py
             (local / external runner)
                      |
                      v
              validate snapshots
                      |
                      v
Git repository ──> static JSON + HTML/CSS/JS
                      |
                      v
                main branch
                /(repository root)
                      |
                      v
              GitHub Pages
       /Market-Risk-Monitor/
```

### Pages settings

Target publishing source:

- Source: **Deploy from a branch**
- Branch: **main**
- Folder: **/(root)**

The repository contains publish-ready static files and a root `.nojekyll` marker. No custom GHA **deployment** workflow is required; the only allowed workflow refreshes data.

## Frontend choice: buildless static application

v0.1 uses browser-native static assets:

```text
index.html
assets/
  app.js
  styles.css
  charts.js
data/
  catalog.json
  metrics/*.json
.nojekyll
```

No React/Vite/Next build is required in v0.1.

Why:
- removes the build pipeline entirely;
- works with branch-based Pages publishing;
- is easy to inspect/debug;
- keeps the repo itself equal to the deployed artifact;
- avoids a second "generated site" branch;
- keeps static deployment separate from scheduled data refresh.

A chart library may be loaded from a public CDN initially, or vendored later if fully offline/reproducible rendering is desired.

## Project-page-safe paths

This is a project Pages site, so deployed URLs live below:

```text
/Market-Risk-Monitor/
```

All application assets/data must use relative paths such as:

```text
./assets/styles.css
./assets/app.js
./data/catalog.json
```

Do not use root-absolute URLs such as `/assets/app.js`, because those resolve outside the project path.

## Data architecture

The frontend never talks directly to a secret-bearing API.

```text
official/public sources
       |
       v
scripts/refresh_data.py
       |
       +--> parse / normalize
       +--> preserve provenance
       +--> derive deterministic metrics
       +--> validate
       |
       v
data/generated/
  catalog.json
  current.json
  series/
    nfci.json
    vix.json
    finra-margin.json
    ...
       |
       v
static frontend
```

### Raw vs generated

For sources that can be redistributed safely:

```text
data/raw/          source snapshots / fixtures
data/generated/    canonical UI contract
```

For sources whose terms discourage redistribution, store only the minimum permissible derived/current data or fetch them during a refresh run; document the restriction in the catalog.

## Refresh strategy

### Authoritative refresh command

Local/manual refresh:

```bash
python scripts/refresh_public_snapshot.py
```

The command:
1. rehydrates CIER/NDC rolling-window history from the tracked canonical audit;
2. downloads FINRA/Shiller and current Taiwan macro/rate sources;
3. executes the exact public-source allowlist with `--clean-output`;
4. runs the deterministic unit suite, artifact validation, publishing-policy validation, and Pages smoke test;
5. restores the previous `data/generated/` tree if any step fails.

### GitHub Actions scheduler

`.github/workflows/refresh-public-snapshot.yml` provides:
- `workflow_dispatch` for manual one-click refresh;
- weekday `07:30 UTC` (~15:30 Asia/Taipei) after TWSE close;
- weekday `22:30 UTC` (~06:30 Asia/Taipei) after the U.S. cash session.

The job uses `contents: write`, commits only changed `data/generated/` files, and never deploys/builds the site itself. A failed run produces no push.

The data pipeline remains deterministic and runnable outside GitHub. Pages simply serves the newest valid snapshot already committed to `main`; the frontend contract does not depend on which runner produced it.

## Secrets

Rules:
1. No API key, token or credential in `index.html`, browser JS, JSON snapshots, commit history, or query strings.
2. Local secrets live in an untracked `.env` or process environment.
3. The static frontend may call only endpoints safe for public browser use.
4. Sources requiring an API key are fetched only by the refresh process.
5. If a future external runner is used, secrets are stored in that runner's secret store.

## Freshness and failure semantics

Every metric record carries:
- source observation `as_of`;
- snapshot `fetched_at`;
- frequency;
- configured freshness limit;
- status.

Status vocabulary:

```text
fresh
stale
missing
error
insufficient_data
```

Rules:
- A stale previous real observation may remain visible only with its original `as_of` date and a visible stale state.
- A failed refresh never writes a fabricated fallback number.
- Missing/error cannot be interpreted as "normal" or "low risk".
- Refresh writes are atomic: fetch → parse → validate → replace generated file.
- If validation fails, the previous valid snapshot remains in place.

Exact freshness thresholds belong to the data-contract ticket (#4), not scattered in UI code.

## Historical comparison architecture

Historical comparison is not computed from a single common clipped dataset.

Each metric keeps:
- its own maximum valid coverage;
- raw/source frequency;
- coverage start/end;
- transform configuration.

The frontend can therefore show:
- Shiller/CAPE long-run history;
- NFCI-family history from the 1970s;
- VIX from 1990;
- FINRA margin history from its own later start.

If a metric does not exist for an event, the historical explorer shows `unavailable`; it does not silently substitute a proxy.

## Point-in-time rule

Derived historical values at date T must not use observations after T when the transform is intended to represent what was knowable at T.

Examples:
- a 2008 rolling percentile uses the trailing history ending in 2008;
- a 2008 z-score baseline excludes future 2009–2026 observations;
- event overlays may also offer a clearly labeled retrospective full-history percentile, but that is a different statistic.

Revision-prone macro series added later should use vintage/ALFRED data when they feed historical "what was known then?" logic.

## Repository shape

```text
.
├── .nojekyll
├── index.html
├── assets/
│   ├── app.js
│   ├── charts.js
│   └── styles.css
├── data/
│   ├── raw/
│   ├── generated/
│   │   ├── catalog.json
│   │   ├── current.json
│   │   └── series/
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── methodology.md
│   └── research/
├── scripts/
│   ├── refresh_data.py
│   └── validate_data.py
└── README.md
```

## Extension boundaries

The following may change independently:
- data source adapters;
- refresh runner/scheduler;
- chart library;
- historical metric set.

The stable boundary is the generated JSON data contract defined in #4. The frontend reads that contract only.

## Architecture acceptance check

- GitHub Pages branch source documented.
- Buildless frontend documented.
- Refresh path works locally and through the scheduled GitHub Actions runner.
- No secret reaches the browser.
- Stale/error behavior is explicit.
- Future external scheduling is an adapter, not a frontend rewrite.
- Historical coverage is metric-specific.

## Enforced repository choke points

The repository treats the following as structural invariants, not conventions:

- **Canonical JSON writes:** pipeline.artifacts.write_json_artifact() is the only
  serializer allowed under pipeline/. It applies presentation finalization
  before atomic replacement. tests/test_artifact_writer.py scans the pipeline
  and fails if another module starts serializing JSON directly.
- **Release membership:** scripts/refresh_data.py records every written
  artifact and --clean-output prunes anything not written or explicitly
  preserved by a failed source. Tests pre-seed a dirty output directory so stale
  files cannot bypass source allowlists.
- **Grouped failures:** multi-metric sources declare the complete preserved
  metric group. The TWSE path reports both TAIEX and breadth groups even when an
  earlier dependent fetch fails, so pruning cannot erase a sibling group.
- **Contract examples:** repository JSON fixtures/examples that look like metric
  artifacts are scanned against the canonical JSON Schema, rather than relying
  on a manually maintained filename list.
- **Presentation semantics:** ID-specific ambiguous comparison behavior lives in
  data/config/presentation.json. Unknown index IDs fail safe to absolute change
  until explicitly classified, preventing a new zero-centred index from
  silently receiving relative-percent semantics.

These checks run in the ordinary deterministic local test suite and do not
depend on GitHub Actions.
