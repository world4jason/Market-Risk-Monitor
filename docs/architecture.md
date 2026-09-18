# Architecture: GitHub Pages without GitHub Actions

Issue: #3

## Constraint

GitHub Actions is unavailable for this repository. The site therefore cannot depend on a custom Actions workflow for build, data refresh, or deployment.

GitHub Pages can publish directly from a branch. GitHub's Pages documentation also documents using a `.nojekyll` file to bypass Jekyll processing when Actions is unavailable/disabled and the repository already contains publish-ready static files.

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

The repository contains publish-ready static files and a root `.nojekyll` marker. No custom GHA workflow is required.

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
- keeps the no-GHA constraint explicit.

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

## Refresh strategy without GHA

### v0.1: explicit refresh command

A local or agent-operated refresh command updates data:

```bash
python scripts/refresh_data.py
python scripts/validate_data.py
git add data/
git commit -m "data: refresh market snapshots"
git push
```

The data pipeline must be deterministic and runnable outside GitHub.

This is intentionally separate from Pages deployment:
- Pages serves whatever valid snapshots are committed.
- A refresh failure does not corrupt the currently deployed snapshots.
- The UI uses metadata to show whether the last committed snapshot is stale.

### Future: external scheduler adapter

A future scheduler may run the **same** refresh/validation command on any external runner and commit only changed snapshots through a GitHub App/PAT.

Examples of possible runners:
- a small VPS cron job;
- a Cloudflare/other scheduled service plus a compatible ingestion implementation;
- a hosted CI system other than GitHub Actions.

The frontend contract must not change when the runner changes.

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
- Refresh path works without GHA.
- No secret reaches the browser.
- Stale/error behavior is explicit.
- Future external scheduling is an adapter, not a frontend rewrite.
- Historical coverage is metric-specific.
