"""gdpb: a reusable toolkit for GDP-B style willingness-to-accept surveys.

Pipeline
--------
design    -> price grids, respondent allocation, sample-size rules
clean     -> protocol cleaning rules with an audit trail
estimate  -> per-item WTA (logit/probit median and mean, bootstrap CI,
             isotonic and Kaplan-Meier curves, censoring flags)
aggregate -> consumer surplus and the total-income GDP-B adjustment
report    -> deposit files (item CSV, metadata JSON, audit JSON, summary)

Every stage reads and writes the two schemas defined in gdpb.schema:
an item file and a long response file. Adapt the data, not the formulas.
"""

from .schema import validate_responses, validate_items, SchemaError  # noqa: F401
from .clean import clean_responses  # noqa: F401
from .estimate import (  # noqa: F401
    ItemFit,
    fit_item,
    median_wta,
    mean_wta,
    bootstrap_median_ci,
    isotonic_acceptance,
    km_item_curve,
    estimate_item,
    estimate_all_items,
)
from .aggregate import usage_rate, aggregate_surplus, total_income_growth  # noqa: F401
from .design import log_grid, recenter_grid, allocate, required_sample  # noqa: F401
from .simulate import simulate_survey  # noqa: F401

__version__ = "0.1.0"
