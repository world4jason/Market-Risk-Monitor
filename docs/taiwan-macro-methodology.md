# Taiwan Macro Regime Methodology

Issue: #38

The MRM Taiwan macro regime is a transparent public-input classifier. It does **not** reproduce MacroMicro/MM's manufacturing-cycle index.

## Raw inputs

The classifier can use:

- `tw_manufacturing_pmi` — CIER Taiwan Manufacturing PMI
- `tw_ndc_leading_index` — NDC trend-adjusted leading index
- `tw_ndc_coincident_index` — NDC trend-adjusted coincident index
- `tw_manufacturing_production` — MOEA manufacturing production index

The official NDC monitoring score/light is also retained independently as:
- `tw_ndc_monitoring_score`
- derived official light label

It is **not** one of the MRM vote components by default.

### Current-vintage limitation

NDC series are revision-prone and the repository does not yet retain historical
vintages. They are therefore treated as retrospective current-vintage context:
`availability_basis` remains `unknown`, historical PIT claims are disabled, and
a later manual NDC snapshot may revise earlier months. CIER release-aware PMI
rows can coexist in the same assembled macro dataset without upgrading NDC rows
to PIT-safe history.

The refresh command may take multiple `--taiwan-macro-file` arguments. Each
canonical series belongs to exactly one source file in a run, and partial
follow-up refreshes that would remove an already published series/date are
rejected before output is rewritten.

## NDC official monitoring light

NDC's published score bands are:

| Score | Official light |
|---:|---|
| 38–45 | Red |
| 32–37 | Yellow-red |
| 23–31 | Green |
| 17–22 | Yellow-blue |
| 9–16 | Blue |

MRM displays this official light separately from the MRM macro-regime label.

## Component votes

Each available component contributes either +1 or -1.

### PMI level

```text
PMI >= 50  -> +1
PMI < 50   -> -1
```

### NDC leading momentum

```text
Leading_t - Leading_(t-3) >= 0  -> +1
otherwise                        -> -1
```

### NDC coincident momentum

```text
Coincident_t - Coincident_(t-3) >= 0  -> +1
otherwise                              -> -1
```

### Manufacturing-production momentum

```text
100 * (Production_t / Production_(t-3) - 1) >= 0  -> +1
otherwise                                          -> -1
```

The current config requires at least **2 known components**.

## Composite score

```text
score_t = mean(known component votes)
```

Range:

```text
-1 ... +1
```

Confidence is:

```text
known components / configured components
```

A missing macro release is not converted to a negative vote.

## Regime direction

The classifier also looks at the change in composite score over three monthly observations:

```text
momentum_t = score_t - score_(t-3)
```

Labels:

| Current score | Score momentum | Regime |
|---|---|---|
| >= 0 | >= 0 / insufficient prior history | Expansion |
| >= 0 | < 0 | Deceleration |
| < 0 | > 0 | Recovery |
| < 0 | <= 0 / insufficient prior history | Contraction |

If too few components are known, the regime is `unknown`.

## Point-in-time / release dates

The import contract retains both:
- observation month (`date`)
- publication date (`release_date`)

Each regime row records `available_on`, equal to the latest release date among the components contributing at that observation month.

The classifier itself never uses future observation rows to calculate a historical month's votes or momentum.

Any event-study layer that asks "what was known on date T?" must additionally require:

```text
available_on <= T
```

## Configuration

All thresholds and component rules are stored in:

`data/config/taiwan-macro.json`

They are not embedded in the browser.

## Interpretation

The regime is descriptive:

- **Expansion** — public manufacturing/business-cycle inputs are broadly positive and not weakening.
- **Deceleration** — inputs remain net-positive but their composite direction has weakened.
- **Recovery** — inputs remain net-negative but are improving.
- **Contraction** — inputs are net-negative and are not improving.

It is not:
- a recession declaration;
- a market-bottom signal;
- a buy/sell recommendation;
- an attempt to duplicate MM's proprietary composite.
