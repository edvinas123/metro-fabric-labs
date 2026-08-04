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
    scamalytics: Optional[Callable[[str], dict]] = None,
    ipqs: Optional[Callable[[str], dict]] = None,
    greynoise: Optional[Callable[[str], dict]] = None,
    shodan: Optional[Callable[[str], dict]] = None,
    apivoid: Optional[Callable[[str], dict]] = None,
    maxmind: Optional[Callable[[str], dict]] = None,
    ip2location: Optional[Callable[[str], dict]] = None,
    ipinfo: Optional[Callable[[str], dict]] = None,
    peeringdb: Optional[Callable[[int], Optional[str]]] = None,
    now: Optional[str] = None,
) -> IPReport:
    ipaddress.ip_address(ip)  # raises ValueError on malformed input

    if fetch_json is None or tor_get is None:
        http = HttpClient()
        fetch_json = fetch_json or http.get_json
        tor_get = tor_get or (lambda: http.get_text(TOR_EXIT_LIST))
    dns = dns or SocketDns()

    ownership = own_mod.lookup(ip, fetch_json)
    geo = geo_mod.lookup(ip, fetch_json, maxmind=maxmind, ip2location=ip2location,
                         ipinfo=ipinfo, registrant_country=ownership.country)
    announcement = ann_mod.lookup(ip, fetch_json)
    abuse = abuse_mod.lookup(ip, dns=dns, tor_get=tor_get, abuseipdb=abuseipdb,
                             scamalytics=scamalytics, ipqs=ipqs, greynoise=greynoise,
                             shodan=shodan, apivoid=apivoid,
                             abuse_email=ownership.abuse_email)

    # APIVoid anonymity (proxy/VPN) is a dedicated signal — a positive detection
    # sets the geo proxy flag the classifier reads (even if a geo provider said
    # False), since APIVoid is the more specialized source for this.
    if not geo.proxy_vpn and any(f in ("proxy", "vpn", "webproxy")
                                 for f in abuse.anonymity_flags):
        geo.proxy_vpn = True

    # ASN → PeeringDB network type feeds the origin verdict (strongest signal).
    asn = announcement.origin_asn or geo.asn
    peeringdb_type = peeringdb(asn) if (peeringdb and asn) else None
    origin = classify(ownership, geo, abuse, peeringdb_type=peeringdb_type,
                      usage_type=abuse.usage_type)

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
        ("Usage type", a.usage_type),
        ("Reports", ", ".join(a.report_categories)),
        ("Fraud score", f"{a.fraud_score} ({a.fraud_risk})" if a.fraud_risk
                        else a.fraud_score),
        ("GreyNoise", f"{a.greynoise_class} ({a.greynoise_name})" if a.greynoise_name
                      else a.greynoise_class),
        ("APIVoid risk", a.risk_score),
        ("APIVoid detections", a.blacklist_detections),
        ("Anonymity", ", ".join(a.anonymity_flags) if a.anonymity_flags else None),
        ("Open ports", ", ".join(str(p) for p in a.open_ports) if a.open_ports else None),
        ("Exposure tags", ", ".join(a.exposure_tags) if a.exposure_tags else None),
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
        ("Postal", g.postal),
        ("Lat / Lon", f"{g.latitude}, {g.longitude}" if g.latitude is not None else None),
        ("Timezone", g.timezone), ("ISP", g.isp), ("Org", g.org),
        ("ASN", f"AS{g.asn}" if g.asn else None),
        ("Connection", g.connection_type),
        ("Proxy / VPN", g.proxy_vpn),
        ("Privacy flags", ", ".join(g.privacy_flags) if g.privacy_flags else None),
        ("Country by source", ", ".join(f"{s}={c}" for s, c in g.by_source.items())
                              if g.by_source else None),
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


_DASHBOARD_CSS = """
:root{--bg:#f7f8fa;--card:#fff;--ink:#1a2233;--muted:#5b6472;--line:#e3e7ee;--bad:#c62828;--ok:#2e7d32;--dc:#b26a00;--dcbg:#fff3e0}
@media (prefers-color-scheme:dark){:root{--bg:#0e1420;--card:#161d2b;--ink:#e6ebf2;--muted:#9aa5b5;--line:#263040;--bad:#ff6b6b;--ok:#6bd08a;--dc:#ffb74d;--dcbg:#3a2a12}}
:root[data-theme=dark]{--bg:#0e1420;--card:#161d2b;--ink:#e6ebf2;--muted:#9aa5b5;--line:#263040;--bad:#ff6b6b;--ok:#6bd08a;--dc:#ffb74d;--dcbg:#3a2a12}
:root[data-theme=light]{--bg:#f7f8fa;--card:#fff;--ink:#1a2233;--muted:#5b6472;--line:#e3e7ee;--bad:#c62828;--ok:#2e7d32;--dc:#b26a00;--dcbg:#fff3e0}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1000px;margin:0 auto;padding:2rem 1.2rem 3rem}h1{font-size:1.5rem;margin:0 0 .2rem}
.sub{color:var(--muted);margin:0 0 1.5rem;font-size:.9rem}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.8rem;margin-bottom:1.5rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:.9rem 1rem}
.card .k{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;margin-bottom:.25rem}
.card .v{font-weight:600;word-break:break-word}h2{font-size:1.05rem;margin:1.6rem 0 .6rem}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;min-width:720px;background:var(--card)}
th,td{text-align:left;padding:.55rem .8rem;border-bottom:1px solid var(--line);font-size:.88rem;white-space:nowrap}
th{color:var(--muted);font-size:.7rem;text-transform:uppercase;letter-spacing:.04em}tr:last-child td{border-bottom:none}
.num{text-align:right;font-variant-numeric:tabular-nums}.bad{color:var(--bad);font-weight:600}.ok{color:var(--ok)}
.pill{display:inline-block;padding:.1rem .5rem;border-radius:999px;font-size:.7rem;font-weight:700;text-transform:uppercase}
.pill.datacenter{background:var(--dcbg);color:var(--dc)}.pill.isp_org{background:#e6f4ea;color:var(--ok)}
.pill.mobile{background:#e3f2fd;color:#1565c0}.pill.reserved,.pill.unknown{background:var(--line);color:var(--muted)}
.foot{color:var(--muted);font-size:.78rem;margin-top:2rem;border-top:1px solid var(--line);padding-top:1rem}
"""


