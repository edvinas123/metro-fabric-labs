from __future__ import annotations

"""Geolocation section — several providers, reconciled.

No-key by default: ip-api.com (primary) + ipwho.is (cross-check). Two more high-
quality providers activate automatically when their local database is configured:
MaxMind GeoLite2 (`MAXMIND_DB`) and IP2Location LITE (`IP2LOCATION_DB`). Each
provider's country goes into `by_source`, missing fields are filled from whichever
provider has them, and any country-level disagreement — including against the WHOIS
registrant country — is surfaced rather than hidden. Geo is where the IP *resolves*
and is approximate; it can legitimately differ from the registrant country.
"""

import re
from typing import Callable, Optional

from .models import Geo

IPAPI_URL = "http://ip-api.com/json/{ip}"
IPAPI_FIELDS = ("status,message,country,regionName,city,zip,lat,lon,timezone,"
                "isp,org,as,asname,mobile,proxy,hosting,query")
IPWHOIS_URL = "https://ipwho.is/{ip}"

_AS_RE = re.compile(r"AS(\d+)", re.I)


def _parse_asn(*values: Optional[str]) -> Optional[int]:
    for v in values:
        if v:
            m = _AS_RE.search(v)
            if m:
                return int(m.group(1))
    return None


def _connection_type(mobile: bool, hosting: bool) -> str | None:
    if hosting:
        return "hosting"
    if mobile:
        return "mobile"
    return None


def parse_ipapi(data: dict) -> Geo:
    if data.get("status") != "success":
        return Geo(errors=[f"ip-api: {data.get('message', 'lookup failed')}"],
                   sources=["ip-api"])
    g = Geo(
        country=data.get("country"),
        region=data.get("regionName"),
        city=data.get("city"),
        postal=data.get("zip") or None,
        latitude=data.get("lat"),
        longitude=data.get("lon"),
        timezone=data.get("timezone"),
        isp=data.get("isp"),
        org=data.get("org") or data.get("asname") or None,
        asn=_parse_asn(data.get("as"), data.get("asname")),
        connection_type=_connection_type(bool(data.get("mobile")),
                                         bool(data.get("hosting"))),
        proxy_vpn=bool(data.get("proxy")) if data.get("proxy") is not None else None,
        sources=["ip-api"],
    )
    if g.country:
        g.by_source["ip-api"] = g.country
    return g


def _merge(geo: Geo, other: dict, source: str) -> None:
    """Add a provider's result: record its country, fill any gaps, flag conflicts."""
    country = other.get("country")
    if country:
        geo.by_source[source] = country
    geo.sources.append(source)
    # Fill missing scalar fields from this provider.
    for attr in ("country", "region", "city", "postal", "latitude", "longitude",
                 "timezone", "isp", "org", "asn"):
        if getattr(geo, attr) in (None, "") and other.get(attr) not in (None, ""):
            setattr(geo, attr, other.get(attr))


def _reconcile(geo: Geo, registrant_country: Optional[str]) -> None:
    countries = {src: c for src, c in geo.by_source.items() if c}
    if len(set(countries.values())) > 1:
        geo.disagreements.append(
            "geo country: " + ", ".join(f"{s}={c}" for s, c in countries.items()))
    if registrant_country and geo.country and registrant_country != geo.country:
        geo.disagreements.append(
            f"geo={geo.country} vs WHOIS registrant={registrant_country}")


def lookup(
    ip: str,
    fetch_json: Callable[[str], dict],
    *,
    maxmind: Optional[Callable[[str], dict]] = None,
    ip2location: Optional[Callable[[str], dict]] = None,
    registrant_country: Optional[str] = None,
) -> Geo:
    try:
        primary = fetch_json(f"{IPAPI_URL.format(ip=ip)}?fields={IPAPI_FIELDS}")
        geo = parse_ipapi(primary)
    except Exception as e:  # noqa: BLE001
        geo = Geo(errors=[f"ip-api lookup failed: {e}"], sources=["ip-api"])

    # ipwho.is cross-check (no key).
    try:
        second = fetch_json(IPWHOIS_URL.format(ip=ip))
        if second.get("success", True):
            conn = second.get("connection") or {}
            _merge(geo, {
                "country": second.get("country"), "region": second.get("region"),
                "city": second.get("city"), "postal": second.get("postal"),
                "isp": conn.get("isp") or conn.get("org"),
                "asn": conn.get("asn"),
            }, "ipwho.is")
    except Exception as e:  # noqa: BLE001
        geo.errors.append(f"ipwho.is cross-check failed: {e}")

    # MaxMind GeoLite2 — activates only if a DB reader was injected.
    if maxmind is not None:
        try:
            _merge(geo, maxmind(ip), "maxmind")
        except Exception as e:  # noqa: BLE001
            geo.errors.append(f"maxmind failed: {e}")

    # IP2Location LITE — activates only if a DB reader was injected.
    if ip2location is not None:
        try:
            _merge(geo, ip2location(ip), "ip2location")
        except Exception as e:  # noqa: BLE001
            geo.errors.append(f"ip2location failed: {e}")

    _reconcile(geo, registrant_country)
    return geo
