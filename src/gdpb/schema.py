"""The two data contracts every stage of the pipeline shares.

Response file (long, one row per respondent x item question)
-------------------------------------------------------------
respondent_id   str     stable id, unique per respondent
item            str     item key, must match the item file
price           float   the single randomized monthly payment shown
response        str     one of {yes, no, dont_use}
                        yes  = would give up the item for the payment (WTA <= price)
                        no   = would not (WTA > price)
                        dont_use = does not use the item

Optional columns used by cleaning when present:
duration_seconds, attention_check_passed, selected_fake_item, weight.
Any further columns (demographics) pass through untouched.

Item file (one row per item)
----------------------------
item        str   key used in the response file
label       str   wording shown to respondents
category    str   free text grouping
scope       str   "brand" or "category" (do not add across the two)
grid        str   pipe-separated prices, e.g. "1|10|20|50|100|200|500"
"""

import pandas as pd

RESPONSE_VALUES = ("yes", "no", "dont_use")
RESPONSE_REQUIRED = ("respondent_id", "item", "price", "response")
ITEM_REQUIRED = ("item", "label", "scope", "grid")


class SchemaError(ValueError):
    pass


def _require(df, cols, what):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise SchemaError(f"{what} is missing required columns: {missing}")


def validate_responses(df: pd.DataFrame, coerce: bool = True) -> pd.DataFrame:
    """Check the response file against the schema. Returns a typed copy.

    With coerce=True, common export codings are mapped onto the schema:
    Yes/No/Don't use strings in any case, and 1/0 integers for yes/no.
    """
    _require(df, RESPONSE_REQUIRED, "response file")
    d = df.copy()
    d["respondent_id"] = d["respondent_id"].astype(str)
    d["item"] = d["item"].astype(str)
    d["price"] = pd.to_numeric(d["price"], errors="coerce")

    if coerce:
        mapping = {
            "yes": "yes", "y": "yes", "1": "yes", "true": "yes", "accept": "yes",
            "no": "no", "n": "no", "0": "no", "false": "no", "reject": "no",
            "dont_use": "dont_use", "don't use": "dont_use", "dont use": "dont_use",
            "do not use": "dont_use", "non-user": "dont_use", "nonuser": "dont_use",
        }
        d["response"] = (d["response"].astype(str).str.strip().str.lower()
                         .map(lambda s: mapping.get(s, s)))

    bad_price = d["price"].isna() | (d["price"] <= 0)
    if bad_price.any():
        raise SchemaError(f"{int(bad_price.sum())} rows have missing or non-positive price")
    bad_resp = ~d["response"].isin(RESPONSE_VALUES)
    if bad_resp.any():
        seen = sorted(d.loc[bad_resp, "response"].unique().tolist())[:10]
        raise SchemaError(f"{int(bad_resp.sum())} rows have responses outside "
                          f"{RESPONSE_VALUES}; examples: {seen}")
    return d


def parse_grid(s) -> list[float]:
    if isinstance(s, (list, tuple)):
        return [float(x) for x in s]
    return [float(x) for x in str(s).split("|") if str(x).strip()]


def validate_items(df: pd.DataFrame) -> pd.DataFrame:
    """Check the item file. Grids must be positive and strictly increasing."""
    _require(df, ITEM_REQUIRED, "item file")
    d = df.copy()
    d["item"] = d["item"].astype(str)
    if d["item"].duplicated().any():
        raise SchemaError("item file has duplicate item keys")
    bad_scope = ~d["scope"].isin(["brand", "category"])
    if bad_scope.any():
        raise SchemaError("scope must be 'brand' or 'category' for every item")
    for _, row in d.iterrows():
        g = parse_grid(row["grid"])
        if len(g) < 3 or any(p <= 0 for p in g) or any(b <= a for a, b in zip(g, g[1:])):
            raise SchemaError(f"item {row['item']}: grid must be >=3 positive increasing prices")
    return d
