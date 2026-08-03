from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
from pathlib import Path

from .net import HttpClient
from .report import EXT, RENDERERS, build_report
from .whoami import whoami

SUBCOMMANDS = {"report", "whoami"}


def _abuseipdb_client(http: HttpClient):
    """Return an AbuseIPDB check callable if a free key is in the env, else None."""
    key = os.environ.get("ABUSEIPDB_KEY")
    if not key:
        return None

    def check(ip: str) -> dict:
        data = http.get_json(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": ip, "maxAgeInDays": 90},
            headers={"Key": key, "Accept": "application/json"},
        )
        return data.get("data", {})

    return check


def _resolve_target(token: str) -> tuple[str, str | None]:
    """Map a user token to the IP to actually query.

    A CIDR is reported via a representative host inside it (the covering prefix,
    RDAP block, and BGP origin are identical for the whole range). Returns
    (ip_to_query, note-or-None).
    """
    if "/" in token:
        net = ipaddress.ip_network(token, strict=False)
        if net.num_addresses == 1:
            return str(net.network_address), None
        sample = next(net.hosts(), net.network_address)
        return str(sample), f"subnet {net} → sampling representative host {sample}"
    return token, None


def _targets(args) -> list[str]:
    targets = list(args.ips)
    if args.input:
        for line in Path(args.input).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                targets.append(line)
    return targets


def cmd_report(args) -> int:
    formats = [f.strip() for f in args.format.split(",") if f.strip()]
    for f in formats:
        if f not in RENDERERS:
            print(f"unknown format: {f} (choose from {', '.join(RENDERERS)})",
                  file=sys.stderr)
            return 2

    http = HttpClient()
    abuseipdb = _abuseipdb_client(http)
    tokens = _targets(args)
    if not tokens:
        print("no IPs given", file=sys.stderr)
        return 2

    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for token in tokens:
        try:
            ip, note = _resolve_target(token)
        except ValueError as e:
            print(f"skipping {token!r}: {e}", file=sys.stderr)
            continue
        if note:
            print(f"# {note}", file=sys.stderr)

        try:
            report = build_report(ip, fetch_json=http.get_json,
                                  tor_get=lambda: http.get_text(
                                      "https://check.torproject.org/torbulkexitlist"),
                                  abuseipdb=abuseipdb)
        except ValueError as e:
            print(f"skipping {token!r}: {e}", file=sys.stderr)
            continue

        if out_dir:
            for f in formats:
                path = out_dir / f"{ip}.report.{EXT[f]}"
                path.write_text(RENDERERS[f](report))
                print(f"wrote {path}")
        else:
            # stdout: emit the first requested format only
            print(RENDERERS[formats[0]](report))
    return 0


def cmd_whoami(args) -> int:
    http = HttpClient()
    result = whoami(args.ip, fetch_json=http.get_json,
                    tor_get=lambda: http.get_text(
                        "https://check.torproject.org/torbulkexitlist"),
                    abuseipdb=_abuseipdb_client(http))
    print(json.dumps(result, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Convenience: `ipintel 8.8.8.8` == `ipintel report 8.8.8.8`.
    if argv and argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        argv.insert(0, "report")

    p = argparse.ArgumentParser(
        prog="ipintel",
        description="IP information report: ownership / abuse / geo / announcement.")
    sub = p.add_subparsers(required=True)

    r = sub.add_parser("report", help="build a full report for one or more IPs/CIDRs")
    r.add_argument("ips", nargs="*", help="IP address(es) or CIDR(s) to report on")
    r.add_argument("--input", help="file with one IP/CIDR per line")
    r.add_argument("--format", default="md",
                   help="comma list of md,json,html (default: md)")
    r.add_argument("--out", help="output directory (default: print to stdout)")
    r.set_defaults(func=cmd_report)

    w = sub.add_parser("whoami", help="identity view of your own (or a given) IP")
    w.add_argument("ip", nargs="?", help="IP to inspect (default: your public IP)")
    w.set_defaults(func=cmd_whoami)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
