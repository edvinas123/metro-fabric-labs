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
IPAPI_FIELDS = ("status,message,country,countryCode,regionName,city,zip,lat,lon,"
                "timezone,isp,org,as,asname,mobile,proxy,hosting,query")
IPWHOIS_URL = "https://ipwho.is/{ip}"

_AS_RE = re.compile(r"AS(\d+)", re.I)

# Common country name → ISO-3166 alpha-2. Providers mix full names (ip-api,
# geo DBs) with codes (ipinfo, RDAP); we compare on the code to avoid false
# "disagreements" like "United Arab Emirates" vs "AE". Unmapped names fall back
# to their upper-cased selves, so two providers using the same name still match.
_NAME_TO_ISO = {
    "united states": "US", "united states of america": "US", "usa": "US",
    "united kingdom": "GB", "great britain": "GB", "canada": "CA",
    "germany": "DE", "france": "FR", "spain": "ES", "italy": "IT",
    "netherlands": "NL", "belgium": "BE", "switzerland": "CH", "austria": "AT",
    "ireland": "IE", "portugal": "PT", "sweden": "SE", "norway": "NO",
    "denmark": "DK", "finland": "FI", "poland": "PL", "czechia": "CZ",
    "czech republic": "CZ", "romania": "RO", "hungary": "HU", "greece": "GR",
    "russia": "RU", "russian federation": "RU", "ukraine": "UA", "turkey": "TR",
    "türkiye": "TR", "united arab emirates": "AE", "saudi arabia": "SA",
    "israel": "IL", "india": "IN", "china": "CN", "japan": "JP",
    "south korea": "KR", "korea, republic of": "KR", "singapore": "SG",
    "hong kong": "HK", "taiwan": "TW", "australia": "AU", "new zealand": "NZ",
    "brazil": "BR", "argentina": "AR", "mexico": "MX", "chile": "CL",
    "colombia": "CO", "south africa": "ZA", "nigeria": "NG", "egypt": "EG",
    "indonesia": "ID", "malaysia": "MY", "thailand": "TH", "vietnam": "VN",
    "viet nam": "VN", "philippines": "PH", "pakistan": "PK", "bangladesh": "BD",
    "iran": "IR", "iran, islamic republic of": "IR",
}


def _norm_country(value: Optional[str]) -> Optional[str]:
    """Canonicalize a country name-or-code to ISO alpha-2 for comparison."""
    if not value:
        return None
    v = value.strip()
    if len(v) == 2:
        return v.upper()
    return _NAME_TO_ISO.get(v.lower(), v.upper())


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
    # Record the ISO code for comparison (falls back to the name if ip-api didn't
    # return a code), while `country` keeps the human-readable name for display.
    code = data.get("countryCode") or g.country
    if code:
        g.by_source["ip-api"] = code
    return g


def _merge(geo: Geo, other: dict, source: str) -> None:
    """Add a provider's result: record its country, fill any gaps, flag conflicts."""
    code = other.get("country_code") or other.get("country")
    if code:
        geo.by_source[source] = code
    geo.sources.append(source)
    # Fill missing scalar fields from this provider.
    for attr in ("country", "region", "city", "postal", "latitude", "longitude",
                 "timezone", "isp", "org", "asn"):
        if getattr(geo, attr) in (None, "") and other.get(attr) not in (None, ""):
            setattr(geo, attr, other.get(attr))


def _reconcile(geo: Geo, registrant_country: Optional[str]) -> None:
    countries = {src: c for src, c in geo.by_source.items() if c}
    geo_codes = {_norm_country(c) for c in countries.values()}
    # Compare on normalized ISO codes so "United States" == "US" == "us".
    if len(geo_codes) > 1:
        geo.disagreements.append(
            "geo country: " + ", ".join(f"{s}={c}" for s, c in countries.items()))
    rc = _norm_country(registrant_country)
    if rc and geo_codes and rc not in geo_codes:
        geo.disagreements.append(
            f"geo={geo.country} vs WHOIS registrant={registrant_country}")


def lookup(
    ip: str,
    fetch_json: Callable[[str], dict],
    *,
    maxmind: Optional[Callable[[str], dict]] = None,
    ip2location: Optional[Callable[[str], dict]] = None,
    ipinfo: Optional[Callable[[str], dict]] = None,
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
                "country": second.get("country"),
                "country_code": second.get("country_code"),
                "region": second.get("region"),
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

    # IPinfo — geo + ASN + privacy flags (key-gated).
    if ipinfo is not None:
        try:
            data = ipinfo(ip)
            _merge(geo, data, "ipinfo")
            for f in data.get("privacy_flags") or []:
                if f not in geo.privacy_flags:
                    geo.privacy_flags.append(f)
            if geo.proxy_vpn is None and data.get("proxy_vpn") is not None:
                geo.proxy_vpn = data["proxy_vpn"]
            elif data.get("proxy_vpn"):
                geo.proxy_vpn = True
        except Exception as e:  # noqa: BLE001
            geo.errors.append(f"ipinfo failed: {e}")

    _reconcile(geo, registrant_country)
    return geo
