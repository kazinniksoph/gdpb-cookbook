import json
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

from gdpb import (clean_responses, simulate_survey, validate_responses, validate_items,
                  SchemaError)
from gdpb.aggregate import (aggregate_value, total_income_growth, compound_annual_rate,
                            productivity_b, aggregate_table, sum_values)
from gdpb.design import log_grid, recenter_grid, required_sample, allocate


# ------------------------------------------------------------------ schema

def test_schema_accepts_cookbook_format():
    df = pd.DataFrame({"respondent_id": [1, 2, 3], "item_id": ["a"] * 3, "is_user": [1, 1, 0],
                       "offer": [5, 50, ""], "response": ["no", "yes", "not_asked"],
                       "weight": [1, 1, 1]})
    out = validate_responses(df)
    assert out["response"].tolist() == ["no", "yes", "not_asked"]
    assert np.isnan(out.loc[2, "offer"])


def test_schema_maps_legacy_dont_use_and_aliases():
    df = pd.DataFrame({"respondent_id": [1, 2, 3], "item": ["a"] * 3,
                       "price": [1, 10, 100], "response": ["Yes", 0, "Don't use"]})
    out = validate_responses(df)
    assert list(out["item_id"]) == ["a"] * 3
    assert out["is_user"].tolist() == [1, 1, 0]
    assert out["response"].tolist() == ["yes", "no", "not_asked"]
    assert out["weight"].tolist() == [1.0, 1.0, 1.0]


def test_schema_rejects_bad_rows():
    base = {"respondent_id": ["1"], "item_id": ["a"], "is_user": [1], "offer": [0],
            "response": ["yes"]}
    with pytest.raises(SchemaError):
        validate_responses(pd.DataFrame(base))
    base.update(offer=[5], response=["maybe"])
    with pytest.raises(SchemaError):
        validate_responses(pd.DataFrame(base))
    base.update(is_user=[0], response=["yes"])
    with pytest.raises(SchemaError):          # nonuser carrying a valuation
        validate_responses(pd.DataFrame(base))


def test_item_file_validation():
    ok = pd.DataFrame({"item_id": ["a"], "scope": ["brand"], "currency": ["USD"],
                       "duration_months": [1], "price_grid": ["1|10|100"]})
    validate_items(ok)
    with pytest.raises(SchemaError):
        validate_items(ok.assign(price_grid=["10|1|100"]))
    with pytest.raises(SchemaError):
        validate_items(ok.assign(scope=["bundle"]))


# ------------------------------------------------------------------ cleaning

def test_cleaning_removes_bad_rows_and_records_offers():
    raw, _, _ = simulate_survey(n_per_item=500, seed=1)
    clean, audit = clean_responses(validate_responses(raw))
    r = audit["rules"]
    assert r["duplicates"]["removed"] > 0
    assert r["fake_item_check"]["removed"] > 0
    assert r["speeders"]["removed"] > 0
    assert isinstance(r["speeders"]["offers_of_removed_users"], dict)
    assert not clean.duplicated(["respondent_id", "item_id"]).any()
    assert audit["rows_out"] == len(clean)


def test_cleaning_skips_rules_without_columns():
    df = validate_responses(pd.DataFrame({"respondent_id": ["1", "2"], "item_id": ["a", "a"],
                                          "is_user": [1, 1], "offer": [1.0, 2.0],
                                          "response": ["yes", "no"]}))
    clean, audit = clean_responses(df)
    assert audit["rules"]["speeders"] == "skipped"
    assert len(clean) == 2


# ------------------------------------------------------------------ design

def test_log_grid_shape():
    g = log_grid(100, n=7, span=2.5)
    assert len(g) == 7 and g == sorted(g) and g[3] == pytest.approx(100, rel=0.01)


