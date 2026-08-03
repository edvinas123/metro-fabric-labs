from __future__ import annotations

"""Origin classification — the Metro Fabric value-add.

Design principle #6: *ISP-ORG is the trust anchor. A cert bound to a confirmed
ISP-ORG range carries real identity weight; a datacenter-IP cert does not.*

This turns the raw ownership/geo signals into a single verdict — is this IP a
clean ISP/carrier origin, a datacenter, mobile, or reserved — with a short
rationale and what it means for a Certificate of Origin. It is a **heuristic**
(keyword + provider-flag based), clearly labelled as such; it is a signal to
weight a cert, never a substitute for a confirmed ISP-ORG range.
"""

from .models import (Abuse, Geo, Ownership, OriginClass,
                     ISP_ORG, DATACENTER, MOBILE, RESERVED, UNKNOWN)

_DC_KEYWORDS = (
    "hosting", "datacenter", "data center", "data-center", "cloud", "vps",
    "server", "colo", "colocation", "dedicated", "amazon", "aws", "google",
    "microsoft", "azure", "digitalocean", "linode", "ovh", "hetzner", "vultr",
    "leaseweb", "contabo", "scaleway", "oracle", "cloudflare", "fastly",
)
_ISP_KEYWORDS = (
    "telecom", "telecommunication", "communications", "broadband", "cable",
    "fiber", "fibre", "dsl", "isp", "internet service", "wireless", "mobile",
    "cellular", "telefonica", "comcast", "verizon", "at&t", "vodafone",
    "orange", "deutsche telekom", "bt group", "charter", "cox", "kpn",
    "telia", "telenor",
)
_MOBILE_KEYWORDS = ("mobile", "cellular", "wireless lte", "gsm", "3g", "4g", "5g")


def _text(*parts: str | None) -> str:
    return " ".join(p.lower() for p in parts if p)


def classify(ownership: Ownership, geo: Geo, abuse: Abuse) -> OriginClass:
    if abuse.is_bogon:
        return OriginClass(
            kind=RESERVED, confidence="high",
            rationale=f"special-use / non-global address ({abuse.special_use})",
            trust_note="Not routable public space — cannot anchor a Certificate of Origin.")

    blob = _text(ownership.organization, ownership.network_name,
                 geo.isp, geo.org)

    # Provider flags are stronger than name keywords.
    if geo.connection_type == "hosting":
        return OriginClass(
            kind=DATACENTER, confidence="high",
            rationale="geo provider flags this as hosting/datacenter space",
            trust_note="Datacenter origin — a cert here carries low identity weight (principle #6).")
    if geo.connection_type == "mobile" or any(k in blob for k in _MOBILE_KEYWORDS):
        return OriginClass(
            kind=MOBILE, confidence="medium",
            rationale="mobile/cellular carrier indicators",
            trust_note="Mobile carrier space — shared CGNAT is common; attribution is weak.")

    dc = any(k in blob for k in _DC_KEYWORDS)
    isp = any(k in blob for k in _ISP_KEYWORDS)

    if dc and not isp:
        return OriginClass(
            kind=DATACENTER, confidence="medium",
            rationale="ownership/geo names match datacenter/hosting keywords",
            trust_note="Datacenter origin — a cert here carries low identity weight (principle #6).")
    if isp and not dc:
        return OriginClass(
            kind=ISP_ORG, confidence="medium",
            rationale="ownership/geo names match ISP/carrier keywords",
            trust_note="Clean ISP-ORG origin — the trust anchor; a cert here carries real weight (principle #6).")
    if isp and dc:
        return OriginClass(
            kind=UNKNOWN, confidence="low",
            rationale="mixed ISP and datacenter signals — needs manual confirmation",
            trust_note="Ambiguous — confirm the ISP-ORG range before trusting a cert.")

    return OriginClass(
        kind=UNKNOWN, confidence="low",
        rationale="no strong ISP or datacenter signal in ownership/geo data",
        trust_note="Unclassified — confirm the ISP-ORG range before trusting a cert.")
