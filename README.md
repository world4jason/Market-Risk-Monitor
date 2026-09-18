# Market Risk Monitor

A public, explainable dashboard for monitoring U.S. market leverage, financial stress, volatility, credit/risk conditions, and historical regime context.

## Product questions

1. Is leverage/risk appetite historically elevated?
2. Is stress actually rising?
3. Is deleveraging underway?
4. How does the current regime compare with prior cycles?

This project intentionally avoids hidden BUY/SELL logic. Current values are always paired with source, as-of date, freshness, and historical context.

## Constraints

- Frontend target: GitHub Pages.
- GitHub Actions is unavailable.
- Static/buildless delivery is preferred.
- No hard-coded fallback value may masquerade as current data.
- Historical comparison is a first-class feature, not an afterthought.

## Roadmap

See issue #1 and its child tickets.

Initial implementation order:

`research → architecture → data contract → history/FINRA → methodology → UI → history explorer → signals → QA → deploy`

## Status

Project bootstrap in progress.
