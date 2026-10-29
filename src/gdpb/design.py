"""Survey design: offer grids, recentering, allocation, sample size.

Follows Section 3 of the GDP-B Cookbook. One randomized offer per
respondent per item, drawn from a grid that should bracket the median and
reach high enough to estimate the capped mean. The spacing rule here is a
convenience, not a requirement: payments need not follow exact log spacing.
"""

import numpy as np
import pandas as pd


def log_grid(center: float, n: int = 7, span: float = 2.5, round_to: int = 0) -> list[float]:
    """Log-spaced grid of n offers centred on `center`.

    `span` is the half-width in log units; the extreme offers are
    center * exp(+-span). With span=2.5 the grid covers a factor of about
    150 either side, wide enough for first-wave uncertainty.
    """
    if center <= 0:
        raise ValueError("center must be positive")
    g = np.exp(np.log(center) + np.linspace(-span, span, n))
    g = np.unique(np.round(g, round_to).clip(min=1.0))
    return [float(x) for x in g]


def recenter_grid(fit_row, n: int = 7, span: float = 1.5, keep: list[float] | None = None) -> list[float]:
    """Second-wave grid from a first-wave fit (a row of the item table).

    - median above the grid: centre on 3x the old maximum
    - median below the grid: centre on the old minimum / 3
    - otherwise centre on the estimated median with a narrower span
    `keep` lists offers to retain for comparability across waves.
    """
    loc = fit_row.get("median_location", "within_grid")
    med = fit_row.get("median_wta", np.nan)
    if loc == "above_grid" or not np.isfinite(med):
        g = log_grid(3.0 * float(fit_row["grid_max"]), n=n, span=span)
    elif loc == "below_grid":
        g = log_grid(max(1.0, float(fit_row["grid_min"]) / 3.0), n=n, span=span)
    else:
        g = log_grid(float(med), n=n, span=span)
    if keep:
        g = sorted(set(g) | {float(k) for k in keep})
    return g


def required_sample(n_offers: int, per_offer: int = 200, p_use: float = 1.0,
                    attrition: float = 0.10) -> int:
    """Respondents to recruit per item so each offer has about `per_offer`
    usable user responses after nonusers and cleaning losses.

    `per_offer` is a planning input, not a universal rule: the precision you
    need, the number of items, and whether information is pooled across
    items all change it (Cookbook 3.3).
    """
    if not 0 < p_use <= 1:
        raise ValueError("p_use must be in (0, 1]")
    return int(np.ceil(n_offers * per_offer / (p_use * (1.0 - attrition))))


def allocate(items: pd.DataFrame, n_respondents: int, items_per_respondent: int = 1,
             seed: int = 0) -> pd.DataFrame:
    """Assign each respondent `items_per_respondent` items and one offer per item.

    Offers are balanced within item (round-robin over a shuffled grid) so
    cells fill evenly. Returns respondent_id, item_id, offer, position.
    The usage question must still be asked before the offer is shown.
    """
    from .schema import parse_grid

    rng = np.random.default_rng(seed)
    keys = items["item_id"].tolist()
    grids = {r["item_id"]: parse_grid(r["price_grid"]) for _, r in items.iterrows()}
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
            rows.append({"respondent_id": f"R{i + 1:06d}", "item_id": k,
                         "offer": float(g[idx]), "position": pos})
    return pd.DataFrame(rows)
