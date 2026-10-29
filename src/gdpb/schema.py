"""The data contracts every stage of the pipeline shares.

These follow Section 8.2 of the GDP-B Cookbook.

Response file (long, one row per respondent x item)
----------------------------------------------------
respondent_id   str     stable id, unique per respondent
item_id         str     item key, must match the item file
is_user         0/1     usage measured BEFORE any offer was shown
offer           float   the single randomized compensation offer (users only; blank for nonusers)
response        str     yes  = would give up access for the offer   (WTA <= offer)
                        no   = would not                            (WTA >  offer)
                        not_asked = nonuser, no valuation question shown
weight          float   survey weight (optional; defaults to 1)

Optional columns used by cleaning when present:
duration_seconds, attention_check_passed, selected_fake_item.
Any further columns (demographics) pass through untouched.

Item file (one row per item)
----------------------------
item_id          str   key used in the response file
scope            str   "brand" or "category" (never sum valuations across the two)
currency         str   ISO code, e.g. USD
duration_months  num   length of the access restriction valued (1 = one month)
price_grid       str   pipe-separated offers, e.g. "5|10|25|50|100|250|500"
label            str   optional: wording shown to respondents

Legacy codings are mapped on validation: a `dont_use` response becomes
is_user=0 / response=not_asked; columns `item` and `price` are accepted
as aliases for item_id and offer; Yes/No strings and 1/0 become yes/no.
"""

import numpy as np
import pandas as pd

RESPONSE_VALUES = ("yes", "no", "not_asked")
RESPONSE_REQUIRED = ("respondent_id", "item_id", "is_user", "offer", "response")
ITEM_REQUIRED = ("item_id", "scope", "currency", "duration_months", "price_grid")

_ALIASES = {"item": "item_id", "price": "offer", "grid": "price_grid"}
_RESPONSE_MAP = {
    "yes": "yes", "y": "yes", "1": "yes", "1.0": "yes", "true": "yes", "accept": "yes",
    "no": "no", "n": "no", "0": "no", "0.0": "no", "false": "no", "reject": "no",
    "not_asked": "not_asked", "not asked": "not_asked", "": "not_asked", "nan": "not_asked",
    "dont_use": "dont_use", "don't use": "dont_use", "dont use": "dont_use",
    "do not use": "dont_use", "non-user": "dont_use", "nonuser": "dont_use",
}


class SchemaError(ValueError):
    pass


def _require(df, cols, what):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise SchemaError(f"{what} is missing required columns: {missing}")


def validate_responses(df: pd.DataFrame) -> pd.DataFrame:
    """Check and standardize the response file. Returns a typed copy.

    Rules enforced:
    - users (is_user == 1) have a positive offer and a yes/no response
    - nonusers (is_user == 0) have response not_asked (offer is ignored)
    - weights are positive; a missing weight column is filled with 1
    """
    d = df.rename(columns={k: v for k, v in _ALIASES.items() if k in df.columns and v not in df.columns})
    d = d.copy()

    # Legacy three-way response: derive is_user from dont_use when absent.
    resp = d["response"].astype(str).str.strip().str.lower().map(lambda s: _RESPONSE_MAP.get(s, s)) \
        if "response" in d.columns else None
    if resp is not None and "is_user" not in d.columns:
        d["is_user"] = (resp != "dont_use").astype(int)
    if resp is not None:
        d["response"] = resp.replace({"dont_use": "not_asked"})

    _require(d, RESPONSE_REQUIRED, "response file")
    d["respondent_id"] = d["respondent_id"].astype(str)
    d["item_id"] = d["item_id"].astype(str)
    d["is_user"] = pd.to_numeric(d["is_user"], errors="coerce")
    if not d["is_user"].isin([0, 1]).all():
        raise SchemaError("is_user must be 0 or 1 for every row")
    d["is_user"] = d["is_user"].astype(int)
    d["offer"] = pd.to_numeric(d["offer"], errors="coerce")
    if "weight" not in d.columns:
        d["weight"] = 1.0
    d["weight"] = pd.to_numeric(d["weight"], errors="coerce")
    if (d["weight"].isna() | (d["weight"] <= 0)).any():
        raise SchemaError("weights must be positive numbers")

    users = d["is_user"] == 1
    bad_offer = users & (d["offer"].isna() | (d["offer"] <= 0))
    if bad_offer.any():
        raise SchemaError(f"{int(bad_offer.sum())} user rows have a missing or non-positive offer")
    bad_user_resp = users & ~d["response"].isin(["yes", "no"])
    if bad_user_resp.any():
        seen = sorted(d.loc[bad_user_resp, "response"].unique().tolist())[:10]
        raise SchemaError(f"{int(bad_user_resp.sum())} user rows have responses outside yes/no; "
                          f"examples: {seen}")
    bad_nonuser = ~users & d["response"].isin(["yes", "no"])
    if bad_nonuser.any():
        raise SchemaError(f"{int(bad_nonuser.sum())} nonuser rows carry a yes/no valuation; "
                          "set is_user=1 or response=not_asked")
    d.loc[~users, "response"] = "not_asked"
    d.loc[~users, "offer"] = np.nan
    return d


def parse_grid(s) -> list[float]:
    if isinstance(s, (list, tuple, np.ndarray)):
        return [float(x) for x in s]
    return [float(x) for x in str(s).split("|") if str(x).strip()]


def validate_items(df: pd.DataFrame) -> pd.DataFrame:
    """Check the item file. Grids must be positive and strictly increasing."""
    d = df.rename(columns={k: v for k, v in _ALIASES.items() if k in df.columns and v not in df.columns})
    d = d.copy()
    _require(d, ITEM_REQUIRED, "item file")
    d["item_id"] = d["item_id"].astype(str)
    if d["item_id"].duplicated().any():
        raise SchemaError("item file has duplicate item_id keys")
    if (~d["scope"].isin(["brand", "category"])).any():
        raise SchemaError("scope must be 'brand' or 'category' for every item")
    d["duration_months"] = pd.to_numeric(d["duration_months"], errors="coerce")
    if (d["duration_months"].isna() | (d["duration_months"] <= 0)).any():
        raise SchemaError("duration_months must be a positive number")
    for _, row in d.iterrows():
        g = parse_grid(row["price_grid"])
        if len(g) < 3 or any(p <= 0 for p in g) or any(b <= a for a, b in zip(g, g[1:])):
            raise SchemaError(f"item {row['item_id']}: price_grid must be >=3 positive "
                              "increasing offers")
    return d
