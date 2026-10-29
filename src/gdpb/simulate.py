"""Synthetic SBDC survey with a known ground truth.

Used for tests, examples and dry runs of a design before fielding.
Mirrors the fielded protocol: usage screened before any offer, one
randomized offer per user per item, nonusers receive no valuation
question (response = not_asked), log-normal WTA heterogeneity within item,
item-specific adoption, and a small share of inattentive respondents,
speeders and duplicate submissions so the cleaning stage has work to do.
All observations are synthetic.
"""

import numpy as np
import pandas as pd

from .design import log_grid

DEFAULT_ITEMS = {
    # item_id: median monthly WTA (USD), log-sd, adoption share
    "electricity":     {"median_wta": 8000, "sigma": 1.6, "p_use": 0.99},
    "search_engines":  {"median_wta": 1200, "sigma": 1.5, "p_use": 0.97},
    "email":           {"median_wta": 500,  "sigma": 1.4, "p_use": 0.95},
    "maps":            {"median_wta": 150,  "sigma": 1.3, "p_use": 0.90},
    "video_streaming": {"median_wta": 80,   "sigma": 1.3, "p_use": 0.80},
    "social_media":    {"median_wta": 40,   "sigma": 1.5, "p_use": 0.75},
    "music_streaming": {"median_wta": 15,   "sigma": 1.4, "p_use": 0.65},
    "ai_chatbots":     {"median_wta": 12,   "sigma": 1.8, "p_use": 0.55},
    "fitness_apps":    {"median_wta": 8,    "sigma": 1.5, "p_use": 0.30},
    "dating_apps":     {"median_wta": 5,    "sigma": 1.6, "p_use": 0.20},
}


def simulate_survey(items: dict | None = None, n_per_item: int = 2100, seed: int = 20260805,
                    share_inattentive: float = 0.03, share_speeders: float = 0.02,
                    share_duplicates: float = 0.005, grid_span: float = 2.5,
                    grid_n: int = 7, currency: str = "USD"):
    """Return (raw_responses, ground_truth, item_file)."""
    items = items or DEFAULT_ITEMS
    rng = np.random.default_rng(seed)
    ages = ["18-34", "35-54", "55+"]
    incomes = ["under_75k", "over_75k"]

    rows, truth, item_rows = [], {}, []
    rid = 0
    for item_id, t in items.items():
        grid = log_grid(t["median_wta"], n=grid_n, span=grid_span)
        truth[item_id] = {**t, "price_grid": grid}
        item_rows.append({"item_id": item_id, "label": item_id.replace("_", " "),
                          "scope": "category", "currency": currency, "duration_months": 1,
                          "price_grid": "|".join(f"{p:g}" for p in grid)})
        mu = np.log(t["median_wta"])
        for _ in range(n_per_item):
            rid += 1
            income = rng.choice(incomes, p=[0.6, 0.4])
            shift = 0.35 if income == "over_75k" else 0.0
            wta = np.exp(rng.normal(mu + shift, t["sigma"]))
            inattentive = rng.random() < share_inattentive
            speeder = rng.random() < share_speeders
            duration = max(20.0, rng.normal(195, 60)) if not speeder else rng.uniform(5, 25)
            is_user = int(rng.random() < t["p_use"])
            if inattentive:
                is_user = int(rng.random() < 0.8)
                fake = rng.random() < 0.5
            else:
                fake = False
            if is_user:
                offer = float(rng.choice(grid))
                if inattentive:
                    response = rng.choice(["yes", "no"])
                else:
                    response = "yes" if offer >= wta else "no"
            else:
                offer, response = np.nan, "not_asked"
            rows.append({
                "respondent_id": f"R{rid:06d}", "item_id": item_id, "is_user": is_user,
                "offer": offer, "response": response, "weight": 1.0,
                "age_group": rng.choice(ages, p=[.35, .4, .25]), "income_group": income,
                "duration_seconds": round(float(duration), 1),
                "selected_fake_item": bool(fake),
                "attention_check_passed": bool((not inattentive) or rng.random() < 0.3),
            })

    df = pd.DataFrame(rows)
    if share_duplicates > 0:
        dupes = df.sample(frac=share_duplicates, random_state=seed + 1)
        df = pd.concat([df, dupes], ignore_index=True)
    df = df.sample(frac=1, random_state=seed + 2).reset_index(drop=True)
    return df, truth, pd.DataFrame(item_rows)
