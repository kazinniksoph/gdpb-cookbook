# gdpb

`gdpb` is an open-source Python package for conducting GDP-B willingness-to-accept (WTA) surveys. It provides a reproducible workflow for **designing surveys, cleaning responses, estimating product-level WTA, calculating aggregate consumer value, and producing standardized research outputs**.

The package implements the workflow of [*The GDP-B Cookbook*](GDP-B_COOKBOOK.md), a practical guide to survey design, valuation, aggregation, and GDP-B growth accounting. The methodology follows Brynjolfsson, Collis, Diewert, Eggers, and Fox, "GDP-B: Accounting for the Value of New and Free Goods" (*American Economic Journal: Macroeconomics*, 2025). Section numbers below refer to the cookbook.

The goal is to make the methodology reusable across products, populations, and survey waves without rewriting the estimation code. Adaptation happens in the data files, not in the formulas.

## Installation

```bash
pip install git+https://github.com/kazinniksoph/gdpb-cookbook
```

For development:

```bash
git clone https://github.com/kazinniksoph/gdpb-cookbook
cd gdpb-cookbook
pip install -e ".[dev]"
pytest
```

Requires Python 3.10 or later. Dependencies: `numpy`, `pandas`, `scipy`, `statsmodels`, `scikit-learn`, and `pyyaml`.

## Quick start

Run the pipeline on synthetic survey data with known WTA values and adoption rates:

```bash
# Generate synthetic survey responses (all observations are synthetic)
gdpb simulate demo --n-per-item 2100

# Clean responses and write an audit of what each rule removed
gdpb clean demo/raw_responses.csv -o demo/clean.csv

# Estimate WTA for each product, with the mean capped at $500
gdpb estimate demo/clean.csv --cap 500 -o demo/items.csv

# Annualized capped aggregate value
gdpb aggregate demo/items.csv --population 260000000 -o demo/aggregate.csv
```

Alternatively, run the entire pipeline from one configuration file. The keys are those of the cookbook's example (Section 8.2):

```yaml
# config.yaml
responses: responses.csv
items: items.csv
item_id: demo_service          # optional: restrict to one item
population: 1000000
adoption_rate: 0.40            # a number, a CSV with item_id and adoption_rate, or null for the survey's usage question
adoption_source: hypothetical fixed input
reporting_cap: 500             # cap for the mean, chosen separately from the offer grid
annualization_factor: 12
seed: 314159
cleaning:
  min_duration_seconds: 45
  require_attention: true
estimation:
  link: logit
  n_boot: 500
output: deposit
```

```bash
gdpb run config.yaml       # config.json works too
```

The resulting `deposit/` directory contains:

- `items.csv`: product-level estimates with their diagnostics
- `acceptance_by_offer.csv`: observed acceptance rate and count at every offer shown
- `aggregate.csv`: adoption used and its source, users, annualized capped value
- `metadata.json`: configuration, reporting caps, software versions, counts of median locations
- `audit.json`: cleaning rules, rows removed, and the offers assigned to removed users
- `summary.md`: readable summary with the labels the cookbook asks for

These files are the record a study hands over so others can reproduce it and compare across countries and waves (Section 8.4).

## Input data

The package uses two files, in the formats of the cookbook's worked example (Section 8.2).

### 1. Responses

Long format, **one row per respondent and product**. Usage is measured before any offer is shown; nonusers receive no valuation question.

| Column | Description |
|---|---|
| `respondent_id` | Unique respondent identifier |
| `item_id` | Product identifier matching the items file |
| `is_user` | 1 if the respondent meets the study's definition of a user, measured before the offer; 0 otherwise |
| `offer` | Randomly assigned compensation offer; positive for users, blank for nonusers |
| `response` | `yes` (accepts the offer), `no` (rejects), or `not_asked` for nonusers |
| `weight` | Survey weight (optional, defaults to 1) |
| Optional | `duration_seconds`, `attention_check_passed`, `selected_fake_item`, demographics |

Legacy exports are mapped on validation: a three-way `dont_use` answer becomes `is_user = 0`, `response = not_asked`; `item`/`price` are accepted as aliases; Yes/No strings and 1/0 become `yes`/`no`. The cookbook recommends a separate usage question rather than relying on a "Don't use" option (Section 3.1).

### 2. Items

| Column | Description |
|---|---|
| `item_id` | Product identifier |
| `scope` | `brand` or `category`; valuations across the two should not be summed |
| `currency` | ISO code, e.g. `USD` |
| `duration_months` | Length of the access restriction valued (1 for one month) |
| `price_grid` | Offers separated by pipes, e.g. `5\|10\|25\|50\|100\|250\|500` |
| `label` | Optional wording shown to respondents |

The package is independent of the survey platform. `gdpb design` produces offer grids and a balanced respondent-to-offer allocation to load into any survey tool. Exporters for Qualtrics and other platforms are planned.

## WTA estimation (Section 4)

For each product, among users only:

1. **Current-status data.** A `yes` at offer *p* means WTA ≤ *p*; a `no` means WTA > *p* (E1). Accepted offers are never treated as exact WTA values.

