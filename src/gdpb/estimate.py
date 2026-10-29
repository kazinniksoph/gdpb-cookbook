"""Per-item WTA estimation from single binary discrete choice responses.

Follows Section 4 of the GDP-B Cookbook. Equation labels (E1-E5) refer to it.

Each user response is a current-status observation of that user's WTA (E1):
    yes => WTA <= offer        no => WTA > offer
Nonusers (is_user == 0) are excluded from the fit and enter only through
the sample usage rate.

Parametric core (E3-E5)
    Pr(accept | p) = F(alpha + beta ln p),  F logistic (default) or normal CDF
    median WTA     = exp(-alpha / beta)
    capped mean    = integral_0^c [1 - F(alpha + beta ln p)] dp
The cap c is a reporting choice set separately from the price grid. The
default is the top of the observed grid for the item; it is always recorded.

Nonparametric check
    The pooled-adjacent-violators (isotonic) fit of acceptance on offer is
    the nonparametric maximum-likelihood estimate of F for current-status
    data (the Turnbull estimator reduces to it when every respondent sees
    one offer). It is reported as `npmle_median`. It is not a Kaplan-Meier
    estimate and must not be computed as one.

Diagnostics
    median_location: within_grid / below_grid / above_grid / undefined,
    judged against the offers actually shown. Medians outside the grid
    are extrapolations and are labelled as such.
"""

from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
from sklearn.isotonic import IsotonicRegression

LINKS = ("logit", "probit")


@dataclass
class ItemFit:
    item_id: str
    link: str
    n_respondents: int
    n_users: int
    sample_usage_rate: float
    alpha: float
    beta: float
    median_wta: float
    median_lo: float
    median_hi: float
    median_location: str
    reporting_cap: float
    capped_mean_wta: float
    capped_mean_lo: float
    capped_mean_hi: float
    npmle_median: float
    grid_min: float
    grid_max: float
    accept_at_min_offer: float
    accept_at_max_offer: float
    bootstrap_requested: int
    bootstrap_successful: int
    notes: list = field(default_factory=list)

    def to_row(self) -> dict:
        d = asdict(self)
        d["notes"] = "; ".join(self.notes)
        return d


# ------------------------------------------------------------------ helpers

def users_of(item_df: pd.DataFrame) -> pd.DataFrame:
    return item_df[item_df["is_user"] == 1]


def _cdf(link: str):
    if link == "logit":
        return lambda z: 1.0 / (1.0 + np.exp(-z))
    return norm.cdf


def _design(users: pd.DataFrame):
    y = (users["response"] == "yes").astype(int).to_numpy()
    X = sm.add_constant(np.log(users["offer"].to_numpy(dtype=float)), has_constant="add")
    w = users["weight"].to_numpy(dtype=float) if "weight" in users.columns else None
    return y, X, w


# ------------------------------------------------------------------ parametric core

def fit_item(users: pd.DataFrame, link: str = "logit"):
    """Fit accept ~ ln(offer) among users (E3). Returns (alpha, beta, results)."""
    if link not in LINKS:
        raise ValueError(f"link must be one of {LINKS}")
    y, X, w = _design(users)
    fam = sm.families.Binomial(link=sm.families.links.Logit() if link == "logit"
                               else sm.families.links.Probit())
    res = sm.GLM(y, X, family=fam, freq_weights=w).fit()
    alpha, beta = (float(v) for v in res.params)
    return alpha, beta, res


def median_wta(alpha: float, beta: float) -> float:
    """Offer at which half of users accept (E4). NaN if beta <= 0."""
    if not np.isfinite(beta) or beta <= 0:
        return float("nan")
    return float(np.exp(-alpha / beta))


def capped_mean_wta(alpha: float, beta: float, cap: float, link: str = "logit",
                    n_grid: int = 20000) -> float:
    """E[min(W, cap)] = integral_0^cap [1 - F(alpha + beta ln p)] dp (E5)."""
    if cap <= 0:
        raise ValueError("cap must be positive")
    F = _cdf(link)
    p = np.linspace(1e-9, cap, n_grid)
    keep = 1.0 - F(alpha + beta * np.log(p))
    return float(np.trapezoid(keep, p))


