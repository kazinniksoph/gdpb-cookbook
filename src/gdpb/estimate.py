"""Per-item WTA estimation from single binary discrete choice responses.

Parametric core
    Pr(accept | p) = F(alpha + beta ln p),  F = logistic or normal CDF
    median WTA = exp(-alpha / beta)
    mean WTA   = integral_0^{p_max} [1 - F(alpha + beta ln p)] dp   (truncated: lower bound)

Nonparametric layer
    isotonic (pooled adjacent violators) acceptance curve and median crossing
    Kaplan-Meier style survival S(p) = 1 - acceptance(p), and its truncated mean

Each response is a censored observation of the respondent's WTA:
    yes  => WTA <= p      no => WTA > p
Rows with response == dont_use are excluded from the WTA fit and used for P(use).
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
    item: str
    link: str
    n_users: int
    n_dont_use: int
    p_use: float
    alpha: float
    beta: float
    median_wta: float
    median_lo: float
    median_hi: float
    mean_wta: float
    median_wta_isotonic: float
    mean_wta_isotonic: float
    grid_min: float
    grid_max: float
    accept_at_min: float
    accept_at_max: float
    left_censored: bool
    right_censored: bool
    notes: list = field(default_factory=list)

    def to_row(self) -> dict:
        d = asdict(self)
        d["notes"] = "; ".join(self.notes)
        return d


def _users(item_df: pd.DataFrame) -> pd.DataFrame:
    return item_df[item_df["response"] != "dont_use"]


def _design(users: pd.DataFrame):
    y = (users["response"] == "yes").astype(int).to_numpy()
    X = sm.add_constant(np.log(users["price"].to_numpy(dtype=float)), has_constant="add")
    w = users["weight"].to_numpy(dtype=float) if "weight" in users.columns else None
    return y, X, w


def fit_item(users: pd.DataFrame, link: str = "logit"):
    """Fit accept ~ ln(price) among users. Returns (alpha, beta, results)."""
    if link not in LINKS:
        raise ValueError(f"link must be one of {LINKS}")
    y, X, w = _design(users)
    fam = sm.families.Binomial(link=sm.families.links.Logit() if link == "logit"
                               else sm.families.links.Probit())
    res = sm.GLM(y, X, family=fam, freq_weights=w).fit()
    alpha, beta = (float(v) for v in res.params)
    return alpha, beta, res


def _cdf(link: str):
    if link == "logit":
        return lambda z: 1.0 / (1.0 + np.exp(-z))
    return norm.cdf


def median_wta(alpha: float, beta: float) -> float:
    """Price at which half of users accept: exp(-alpha/beta). NaN if beta <= 0."""
    if not np.isfinite(beta) or beta <= 0:
        return float("nan")
    return float(np.exp(-alpha / beta))


def mean_wta(alpha: float, beta: float, p_max: float, link: str = "logit",
             n_grid: int = 20000) -> float:
    """Area under the fitted survival curve from 0 to p_max (a lower bound)."""
    F = _cdf(link)
    p = np.linspace(1e-6, p_max, n_grid)
    keep = 1.0 - F(alpha + beta * np.log(p))
    return float(np.trapezoid(keep, p))


def bootstrap_median_ci(users: pd.DataFrame, link: str = "logit", n_boot: int = 500,
                        seed: int = 0, level: float = 0.95) -> tuple[float, float]:
    """Percentile bootstrap CI for the median, resampling respondents."""
    rng = np.random.default_rng(seed)
    idx = np.arange(len(users))
    meds = []
    for _ in range(n_boot):
        take = rng.choice(idx, size=len(idx), replace=True)
        try:
            a, b, _ = fit_item(users.iloc[take], link=link)
        except Exception:
            continue
        m = median_wta(a, b)
        if np.isfinite(m):
            meds.append(m)
    if len(meds) < max(10, n_boot // 10):
        return (float("nan"), float("nan"))
    lo, hi = np.percentile(meds, [(1 - level) / 2 * 100, (1 + level) / 2 * 100])
    return float(lo), float(hi)


def isotonic_acceptance(users: pd.DataFrame):
    """Monotone acceptance rate by price. Returns (prices, rates, median_or_nan)."""
    g = (users.assign(accept=(users["response"] == "yes").astype(int))
              .groupby("price")["accept"].agg(["mean", "size"]).reset_index()
              .sort_values("price"))
    iso = IsotonicRegression(increasing=True, out_of_bounds="clip")
    rates = iso.fit_transform(np.log(g["price"]), g["mean"], sample_weight=g["size"])
    median = float("nan")
    if rates.min() <= 0.5 <= rates.max():
        median = float(np.exp(np.interp(0.5, rates, np.log(g["price"]))))
    return g["price"].to_numpy(dtype=float), np.asarray(rates, dtype=float), median


def km_item_curve(users: pd.DataFrame):
    """Survival S(p) = P(WTA > p). With one price per respondent this is
    1 - isotonic acceptance; the survival framing matches the production
    Kaplan-Meier pipeline and generalizes to multi-price designs."""
    prices, rates, _ = isotonic_acceptance(users)
    return prices, 1.0 - rates


def mean_wta_isotonic(prices: np.ndarray, survival: np.ndarray) -> float:
    """Step-function area under S(p) from 0 to the top of the grid.
    Below the lowest price S is taken as 1 (nobody accepts less than the
    lowest offer was tested); this is a truncated lower bound like mean_wta."""
    p = np.concatenate([[0.0], prices])
    s = np.concatenate([[1.0], survival])
    return float(np.sum(np.diff(p) * s[:-1]))


def estimate_item(item_df: pd.DataFrame, link: str = "logit", n_boot: int = 500,
                  seed: int = 0, grid_flag_low: float = 0.35,
                  grid_flag_high: float = 0.65) -> ItemFit:
    """Full per-item recipe. `item_df` holds all rows for one item."""
    item = str(item_df["item"].iloc[0])
    users = _users(item_df)
    n_dont = int((item_df["response"] == "dont_use").sum())
    p_use = float(len(users) / max(1, len(item_df)))
    grid_min, grid_max = float(item_df["price"].min()), float(item_df["price"].max())
    notes: list[str] = []

    if len(users) < 20 or users["response"].nunique() < 2:
        notes.append("too few user responses or no variation: parametric fit skipped")
        alpha = beta = med = lo = hi = mean_ = float("nan")
    else:
        alpha, beta, _ = fit_item(users, link=link)
        med = median_wta(alpha, beta)
        lo, hi = bootstrap_median_ci(users, link=link, n_boot=n_boot, seed=seed)
        mean_ = mean_wta(alpha, beta, grid_max, link=link)
        if not np.isfinite(med):
            notes.append("acceptance does not rise with price: median undefined")

    prices, rates, med_iso = isotonic_acceptance(users) if len(users) else (
        np.array([]), np.array([]), float("nan"))
    mean_iso = mean_wta_isotonic(prices, 1.0 - rates) if len(prices) else float("nan")

    left_c = bool(np.isfinite(med) and med < grid_min)
    right_c = bool(np.isfinite(med) and med > grid_max)
    if left_c:
        notes.append("median below grid: left-censored, treat as upper bound")
    if right_c:
        notes.append("median above grid: right-censored, treat as lower bound")

    acc_lo = float((users.loc[users["price"] == grid_min, "response"] == "yes").mean()) \
        if len(users) else float("nan")
    acc_hi = float((users.loc[users["price"] == grid_max, "response"] == "yes").mean()) \
        if len(users) else float("nan")
    if np.isfinite(acc_lo) and acc_lo > grid_flag_low:
        notes.append(f"acceptance at lowest price {acc_lo:.0%}: grid may sit too high")
    if np.isfinite(acc_hi) and acc_hi < grid_flag_high:
        notes.append(f"acceptance at highest price {acc_hi:.0%}: grid may sit too low")

    return ItemFit(item=item, link=link, n_users=int(len(users)), n_dont_use=n_dont,
                   p_use=p_use, alpha=alpha, beta=beta, median_wta=med, median_lo=lo,
                   median_hi=hi, mean_wta=mean_, median_wta_isotonic=med_iso,
                   mean_wta_isotonic=mean_iso, grid_min=grid_min, grid_max=grid_max,
                   accept_at_min=acc_lo, accept_at_max=acc_hi,
                   left_censored=left_c, right_censored=right_c, notes=notes)


def estimate_all_items(clean_df: pd.DataFrame, link: str = "logit", n_boot: int = 500,
                       seed: int = 0) -> tuple[pd.DataFrame, list[ItemFit]]:
    """Run estimate_item for every item. Returns (item table, list of fits)."""
    fits = [estimate_item(g, link=link, n_boot=n_boot, seed=seed)
            for _, g in clean_df.groupby("item", sort=True)]
    table = pd.DataFrame([f.to_row() for f in fits])
    return table.sort_values("median_wta", ascending=False).reset_index(drop=True), fits


def winsorize_column(table: pd.DataFrame, col: str = "mean_wta", q: float = 0.995):
    """Cap a column at its q-quantile; returns (table, cap, n_affected).
    Record the cap and the share affected whenever this is used."""
    cap = float(table[col].quantile(q))
    affected = int((table[col] > cap).sum())
    out = table.copy()
    out[col] = out[col].clip(upper=cap)
    return out, cap, affected
