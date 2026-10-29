import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from gdpb import clean_responses, estimate_all_items, simulate_survey, validate_responses
from gdpb.estimate import (capped_mean_wta, median_wta, fit_item, estimate_item,
                           npmle_acceptance, median_location)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def sim():
    raw, truth, items = simulate_survey(n_per_item=2100, seed=20260805)
    clean, audit = clean_responses(validate_responses(raw))
    return raw, clean, audit, truth, items


def test_median_formula():
    assert median_wta(alpha=-np.log(50.0) * 2.0, beta=2.0) == pytest.approx(50.0)
    assert np.isnan(median_wta(0.0, -1.0))


def test_capped_mean_rises_with_cap():
    a, b = -np.log(50.0) * 1.0, 1.0
    assert capped_mean_wta(a, b, cap=100) < capped_mean_wta(a, b, cap=1000)


def test_recovers_ground_truth_medians(sim):
    _, clean, _, truth, _ = sim
    table, _, acc = estimate_all_items(clean, n_boot=50)
    t = table.set_index("item_id")
    for item, tr in truth.items():
        est = t.loc[item, "median_wta"]
        # the income shifter raises the population median above the item's base
        # median by about exp(0.4*0.35); allow 35% relative error
        assert abs(est / tr["median_wta"] - 1) < 0.35, (item, est, tr["median_wta"])
        assert abs(t.loc[item, "sample_usage_rate"] - tr["p_use"]) < 0.05, item
        assert t.loc[item, "median_location"] == "within_grid"
    assert set(acc["item_id"]) == set(truth)


def test_npmle_median_close_to_parametric(sim):
    _, clean, _, _, _ = sim
    g = clean[clean["item_id"] == "email"]
    users = g[g["is_user"] == 1]
    a, b, _ = fit_item(users)
    _, _, m_np = npmle_acceptance(users)
    assert abs(m_np / median_wta(a, b) - 1) < 0.4


def test_probit_and_logit_agree_on_median(sim):
    _, clean, _, _, _ = sim
    users = clean[(clean["item_id"] == "email") & (clean["is_user"] == 1)]
    a1, b1, _ = fit_item(users, link="logit")
    a2, b2, _ = fit_item(users, link="probit")
    assert abs(median_wta(a1, b1) / median_wta(a2, b2) - 1) < 0.05


def test_ci_brackets_point_estimates(sim):
    _, clean, _, _, _ = sim
    f = estimate_item(clean[clean["item_id"] == "maps"], n_boot=100)
    assert f.median_lo <= f.median_wta <= f.median_hi
    assert f.capped_mean_lo <= f.capped_mean_wta <= f.capped_mean_hi
    assert f.reporting_cap == f.grid_max
    assert f.bootstrap_successful >= 95


def test_explicit_cap_is_recorded_and_flagged_above_grid(sim):
    _, clean, _, _, _ = sim
    g = clean[clean["item_id"] == "maps"]
    f_in = estimate_item(g, reporting_cap=100, n_boot=20)
    f_out = estimate_item(g, reporting_cap=10 * f_in.grid_max, n_boot=20)
    assert f_in.reporting_cap == 100 and f_in.capped_mean_wta < f_out.capped_mean_wta
    assert any("exceeds the largest offer" in n for n in f_out.notes)


def test_median_location_when_grid_misses():
    # grid tops out at 50 while the true median is 500
    rng = np.random.default_rng(3)
    grid = np.array([1, 2, 5, 10, 20, 50], dtype=float)
    offer = rng.choice(grid, size=3000)
    wta = np.exp(rng.normal(np.log(500), 1.5, size=3000))
    raw = pd.DataFrame({"respondent_id": [f"R{i}" for i in range(3000)], "item_id": "x",
                        "is_user": 1, "offer": offer,
                        "response": np.where(offer >= wta, "yes", "no"), "weight": 1.0})
    f = estimate_item(raw, n_boot=20)
    assert f.median_location == "above_grid"
    assert any("never reaches 50%" in n for n in f.notes)
    assert median_location(0.5, 1, 50) == "below_grid"
    assert median_location(np.nan, 1, 50) == "undefined"


def test_too_few_users_does_not_crash(sim):
    _, clean, _, _, _ = sim
    small = clean[clean["item_id"] == "email"].head(10)
    f = estimate_item(small, n_boot=5)
    assert np.isnan(f.median_wta) and f.notes


def test_matches_cookbook_appendix_b(tmp_path):
    """The package must reproduce the standalone Appendix B script on its own files."""
    script = ROOT / "examples" / "gdpb_example.py"
    subprocess.run([sys.executable, str(script), "--make-example", "--folder", str(tmp_path),
                    "--bootstrap", "20"], check=True, capture_output=True)
    resp = validate_responses(pd.read_csv(tmp_path / "responses.csv"))
    f = estimate_item(resp, reporting_cap=500, n_boot=20)
    assert f.n_respondents == 2100 and f.n_users == 840
    assert f.median_wta == pytest.approx(50.34, abs=0.02)
    assert f.capped_mean_wta == pytest.approx(100.41, abs=0.05)
    assert f.median_location == "within_grid"