def bootstrap_ci(users: pd.DataFrame, cap: float, link: str = "logit", n_boot: int = 500,
                 seed: int = 0, level: float = 0.95) -> dict:
    """Percentile bootstrap for the median and capped mean.

    Resampling is by respondent, so repeated rows from one person stay
    together. With one row per respondent per item this is an ordinary
    respondent bootstrap.
    """
    rng = np.random.default_rng(seed)
    ids = users["respondent_id"].to_numpy()
    uniq = np.unique(ids)
    groups = {u: np.flatnonzero(ids == u) for u in uniq}
    meds, means = [], []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        take = np.concatenate([groups[u] for u in pick])
        try:
            a, b, _ = fit_item(users.iloc[take], link=link)
        except Exception:
            continue
        m = median_wta(a, b)
        if np.isfinite(m):
            meds.append(m)
            means.append(capped_mean_wta(a, b, cap, link=link))
    out = {"requested": n_boot, "successful": len(meds)}
    if len(meds) < max(10, int(0.5 * n_boot)):
        out.update(median_ci=(float("nan"), float("nan")),
                   capped_mean_ci=(float("nan"), float("nan")))
        return out
    q = [(1 - level) / 2 * 100, (1 + level) / 2 * 100]
    lo, hi = np.percentile(meds, q)
    mlo, mhi = np.percentile(means, q)
    out.update(median_ci=(float(lo), float(hi)), capped_mean_ci=(float(mlo), float(mhi)))
    return out


# ------------------------------------------------------------------ nonparametric layer

def acceptance_by_offer(users: pd.DataFrame) -> pd.DataFrame:
    """Weighted acceptance rate and count at each offer actually shown."""
    u = users.assign(accept=(users["response"] == "yes").astype(float))
    w = u["weight"] if "weight" in u.columns else pd.Series(1.0, index=u.index)
    g = u.assign(w=w, aw=u["accept"] * w).groupby("offer").agg(
        n=("accept", "size"), w=("w", "sum"), aw=("aw", "sum")).reset_index()
    g["accept_rate"] = g["aw"] / g["w"]
    return g[["offer", "n", "accept_rate"]].sort_values("offer").reset_index(drop=True)


def npmle_acceptance(users: pd.DataFrame):
    """Monotone (PAVA) acceptance curve: the NPMLE for current-status data.
    Returns (offers, rates, median_crossing_or_nan)."""
    g = acceptance_by_offer(users)
    iso = IsotonicRegression(increasing=True, out_of_bounds="clip")
    rates = iso.fit_transform(np.log(g["offer"]), g["accept_rate"], sample_weight=g["n"])
    median = float("nan")
    if len(rates) and rates.min() <= 0.5 <= rates.max():
        median = float(np.exp(np.interp(0.5, rates, np.log(g["offer"]))))
    return g["offer"].to_numpy(dtype=float), np.asarray(rates, dtype=float), median


def median_location(median: float, grid_min: float, grid_max: float) -> str:
    if not np.isfinite(median):
        return "undefined"
    if median < grid_min:
        return "below_grid"
    if median > grid_max:
        return "above_grid"
    return "within_grid"


# ------------------------------------------------------------------ per-item recipe

