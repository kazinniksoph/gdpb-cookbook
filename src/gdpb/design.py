"""Survey design: price grids, recentring, allocation, sample size.

The fielded protocol uses one randomized price per respondent per item,
drawn from a log-spaced grid. The grid should bracket the median WTA:
acceptance near the bottom of the grid should be low, near the top high.
"""

import numpy as np
import pandas as pd


def log_grid(center: float, n: int = 7, span: float = 2.5, round_to: int = 0) -> list[float]:
    """Log-spaced grid of n prices centred on `center`.

    `span` is the half-width in log units: the extreme prices are
    center * exp(+-span). With span=2.5 the grid covers a factor of ~150
    in each direction, wide enough for first-wave uncertainty.
    """
    if center <= 0:
        raise ValueError("center must be positive")
    g = np.exp(np.log(center) + np.linspace(-span, span, n))
    g = np.round(g, round_to)
    g = np.unique(g.clip(min=1.0))
    return [float(x) for x in g]


def recenter_grid(fit_row, n: int = 7, span: float = 1.5) -> list[float]:
    """Second-wave grid from a first-wave fit (a row of the item table).

    Rules, in order:
    - right-censored (median above the grid): centre on 3x the old grid max
    - left-censored (median below the grid): centre on the old grid min / 3
    - otherwise centre on the estimated median with a narrower span
    """
    med = fit_row.get("median_wta", np.nan)
    if bool(fit_row.get("right_censored", False)) or not np.isfinite(med):
        return log_grid(3.0 * float(fit_row["grid_max"]), n=n, span=span)
    if bool(fit_row.get("left_censored", False)):
        return log_grid(max(1.0, float(fit_row["grid_min"]) / 3.0), n=n, span=span)
    return log_grid(float(med), n=n, span=span)


def required_sample(n_prices: int, per_price: int = 200, p_use: float = 1.0,
                    attrition: float = 0.10) -> int:
    """Respondents to recruit per item so that each price point has
    `per_price` usable *user* responses after nonusers and cleaning losses."""
    if not 0 < p_use <= 1:
        raise ValueError("p_use must be in (0, 1]")
    return int(np.ceil(n_prices * per_price / (p_use * (1.0 - attrition))))


def allocate(items: pd.DataFrame, n_respondents: int, items_per_respondent: int = 1,
             seed: int = 0) -> pd.DataFrame:
    """Assign each respondent `items_per_respondent` items and one price per item.

    Prices are balanced within item (round-robin over a shuffled grid) so
    that cells fill evenly rather than by chance. Returns a long table with
    columns respondent_id, item, price, position.
    """
    from .schema import parse_grid

    rng = np.random.default_rng(seed)
    keys = items["item"].tolist()
    grids = {r["item"]: parse_grid(r["grid"]) for _, r in items.iterrows()}
    if items_per_respondent > len(keys):
        raise ValueError("items_per_respondent exceeds number of items")

    counters = {k: 0 for k in keys}
    orders = {k: rng.permutation(len(grids[k])) for k in keys}
    rows = []
    for i in range(n_respondents):
        chosen = rng.choice(keys, size=items_per_respondent, replace=False)
        for pos, k in enumerate(chosen):
            g = grids[k]
            idx = orders[k][counters[k] % len(g)]
            counters[k] += 1
            if counters[k] % len(g) == 0:
                orders[k] = rng.permutation(len(g))
            rows.append({"respondent_id": f"R{i + 1:06d}", "item": k,
                         "price": float(g[idx]), "position": pos})
    return pd.DataFrame(rows)
