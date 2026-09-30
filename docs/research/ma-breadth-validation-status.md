# Moving-average breadth: final validation status

Issues: #26, #29, #22

Checked: 2026-10-01

## Decision summary

The moving-average breadth implementation is complete. The remaining risk is
**source validity**, not missing feature code.

The repository therefore treats source validation as a fail-closed gate:

- a source that is not point-in-time is blocked from canonical historical study;
- a cross-provider mismatch outside the declared tolerance is a **rejection of
  that source for canonical research**, not a reason to widen the tolerance;
- proprietary/licensed historical data is consumed locally and is never
  committed merely to make an issue turn green.

## #29 QA verdict

The existing TraderMonty/FMP convenience history was compared with the fixed
Barchart `$S5FI` reference for 2026-09-01:

- local: 46.50698603
- reference: 45.52
- difference: 0.98698603 percentage points
- declared tolerance: 0.5 percentage points
- result: **outside tolerance**

This is the behavior #29 is intended to detect. The convenience source is
current-constituent retroactive history and is already barred from canonical
point-in-time analysis. The mismatch is additional evidence that it must remain
context-only.

Do **not** widen the 0.5pp tolerance simply to accept this source.

The public release/publishing policy also keeps the relevant restricted/local
families out of the public snapshot.

## #26 event-study status

The event-study engine is implemented and tested:

- 25% / 15% down-cross and up-recross events;
- anchored cooldown/de-duplication;
- no-look-ahead event detection;
- 1W / 1M / 3M / 6M forward returns;
- maximum adverse excursion;
- local-low timing for retrospective context;
- unconditional forward-return comparison;
- event-level dashboard inspection;
- point-in-time membership hard gate.

The public/open reconstruction path can be used for historical research where
its source coverage is valid. The repository deliberately does not copy a
proprietary full S5FI/SPXA50R history into git.

For 2025/2026, the project keeps two distinct concepts:

1. **public point observations / coarse episode corroboration** in
   `docs/research/ma-breadth-public-cross-check.md`;
2. **canonical daily event-study results**, which require authorized
   point-in-time breadth plus a permitted daily S&P 500 index series.

The first must never be presented as the second.

## Licensed/local-only completion path

Use the canonical MA-breadth CSV contract documented in
`docs/moving-average-breadth-sources.md`.

Then run:

```bash
python scripts/run_ma_breadth_research.py \
  --ma-breadth-file /path/to/authorized-pit-ma-breadth.csv \
  --sp500-index-file /path/to/local-only-sp500-index.json \
  --reference tests/fixtures/ma_breadth_reference.json \
  --reference tests/fixtures/ma_breadth_reference_latest.json
```

The runner:

1. imports the authorized MA-breadth file through the normal refresh path;
2. validates and copies the local-only `sp500_index` metric into a
   `.cache/` working directory;
3. runs every requested cross-provider reference check;
4. **stops immediately** if any reference is outside tolerance;
5. builds the canonical event study;
6. rejects non-point-in-time history;
7. runs artifact validation;
8. prints event/sample counts and output paths.

This workflow defaults to `.cache/ma-breadth-research`, so restricted raw
inputs are not accidentally treated as public release artifacts.

## Candidate PIT data

A currently available commercial option is PowakaData's S&P 500 point-in-time
research package. As checked on 2026-10-01, its product page states:

- point-in-time membership with daily D1 market data;
- coverage 2016-2026;
- versioned release / integrity manifests;
- purchaser use for trading/research/system development;
- **redistribution/resale of the dataset is not permitted**.

That makes it suitable as a possible **local research input**, not something to
commit to this public repository.

The free sample is useful for inspecting structure, but the vendor describes it
as example intervals/events/documentation, not a substitute for the full
history.

Barchart's current terms likewise prohibit reproducing/distributing its content
without permission, so fixed individual QA observations may be recorded with
attribution, but a full historical scrape is not an acceptable repository data
source.

## Open-data path

The repository already supports a survivorship-aware reconstruction using:

- `chinobing/historical_sp500_constituents` point-in-time membership;
- delisted-inclusive FINSABER historical prices;
- an optional local-only recent-price supplement.

Current FINSABER-V2 documentation describes `price_daily` coverage through
2025 and includes `adjusted_close`. Dataset/provider terms still need to be
reviewed for the intended use before derived recent results are published.

## Issue-closing rule

Engineering tickets should not remain open indefinitely merely because the
repository owner has not purchased or supplied a licensed dataset.

After this workflow lands:

- #29 is complete when the fail-closed source verdict is recorded and enforced;
- #26 implementation is complete; exact licensed-history empirical output is an
  **external research input**, not missing code;
- #22 can close once its DoD is rechecked against the completed implementation
  and fail-closed data policy.

If a licensed PIT dataset is later supplied, rerun the command above and record
the resulting study as a new research artifact/revision rather than reopening
the implementation design from scratch.
