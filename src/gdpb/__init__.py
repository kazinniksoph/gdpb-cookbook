"""gdpb: a reusable toolkit for GDP-B style willingness-to-accept surveys.

Implements the workflow of the GDP-B Cookbook (Sections 3-5 and 8).

design    -> offer grids, recentering, respondent allocation, sample-size planning
clean     -> protocol cleaning rules with an audit trail
estimate  -> per-item WTA: logit/probit median with bootstrap CI, capped mean,
             NPMLE acceptance curve, median location against the offers shown
aggregate -> annualized capped value, total-income GDP-B growth, Productivity-B
report    -> deposit files (items, acceptance by offer, aggregate, metadata, audit, summary)

Every stage reads and writes the schemas in gdpb.schema: an item file and a
long response file with usage measured before the offer. Adapt the data,
not the formulas.
"""

__version__ = "0.2.0"

from .schema import validate_responses, validate_items, parse_grid, SchemaError  # noqa: E402,F401
from .clean import clean_responses  # noqa: E402,F401
from .estimate import (  # noqa: E402,F401
    ItemFit,
    fit_item,
    median_wta,
    capped_mean_wta,
    bootstrap_ci,
    acceptance_by_offer,
    npmle_acceptance,
    median_location,
    estimate_item,
    estimate_all_items,
    winsorize_column,
)
from .aggregate import (  # noqa: E402,F401
    sample_usage_rate,
    aggregate_value,
    aggregate_table,
    total_income_growth,
    compound_annual_rate,
    productivity_b,
    sum_values,
)
from .design import log_grid, recenter_grid, allocate, required_sample  # noqa: E402,F401
from .simulate import simulate_survey  # noqa: E402,F401
from .report import write_deposit  # noqa: E402,F401
