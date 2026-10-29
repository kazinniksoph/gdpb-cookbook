"""Reproduce the generative-AI survey medians from raw microdata.

Published figures (Brynjolfsson, Collis, Eggers, Kazinnik, Nguyen 2026, Table 2):
    July 2025   median $3.39   mean $98.00    N = 1,491
    March 2026  median $11.48  mean $124.50   N = 1,908 after cleaning
The Stata reference uses `probit accept ln_pp` and `nlcom exp(-_b[_cons]/_b[ln_pp])`.

Usage:
    python scripts/validate_genai.py JULY2025.csv [MARCH2026.xlsx [PROLIFIC_EXPORT.csv]]

The March file is the raw Qualtrics export; the cleaning steps of the Stata
file are applied here (drop never-users, duplicates, failed attention check,
and respondents not APPROVED in the Prolific export). The bot-authenticity
filter lives in a column absent from the Qualtrics export, so the sample here
is slightly larger than the paper's (1,956 vs 1,908 on the 2026-03-05 export)
and the median lands within about 1% of the published figure.

Last run (2026-10-29):
    July 2025    probit  n=1491  median  2.79  mean(trunc @400)  93.1
    March 2026   probit  n=1956  median 11.62  mean(trunc @500) 122.1
The July gap to the published 3.39 is not yet explained; the July CSV is a
different platform export and may have been weighted in the paper.

The microdata are not distributed with this repository.
"""
import sys

import pandas as pd

from gdpb.estimate import fit_item, median_wta, mean_wta


def july_2025(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    return pd.DataFrame({"respondent_id": df["resp_id"].astype(str), "item": "genai",
                         "price": df["91_BCE prices"].astype(float),
                         "response": df["92_BCE "].map({1: "yes", 0: "no"})})


def march_2026(path, prolific=None):
    x = pd.read_excel(path).iloc[1:]                       # first row is question text
    x = x[pd.to_numeric(x["usage-freq"], errors="coerce") != 5]   # never used GenAI
    x = x.drop_duplicates("PROLIFIC_PID")
    x = x[pd.to_numeric(x["attention"], errors="coerce") == 6]
    if prolific:
        dem = pd.read_csv(prolific)
        ok = set(dem.loc[dem["Status"] == "APPROVED", "Participant id"].astype(str))
        x = x[x["PROLIFIC_PID"].astype(str).isin(ok)]
    rows = []
    for p in (1, 10, 20, 50, 100, 200, 500):
        col = pd.to_numeric(x[f"wta-anyllm{p}"], errors="coerce")
        m = col.notna()
        rows.append(pd.DataFrame({"respondent_id": x.loc[m, "ResponseId"].astype(str),
                                  "item": "genai", "price": float(p),
                                  "response": col[m].map({2: "yes", 1: "no"})}))
    return pd.concat(rows, ignore_index=True)


def report(label, d):
    for link in ("probit", "logit"):
        a, b, _ = fit_item(d, link=link)
        print(f"{label:12s} {link:6s} n={len(d):5d}  median={median_wta(a, b):8.2f}  "
              f"mean(trunc @{d['price'].max():.0f})={mean_wta(a, b, d['price'].max(), link):8.2f}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        report("July 2025", july_2025(sys.argv[1]))
    if len(sys.argv) > 2:
        report("March 2026", march_2026(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None))