def render_dashboard(reports: list[IPReport], title: Optional[str] = None) -> str:
    """One self-contained HTML page comparing many IPs side by side. Shows a
    shared-facts panel when every target sits in the same allocation, then a
    per-host table of the fields that vary (verdict, proxy, blocklists, ports)."""
    def e(x) -> str:
        return _html.escape(str(x)) if x not in (None, "", []) else "—"

    reports = list(reports)
    cidrs = {r.ownership.cidr for r in reports if r.ownership.cidr}
    owners = {r.ownership.organization for r in reports if r.ownership.organization}
    shared = ""
    if len(reports) > 1 and len(cidrs) == 1 and len(owners) <= 1:
        o0, n0 = reports[0].ownership, reports[0].announcement
        shared = f"""<h2>Shared facts <small style="color:var(--muted);font-weight:400">(common to all targets)</small></h2>
<div class="grid">
  <div class="card"><div class="k">Owner</div><div class="v">{e(o0.organization)}</div></div>
  <div class="card"><div class="k">Allocation</div><div class="v mono">{e(o0.cidr)} · {e(o0.rir)}</div></div>
  <div class="card"><div class="k">Abuse contact</div><div class="v">{e(o0.abuse_email)}</div></div>
  <div class="card"><div class="k">BGP announced</div><div class="v">{'<span class="bad">No — dark / unrouted</span>' if n0.announced is False else e(n0.announced)}</div></div>
</div>"""

    rows = ""
    for r in reports:
        a, g, oc = r.abuse, r.geo, r.origin
        bl = ", ".join(a.blocklists_listed)
        bl_cell = f'<span class="bad">{e(bl)}</span>' if bl else '<span class="ok">clean</span>'
        proxy = '<span class="bad">yes</span>' if g.proxy_vpn else e(g.proxy_vpn)
        ports = ", ".join(str(p) for p in a.open_ports) if a.open_ports else "—"
        rows += (f'<tr><td class="mono">{e(r.ip)}</td>'
                 f'<td><span class="pill {oc.kind}">{e(oc.kind)}</span> <small>{e(oc.confidence)}</small></td>'
                 f'<td>{e(r.ownership.organization)}</td>'
                 f'<td>{e(g.country)}</td><td>{proxy}</td><td>{bl_cell}</td>'
                 f'<td class="num">{e(a.abuse_confidence)}</td>'
                 f'<td class="num">{e(a.fraud_score)}</td><td>{ports}</td></tr>\n')

    title = title or (f"{sorted(cidrs)[0]}" if len(cidrs) == 1 and len(reports) > 1
                      else f"{len(reports)} IP(s)")
    gen = reports[0].generated_at if reports else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ip-intel — {_html.escape(title)}</title><style>{_DASHBOARD_CSS}</style></head>
<body><div class="wrap">
<h1>IP Intel Report — <span class="mono">{_html.escape(title)}</span></h1>
<p class="sub">Generated {e(gen)} · {len(reports)} host(s) · ip-intel (Metro Fabric Labs) · read-only OSINT, blank = undetermined</p>
{shared}
<h2>Per-host findings</h2>
<div class="tablewrap"><table>
<thead><tr><th>IP</th><th>Verdict</th><th>Owner</th><th>Country</th><th>Proxy/VPN</th><th>Blocklists</th><th>Abuse</th><th>Fraud</th><th>Open ports</th></tr></thead>
<tbody>
{rows}</tbody></table></div>
<p class="foot">Sources: RDAP · AbuseIPDB · Scamalytics/IPQS · Shodan · IPinfo · ip-api · ipwho.is · RIPEstat · BGPView · DNSBL · Tor exit list. Geolocation and origin class are approximate. For legitimate network, security, and research use.</p>
</div>
<script>try{{var t=localStorage.getItem('theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>
</body></html>"""


RENDERERS: dict[str, Callable[[IPReport], str]] = {
    "md": render_markdown,
    "json": render_json,
    "html": render_html,
}
EXT = {"md": "md", "json": "json", "html": "html"}
