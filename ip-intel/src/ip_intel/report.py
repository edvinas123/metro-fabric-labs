from __future__ import annotations

"""Assemble the four sections into an IPReport and render it.

`build_report` wires real network clients by default, but every source's access
point is injectable so the whole pipeline runs offline in tests. Rendering is
pure: it only reads the assembled report.
"""

import html as _html
import ipaddress
from datetime import datetime, timezone
from typing import Callable, Optional

from . import abuse as abuse_mod
from . import announcement as ann_mod
from . import geo as geo_mod
from . import ownership as own_mod
from .abuse import TOR_EXIT_LIST
from .classify import classify
from .models import IPReport
from .net import DnsResolver, HttpClient, SocketDns


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_report(
    ip: str,
    *,
    fetch_json: Optional[Callable[[str], dict]] = None,
    dns: Optional[DnsResolver] = None,
    tor_get: Optional[Callable[[], str]] = None,
    abuseipdb: Optional[Callable[[str], dict]] = None,
    now: Optional[str] = None,
) -> IPReport:
    ipaddress.ip_address(ip)  # raises ValueError on malformed input

    if fetch_json is None or tor_get is None:
        http = HttpClient()
        fetch_json = fetch_json or http.get_json
        tor_get = tor_get or (lambda: http.get_text(TOR_EXIT_LIST))
    dns = dns or SocketDns()

    ownership = own_mod.lookup(ip, fetch_json)
    geo = geo_mod.lookup(ip, fetch_json)
    announcement = ann_mod.lookup(ip, fetch_json)
    abuse = abuse_mod.lookup(ip, dns=dns, tor_get=tor_get,
                             abuseipdb=abuseipdb, abuse_email=ownership.abuse_email)
    origin = classify(ownership, geo, abuse)

    return IPReport(
        ip=ip, generated_at=now or _now_iso(),
        ownership=ownership, abuse=abuse, geo=geo,
        announcement=announcement, origin=origin,
    )


# --- Renderers -------------------------------------------------------------

def _v(x) -> str:
    return "—" if x in (None, "", []) else str(x)


def render_markdown(r: IPReport) -> str:
    o, a, g, n, oc = r.ownership, r.abuse, r.geo, r.announcement, r.origin
    L: list[str] = []
    L.append(f"# IP intel report — `{r.ip}`")
    L.append("")
    L.append(f"*Generated {r.generated_at} · sources are cited per section · "
             f"blank fields are undetermined, never guessed.*")
    L.append("")
    L.append(f"**Origin verdict:** `{oc.kind}` ({oc.confidence} confidence) — {oc.rationale}  ")
    L.append(f"> {oc.trust_note}")
    L.append("")

    L.append("## 1. Ownership (RDAP / WHOIS)")
    L.append("")
    L.append("| Field | Value |")
    L.append("|---|---|")
    for label, val in [
        ("Network", o.network_name), ("CIDR", o.cidr), ("Organization", o.organization),
        ("RIR", o.rir), ("Country", o.country), ("Status", o.allocation_status),
        ("Registered", o.registered), ("Last changed", o.last_changed),
        ("Abuse contact", o.abuse_email), ("Admin", o.admin_contact), ("Tech", o.tech_contact),
    ]:
        L.append(f"| {label} | {_v(val)} |")
    L.append(f"\n*sources: {_v(', '.join(o.sources))}*")
    _errs(L, o.errors)

    L.append("\n## 2. Abuse & reputation")
    L.append("")
    L.append("| Field | Value |")
    L.append("|---|---|")
    for label, val in [
        ("Abuse contact", a.abuse_email), ("Reverse DNS", a.reverse_dns),
        ("Forward-confirmed", a.forward_confirmed),
        ("Blocklists listed", ", ".join(a.blocklists_listed) if a.blocklists_listed else "none"),
        ("Blocklists checked", ", ".join(a.blocklists_checked)),
        ("Tor exit node", a.tor_exit_node), ("Bogon / special-use", a.special_use or "no"),
        ("Abuse confidence", a.abuse_confidence),
        ("Reports", ", ".join(a.report_categories)),
    ]:
        L.append(f"| {label} | {_v(val)} |")
    L.append(f"\n*sources: {_v(', '.join(a.sources))}*")
    _errs(L, a.errors)

    L.append("\n## 3. Geolocation")
    L.append("")
    L.append("| Field | Value |")
    L.append("|---|---|")
    for label, val in [
        ("Country", g.country), ("Region", g.region), ("City", g.city),
        ("Lat / Lon", f"{g.latitude}, {g.longitude}" if g.latitude is not None else None),
        ("Timezone", g.timezone), ("ISP", g.isp), ("Org", g.org),
        ("Connection", g.connection_type),
    ]:
        L.append(f"| {label} | {_v(val)} |")
    if g.disagreements:
        L.append(f"\n> ⚠️ cross-source disagreement: {'; '.join(g.disagreements)}")
    L.append(f"\n*sources: {_v(', '.join(g.sources))} · geo is approximate and may "
             f"differ from registrant country above*")
    _errs(L, g.errors)

    L.append("\n## 4. Announcement (BGP)")
    L.append("")
    L.append("| Field | Value |")
    L.append("|---|---|")
    for label, val in [
        ("Announced", n.announced), ("Prefix", n.prefix),
        ("Origin ASN", f"AS{n.origin_asn}" if n.origin_asn else None),
        ("AS name", n.as_name), ("RPKI", n.rpki_status),
        ("Visibility (peers)", n.visibility),
        ("Upstreams", ", ".join(f"AS{u}" for u in n.upstreams) if n.upstreams else None),
        ("More specifics", ", ".join(n.more_specifics) if n.more_specifics else None),
    ]:
        L.append(f"| {label} | {_v(val)} |")
    L.append(f"\n*sources: {_v(', '.join(n.sources))}*")
    _errs(L, n.errors)

    L.append("\n---")
    L.append("*ip-intel · public registration, reputation, geo, and routing data only · "
             "geolocation and origin class are approximate. For legitimate network, "
             "security, and research use.*")
    return "\n".join(L) + "\n"


def _errs(L: list[str], errors: list[str]) -> None:
    for e in errors:
        L.append(f"\n> ⚠️ {e}")


def render_json(r: IPReport) -> str:
    return r.to_json()


def render_html(r: IPReport) -> str:
    body = _html.escape(render_markdown(r))
    return (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>ip-intel — {_html.escape(r.ip)}</title>"
        "<style>body{font:15px/1.5 system-ui,sans-serif;max-width:820px;margin:2rem auto;"
        "padding:0 1rem;color:#1a2233}pre{white-space:pre-wrap}</style>"
        f"<pre>{body}</pre>"
    )


RENDERERS: dict[str, Callable[[IPReport], str]] = {
    "md": render_markdown,
    "json": render_json,
    "html": render_html,
}
EXT = {"md": "md", "json": "json", "html": "html"}
