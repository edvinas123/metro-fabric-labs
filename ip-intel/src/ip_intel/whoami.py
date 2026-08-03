from __future__ import annotations

"""whoami — the thin identity layer on top of the ip-intel core.

This is the seed of the `whoami-agent` labs project ("an ipinfo.io for agents"):
given the caller's own IP (or one you pass), it returns the identity-relevant
slice of a full report — verified origin class + ISP-ORG tag, geo, and
reputation — reusing the same lookups. The core (`build_report`) ships first;
this is deliberately a small projection over it, ready to sit behind an HTTP
endpoint later.
"""

from typing import Callable, Optional

from .net import HttpClient
from .report import build_report

IPIFY = "https://api.ipify.org?format=json"


def detect_self_ip(fetch_json: Callable[[str], dict]) -> str:
    return fetch_json(IPIFY)["ip"]


def whoami(ip: Optional[str] = None, *, fetch_json: Optional[Callable[[str], dict]] = None,
           **build_kwargs) -> dict:
    if fetch_json is None:
        fetch_json = HttpClient().get_json
    if ip is None:
        ip = detect_self_ip(fetch_json)

    r = build_report(ip, fetch_json=fetch_json, **build_kwargs)
    return {
        "ip": r.ip,
        "origin_class": r.origin.kind,
        "origin_confidence": r.origin.confidence,
        "trust_note": r.origin.trust_note,
        "isp_org": r.geo.isp or r.ownership.organization,
        "asn": f"AS{r.announcement.origin_asn}" if r.announcement.origin_asn else None,
        "as_name": r.announcement.as_name,
        "rpki": r.announcement.rpki_status,
        "geo": {"country": r.geo.country, "city": r.geo.city},
        "reputation": {
            "blocklists_listed": r.abuse.blocklists_listed,
            "tor_exit_node": r.abuse.tor_exit_node,
            "abuse_confidence": r.abuse.abuse_confidence,
        },
    }
