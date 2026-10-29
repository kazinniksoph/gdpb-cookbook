"""One-item SBDC example. All generated observations are synthetic.

This is Appendix B of the GDP-B Cookbook, kept verbatim so that the
cookbook's worked numbers can be reproduced without installing the package.
It depends only on numpy and scipy.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.special import expit


def make_example(folder):
    folder.mkdir(parents=True, exist_ok=True)
    grid = [5, 10, 25, 50, 100, 250, 500]
    rng = np.random.default_rng(20261029)
    rows = []
    # Known user WTA distribution: median 50, log-logistic shape 1.3.
    # One independent offer/response per user; all survey weights equal one.
    for offer in grid:
        for accepted in rng.binomial(1, expit(1.3 * np.log(offer / 50)), 120):
            rows.append([len(rows) + 1, "demo_service", 1, offer,
                         "yes" if accepted else "no", 1])
    # Usage was screened before any offer. Nonusers receive no WTA question.
    for _ in range(1260):
        rows.append([len(rows) + 1, "demo_service", 0, "", "not_asked", 1])
    with (folder / "responses.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["respondent_id", "item_id", "is_user", "offer",
                         "response", "weight"])
        writer.writerows(rows)
    with (folder / "items.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "scope", "currency", "duration_months",
                         "price_grid"])
        writer.writerow(["demo_service", "category", "USD", 1,
                         "|".join(map(str, grid))])
    config = {"item_id": "demo_service", "population": 1000000,
              "adoption_rate": 0.40, "reporting_cap": 500,
              "annualization_factor": 12, "seed": 314159,
              "adoption_source": "hypothetical fixed input"}
    (folder / "config.json").write_text(json.dumps(config, indent=2) + "\n")


def fit_curve(offers, accepted, cap):
    x = np.column_stack([np.ones(len(offers)), np.log(offers)])

    def objective(theta):
        z = x @ theta
        return np.mean(np.logaddexp(0, z) - accepted * z)

    def gradient(theta):
        return x.T @ (expit(x @ theta) - accepted) / len(offers)

    fit = minimize(objective, [0.0, 1.0], jac=gradient, method="BFGS",
                   options={"gtol": 1e-7, "maxiter": 1000})
    alpha, beta = fit.x
    fitted = expit(x @ fit.x)
    hessian = x.T @ (x * (fitted * (1 - fitted))[:, None]) / len(offers)
    if (not fit.success or beta <= 0 or not np.isfinite(fit.x).all()
            or np.linalg.eigvalsh(hessian).min() < 1e-8):
        raise ValueError("Unstable fit, wrong-sign slope, or separation.")
    median = float(np.exp(-alpha / beta))
    capped_mean = quad(
        lambda p: 1.0 if p == 0 else expit(-(alpha + beta * np.log(p))),
        0, cap, epsabs=1e-7)[0]
    return float(alpha), float(beta), median, float(capped_mean)


def run(folder, bootstrap):
    config = json.loads((folder / "config.json").read_text())
    with (folder / "items.csv").open(newline="") as f:
        items = list(csv.DictReader(f))
    with (folder / "responses.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    item_id = config["item_id"]
    if len(items) != 1 or items[0]["item_id"] != item_id:
        raise ValueError("This example supports one item only.")
    if float(items[0]["duration_months"]) != 1:
        raise ValueError("This example requires one-month valuations.")
    if not rows or any(r["item_id"] != item_id for r in rows):
        raise ValueError("Responses must refer to the configured item.")
    if len({r["respondent_id"] for r in rows}) != len(rows):
        raise ValueError("Expected one row per respondent for this item.")
    if any(float(r["weight"]) != 1 for r in rows):
        raise ValueError("This illustration requires equal weights.")
    if any(r["is_user"] not in {"0", "1"} for r in rows):
        raise ValueError("is_user must be 0 or 1.")
    users = [r for r in rows if r["is_user"] == "1"]
    if not users or any(r["response"] not in {"yes", "no"} for r in users):
        raise ValueError("Eligible users need yes/no responses.")
    offers = np.array([float(r["offer"]) for r in users])
    accepted = np.array([r["response"] == "yes" for r in users], dtype=float)
    cap = float(config["reporting_cap"])
    adoption = float(config["adoption_rate"])
    if not np.isfinite(offers).all() or np.any(offers <= 0):
        raise ValueError("Offers must be finite and positive.")
    if not 0 < cap <= offers.max() or not 0 <= adoption <= 1:
        raise ValueError("Check reporting cap and adoption rate.")
    if len(np.unique(offers)) < 3 or len(np.unique(accepted)) < 2:
        raise ValueError("Insufficient variation for the example model.")
    if config["population"] <= 0 or config["annualization_factor"] != 12:
        raise ValueError("Use a positive population and annualization factor 12.")
    alpha, beta, median, mean_c = fit_curve(offers, accepted, cap)
    rng = np.random.default_rng(config["seed"])
    draws = []
    for _ in range(bootstrap):
        selected = rng.integers(0, len(users), size=len(users))
        try:
            draws.append(fit_curve(offers[selected], accepted[selected], cap)[2:])
        except ValueError:
            pass
    if len(draws) < 0.95 * bootstrap:
        raise ValueError("Too many bootstrap fits failed; inspect identification.")
    bounds = np.quantile(np.asarray(draws), [0.025, 0.975], axis=0)
    scale = 12 * config["population"] * adoption
    location = ("below_grid" if median < offers.min() else
                "above_grid" if median > offers.max() else "within_grid")
    result = {
        "data_status": "synthetic illustration; no empirical claim",
        "item_id": item_id, "currency": items[0]["currency"],
        "respondents": len(rows), "users": len(users),
        "sample_usage_rate": len(users) / len(rows),
        "adoption_rate_used": adoption, "population": config["population"],
        "alpha": alpha, "beta": beta, "reporting_cap": cap,
        "median_monthly_wta": median, "median_location": location,
        "capped_mean_monthly_wta": mean_c,
        "median_ci95": bounds[:, 0].tolist(),
        "capped_mean_ci95": bounds[:, 1].tolist(),
        "annualized_capped_value": scale * mean_c,
        "annualized_value_ci95_conditional": (scale * bounds[:, 1]).tolist(),
        "bootstrap_requested": bootstrap, "bootstrap_successful": len(draws),
        "interval_scope": "WTA sampling only; fixed adoption and population"
    }
    (folder / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, default=Path("example"))
    parser.add_argument("--make-example", action="store_true")
    parser.add_argument("--bootstrap", type=int, default=200)
    args = parser.parse_args()
    if args.bootstrap < 20:
        parser.error("Use at least 20 replicates for this illustration.")
    if args.make_example:
        make_example(args.folder)
    run(args.folder, args.bootstrap)
