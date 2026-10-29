# gdpb

A reusable toolkit for running GDP-B style willingness-to-accept (WTA) surveys:
design the price grids, clean the responses, estimate per-item WTA, aggregate to
consumer surplus, and write a deposit that other teams can compare against.

The method is from Brynjolfsson, Collis, Diewert, Eggers and Fox,
"GDP-B: Accounting for the Value of New and Free Goods" (*AEJ: Macro*, 2025).
The code distils the pipelines used for the Stanford Digital Economy Lab's
GDP-B Waves 1 and 2 and the "What is Generative AI Worth?" survey.

## Install

```bash
pip install git+https://github.com/kazinniksoph/gdpb
# or, for development
git clone https://github.com/kazinniksoph/gdpb && cd gdpb && pip install -e ".[dev]" && pytest
```

Python 3.10 or later. Depends on numpy, pandas, statsmodels, scikit-learn, pyyaml.

## Five-minute tour

```bash
gdpb simulate demo --n-per-item 2100      # synthetic survey with known ground truth
gdpb clean demo/raw_responses.csv -o demo/clean.csv
gdpb estimate demo/clean.csv -o demo/items.csv
gdpb aggregate demo/items.csv --population 260000000 -o demo/aggregate.csv
```

Or drive the whole thing from one file:

```yaml
# config.yaml
responses: raw_responses.csv
items: items.csv
cleaning:    { min_duration_seconds: 45, require_attention: true }
estimation:  { link: logit, n_boot: 500, seed: 0 }
aggregation: { population: 260000000, adoption: adoption.csv }   # adoption.csv optional
output: deposit
```

```bash
gdpb run config.yaml
```

The deposit folder holds `items.csv`, `aggregate.csv`, `metadata.json`,
`audit.json` and a readable `summary.md`.

## The two files everything shares

**Responses** (long, one row per respondent × item):

| column | meaning |
|---|---|
| `respondent_id` | stable id |
| `item` | key matching the item file |
| `price` | the one randomized monthly payment the respondent saw |
| `response` | `yes` (would give it up for the payment), `no`, or `dont_use` |
| optional | `duration_seconds`, `attention_check_passed`, `selected_fake_item`, `weight`, demographics |

Common export codings (Yes/No strings, 1/0) are mapped automatically by `gdpb validate`.

**Items** (one row per item):

| column | meaning |
|---|---|
| `item` | key |
| `label` | wording shown to respondents |
| `scope` | `brand` or `category`; never sum surplus across the two |
| `grid` | pipe-separated prices, e.g. `1|10|20|50|100|200|500` |

Platform exporters (Qualtrics and others) will read the item file and write a
survey; until then, the item file plus `gdpb design` give you the per-respondent
allocation to load into any survey tool.

## What the estimator does

For each item, among users only:

1. Fit `Pr(accept) = F(α + β ln price)` with a logit (default) or probit link.
2. Median WTA = `exp(−α/β)`, with a percentile bootstrap CI over respondents.
3. Mean WTA = area under the fitted survival curve, truncated at the top of the grid.
   This is a lower bound and is the figure used for aggregate surplus.
4. Isotonic (monotone) acceptance curve and its median crossing as a
   nonparametric check, plus a Kaplan–Meier style survival curve.
5. Flags: median outside the grid (left/right censored), acceptance too high at
   the lowest price or too low at the highest (grid misplaced).

`P(use)` comes from the `dont_use` option, or from an external adoption file
when you have a representative source. Aggregate annual surplus is
`P(use) × mean WTA × population × 12`. The total-income route to GDP-B growth
(eq. 33 of the paper) is in `gdpb.aggregate.total_income_growth`.

## Python API

```python
import pandas as pd
from gdpb import validate_responses, clean_responses, estimate_all_items

raw = validate_responses(pd.read_csv("raw_responses.csv"))
clean, audit = clean_responses(raw)
table, fits = estimate_all_items(clean, link="probit", n_boot=1000)
```

## Design helpers

```python
from gdpb import log_grid, recenter_grid, required_sample, allocate
log_grid(center=50, n=7, span=2.5)          # first-wave grid around a pilot median
recenter_grid(table.iloc[0])                # second-wave grid from a first-wave fit
required_sample(n_prices=7, per_price=200, p_use=0.6, attrition=0.1)
```

## Validation

Tests recover the medians and usage rates of a synthetic survey with known
ground truth (`pytest`). `scripts/validate_genai.py` reproduces the published
medians of the generative-AI survey from the raw microdata when that data is
available locally; the data itself is not in this repository.

## Roadmap

- Survey exporters: Qualtrics (REST) from the Wave 1/2 builders, plus a generic CSV/QSF export
- Interval-censored parametric fits (Weibull, log-logistic AFT) for sparse multi-item designs
- Post-stratification weights from census margins
- Documentation site from the executable protocol chapters

## License

MIT.
