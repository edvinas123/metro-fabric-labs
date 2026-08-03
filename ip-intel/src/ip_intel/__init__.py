"""ip-intel — IP information report from free public sources.

Four sections: ownership (RDAP/WHOIS), abuse (blocklists + contacts + reputation),
geolocation (multi-provider), announcement (BGP routing / RPKI).

The `report()` entrypoint fans out the four lookups, reconciles cross-source
conflicts, and returns an `IPReport`. Every source function accepts an injectable
client so the whole pipeline is testable offline against recorded fixtures.
"""
from .models import IPReport, Ownership, Abuse, Geo, Announcement, OriginClass
from .report import build_report

__all__ = [
    "IPReport",
    "Ownership",
    "Abuse",
    "Geo",
    "Announcement",
    "OriginClass",
    "build_report",
]
