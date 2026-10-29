"""From per-user WTA to aggregate consumer surplus and GDP-B growth.

Consumer surplus identity
    annual CS = P(use) x E[WTA | use] (monthly) x population x 12

Use the *mean* conditional WTA for aggregate surplus and the median as
the headline per-user figure. Prefer an external, representative P(use)
over the survey panel's own usage rate when one exists.

Total-income route to GDP-B (NBER WP 25695 eq. 32-33)
    T_t = GDP_t + CS_t          (nominal, free goods valued at WTA)
    GDP-B_T growth = (T_1 / T_0) / P   with P the conventional GDP deflator ratio
This needs no reservation price and is a lower bound, because the
official deflator over-deflates when new goods are missing from it.
"""

import numpy as np
import pandas as pd


def usage_rate(item_df: pd.DataFrame) -> float:
    """P(use) from the dont_use option in the survey itself."""
    return float((item_df["response"] != "dont_use").mean())


def aggregate_surplus(mean_wta_monthly: float, p_use: float, population: float,
                      months: int = 12) -> dict:
    """Aggregate annual consumer surplus for one item."""
    users = p_use * population
    return {
        "users": float(users),
        "annual_surplus_per_user": float(mean_wta_monthly * months),
        "aggregate_annual_surplus": float(mean_wta_monthly * months * users),
    }


def aggregate_table(item_table: pd.DataFrame, population: float,
                    p_use_external: dict | None = None, months: int = 12) -> pd.DataFrame:
    """Apply aggregate_surplus to every row of an item table.

    `p_use_external` maps item -> adoption share from an outside source;
    items not in the map fall back to the survey's own p_use.
    """
    rows = []
    for _, r in item_table.iterrows():
        p_use = (p_use_external or {}).get(r["item"], r["p_use"])
        src = "external" if r["item"] in (p_use_external or {}) else "survey"
        agg = aggregate_surplus(r["mean_wta"], p_use, population, months)
        rows.append({"item": r["item"], "p_use_used": p_use, "p_use_source": src,
                     "mean_wta_monthly": r["mean_wta"], **agg,
                     "right_censored": bool(r.get("right_censored", False))})
    return pd.DataFrame(rows)


def total_income_growth(gdp0: float, gdp1: float, cs0: float, cs1: float,
                        deflator_ratio: float) -> dict:
    """GDP-B_T growth over one interval via the total-income route (eq. 33).

    gdp0, gdp1        nominal GDP in the two periods
    cs0, cs1          nominal consumer surplus of the free goods in each period
                      (cs0 = 0 if the goods did not exist in period 0)
    deflator_ratio    P_1 / P_0 from the conventional GDP deflator
    Returns conventional real growth, GDP-B_T growth, and the gap, all as
    decimal growth rates over the interval.
    """
    if min(gdp0, gdp1, deflator_ratio) <= 0 or cs0 < 0 or cs1 < 0:
        raise ValueError("GDP, deflator must be positive; surplus non-negative")
    conv = (gdp1 / gdp0) / deflator_ratio - 1.0
    gdpb = ((gdp1 + cs1) / (gdp0 + cs0)) / deflator_ratio - 1.0
    return {"conventional_real_growth": float(conv),
            "gdpb_total_income_growth": float(gdpb),
            "adjustment_pp": float((gdpb - conv) * 100)}


def annualize_growth(total_growth: float, years: float) -> float:
    """Convert growth over `years` to a compound annual rate."""
    return float((1.0 + total_growth) ** (1.0 / years) - 1.0)


def category_sum_warning(item_table: pd.DataFrame, items_df: pd.DataFrame) -> list[str]:
    """Flag any attempt to add brand-level and category-level items together."""
    scopes = items_df.set_index("item")["scope"].to_dict()
    present = {scopes.get(i) for i in item_table["item"]}
    if {"brand", "category"} <= present:
        return ["item table mixes brand and category scopes: do not sum surplus across them"]
    return []


def sum_surplus(agg_table: pd.DataFrame, items_df: pd.DataFrame | None = None) -> dict:
    """Total aggregate surplus with the adding-up caveats attached."""
    notes = category_sum_warning(agg_table, items_df) if items_df is not None else []
    n_rc = int(agg_table["right_censored"].sum()) if "right_censored" in agg_table else 0
    if n_rc:
        notes.append(f"{n_rc} items right-censored: total is a lower bound")
    return {"total_aggregate_annual_surplus": float(np.nansum(agg_table["aggregate_annual_surplus"])),
            "n_items": int(len(agg_table)), "notes": notes}
