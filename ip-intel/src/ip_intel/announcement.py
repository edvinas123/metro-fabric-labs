from __future__ import annotations

"""Announcement section — live BGP routing, no key required.

Primary: RIPEstat Data API
  network-info      → covering prefix + origin ASN(s)
  as-overview       → the AS holder name
  routing-status    → is the prefix visible, and to how many collector peers
  rpki-validation   → RPKI state of (origin, prefix)

Cross-check / fallback: BGPView (bgpview.io, no key) fills the AS holder name,
upstream ASNs, and more-specific prefixes that RIPEstat doesn't return, and can
supply an origin ASN when RIPEstat's RIS view is empty.

Each call is independent and best-effort: a failure records an error on the
section and leaves that field unset, never a fabricated value.
"""

from typing import Callable

from .models import Announcement

BASE = "https://stat.ripe.net/data"
NETWORK_INFO = BASE + "/network-info/data.json?resource={ip}"
AS_OVERVIEW = BASE + "/as-overview/data.json?resource=AS{asn}"
ROUTING_STATUS = BASE + "/routing-status/data.json?resource={prefix}"
RPKI = BASE + "/rpki-validation/data.json?resource=AS{asn}&prefix={prefix}"
BGPVIEW_IP = "https://api.bgpview.io/ip/{ip}"
BGPVIEW_ASN_UP = "https://api.bgpview.io/asn/{asn}/upstreams"


def _bgpview_fallback(ip: str, ann: Announcement,
                      fetch_json: Callable[[str], dict]) -> None:
    """Fill AS name / origin ASN / more-specifics / upstreams from BGPView."""
    try:
        data = fetch_json(BGPVIEW_IP.format(ip=ip)).get("data", {})
    except Exception as e:  # noqa: BLE001
        ann.errors.append(f"bgpview failed: {e}")
        return
    ann.sources.append("bgpview")
    prefixes = data.get("prefixes") or []
    if prefixes:
        # Most specific prefix first is what BGPView returns; use it as the cover.
        cover = prefixes[0]
        ann.prefix = ann.prefix or cover.get("prefix")
        asn = (cover.get("asn") or {})
        if ann.origin_asn is None and asn.get("asn"):
            ann.origin_asn = int(asn["asn"])
            ann.announced = True
        ann.as_name = ann.as_name or asn.get("name") or asn.get("description")
        ann.more_specifics = [p.get("prefix") for p in prefixes[1:6] if p.get("prefix")]

    if ann.origin_asn and not ann.upstreams:
        try:
            up = fetch_json(BGPVIEW_ASN_UP.format(asn=ann.origin_asn)).get("data", {})
            ipv4 = (up.get("ipv4_upstreams") or [])
            ann.upstreams = [int(u["asn"]) for u in ipv4[:8] if u.get("asn")]
        except Exception as e:  # noqa: BLE001
            ann.errors.append(f"bgpview upstreams failed: {e}")


def lookup(ip: str, fetch_json: Callable[[str], dict]) -> Announcement:
    ann = Announcement(sources=["ripestat"])

    try:
        ni = fetch_json(NETWORK_INFO.format(ip=ip)).get("data", {})
        ann.prefix = ni.get("prefix")
        asns = ni.get("asns") or []
        if asns:
            ann.origin_asn = int(asns[0])
    except Exception as e:  # noqa: BLE001
        ann.errors.append(f"network-info failed: {e}")

    if ann.origin_asn and ann.prefix:
        ann.announced = True
        try:
            ov = fetch_json(AS_OVERVIEW.format(asn=ann.origin_asn)).get("data", {})
            ann.as_name = ov.get("holder")
        except Exception as e:  # noqa: BLE001
            ann.errors.append(f"as-overview failed: {e}")

        try:
            rs = fetch_json(ROUTING_STATUS.format(prefix=ann.prefix)).get("data", {})
            v4 = (rs.get("visibility") or {}).get("v4") or {}
            v6 = (rs.get("visibility") or {}).get("v6") or {}
            ann.visibility = v4.get("ris_peers_seeing") or v6.get("ris_peers_seeing")
        except Exception as e:  # noqa: BLE001
            ann.errors.append(f"routing-status failed: {e}")

        try:
            rp = fetch_json(RPKI.format(asn=ann.origin_asn, prefix=ann.prefix)).get("data", {})
            ann.rpki_status = rp.get("status")
        except Exception as e:  # noqa: BLE001
            ann.errors.append(f"rpki-validation failed: {e}")

    # Cross-check / fill gaps via BGPView (also recovers origin when RIS is empty).
    if ann.origin_asn is None or ann.as_name is None or not ann.upstreams:
        _bgpview_fallback(ip, ann, fetch_json)

    if ann.origin_asn is None or not ann.prefix:
        ann.announced = False
        ann.errors.append("no covering prefix announced for this IP")

    return ann
