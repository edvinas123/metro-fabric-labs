from __future__ import annotations

"""Geolocation section — multiple free providers, reconciled.

Primary: ip-api.com (no key). Cross-check: ipwho.is (no key). We surface both and
flag any country-level disagreement rather than silently trusting one — IP geo is
approximate and providers routinely differ. Note also that this is *where the IP
resolves*, which can differ from the registrant country in the Ownership section.
"""

from typing import Callable

from .models import Geo

IPAPI_URL = "http://ip-api.com/json/{ip}"
IPAPI_FIELDS = ("status,message,country,regionName,city,lat,lon,timezone,"
                "isp,org,as,mobile,proxy,hosting,query")
IPWHOIS_URL = "https://ipwho.is/{ip}"


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
    return Geo(
        country=data.get("country"),
        region=data.get("regionName"),
        city=data.get("city"),
        latitude=data.get("lat"),
        longitude=data.get("lon"),
        timezone=data.get("timezone"),
        isp=data.get("isp"),
        org=data.get("org") or data.get("as"),
        connection_type=_connection_type(bool(data.get("mobile")),
                                         bool(data.get("hosting"))),
        sources=["ip-api"],
    )


def lookup(ip: str, fetch_json: Callable[[str], dict]) -> Geo:
    try:
        primary = fetch_json(f"{IPAPI_URL.format(ip=ip)}?fields={IPAPI_FIELDS}")
        geo = parse_ipapi(primary)
    except Exception as e:  # noqa: BLE001
        geo = Geo(errors=[f"ip-api lookup failed: {e}"], sources=["ip-api"])

    # Cross-check country against a second provider.
    try:
        second = fetch_json(IPWHOIS_URL.format(ip=ip))
        if second.get("success", True):
            geo.sources.append("ipwho.is")
            other_country = second.get("country")
            if geo.country and other_country and other_country != geo.country:
                geo.disagreements.append(
                    f"country: ip-api={geo.country} ipwho.is={other_country}")
            if geo.country is None and other_country:
                geo.country = other_country
                geo.city = geo.city or second.get("city")
    except Exception as e:  # noqa: BLE001
        geo.errors.append(f"ipwho.is cross-check failed: {e}")

    return geo
