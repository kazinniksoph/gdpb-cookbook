"""Protocol cleaning rules, applied in a fixed order, with an audit trail.

Rules are skipped, and recorded as skipped, when the column they need
is absent. The order matters for the audit counts: a row dropped as a
duplicate is not counted again as a speeder.
"""

import pandas as pd

from .schema import RESPONSE_VALUES


def clean_responses(df: pd.DataFrame, min_duration_seconds: float = 45,
                    require_attention: bool = True,
                    drop_fake_item: bool = True) -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, audit). `audit` counts rows removed at each step."""
    audit: dict = {"rows_in": int(len(df))}
    d = df

    n = len(d)
    d = d.drop_duplicates(subset=["respondent_id", "item"], keep="first")
    audit["duplicates"] = n - len(d)

    if drop_fake_item and "selected_fake_item" in d.columns:
        m = d["selected_fake_item"].astype(bool)
        audit["fake_item_check"] = int(m.sum())
        d = d[~m]
    else:
        audit["fake_item_check"] = None

    if require_attention and "attention_check_passed" in d.columns:
        m = ~d["attention_check_passed"].astype(bool)
        audit["attention_check"] = int(m.sum())
        d = d[~m]
    else:
        audit["attention_check"] = None

    if "duration_seconds" in d.columns:
        dur = pd.to_numeric(d["duration_seconds"], errors="coerce")
        m = dur < min_duration_seconds
        audit["speeders"] = int(m.sum())
        d = d[~m]
    else:
        audit["speeders"] = None

    m = ~d["response"].isin(RESPONSE_VALUES)
    audit["invalid_response"] = int(m.sum())
    d = d[~m]

    audit["rows_out"] = int(len(d))
    audit["share_kept"] = round(len(d) / max(1, audit["rows_in"]), 4)
    return d.reset_index(drop=True), audit
