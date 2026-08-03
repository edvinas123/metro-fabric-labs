from __future__ import annotations

"""Optional external providers — the key/DB-gated edge.

Everything here is off by default and turns on only when its credential or local
database is configured, so the core report always runs with zero setup. Each
factory returns a ready-to-inject callable, or `None` when it isn't configured
(a short reason is printed to stderr so the user knows why an enrichment is
absent). Heavy third-party libraries are imported lazily inside the factory.

Env:
  MAXMIND_DB        path to a GeoLite2-City .mmdb   (free: MaxMind license)
  IP2LOCATION_DB    path to an IP2Location LITE .BIN (free: IP2Location LITE)
  SCAMALYTICS_BASE  your account base URL, e.g. https://api11.scamalytics.com/<user>
  SCAMALYTICS_KEY   your Scamalytics API key
  ABUSEIPDB_KEY     AbuseIPDB free-tier key
"""

import os
import sys
from pathlib import Path
from typing import Callable, Optional

PEERINGDB_NET = "https://www.peeringdb.com/api/net"


def _note(msg: str) -> None:
    print(f"# provider: {msg}", file=sys.stderr)


# --- Geo databases ---------------------------------------------------------

def make_maxmind() -> Optional[Callable[[str], dict]]:
    db = os.environ.get("MAXMIND_DB")
    if not db:
        return None
    if not Path(db).exists():
        _note(f"MAXMIND_DB set but not found: {db}")
        return None
    try:
        import geoip2.database  # lazy
    except ImportError:
        _note("geoip2 not installed — `pip install .[maxmind]`")
        return None
    reader = geoip2.database.Reader(db)

    def lookup(ip: str) -> dict:
        r = reader.city(ip)
        sub = r.subdivisions.most_specific
        return {
            "country": r.country.name,
            "region": sub.name if sub else None,
            "city": r.city.name,
            "postal": r.postal.code,
            "latitude": r.location.latitude,
            "longitude": r.location.longitude,
            "timezone": r.location.time_zone,
        }

    return lookup


def make_ip2location() -> Optional[Callable[[str], dict]]:
    db = os.environ.get("IP2LOCATION_DB")
    if not db:
        return None
    if not Path(db).exists():
        _note(f"IP2LOCATION_DB set but not found: {db}")
        return None
    try:
        import IP2Location  # lazy
    except ImportError:
        _note("IP2Location not installed — `pip install .[ip2location]`")
        return None
    reader = IP2Location.IP2Location(db)

    def lookup(ip: str) -> dict:
        rec = reader.get_all(ip)

        def clean(v):
            # LITE DBs use these sentinels for fields absent at that tier.
            if not v or v in ("-", "This parameter is unavailable for free version. "
                              "Please upgrade to paid version."):
                return None
            return v

        return {
            "country": clean(getattr(rec, "country_long", None)),
            "region": clean(getattr(rec, "region", None)),
            "city": clean(getattr(rec, "city", None)),
            "postal": clean(getattr(rec, "zipcode", None)),
            "latitude": getattr(rec, "latitude", None),
            "longitude": getattr(rec, "longitude", None),
            "timezone": clean(getattr(rec, "timezone", None)),
        }

    return lookup


# --- ASN type (classifier signal) -----------------------------------------

def make_peeringdb(fetch_json: Callable[..., dict]) -> Callable[[int], Optional[str]]:
    """Return AS network type from PeeringDB (e.g. 'Cable/DSL/ISP', 'NSP',
    'Content', 'Enterprise'). No key required. Cached per ASN."""
    cache: dict[int, Optional[str]] = {}

    def lookup(asn: int) -> Optional[str]:
        if asn in cache:
            return cache[asn]
        result = None
        try:
            data = fetch_json(PEERINGDB_NET, params={"asn": asn}).get("data") or []
            if data:
                result = data[0].get("info_type") or None
        except Exception:  # noqa: BLE001 — enrichment, never fatal
            result = None
        cache[asn] = result
        return result

    return lookup


# --- Reputation ------------------------------------------------------------

def make_abuseipdb(fetch_json: Callable[..., dict]) -> Optional[Callable[[str], dict]]:
    key = os.environ.get("ABUSEIPDB_KEY")
    if not key:
        return None

    def check(ip: str) -> dict:
        data = fetch_json(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": ip, "maxAgeInDays": 90},
            headers={"Key": key, "Accept": "application/json"},
        )
        return data.get("data", {})

    return check


def make_scamalytics(fetch_json: Callable[..., dict]) -> Optional[Callable[[str], dict]]:
    base = os.environ.get("SCAMALYTICS_BASE")
    key = os.environ.get("SCAMALYTICS_KEY")
    if not base or not key:
        return None

    def check(ip: str) -> dict:
        data = fetch_json(base.rstrip("/") + "/", params={"key": key, "ip": ip})
        # The free API nests results under `scamalytics` in some tiers.
        inner = data.get("scamalytics") or data
        score = inner.get("scamalytics_score", inner.get("score"))
        risk = inner.get("scamalytics_risk", inner.get("risk"))
        return {"score": int(score) if score not in (None, "") else None,
                "risk": risk}

    return check
