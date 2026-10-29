"""Protocol cleaning rules, applied in a fixed order, with an audit trail.

Follows Cookbook 3.3: decide exclusion rules before looking at valuations,
report how many observations each rule removes and at which offers, and
never drop respondents merely for rejecting a high offer.

Rules are skipped, and recorded as skipped, when the column they need is
absent. Order matters for the counts: a row dropped as a duplicate is not
counted again as a speeder.
"""

import pandas as pd


def clean_responses(df: pd.DataFrame, min_duration_seconds: float = 45,
                    require_attention: bool = True,
                    drop_fake_item: bool = True) -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, audit). The audit counts rows removed by each rule
    and, for user rows, the offers assigned to the removed rows."""
    audit: dict = {"rows_in": int(len(df)), "rules": {}}
    d = df

    def record(name, mask):
        removed = d[mask]
        users = removed[removed["is_user"] == 1] if "is_user" in removed else removed
        audit["rules"][name] = {
            "removed": int(mask.sum()),
            "offers_of_removed_users": {str(k): int(v) for k, v in
                                        users["offer"].value_counts().sort_index().items()}
            if "offer" in users else {},
        }

    dup = d.duplicated(subset=["respondent_id", "item_id"], keep="first")
    record("duplicates", dup)
    d = d[~dup]

    if drop_fake_item and "selected_fake_item" in d.columns:
        m = d["selected_fake_item"].astype(bool)
        record("fake_item_check", m)
        d = d[~m]
    else:
        audit["rules"]["fake_item_check"] = "skipped"

    if require_attention and "attention_check_passed" in d.columns:
        m = ~d["attention_check_passed"].astype(bool)
        record("attention_check", m)
        d = d[~m]
    else:
        audit["rules"]["attention_check"] = "skipped"

    if "duration_seconds" in d.columns:
        dur = pd.to_numeric(d["duration_seconds"], errors="coerce")
        m = dur < min_duration_seconds
        record("speeders", m)
        d = d[~m]
    else:
        audit["rules"]["speeders"] = "skipped"

    m = (d["is_user"] == 1) & ~d["response"].isin(["yes", "no"])
    record("users_without_valid_response", m)
    d = d[~m]

    audit["rows_out"] = int(len(d))
    audit["share_kept"] = round(len(d) / max(1, audit["rows_in"]), 4)
    audit["note"] = ("No rule removes respondents for rejecting high offers; "
                     "such responses may reflect genuinely high valuations.")
    return d.reset_index(drop=True), audit