def estimate_item(item_df: pd.DataFrame, reporting_cap: float | None = None,
                  link: str = "logit", n_boot: int = 500, seed: int = 0) -> ItemFit:
    """Full per-item recipe on all rows for one item (users and nonusers)."""
    item_id = str(item_df["item_id"].iloc[0])
    users = users_of(item_df)
    n_resp, n_users = int(len(item_df)), int(len(users))
    w_all = item_df["weight"] if "weight" in item_df.columns else pd.Series(1.0, index=item_df.index)
    usage = float((w_all * item_df["is_user"]).sum() / w_all.sum()) if n_resp else float("nan")
    notes: list[str] = []

    if n_users == 0:
        return ItemFit(item_id, link, n_resp, 0, usage, *[float("nan")] * 3, "undefined",
                       float("nan"), *[float("nan")] * 4, float("nan"), float("nan"),
                       float("nan"), float("nan"), n_boot, 0, ["no users: nothing to estimate"])

    grid_min, grid_max = float(users["offer"].min()), float(users["offer"].max())
    cap = float(reporting_cap) if reporting_cap is not None else grid_max
    if cap > grid_max:
        notes.append(f"reporting cap {cap:g} exceeds the largest offer {grid_max:g}: "
                     "the capped mean relies on the model above the observed range")

    acc = acceptance_by_offer(users)
    acc_lo = float(acc.loc[acc["offer"] == grid_min, "accept_rate"].iloc[0])
    acc_hi = float(acc.loc[acc["offer"] == grid_max, "accept_rate"].iloc[0])
    _, _, npmle_med = npmle_acceptance(users)

    if n_users < 20 or users["response"].nunique() < 2 or acc["offer"].nunique() < 3:
        notes.append("too few users, no response variation, or fewer than three offers: "
                     "parametric fit skipped")
        alpha = beta = med = mean_c = float("nan")
        ci = {"median_ci": (np.nan, np.nan), "capped_mean_ci": (np.nan, np.nan),
              "requested": n_boot, "successful": 0}
    else:
        alpha, beta, _ = fit_item(users, link=link)
        med = median_wta(alpha, beta)
        if not np.isfinite(med):
            notes.append("acceptance does not rise with the offer: median undefined")
            mean_c = float("nan")
            ci = {"median_ci": (np.nan, np.nan), "capped_mean_ci": (np.nan, np.nan),
                  "requested": n_boot, "successful": 0}
        else:
            mean_c = capped_mean_wta(alpha, beta, cap, link=link)
            ci = bootstrap_ci(users, cap, link=link, n_boot=n_boot, seed=seed)
            if ci["successful"] < 0.95 * n_boot:
                notes.append(f"only {ci['successful']} of {n_boot} bootstrap fits succeeded: "
                             "inspect identification")

    loc = median_location(med, grid_min, grid_max)
    if loc == "below_grid":
        notes.append("median below the smallest offer: extrapolated estimate")
    if loc == "above_grid":
        notes.append("median above the largest offer: extrapolated estimate")
    if acc_lo > 0.5:
        notes.append(f"acceptance at the smallest offer is already {acc_lo:.0%}")
    if acc_hi < 0.5:
        notes.append(f"acceptance never reaches 50% (largest offer: {acc_hi:.0%})")

    return ItemFit(item_id=item_id, link=link, n_respondents=n_resp, n_users=n_users,
                   sample_usage_rate=usage, alpha=float(alpha), beta=float(beta),
                   median_wta=med, median_lo=float(ci["median_ci"][0]),
                   median_hi=float(ci["median_ci"][1]), median_location=loc,
                   reporting_cap=cap, capped_mean_wta=mean_c,
                   capped_mean_lo=float(ci["capped_mean_ci"][0]),
                   capped_mean_hi=float(ci["capped_mean_ci"][1]),
                   npmle_median=npmle_med, grid_min=grid_min, grid_max=grid_max,
                   accept_at_min_offer=acc_lo, accept_at_max_offer=acc_hi,
                   bootstrap_requested=n_boot, bootstrap_successful=int(ci["successful"]),
                   notes=notes)


def estimate_all_items(clean_df: pd.DataFrame, reporting_cap=None, link: str = "logit",
                       n_boot: int = 500, seed: int = 0):
    """Run estimate_item for every item.

    `reporting_cap` may be None (top of each item's grid), a number applied
    to all items, or a dict item_id -> cap.
    Returns (item_table, fits, acceptance_table).
    """
    fits, acc_rows = [], []
    for item_id, g in clean_df.groupby("item_id", sort=True):
        cap = reporting_cap.get(item_id) if isinstance(reporting_cap, dict) else reporting_cap
        fits.append(estimate_item(g, reporting_cap=cap, link=link, n_boot=n_boot, seed=seed))
        u = users_of(g)
        if len(u):
            acc_rows.append(acceptance_by_offer(u).assign(item_id=str(item_id)))
    table = pd.DataFrame([f.to_row() for f in fits])
    acc = (pd.concat(acc_rows, ignore_index=True)[["item_id", "offer", "n", "accept_rate"]]
           if acc_rows else pd.DataFrame(columns=["item_id", "offer", "n", "accept_rate"]))
    return table.sort_values("median_wta", ascending=False).reset_index(drop=True), fits, acc


def winsorize_column(table: pd.DataFrame, col: str = "capped_mean_wta", q: float = 0.995):
    """Cap a column at its q-quantile. NOT applied automatically anywhere.

    Returns (table, cap, n_affected). If you use it, report the threshold,
    the share affected, and results with and without it (Cookbook 4.6).
    """
    cap = float(table[col].quantile(q))
    affected = int((table[col] > cap).sum())
    out = table.copy()
    out[col] = out[col].clip(upper=cap)
    return out, cap, affected
