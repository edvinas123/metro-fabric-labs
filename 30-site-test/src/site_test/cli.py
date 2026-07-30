from __future__ import annotations
import argparse, json
from pathlib import Path
from .config import load_sites, load_costs, load_egress
from .adapters.direct import DatacenterAdapter, IspProxyAdapter
from .runner import run_attempts
from .aggregator import aggregate
from .models import attempt_to_json


def _build_direct_adapters(egress: dict) -> list:
    """Build only the direct arms from egress.yaml. The retrieval arm is added
    once Exa/Parallel credentials exist (see issue: RetrievalApiAdapter wiring)."""
    adapters = []
    if "datacenter" in egress:
        dc = egress["datacenter"]
        adapters.append(DatacenterAdapter(geos=dc.get("geos", []), proxy=dc.get("proxy")))
    if "isp_proxy" in egress:
        isp = egress["isp_proxy"]
        adapters.append(IspProxyAdapter(geos=isp.get("geos", []), proxies=isp.get("proxies", {})))
    return adapters


def cmd_run(args):
    sites = load_sites(args.sites)
    costs = load_costs(args.costs)
    egress = load_egress(args.egress)
    adapters = _build_direct_adapters(egress)
    attempts = run_attempts(sites, adapters, costs, rate_limit_s=args.rate_limit)
    with open(args.out, "w") as f:
        for a in attempts:
            f.write(attempt_to_json(a) + "\n")
    print(f"wrote {len(attempts)} attempts to {args.out}")


def cmd_aggregate(args):
    from .models import Attempt
    rows = []
    for line in Path(args.infile).read_text().splitlines():
        if line.strip():
            rows.append(Attempt(**json.loads(line)))
    sc = aggregate(rows)
    Path(args.out).write_text(json.dumps(sc, indent=2))
    print(f"wrote scorecard to {args.out}")


def main():
    p = argparse.ArgumentParser(prog="site-test")
    sub = p.add_subparsers(required=True)

    r = sub.add_parser("run")
    r.add_argument("--sites", default="data/sites.yaml")
    r.add_argument("--costs", default="data/costs.yaml")
    r.add_argument("--egress", default="data/egress.yaml")
    r.add_argument("--out", default="results.jsonl")
    r.add_argument("--rate-limit", type=float, default=2.0)
    r.set_defaults(func=cmd_run)

    a = sub.add_parser("aggregate")
    a.add_argument("--in", dest="infile", default="results.jsonl")
    a.add_argument("--out", default="scorecard.json")
    a.set_defaults(func=cmd_aggregate)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
