import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from gdpb import clean_responses, simulate_survey, validate_responses, validate_items, SchemaError
from gdpb.aggregate import aggregate_surplus, total_income_growth, aggregate_table, sum_surplus
from gdpb.design import log_grid, recenter_grid, required_sample, allocate


# ------------------------------------------------------------------ schema

def test_schema_coerces_common_codings():
    df = pd.DataFrame({"respondent_id": [1, 2, 3], "item": ["a"] * 3,
                       "price": [1, 10, 100], "response": ["Yes", 0, "Don't use"]})
    out = validate_responses(df)
    assert out["response"].tolist() == ["yes", "no", "dont_use"]


def test_schema_rejects_bad_price_and_response():
    base = {"respondent_id": ["1"], "item": ["a"], "price": [0], "response": ["yes"]}
    with pytest.raises(SchemaError):
        validate_responses(pd.DataFrame(base))
    base["price"] = [5]
    base["response"] = ["maybe"]
    with pytest.raises(SchemaError):
        validate_responses(pd.DataFrame(base))


def test_item_file_grid_validation():
    ok = pd.DataFrame({"item": ["a"], "label": ["A"], "scope": ["brand"], "grid": ["1|10|100"]})
    validate_items(ok)
    bad = ok.assign(grid=["10|1|100"])
    with pytest.raises(SchemaError):
        validate_items(bad)


# ------------------------------------------------------------------ cleaning

def test_cleaning_removes_duplicates_and_bad_rows():
    raw, _, _ = simulate_survey(n_per_item=500, seed=1)
    clean, audit = clean_responses(raw)
    assert audit["duplicates"] > 0
    assert audit["fake_item_check"] > 0
    assert audit["speeders"] > 0
    assert not clean.duplicated(["respondent_id", "item"]).any()
    assert audit["rows_out"] == len(clean)


def test_cleaning_skips_rules_without_columns():
    df = pd.DataFrame({"respondent_id": ["1", "2"], "item": ["a", "a"],
                       "price": [1.0, 2.0], "response": ["yes", "no"]})
    clean, audit = clean_responses(df)
    assert audit["speeders"] is None and audit["attention_check"] is None
    assert len(clean) == 2


# ------------------------------------------------------------------ design

def test_log_grid_shape():
    g = log_grid(100, n=7, span=2.5)
    assert len(g) == 7 and g == sorted(g) and g[3] == pytest.approx(100, rel=0.01)


def test_recenter_rules():
    row = {"median_wta": 50.0, "grid_min": 1.0, "grid_max": 500.0,
           "left_censored": False, "right_censored": False}
    g = recenter_grid(row)
    assert g[len(g) // 2] == pytest.approx(50, rel=0.02)
    row_rc = {**row, "median_wta": np.nan, "right_censored": True}
    assert recenter_grid(row_rc)[len(g) // 2] == pytest.approx(1500, rel=0.02)


def test_required_sample():
    assert required_sample(7, per_price=200, p_use=1.0, attrition=0.0) == 1400
    assert required_sample(7, per_price=200, p_use=0.5, attrition=0.1) > 2800


def test_allocation_balances_cells():
    items = pd.DataFrame({"item": ["a", "b"], "label": ["A", "B"], "scope": ["brand"] * 2,
                          "grid": ["1|10|100|1000", "2|20|200|2000"]})
    alloc = allocate(items, n_respondents=800, items_per_respondent=2, seed=0)
    cells = alloc.groupby(["item", "price"]).size()
    assert cells.min() == cells.max() == 200
    assert not alloc.duplicated(["respondent_id", "item"]).any()


# ------------------------------------------------------------------ aggregation

def test_surplus_identity():
    out = aggregate_surplus(mean_wta_monthly=10, p_use=0.5, population=1000)
    assert out["aggregate_annual_surplus"] == pytest.approx(10 * 12 * 500)


def test_total_income_growth_lower_than_naive_sum():
    r = total_income_growth(gdp0=100, gdp1=110, cs0=0, cs1=5, deflator_ratio=1.02)
    assert r["gdpb_total_income_growth"] > r["conventional_real_growth"]
    assert r["adjustment_pp"] > 0


def test_aggregate_table_uses_external_adoption():
    t = pd.DataFrame({"item": ["a", "b"], "mean_wta": [10.0, 20.0], "p_use": [0.5, 0.5],
                      "right_censored": [False, True]})
    agg = aggregate_table(t, population=100, p_use_external={"a": 0.9})
    assert agg.set_index("item").loc["a", "p_use_source"] == "external"
    assert agg.set_index("item").loc["b", "p_use_source"] == "survey"
    tot = sum_surplus(agg)
    assert any("lower bound" in n for n in tot["notes"])


# ------------------------------------------------------------------ CLI end to end

def test_cli_run(tmp_path):
    py = [sys.executable, "-m", "gdpb.cli"]
    subprocess.run(py + ["simulate", str(tmp_path), "--n-per-item", "600"], check=True)
    cfg = {"responses": "raw_responses.csv", "items": "items.csv",
           "cleaning": {"min_duration_seconds": 45},
           "estimation": {"link": "logit", "n_boot": 20},
           "aggregation": {"population": 1_000_000},
           "output": "deposit"}
    import yaml
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg))
    r = subprocess.run(py + ["run", str(tmp_path / "config.yaml")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    dep = tmp_path / "deposit"
    for f in ("items.csv", "aggregate.csv", "metadata.json", "audit.json", "summary.md"):
        assert (dep / f).exists()
    meta = json.loads((dep / "metadata.json").read_text())
    assert meta["n_items"] == 10