2. **Acceptance model.** Fit a logit (default) or probit on log offer (E3):

   `Pr(accept = 1 | offer) = F(α + β ln(offer))`

3. **Median WTA.** `exp(−α/β)` (E4), with a respondent-level percentile bootstrap. Resampling is by respondent, so repeated rows from one person stay together.

4. **Capped mean WTA.** `E[min(W, c)] = ∫₀ᶜ [1 − F(α + β ln p)] dp` (E5). The cap *c* is a reporting choice recorded with every estimate; by default it is the top of the item's offer grid, and a cap above the largest offer is flagged because it relies on the model beyond the observed range. Results are labelled, for example, "mean monthly WTA, capped at $500". A capped mean is not a statistical lower bound.

5. **Nonparametric check.** The monotone (pooled-adjacent-violators) acceptance curve is the nonparametric maximum-likelihood estimate for current-status data; its 50% crossing is reported as `npmle_median`. It is not a Kaplan–Meier estimate.

6. **Median location and grid diagnostics.** Every median is classified as `within_grid`, `below_grid`, `above_grid`, or `undefined` against the offers actually shown. Medians outside the grid are labelled extrapolations. Notes also record when acceptance at the smallest offer already exceeds 50% or never reaches 50% at the largest offer (Section 4.4).

Each estimate carries the bootstrap counts requested and successful, the acceptance rate at the smallest and largest offer, and the full acceptance-by-offer table.

`gdpb.estimate.winsorize_column` exists for sensitivity analysis but is **never applied automatically** (Section 4.6). If you use it, report the threshold, the share affected, and results with and without it.

## Aggregation and growth accounting (Sections 2.4 and 5)

Annualized aggregate value for one product:

**M = annualization_factor × population × adoption rate × capped mean monthly WTA**

Adoption can come from the survey's own usage question or from an external, representative source; the source is recorded in `aggregate.csv`. The calculation assumes nonusers value the restriction at zero, and the ×12 convention gives an annualized value at the conditions observed in the survey month, not compensation for a year without access (Section 5.3). Summaries carry both caveats.

The total-income route to GDP-B growth (equations T11–T13) is implemented as:

```python
from gdpb import total_income_growth, compound_annual_rate, productivity_b

total_income_growth(gdp0=100, gdp1=110, m0=0.9, m1=1.2, deflator_ratio=1.05)
# conventional real growth 4.76%, GDP-B total-income growth 4.96%, adjustment 0.20 pp
compound_annual_rate(growth_index, n_years)
productivity_b(gdpb_quantity_index, hours_index)
```

The deflator is passed as a ratio (1.30, not 130); an index level is rejected. The function reproduces the cookbook's Section 5.4 example.

Summing values across products attaches the adding-up caveats of Section 6.4: no substitution or complementarity assumed, no mixing of brand and category scopes, and a count of items with extrapolated medians.

## Python API

```python
import pandas as pd
from gdpb import validate_responses, clean_responses, estimate_all_items

raw = validate_responses(pd.read_csv("responses.csv"))
clean, audit = clean_responses(raw)
table, fits, acceptance = estimate_all_items(clean, reporting_cap=500, link="probit", n_boot=1000)
```

`table` is one row per item, `fits` the list of `ItemFit` objects, and `acceptance` the acceptance-by-offer table.

## Survey design tools (Section 3)

```python
from gdpb import log_grid, recenter_grid, required_sample, allocate

log_grid(center=50, n=7, span=2.5)                 # first-wave offer grid around a pilot median
recenter_grid(table.iloc[0], keep=[50, 500])       # second-wave grid, retaining offers for comparability
required_sample(n_offers=7, per_offer=200, p_use=0.6, attrition=0.1)
```

The spacing rule is a convenience, not a requirement, and `per_offer` is a planning input rather than a universal rule (Section 3.3).

## Validation

- `pytest` runs 25 tests on synthetic surveys with known WTA distributions and adoption rates.
- `examples/gdpb_example.py` is the cookbook's Appendix B script, verbatim. It depends only on numpy and scipy and reproduces the cookbook's worked numbers (median $50.34, capped mean $100.41 at a $500 cap). Two tests check that the package, run on that script's own files, gives the same median, capped mean, and annualized value.
- `scripts/validate_genai.py` re-estimates the generative AI survey medians from raw microdata when it is available locally. The microdata are **not included** in the repository. On the March 2026 file the package's probit median is within about 1% of the published $11.48 once the paper's cleaning rules are applied; the July 2025 figure does not yet match and is under investigation.

## Roadmap

- **Survey exporters:** Qualtrics REST integration based on the Wave 1/2 survey builders, plus generic CSV and QSF export.
- **Interval-censored estimation:** Turnbull estimation and Weibull, log-normal, and log-logistic models for sparse multi-item designs (Section 4.4).
- **Population weighting:** Post-stratification weights from census margins; design-based bootstrap for complex samples.
- **Documentation:** A documentation site built from the cookbook.

## License

MIT.
