from __future__ import annotations
import argparse, json
from pathlib import Path
from .config import load_sites, load_costs, load_egress
from .connectors import build_host, ConnectorError
from .runner import run_attempts
from .aggregator import aggregate
from .models import attempt_to_json


def _build_host_adapters(egress: dict) -> list:
    """Build one HostAdapter per entry under `hosts:` in egress.yaml, via its
    connector. Any number of hosts is allowed (your machine, cloud servers,
    hosting providers). A host whose connector can't build (e.g. a missing
    credential) is skipped with a message, so the other hosts still run. The
    retrieval arm is added once Exa/Parallel keys exist."""
    adapters = []
    for name, profile in (egress.get("hosts") or {}).items():
        try:
            adapters.append(build_host(name, profile))
        except ConnectorError as e:
            print(f"skipping host: {e}")
    return adapters


def cmd_run(args):
    sites = load_sites(args.sites)
    costs = load_costs(args.costs)
    egress = load_egress(args.egress)
    adapters = _build_host_adapters(egress)
    # Stream each attempt to disk as it completes, so a crash mid-run keeps
    # everything already measured rather than discarding a whole buffered run.
    with open(args.out, "w") as f:
        def sink(a):
            f.write(attempt_to_json(a) + "\n")
            f.flush()
        attempts = run_attempts(sites, adapters, costs,
                                rate_limit_s=args.rate_limit, on_attempt=sink)
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