def test_recenter_rules_and_keep():
    row = {"median_wta": 50.0, "grid_min": 1.0, "grid_max": 500.0, "median_location": "within_grid"}
    g = recenter_grid(row)
    assert g[len(g) // 2] == pytest.approx(50, rel=0.02)
    g2 = recenter_grid({**row, "median_wta": np.nan, "median_location": "above_grid"})
    assert g2[len(g2) // 2] == pytest.approx(1500, rel=0.02)
    assert 500.0 in recenter_grid(row, keep=[500])


def test_required_sample():
    assert required_sample(7, per_offer=200, p_use=1.0, attrition=0.0) == 1400
    assert required_sample(7, per_offer=200, p_use=0.5, attrition=0.1) > 2800


def test_allocation_balances_cells():
    items = pd.DataFrame({"item_id": ["a", "b"], "scope": ["brand"] * 2, "currency": ["USD"] * 2,
                          "duration_months": [1, 1],
                          "price_grid": ["1|10|100|1000", "2|20|200|2000"]})
    alloc = allocate(items, n_respondents=800, items_per_respondent=2, seed=0)
    cells = alloc.groupby(["item_id", "offer"]).size()
    assert cells.min() == cells.max() == 200
    assert not alloc.duplicated(["respondent_id", "item_id"]).any()


# ------------------------------------------------------------------ aggregation

def test_aggregate_value_identity():
    out = aggregate_value(capped_mean_monthly=25, adoption_rate=0.40, population=10_000_000)
    assert out["annualized_capped_value"] == pytest.approx(1.2e9)


def test_cookbook_section_5_4_example():
    # GDP 100 -> 110 (billions), valuation 0.9 -> 1.2, deflator +5%
    r = total_income_growth(gdp0=100, gdp1=110, m0=0.9, m1=1.2, deflator_ratio=1.05)
    assert r["gdpb_total_income_index"] == pytest.approx(1.04960, abs=1e-5)
    assert r["conventional_growth"] == pytest.approx(0.0476, abs=1e-4)
    assert r["adjustment_pp"] == pytest.approx(0.20, abs=0.01)
    assert compound_annual_rate(1.04960 ** 5, 5) == pytest.approx(0.0496, abs=1e-4)
    assert productivity_b(1.05, 1.01) == pytest.approx(1.05 / 1.01)
    with pytest.raises(ValueError):          # index level passed instead of ratio
        total_income_growth(100, 110, 0, 1, deflator_ratio=130)


def test_aggregate_table_sources_and_caveats():
    t = pd.DataFrame({"item_id": ["a", "b"], "capped_mean_wta": [10.0, 20.0],
                      "sample_usage_rate": [0.5, 0.5], "reporting_cap": [500.0, 500.0],
                      "median_location": ["within_grid", "above_grid"]})
    agg = aggregate_table(t, population=100, adoption={"a": 0.9}, adoption_source="census")
    a = agg.set_index("item_id")
    assert a.loc["a", "adoption_source"] == "census" and a.loc["a", "adoption_rate_used"] == 0.9
    assert a.loc["b", "adoption_source"] == "survey usage question"
    tot = sum_values(agg)
    assert any("extrapolated" in n for n in tot["notes"])
    assert any("substitution" in n for n in tot["notes"])


# ------------------------------------------------------------------ CLI end to end

def test_cli_run_yaml(tmp_path):
    py = [sys.executable, "-m", "gdpb.cli"]
    subprocess.run(py + ["simulate", str(tmp_path), "--n-per-item", "600"], check=True)
    cfg = {"responses": "raw_responses.csv", "items": "items.csv",
           "cleaning": {"min_duration_seconds": 45},
           "estimation": {"link": "logit", "n_boot": 20},
           "population": 1_000_000, "reporting_cap": 500, "annualization_factor": 12,
           "adoption_source": "survey usage question", "output": "deposit"}
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(cfg))
    r = subprocess.run(py + ["run", str(tmp_path / "config.yaml")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    dep = tmp_path / "deposit"
    for f in ("items.csv", "acceptance_by_offer.csv", "aggregate.csv", "metadata.json",
              "audit.json", "summary.md"):
        assert (dep / f).exists()
    meta = json.loads((dep / "metadata.json").read_text())
    assert meta["n_items"] == 10 and meta["reporting_caps"] == [500.0]
    assert "software" in meta


def test_cli_run_cookbook_config_json(tmp_path):
    """The Cookbook's config.json keys drive the package directly."""
    import shutil
    from pathlib import Path
    script = Path(__file__).resolve().parents[1] / "examples" / "gdpb_example.py"
    subprocess.run([sys.executable, str(script), "--make-example", "--folder", str(tmp_path),
                    "--bootstrap", "20"], check=True, capture_output=True)
    cfg = json.loads((tmp_path / "config.json").read_text())
    cfg.update(responses="responses.csv", items="items.csv", output="deposit",
               estimation={"n_boot": 20})
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    r = subprocess.run([sys.executable, "-m", "gdpb.cli", "run", str(tmp_path / "config.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    items = pd.read_csv(tmp_path / "deposit" / "items.csv")
    agg = pd.read_csv(tmp_path / "deposit" / "aggregate.csv")
    assert items.loc[0, "median_wta"] == pytest.approx(50.34, abs=0.02)
    assert agg.loc[0, "adoption_rate_used"] == 0.40
    assert agg.loc[0, "annualized_capped_value"] == pytest.approx(481.97e6, rel=1e-3)
    shutil.rmtree(tmp_path / "deposit")
