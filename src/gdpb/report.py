"""Deposit files: what a study hands over so others can compare and reuse it.

    items.csv         one row per item: n, P(use), median (CI), mean, censoring flags, notes
    aggregate.csv     one row per item: adoption used, users, annual surplus
    metadata.json     protocol version, wording, grids, link, cleaning thresholds, dates
    audit.json        cleaning counts by rule
    summary.md        human-readable summary
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

from . import __version__ as _pkg_version


def write_deposit(outdir, item_table: pd.DataFrame, audit: dict, config: dict,
                  agg_table: pd.DataFrame | None = None, totals: dict | None = None) -> Path:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    item_table.to_csv(out / "items.csv", index=False)
    if agg_table is not None:
        agg_table.to_csv(out / "aggregate.csv", index=False)
    meta = {
        "gdpb_version": _pkg_version,
        "generated": date.today().isoformat(),
        "config": config,
        "n_items": int(len(item_table)),
        "n_items_left_censored": int(item_table["left_censored"].sum()),
        "n_items_right_censored": int(item_table["right_censored"].sum()),
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2, default=str))
    (out / "audit.json").write_text(json.dumps(audit, indent=2))
    (out / "summary.md").write_text(summary_markdown(item_table, audit, agg_table, totals))
    return out


def summary_markdown(item_table: pd.DataFrame, audit: dict,
                     agg_table: pd.DataFrame | None = None, totals: dict | None = None) -> str:
    lines = ["# GDP-B survey summary", ""]
    lines += ["## Cleaning", "", "| rule | rows removed |", "|---|---:|"]
    for k, v in audit.items():
        if k in ("rows_in", "rows_out", "share_kept"):
            continue
        lines.append(f"| {k} | {'skipped' if v is None else v} |")
    lines += ["", f"Rows in: {audit.get('rows_in')}. Rows out: {audit.get('rows_out')}.", ""]
    cols = ["item", "n_users", "p_use", "median_wta", "median_lo", "median_hi", "mean_wta"]
    lines += ["## Per-item WTA (monthly)", "",
              "| item | n users | P(use) | median | 95% CI | mean (truncated) | flags |",
              "|---|---:|---:|---:|---|---:|---|"]
    for _, r in item_table[cols + ["left_censored", "right_censored", "notes"]].iterrows():
        flags = []
        if r["left_censored"]:
            flags.append("L")
        if r["right_censored"]:
            flags.append("R")
        lines.append(f"| {r['item']} | {r['n_users']} | {r['p_use']:.2f} | "
                     f"{r['median_wta']:,.2f} | {r['median_lo']:,.2f}–{r['median_hi']:,.2f} | "
                     f"{r['mean_wta']:,.2f} | {''.join(flags)} |")
    if agg_table is not None:
        lines += ["", "## Aggregate annual consumer surplus", "",
                  "| item | P(use) used | source | users | annual surplus |",
                  "|---|---:|---|---:|---:|"]
        for _, r in agg_table.iterrows():
            lines.append(f"| {r['item']} | {r['p_use_used']:.3f} | {r['p_use_source']} | "
                         f"{r['users']:,.0f} | {r['aggregate_annual_surplus']:,.0f} |")
        if totals:
            lines += ["", f"Total: {totals['total_aggregate_annual_surplus']:,.0f} "
                          f"across {totals['n_items']} items."]
            for n in totals.get("notes", []):
                lines.append(f"- {n}")
    lines += ["", "Medians are the headline per-user figures. Means are truncated at the top of "
                  "the price grid and are lower bounds. L/R mark medians outside the grid."]
    return "\n".join(lines) + "\n"
