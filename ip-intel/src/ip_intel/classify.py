from __future__ import annotations

"""Origin classification — the Metro Fabric value-add.

Design principle #6: *ISP-ORG is the trust anchor. A cert bound to a confirmed
ISP-ORG range carries real identity weight; a datacenter-IP cert does not.*

Signal precedence (strongest first):
  1. bogon / special-use        → reserved
  2. PeeringDB AS network type  → authoritative-ish: ISP vs Content/hosting
  3. AbuseIPDB usage type       → Data Center / Fixed Line ISP / Mobile ISP
  4. geo provider `hosting` flag → datacenter
  5. geo proxy/VPN flag         → datacenter/anon egress
  6. mobile indicators          → mobile
  7. ownership/geo name keywords → last-resort fallback

It remains a **heuristic** — a signal to weight a Certificate of Origin, never a
substitute for a confirmed ISP-ORG range.
"""

from typing import Optional

from .models import (Abuse, Geo, Ownership, OriginClass,
                     ISP_ORG, DATACENTER, MOBILE, RESERVED, UNKNOWN)

# PeeringDB `info_type` → our origin class.
_PEERINGDB_ISP = {"Cable/DSL/ISP", "NSP"}
_PEERINGDB_DC = {"Content", "Enterprise", "Educational/Research",
                 "Non-Profit", "Route Server"}

_DC_KEYWORDS = (
    "hosting", "datacenter", "data center", "data-center", "cloud", "vps",
    "server", "colo", "colocation", "dedicated", "amazon", "aws", "google",
    "microsoft", "azure", "digitalocean", "linode", "ovh", "hetzner", "vultr",
    "leaseweb", "contabo", "scaleway", "oracle", "cloudflare", "fastly",
    "raksmart", "peg tech", "petaexpress", "tencent", "alibaba",
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


# AbuseIPDB `usageType` → our origin class.
_USAGE_DC = {"Data Center/Web Hosting/Transit", "Content Delivery Network"}
_USAGE_ISP = {"Fixed Line ISP"}
_USAGE_MOBILE = {"Mobile ISP"}


def classify(ownership: Ownership, geo: Geo, abuse: Abuse, *,
             peeringdb_type: Optional[str] = None,
             usage_type: Optional[str] = None) -> OriginClass:
    if abuse.is_bogon:
        return OriginClass(
            kind=RESERVED, confidence="high",
            rationale=f"special-use / non-global address ({abuse.special_use})",
            trust_note="Not routable public space — cannot anchor a Certificate of Origin.")

    # 2. PeeringDB AS network type — the strongest available signal.
    if peeringdb_type in _PEERINGDB_ISP:
        return OriginClass(
            kind=ISP_ORG, confidence="high",
            rationale=f"PeeringDB AS type '{peeringdb_type}'",
            trust_note="Clean ISP-ORG origin — the trust anchor; a cert here carries real weight (principle #6).")
    if peeringdb_type in _PEERINGDB_DC:
        return OriginClass(
            kind=DATACENTER, confidence="high",
            rationale=f"PeeringDB AS type '{peeringdb_type}' (content/hosting network)",
            trust_note="Datacenter/content origin — a cert here carries low identity weight (principle #6).")

    # 3. AbuseIPDB usage type — an authoritative operator-declared category.
    if usage_type in _USAGE_DC:
        return OriginClass(
            kind=DATACENTER, confidence="high",
            rationale=f"AbuseIPDB usage type '{usage_type}'",
            trust_note="Datacenter/hosting origin — a cert here carries low identity weight (principle #6).")
    if usage_type in _USAGE_ISP:
        return OriginClass(
            kind=ISP_ORG, confidence="high",
            rationale=f"AbuseIPDB usage type '{usage_type}'",
            trust_note="Clean ISP-ORG origin — the trust anchor; a cert here carries real weight (principle #6).")
    if usage_type in _USAGE_MOBILE:
        return OriginClass(
            kind=MOBILE, confidence="high",
            rationale=f"AbuseIPDB usage type '{usage_type}'",
            trust_note="Mobile carrier space — shared CGNAT is common; attribution is weak.")

    # 4. Geo hosting flag.
    if geo.connection_type == "hosting":
        return OriginClass(
            kind=DATACENTER, confidence="high",
            rationale="geo provider flags this as hosting/datacenter space",
            trust_note="Datacenter origin — a cert here carries low identity weight (principle #6).")

    # 4. Proxy / VPN flag — anonymizing egress, effectively datacenter.
    if geo.proxy_vpn:
        return OriginClass(
            kind=DATACENTER, confidence="medium",
            rationale="geo provider flags this as a proxy/VPN/anonymizer",
            trust_note="Anonymizing/datacenter egress — a cert here carries low identity weight (principle #6).")

    blob = _text(ownership.organization, ownership.network_name, geo.isp, geo.org)

    # 5. Mobile.
    if geo.connection_type == "mobile" or any(k in blob for k in _MOBILE_KEYWORDS):
        return OriginClass(
            kind=MOBILE, confidence="medium",
            rationale="mobile/cellular carrier indicators",
            trust_note="Mobile carrier space — shared CGNAT is common; attribution is weak.")

    # 6. Keyword fallback.
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
