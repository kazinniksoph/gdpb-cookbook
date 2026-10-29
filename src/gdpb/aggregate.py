"""From capped mean WTA to population values and GDP-B growth.

Follows Sections 2.4 and 5 of the GDP-B Cookbook (equations T11-T13).

Aggregate valuation (Section 5.1)
    M = annualization_factor x N x pi x mu_c
    N   target population        pi  adoption share (study's user definition)
    mu_c  mean monthly WTA among users, capped at c
Assumes nonusers value the restriction at zero; say so when reporting.
The x12 convention gives an annualized value at the conditions observed in
the survey month, not the compensation for a year without access.

Total-income route (T11-T13)
    T_t = Y_t + M_t ;  G = (T_1/T_0) / D ;  g = G - 1 ;  g_annual = G^(1/n) - 1
    D is the GDP-deflator RATIO P_1/P_0 (1.30, not 130).
"""

import numpy as np
import pandas as pd


def sample_usage_rate(item_df: pd.DataFrame) -> float:
    """Weighted share of respondents who are users (from the pre-offer usage question)."""
    w = item_df["weight"] if "weight" in item_df.columns else pd.Series(1.0, index=item_df.index)
    return float((w * item_df["is_user"]).sum() / w.sum())


def aggregate_value(capped_mean_monthly: float, adoption_rate: float, population: float,
                    annualization_factor: float = 12) -> dict:
    """Annualized capped aggregate value for one item (Section 5.1)."""
    if not 0 <= adoption_rate <= 1:
        raise ValueError("adoption_rate must lie in [0, 1]")
    if population <= 0 or annualization_factor <= 0:
        raise ValueError("population and annualization_factor must be positive")
    users = adoption_rate * population
    return {
        "users": float(users),
        "annualized_value_per_user": float(capped_mean_monthly * annualization_factor),
        "annualized_capped_value": float(capped_mean_monthly * annualization_factor * users),
    }


def aggregate_table(item_table: pd.DataFrame, population: float, adoption=None,
                    adoption_source: str = "survey usage question",
                    annualization_factor: float = 12) -> pd.DataFrame:
    """Apply aggregate_value to every row of an item table.

    `adoption` may be None (use the survey's own usage rate), a number applied
    to all items, or a dict item_id -> adoption rate from an external source.
    """
    rows = []
    for _, r in item_table.iterrows():
        if isinstance(adoption, dict) and r["item_id"] in adoption:
            rate, src = float(adoption[r["item_id"]]), adoption_source
        elif isinstance(adoption, (int, float)) and adoption is not None:
            rate, src = float(adoption), adoption_source
        else:
            rate, src = float(r["sample_usage_rate"]), "survey usage question"
        mean_c = float(r["capped_mean_wta"])
        agg = aggregate_value(mean_c, rate, population, annualization_factor) \
            if np.isfinite(mean_c) else {"users": rate * population,
                                         "annualized_value_per_user": np.nan,
                                         "annualized_capped_value": np.nan}
        rows.append({"item_id": r["item_id"], "adoption_rate_used": rate, "adoption_source": src,
                     "population": population, "annualization_factor": annualization_factor,
                     "capped_mean_monthly_wta": mean_c, "reporting_cap": r["reporting_cap"],
                     "median_location": r.get("median_location", ""), **agg})
    return pd.DataFrame(rows)


def total_income_growth(gdp0: float, gdp1: float, m0: float, m1: float,
                        deflator_ratio: float) -> dict:
    """Real growth via total income (T11-T12).

    gdp0, gdp1       nominal GDP in the two periods (same currency as m)
    m0, m1           annualized valuation of the SAME consistently defined
                     free products in each period (m0 = 0 only if they did
                     not exist in period 0)
    deflator_ratio   P_1 / P_0 from the conventional GDP deflator
    """
    if min(gdp0, gdp1, deflator_ratio) <= 0 or m0 < 0 or m1 < 0:
        raise ValueError("GDP and deflator ratio must be positive; valuations non-negative")
    if deflator_ratio > 20:
        raise ValueError("deflator_ratio looks like an index level; pass the ratio P1/P0")
    g_conv = (gdp1 / gdp0) / deflator_ratio
    g_b = ((gdp1 + m1) / (gdp0 + m0)) / deflator_ratio
    return {"conventional_index": float(g_conv), "conventional_growth": float(g_conv - 1),
            "gdpb_total_income_index": float(g_b), "gdpb_total_income_growth": float(g_b - 1),
            "adjustment_pp": float((g_b - g_conv) * 100)}


def compound_annual_rate(growth_index: float, n_years: float) -> float:
    """g_annual = G^(1/n) - 1 (T13)."""
    if growth_index <= 0 or n_years <= 0:
        raise ValueError("growth_index and n_years must be positive")
    return float(growth_index ** (1.0 / n_years) - 1.0)


def productivity_b(gdpb_quantity_index: float, hours_index: float) -> float:
    """Productivity-B growth index: GDP-B quantity index over the hours-worked index."""
    if gdpb_quantity_index <= 0 or hours_index <= 0:
        raise ValueError("indexes must be positive")
    return float(gdpb_quantity_index / hours_index)


def sum_values(agg_table: pd.DataFrame, items_df: pd.DataFrame | None = None) -> dict:
    """Total across items with the adding-up caveats attached (Cookbook 6.4)."""
    notes = ["sum across items assumes no substitution or complementarity between them"]
    if items_df is not None:
        scopes = items_df.set_index("item_id")["scope"].to_dict()
        if {"brand", "category"} <= {scopes.get(i) for i in agg_table["item_id"]}:
            notes.append("table mixes brand and category scopes: do not sum across them")
    extrap = int(agg_table["median_location"].isin(["below_grid", "above_grid"]).sum()) \
        if "median_location" in agg_table else 0
    if extrap:
        notes.append(f"{extrap} items have extrapolated medians")
    caps = agg_table["reporting_cap"].dropna().unique() if "reporting_cap" in agg_table else []
    if len(caps) > 1:
        notes.append("items use different reporting caps: totals are not on one basis")
    return {"total_annualized_capped_value": float(np.nansum(agg_table["annualized_capped_value"])),
            "n_items": int(len(agg_table)), "notes": notes}
