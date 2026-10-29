"""Command line entry point.

    gdpb simulate  OUTDIR [--n-per-item N] [--seed S]
    gdpb validate  RESPONSES.csv [--items ITEMS.csv]
    gdpb design    ITEMS.csv --n-respondents N [--items-per-respondent K] -o allocation.csv
    gdpb clean     RESPONSES.csv -o clean.csv [--min-duration 45] [--no-attention]
    gdpb estimate  CLEAN.csv -o items.csv [--link logit|probit] [--n-boot 500] [--cap 500]
    gdpb aggregate ITEMS.csv --population N [--adoption-rate R | --adoption adoption.csv]
    gdpb run       config.yaml|config.json     # clean -> estimate -> aggregate -> deposit

The config for `run` accepts the Cookbook's flat keys (Section 8.2):
    responses, items, item_id (optional filter), population, adoption_rate,
    adoption_source, reporting_cap, annualization_factor, seed, output
plus optional nested blocks `cleaning: {...}` and `estimation: {link, n_boot}`.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from . import __version__
from .aggregate import aggregate_table, sum_values
from .clean import clean_responses
from .design import allocate
from .estimate import estimate_all_items
from .report import write_deposit
from .schema import validate_items, validate_responses
from .simulate import simulate_survey


def _read(path):
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p)
    return pd.read_csv(p)


def _read_config(path):
    p = Path(path)
    text = p.read_text()
    return json.loads(text) if p.suffix.lower() == ".json" else yaml.safe_load(text)


def _adoption_arg(value, base=Path(".")):
    """A number, or a path to a CSV with item_id and adoption_rate."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        ad = _read(base / str(value))
        col = "adoption_rate" if "adoption_rate" in ad.columns else "p_use"
        return dict(zip(ad["item_id"].astype(str), ad[col].astype(float)))


def cmd_simulate(a):
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    df, truth, items = simulate_survey(n_per_item=a.n_per_item, seed=a.seed)
    df.to_csv(out / "raw_responses.csv", index=False)
    items.to_csv(out / "items.csv", index=False)
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    print(f"wrote {len(df):,} rows, {len(items)} items -> {out} (synthetic)")


def cmd_validate(a):
    d = validate_responses(_read(a.responses))
    msg = (f"responses ok: {len(d):,} rows, {d['item_id'].nunique()} items, "
           f"{d['respondent_id'].nunique():,} respondents, "
           f"{int(d['is_user'].sum()):,} user rows")
    if a.items:
        items = validate_items(_read(a.items))
        unknown = sorted(set(d["item_id"]) - set(items["item_id"]))
        if unknown:
            print(f"WARNING: {len(unknown)} items in responses not in item file: {unknown[:10]}")
        msg += f"; item file ok: {len(items)} items"
    print(msg)


def cmd_design(a):
    items = validate_items(_read(a.items))
    alloc = allocate(items, a.n_respondents, a.items_per_respondent, seed=a.seed)
    alloc.to_csv(a.output, index=False)
    cells = alloc.groupby(["item_id", "offer"]).size()
    print(f"wrote {len(alloc):,} assignments -> {a.output}; "
          f"cell sizes min {cells.min()} / max {cells.max()}")


