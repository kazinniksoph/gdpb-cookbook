# gdpb

`gdpb` is an open-source Python package for conducting GDP-B willingness-to-accept (WTA) surveys. It provides a reproducible workflow for **designing surveys, cleaning responses, estimating product-level WTA, calculating consumer surplus, and producing standardized research outputs**.

The methodology follows Brynjolfsson, Collis, Diewert, Eggers, and Fox, "GDP-B: Accounting for the Value of New and Free Goods" (*American Economic Journal: Macroeconomics*, 2025). The package builds on the survey and estimation pipelines developed at Stanford's Digital Economy Lab for GDP-B Waves 1 and 2 and the *What Is Generative AI Worth?* study.

The goal is to make the methodology reusable across products, populations, and survey waves without rewriting the estimation code.

## Installation

```bash
pip install git+https://github.com/kazinniksoph/gdpb
```

For development:

```bash
git clone https://github.com/kazinniksoph/gdpb
cd gdpb-cookbook
pip install -e ".[dev]"
pytest
```

Requires Python 3.10 or later. Dependencies include `numpy`, `pandas`, `statsmodels`, `scikit-learn`, and `pyyaml`.

## Quick start

Run the pipeline on synthetic survey data with known WTA values and adoption rates:

```bash
# Generate synthetic survey responses
gdpb simulate demo --n-per-item 2100

# Clean responses
gdpb clean demo/raw_responses.csv -o demo/clean.csv

# Estimate WTA for each product
gdpb estimate demo/clean.csv -o demo/items.csv

# Calculate aggregate consumer surplus
gdpb aggregate demo/items.csv \
  --population 260000000 \
  -o demo/aggregate.csv
```

Alternatively, run the entire pipeline from a single configuration file:

```yaml
# config.yaml
responses: raw_responses.csv
items: items.csv

cleaning:
  min_duration_seconds: 45
  require_attention: true

estimation:
  link: logit
  n_boot: 500
  seed: 0

aggregation:
  population: 260000000
  adoption: adoption.csv  # Optional external adoption data

output: deposit
```

Run:

```bash
gdpb run config.yaml
```

The resulting `deposit/` directory contains:

- `items.csv`: Product-level WTA estimates
- `aggregate.csv`: Aggregate consumer surplus
- `metadata.json`: Estimation settings and survey metadata
- `audit.json`: Cleaning rules and excluded observations
- `summary.md`: Readable summary of the results

These files provide a standardized record that other researchers can reproduce and compare across countries and survey waves.

## Input data

The package uses two files.

### 1. Responses

The response file is in long format, with **one row per respondent and product**.

| Column | Description |
|---|---|
| `respondent_id` | Unique respondent identifier |
| `item` | Product identifier matching the items file |
| `price` | Randomly assigned monthly compensation offer |
| `response` | `yes` (accepts compensation), `no` (rejects), or `dont_use` |
| Optional | `duration_seconds`, `attention_check_passed`, `selected_fake_item`, `weight`, demographics |

Common survey response formats, including Yes/No strings and 1/0 coding, are standardized by `gdpb validate`.

### 2. Items

The items file defines the products and their survey design.

| Column | Description |
|---|---|
| `item` | Product identifier |
| `label` | Wording shown to respondents |
| `scope` | `brand` or `category`; overlapping valuations should not be added |
| `grid` | Payment amounts separated by pipes, e.g. `1\|10\|20\|50\|100\|200\|500` |

The package is independent of the survey platform. Researchers can use `gdpb design` to generate price grids and respondent allocations, then import these into their preferred survey tool.

Automated exporters for Qualtrics and other platforms are planned.

## WTA estimation

For each product, the package estimates WTA among respondents who use it.

1. **Acceptance model.** Fit a logit (default) or probit model relating acceptance to log payment:

   `Pr(accept = 1 | price) = F(α + β ln(price))`

2. **Median WTA.** Calculate the payment at which predicted acceptance reaches 50%:

   `Median WTA = exp(−α/β)`

   Confidence intervals are obtained using a respondent-level percentile bootstrap.

3. **Mean WTA.** Integrate the fitted survival curve up to the highest offered price. This truncated mean is a lower-bound estimate of unrestricted mean WTA and is used to calculate aggregate consumer surplus.

4. **Nonparametric checks.** Estimate an isotonic acceptance curve, which enforces monotonicity, and identify its 50% crossing. The package also produces a Kaplan–Meier-style WTA survival curve.

5. **Identification and grid diagnostics.** Flag estimates whose medians fall outside the offered price range (left- or right-censored). Separately, warn when acceptance at the lowest price exceeds 35% or acceptance at the highest price falls below 65%, which signals that the grid is drifting even when the median is still inside it. Both thresholds are adjustable. These diagnostics help determine whether subsequent survey waves need different price grids.

### Aggregating consumer surplus

The share of the population using each product, `P(use)`, can be estimated from the `dont_use` responses or supplied through an external, representative adoption dataset.

Annual consumer surplus is calculated as:

**Annual CS = P(use) × Mean monthly WTA among users × Population × 12**

The package also implements the total-income approach to GDP-B growth (equation 33 of the paper):

`gdpb.aggregate.total_income_growth`

## Python API

The main functions can also be called directly from Python:

```python
import pandas as pd
from gdpb import (
    validate_responses,
    clean_responses,
    estimate_all_items,
)

# Validate and standardize survey responses
raw = validate_responses(
    pd.read_csv("raw_responses.csv")
)

# Apply cleaning rules and retain an audit
clean, audit = clean_responses(raw)

# Estimate item-level WTA
table, fits = estimate_all_items(
    clean,
    link="probit",
    n_boot=1000,
)
```

This returns item-level estimates and fitted models, allowing researchers to inspect results or extend the analysis.

## Survey design tools

The package includes functions for constructing price grids, updating them between waves, and determining sample sizes.

```python
from gdpb import (
    log_grid,
    recenter_grid,
    required_sample,
    allocate,
)

# First-wave price grid centered on a pilot median
log_grid(center=50, n=7, span=2.5)

# Re-center the grid using a first-wave estimate
recenter_grid(table.iloc[0])

# Calculate required sample size
required_sample(
    n_prices=7,
    per_price=200,
    p_use=0.6,
    attrition=0.1,
)
```

These tools help ensure that randomized payment offers adequately cover the WTA distribution and that each price point receives sufficient observations.

## Validation

The package is tested using synthetic survey data with known WTA distributions and adoption rates. The tests (`pytest`) verify that the estimation pipeline recovers these underlying values.

An additional script, `scripts/validate_genai.py`, reproduces the published median WTA estimates from the generative AI survey when the original microdata are available locally.

The survey microdata are **not included** in the public repository.

## Roadmap

Planned extensions include:

- **Survey exporters:** Qualtrics REST integration based on the Wave 1/2 survey builders, plus generic CSV and QSF export.
- **Sparse-data estimation:** Interval-censored parametric models, including Weibull and log-logistic accelerated failure time (AFT) models.
- **Population weighting:** Post-stratification weights based on census margins.
- **Documentation:** A dedicated documentation site built from the executable methodology and protocol.

## License

MIT.
