"""Deposit files: what a study hands over so others can reproduce and compare it.

Follows Cookbook 4.6 and 8.4.

    items.csv                per item: n, usage rate, median (CI, location), reporting cap,
                             capped mean (CI), NPMLE median, grid, acceptance at the ends,
                             bootstrap counts, notes
    acceptance_by_offer.csv  per item and offer: n and acceptance rate
    aggregate.csv            per item: adoption used and source, users, annualized capped value
    metadata.json            config, software versions, caps, annualization, counts by location
    audit.json               cleaning rules, rows removed, offers of removed users
    summary.md               readable summary with the labels the cookbook asks for
"""

import json
import platform
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
import statsmodels

from . import __version__ as _pkg_version


def write_deposit(outdir, item_table: pd.DataFrame, audit: dict, config: dict,
                  acceptance_table: pd.DataFrame | None = None,
                  agg_table: pd.DataFrame | None = None, totals: dict | None = None) -> Path:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    item_table.to_csv(out / "items.csv", index=False)
    if acceptance_table is not None:
        acceptance_table.to_csv(out / "acceptance_by_offer.csv", index=False)
    if agg_table is not None:
        agg_table.to_csv(out / "aggregate.csv", index=False)
    meta = {
        "gdpb_version": _pkg_version,
        "generated": date.today().isoformat(),
        "software": {"python": platform.python_version(), "numpy": np.__version__,
                     "pandas": pd.__version__, "scipy": scipy.__version__,
                     "statsmodels": statsmodels.__version__, "scikit-learn": sklearn.__version__},
        "config": config,
        "n_items": int(len(item_table)),
        "median_location_counts": item_table["median_location"].value_counts().to_dict(),
        "reporting_caps": sorted(item_table["reporting_cap"].dropna().unique().tolist()),
        "data_status": config.get("data_status", "unspecified"),
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    (out / "audit.json").write_text(json.dumps(audit, indent=2, default=str))
    (out / "summary.md").write_text(summary_markdown(item_table, audit, agg_table, totals))
    return out


def _fmt(x, nd=2):
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:,.{nd}f}"


def summary_markdown(item_table: pd.DataFrame, audit: dict,
                     agg_table: pd.DataFrame | None = None, totals: dict | None = None) -> str:
    L = ["# GDP-B survey summary", ""]
    L += ["## Cleaning", "", "| rule | rows removed |", "|---|---:|"]
    for k, v in audit.get("rules", {}).items():
        L.append(f"| {k} | {'skipped' if v == 'skipped' else v['removed']} |")
    L += ["", f"Rows in: {audit.get('rows_in')}. Rows out: {audit.get('rows_out')}.", ""]

    L += ["## Per-item WTA (monthly, among users)", "",
          "| item | users | usage rate | median | 95% CI | location | cap | capped mean | 95% CI |",
          "|---|---:|---:|---:|---|---|---:|---:|---|"]
    for _, r in item_table.iterrows():
        L.append(f"| {r['item_id']} | {r['n_users']} | {r['sample_usage_rate']:.2f} | "
                 f"{_fmt(r['median_wta'])} | {_fmt(r['median_lo'])}–{_fmt(r['median_hi'])} | "
                 f"{r['median_location']} | {_fmt(r['reporting_cap'], 0)} | "
                 f"{_fmt(r['capped_mean_wta'])} | {_fmt(r['capped_mean_lo'])}–{_fmt(r['capped_mean_hi'])} |")
    notes = item_table[item_table["notes"].astype(str) != ""]
    if len(notes):
        L += ["", "Notes:", ""]
        L += [f"- {r['item_id']}: {r['notes']}" for _, r in notes.iterrows()]

    if agg_table is not None:
        L += ["", "## Annualized capped aggregate value", "",
              "| item | adoption used | source | users | annualized capped value |",
              "|---|---:|---|---:|---:|"]
        for _, r in agg_table.iterrows():
            L.append(f"| {r['item_id']} | {r['adoption_rate_used']:.3f} | {r['adoption_source']} | "
                     f"{r['users']:,.0f} | {_fmt(r['annualized_capped_value'], 0)} |")
        if totals:
            L += ["", f"Total across {totals['n_items']} items: "
                      f"{_fmt(totals['total_annualized_capped_value'], 0)}."]
            L += [f"- {n}" for n in totals.get("notes", [])]

    L += ["", "Medians describe the typical user; capped means feed aggregates. "
              "Each capped mean is labelled with its reporting cap and is not a statistical "
              "lower bound. Medians located below_grid or above_grid are extrapolations. "
              "Aggregates assume nonusers value the restriction at zero and annualize the "
              "survey-month value; they are not compensation for a year without access."]
    return "\n".join(L) + "\n"