def cmd_clean(a):
    d = validate_responses(_read(a.responses))
    clean, audit = clean_responses(d, min_duration_seconds=a.min_duration,
                                   require_attention=not a.no_attention)
    clean.to_csv(a.output, index=False)
    Path(a.output).with_suffix(".audit.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps({k: v for k, v in audit.items() if k != "rules"}, indent=2))
    print(json.dumps({k: (v if v == "skipped" else v["removed"])
                      for k, v in audit["rules"].items()}, indent=2))


def cmd_estimate(a):
    d = validate_responses(_read(a.clean))
    table, _, acc = estimate_all_items(d, reporting_cap=a.cap, link=a.link,
                                       n_boot=a.n_boot, seed=a.seed)
    table.to_csv(a.output, index=False)
    acc.to_csv(Path(a.output).with_name(Path(a.output).stem + "_acceptance_by_offer.csv"),
               index=False)
    cols = ["item_id", "n_users", "sample_usage_rate", "median_wta", "median_lo", "median_hi",
            "median_location", "reporting_cap", "capped_mean_wta"]
    with pd.option_context("display.width", 200, "display.float_format", "{:,.2f}".format):
        print(table[cols].to_string(index=False))


def cmd_aggregate(a):
    table = _read(a.items)
    adoption = _adoption_arg(a.adoption_rate if a.adoption_rate is not None else a.adoption)
    agg = aggregate_table(table, population=a.population, adoption=adoption,
                          adoption_source=a.adoption_source,
                          annualization_factor=a.annualization_factor)
    agg.to_csv(a.output, index=False)
    print(json.dumps(sum_values(agg), indent=2))


def cmd_run(a):
    cfg = _read_config(a.config)
    base = Path(a.config).parent
    est = cfg.get("estimation", {})
    cl = cfg.get("cleaning", {})

    resp = validate_responses(_read(base / cfg["responses"]))
    items_df = validate_items(_read(base / cfg["items"])) if cfg.get("items") else None
    if cfg.get("item_id"):
        resp = resp[resp["item_id"] == str(cfg["item_id"])]
        if items_df is not None:
            items_df = items_df[items_df["item_id"] == str(cfg["item_id"])]

    clean, audit = clean_responses(resp, min_duration_seconds=cl.get("min_duration_seconds", 45),
                                   require_attention=cl.get("require_attention", True))
    table, _, acc = estimate_all_items(
        clean, reporting_cap=cfg.get("reporting_cap", est.get("reporting_cap")),
        link=est.get("link", "logit"), n_boot=est.get("n_boot", 500),
        seed=cfg.get("seed", est.get("seed", 0)))

    agg_table = totals = None
    if cfg.get("population"):
        adoption = _adoption_arg(cfg.get("adoption_rate"), base)
        agg_table = aggregate_table(
            table, population=float(cfg["population"]), adoption=adoption,
            adoption_source=cfg.get("adoption_source", "survey usage question"),
            annualization_factor=float(cfg.get("annualization_factor", 12)))
        totals = sum_values(agg_table, items_df)

    out = write_deposit(base / cfg.get("output", "deposit"), table, audit, cfg, acc,
                        agg_table, totals)
    print(f"deposit written -> {out}")
    print((out / "summary.md").read_text())


def build_parser():
    p = argparse.ArgumentParser(prog="gdpb", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"gdpb {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("simulate", help="write a synthetic survey with ground truth")
    s.add_argument("outdir")
    s.add_argument("--n-per-item", type=int, default=2100)
    s.add_argument("--seed", type=int, default=20260805)
    s.set_defaults(fn=cmd_simulate)

    s = sub.add_parser("validate", help="check files against the schemas")
    s.add_argument("responses")
    s.add_argument("--items")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("design", help="allocate respondents to (item, offer) cells")
    s.add_argument("items")
    s.add_argument("--n-respondents", type=int, required=True)
    s.add_argument("--items-per-respondent", type=int, default=1)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("-o", "--output", default="allocation.csv")
    s.set_defaults(fn=cmd_design)

    s = sub.add_parser("clean", help="apply protocol cleaning rules")
    s.add_argument("responses")
    s.add_argument("-o", "--output", default="clean.csv")
    s.add_argument("--min-duration", type=float, default=45)
    s.add_argument("--no-attention", action="store_true")
    s.set_defaults(fn=cmd_clean)

    s = sub.add_parser("estimate", help="per-item WTA estimates")
    s.add_argument("clean")
    s.add_argument("-o", "--output", default="items.csv")
    s.add_argument("--link", choices=["logit", "probit"], default="logit")
    s.add_argument("--n-boot", type=int, default=500)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--cap", type=float, default=None,
                   help="reporting cap for the mean (default: top of each item's grid)")
    s.set_defaults(fn=cmd_estimate)

    s = sub.add_parser("aggregate", help="annualized capped value from an item table")
    s.add_argument("items")
    s.add_argument("--population", type=float, required=True)
    s.add_argument("--adoption-rate", type=float, default=None,
                   help="single adoption share applied to every item")
    s.add_argument("--adoption", help="CSV with item_id, adoption_rate (external source)")
    s.add_argument("--adoption-source", default="external")
    s.add_argument("--annualization-factor", type=float, default=12)
    s.add_argument("-o", "--output", default="aggregate.csv")
    s.set_defaults(fn=cmd_aggregate)

    s = sub.add_parser("run", help="full pipeline from a config file (yaml or json)")
    s.add_argument("config")
    s.set_defaults(fn=cmd_run)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except Exception as e:  # keep CLI errors short
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
