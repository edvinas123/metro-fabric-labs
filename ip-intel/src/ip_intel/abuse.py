from __future__ import annotations

"""Abuse section — reputation, blocklist membership, and the abuse contact.

Zero-key by default:
  * special-use / bogon flags       → stdlib `ipaddress`
  * reverse DNS + forward-confirmed → DNS
  * DNSBL membership                → DNS A-record queries against public zones
  * Tor exit-node membership        → the public bulk exit list

Optional (free key): AbuseIPDB confidence score, injected as a callable so the
key/HTTP details live at the edge and this stays unit-testable.
"""

import ipaddress
from typing import Callable, Optional

from .models import Abuse
from .net import DnsResolver

# Public DNS blocklists (IPv4). Membership = the reversed-IP query resolves.
DNSBL_ZONES = {
    "spamhaus-zen": "zen.spamhaus.org",
    "spamcop": "bl.spamcop.net",
    "barracuda": "b.barracudacentral.org",
}
TOR_EXIT_LIST = "https://check.torproject.org/torbulkexitlist"


def _reversed_v4(ip: str) -> str:
    return ".".join(reversed(ip.split(".")))


def _special_use(ip: str) -> tuple[bool, Optional[str]]:
    obj = ipaddress.ip_address(ip)
    if obj.is_loopback:
        return True, "loopback"
    if obj.is_private:
        return True, "private"
    if obj.is_link_local:
        return True, "link-local"
    if obj.is_multicast:
        return True, "multicast"
    if obj.is_reserved or obj.is_unspecified:
        return True, "reserved"
    if not obj.is_global:
        return True, "non-global"
    return False, None


def lookup(
    ip: str,
    *,
    dns: DnsResolver,
    tor_get: Optional[Callable[[], str]] = None,
    abuseipdb: Optional[Callable[[str], dict]] = None,
    scamalytics: Optional[Callable[[str], dict]] = None,
    ipqs: Optional[Callable[[str], dict]] = None,
    greynoise: Optional[Callable[[str], dict]] = None,
    shodan: Optional[Callable[[str], dict]] = None,
    apivoid: Optional[Callable[[str], dict]] = None,
    abuse_email: Optional[str] = None,
) -> Abuse:
    obj = ipaddress.ip_address(ip)
    is_bogon, special = _special_use(ip)
    out = Abuse(abuse_email=abuse_email, is_bogon=is_bogon,
                special_use=special, sources=["ipaddress"])

    # Reverse DNS + forward-confirm (FCrDNS).
    ptr = dns.reverse(ip)
    out.reverse_dns = ptr
    if ptr:
        out.forward_confirmed = ip in dns.forward(ptr)
        out.sources.append("dns")

    # Bogon / special-use addresses aren't meaningfully on public blocklists.
    if is_bogon:
        return out

    # DNSBL membership (IPv4 zones only).
    if obj.version == 4:
        rev = _reversed_v4(ip)
        for label, zone in DNSBL_ZONES.items():
            out.blocklists_checked.append(label)
            try:
                if dns.resolves(f"{rev}.{zone}"):
                    out.blocklists_listed.append(label)
            except Exception as e:  # noqa: BLE001
                out.errors.append(f"dnsbl {label} failed: {e}")
        out.sources.append("dnsbl")

    # Tor exit node membership.
    if tor_get is not None:
        try:
            exits = {line.strip() for line in tor_get().splitlines() if line.strip()}
            out.tor_exit_node = ip in exits
            out.sources.append("tor-exit-list")
        except Exception as e:  # noqa: BLE001
            out.errors.append(f"tor exit list failed: {e}")

    # Optional AbuseIPDB enrichment.
    if abuseipdb is not None:
        try:
            data = abuseipdb(ip) or {}
            out.abuse_confidence = data.get("abuseConfidenceScore")
            out.usage_type = data.get("usageType")
            total = data.get("totalReports")
            if total is not None:
                out.report_categories.append(f"{total} reports (AbuseIPDB)")
            out.sources.append("abuseipdb")
        except Exception as e:  # noqa: BLE001
            out.errors.append(f"abuseipdb failed: {e}")

    # Optional Scamalytics fraud score.
    if scamalytics is not None:
        try:
            data = scamalytics(ip) or {}
            out.fraud_score = data.get("score")
            out.fraud_risk = data.get("risk")
            out.sources.append("scamalytics")
        except Exception as e:  # noqa: BLE001
            out.errors.append(f"scamalytics failed: {e}")

    # Optional IPQualityScore — fills the fraud score if Scamalytics didn't.
    if ipqs is not None:
        try:
            data = ipqs(ip) or {}
            if out.fraud_score is None:
                out.fraud_score = data.get("score")
            out.sources.append("ipqs")
        except Exception as e:  # noqa: BLE001
            out.errors.append(f"ipqs failed: {e}")

    # Optional GreyNoise — internet-scanner classification.
    if greynoise is not None:
        try:
            data = greynoise(ip) or {}
            out.greynoise_class = data.get("classification")
            out.greynoise_name = data.get("name")
            out.sources.append("greynoise")
        except Exception as e:  # noqa: BLE001
            out.errors.append(f"greynoise failed: {e}")

    # Optional Shodan — open ports + exposure tags.
    if shodan is not None:
        try:
            data = shodan(ip) or {}
            out.open_ports = data.get("ports") or []
            out.exposure_tags = data.get("tags") or []
            out.sources.append("shodan")
        except Exception as e:  # noqa: BLE001
            out.errors.append(f"shodan failed: {e}")

    # Optional APIVoid — aggregate reputation: detections + risk + anonymity.
    if apivoid is not None:
        try:
            data = apivoid(ip) or {}
            out.blacklist_detections = data.get("detections")
            out.risk_score = data.get("risk")
            out.anonymity_flags = data.get("flags") or []
            out.sources.append("apivoid")
        except Exception as e:  # noqa: BLE001
            out.errors.append(f"apivoid failed: {e}")

    return out
