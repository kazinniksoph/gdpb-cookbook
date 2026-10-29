"""Command line entry point.

    gdpb simulate  OUTDIR [--n-per-item N] [--seed S]
    gdpb validate  RESPONSES.csv [--items ITEMS.csv]
    gdpb design    ITEMS.csv --n-respondents N [--items-per-respondent K] -o allocation.csv
    gdpb clean     RESPONSES.csv -o clean.csv [--min-duration 45] [--no-attention]
    gdpb estimate  CLEAN.csv -o items.csv [--link logit|probit] [--n-boot 500]
    gdpb aggregate ITEMS.csv --population N [--adoption adoption.csv] -o aggregate.csv
    gdpb run       config.yaml        # clean -> estimate -> aggregate -> deposit
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from . import __version__
from .aggregate import aggregate_table, sum_surplus
from .clean import clean_responses
from .design import allocate
from .estimate import estimate_all_items
from .report import write_deposit
from .schema import validate_items, validate_responses
from .simulate import simulate_survey


def _read(path):
    p = Path(path)
    return pd.read_excel(p) if p.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(p)


def cmd_simulate(a):
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    df, truth, items = simulate_survey(n_per_item=a.n_per_item, seed=a.seed)
    df.to_csv(out / "raw_responses.csv", index=False)
    items.to_csv(out / "items.csv", index=False)
    (out / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    print(f"wrote {len(df):,} rows, {len(items)} items -> {out}")


def cmd_validate(a):
    d = validate_responses(_read(a.responses))
    msg = f"responses ok: {len(d):,} rows, {d['item'].nunique()} items, " \
          f"{d['respondent_id'].nunique():,} respondents"
    if a.items:
        items = validate_items(_read(a.items))
        unknown = sorted(set(d["item"]) - set(items["item"]))
        if unknown:
            print(f"WARNING: {len(unknown)} items in responses not in item file: {unknown[:10]}")
        msg += f"; item file ok: {len(items)} items"
    print(msg)


def cmd_design(a):
    items = validate_items(_read(a.items))
    alloc = allocate(items, a.n_respondents, a.items_per_respondent, seed=a.seed)
    alloc.to_csv(a.output, index=False)
    cells = alloc.groupby(["item", "price"]).size()
    print(f"wrote {len(alloc):,} assignments -> {a.output}; "
          f"cell sizes min {cells.min()} / max {cells.max()}")


def cmd_clean(a):
    d = validate_responses(_read(a.responses))
    clean, audit = clean_responses(d, min_duration_seconds=a.min_duration,
                                   require_attention=not a.no_attention)
    clean.to_csv(a.output, index=False)
    Path(a.output).with_suffix(".audit.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


def cmd_estimate(a):
    d = validate_responses(_read(a.clean))
    table, _ = estimate_all_items(d, link=a.link, n_boot=a.n_boot, seed=a.seed)
    table.to_csv(a.output, index=False)
    cols = ["item", "n_users", "p_use", "median_wta", "median_lo", "median_hi", "mean_wta"]
    with pd.option_context("display.width", 160, "display.float_format", "{:,.2f}".format):
        print(table[cols].to_string(index=False))


def cmd_aggregate(a):
    table = _read(a.items)
    ext = None
    if a.adoption:
        ad = _read(a.adoption)
        ext = dict(zip(ad["item"].astype(str), ad["p_use"].astype(float)))
    agg = aggregate_table(table, population=a.population, p_use_external=ext)
    agg.to_csv(a.output, index=False)
    print(json.dumps(sum_surplus(agg), indent=2))


def cmd_run(a):
    cfg = yaml.safe_load(Path(a.config).read_text())
    base = Path(a.config).parent
    resp = validate_responses(_read(base / cfg["responses"]))
    items_df = validate_items(_read(base / cfg["items"])) if cfg.get("items") else None
    cl = cfg.get("cleaning", {})
    clean, audit = clean_responses(resp, min_duration_seconds=cl.get("min_duration_seconds", 45),
                                   require_attention=cl.get("require_attention", True))
    est = cfg.get("estimation", {})
    table, _ = estimate_all_items(clean, link=est.get("link", "logit"),
                                  n_boot=est.get("n_boot", 500), seed=est.get("seed", 0))
    agg_table = totals = None
    ag = cfg.get("aggregation")
    if ag and ag.get("population"):
        ext = None
        if ag.get("adoption"):
            ad = _read(base / ag["adoption"])
            ext = dict(zip(ad["item"].astype(str), ad["p_use"].astype(float)))
        agg_table = aggregate_table(table, population=float(ag["population"]), p_use_external=ext)
        totals = sum_surplus(agg_table, items_df)
    out = write_deposit(base / cfg.get("output", "deposit"), table, audit, cfg, agg_table, totals)
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

    s = sub.add_parser("design", help="allocate respondents to (item, price) cells")
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
    s.set_defaults(fn=cmd_estimate)

    s = sub.add_parser("aggregate", help="consumer surplus from an item table")
    s.add_argument("items")
    s.add_argument("--population", type=float, required=True)
    s.add_argument("--adoption", help="CSV with columns item, p_use (external adoption)")
    s.add_argument("-o", "--output", default="aggregate.csv")
    s.set_defaults(fn=cmd_aggregate)

    s = sub.add_parser("run", help="full pipeline from a config.yaml")
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
