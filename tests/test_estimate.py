import numpy as np
import pytest

from gdpb import clean_responses, estimate_all_items, simulate_survey
from gdpb.estimate import mean_wta, median_wta, fit_item, estimate_item


@pytest.fixture(scope="module")
def sim():
    raw, truth, items = simulate_survey(n_per_item=2100, seed=20260805)
    clean, audit = clean_responses(raw)
    return raw, clean, audit, truth, items


def test_median_formula():
    assert median_wta(alpha=-np.log(50.0) * 2.0, beta=2.0) == pytest.approx(50.0)
    assert np.isnan(median_wta(0.0, -1.0))


def test_mean_is_truncated_lower_bound():
    a, b = -np.log(50.0) * 1.0, 1.0
    assert mean_wta(a, b, p_max=100) < mean_wta(a, b, p_max=1000)


def test_recovers_ground_truth_medians(sim):
    _, clean, _, truth, _ = sim
    table, _ = estimate_all_items(clean, n_boot=50)
    t = table.set_index("item")
    for item, tr in truth.items():
        est = t.loc[item, "median_wta"]
        # the income shifter raises the population median above the item's base
        # median by about exp(0.4*0.35); allow 35% relative error
        assert abs(est / tr["median_wta"] - 1) < 0.35, (item, est, tr["median_wta"])
        assert abs(t.loc[item, "p_use"] - tr["p_use"]) < 0.05, item


def test_probit_and_logit_agree_on_median(sim):
    _, clean, _, _, _ = sim
    g = clean[clean["item"] == "email"]
    users = g[g["response"] != "dont_use"]
    a1, b1, _ = fit_item(users, link="logit")
    a2, b2, _ = fit_item(users, link="probit")
    assert abs(median_wta(a1, b1) / median_wta(a2, b2) - 1) < 0.05


def test_ci_brackets_point_estimate(sim):
    _, clean, _, _, _ = sim
    f = estimate_item(clean[clean["item"] == "maps"], n_boot=100)
    assert f.median_lo <= f.median_wta <= f.median_hi
    assert not f.left_censored and not f.right_censored


def test_censoring_flags_when_grid_misses():
    # grid tops out at 50 while the true median is 500: the median must be
    # flagged as right-censored and the grid as sitting too low
    import pandas as pd
    rng = np.random.default_rng(3)
    grid = np.array([1, 2, 5, 10, 20, 50], dtype=float)
    price = rng.choice(grid, size=3000)
    wta = np.exp(rng.normal(np.log(500), 1.5, size=3000))
    raw = pd.DataFrame({"respondent_id": [f"R{i}" for i in range(3000)], "item": "x",
                        "price": price, "response": np.where(price >= wta, "yes", "no")})
    f = estimate_item(raw, n_boot=20)
    assert f.right_censored
    assert any("too low" in n for n in f.notes)


def test_too_few_responses_does_not_crash(sim):
    _, clean, _, _, _ = sim
    small = clean[clean["item"] == "email"].head(10)
    f = estimate_item(small, n_boot=5)
    assert np.isnan(f.median_wta)
    assert f.notes
