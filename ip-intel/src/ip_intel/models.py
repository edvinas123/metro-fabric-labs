from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


# --- Section models --------------------------------------------------------
# Each section carries the source(s) it came from and any non-fatal errors, so
# the rendered report can cite provenance and degrade gracefully when a source
# is unreachable. A field left None means "not determined", never "guessed".


@dataclass
class Ownership:
    """Who the IP is registered to (RDAP, WHOIS fallback)."""
    network_name: Optional[str] = None      # RDAP `name`
    handle: Optional[str] = None
    cidr: Optional[str] = None              # allocated block covering the IP
    organization: Optional[str] = None
    rir: Optional[str] = None               # ARIN / RIPE / APNIC / LACNIC / AFRINIC
    country: Optional[str] = None           # registrant country
    allocation_status: Optional[str] = None
    registered: Optional[str] = None        # registration event date
    last_changed: Optional[str] = None
    abuse_email: Optional[str] = None
    admin_contact: Optional[str] = None
    tech_contact: Optional[str] = None
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Abuse:
    """Reputation, blocklist membership, and who to report abuse to."""
    abuse_email: Optional[str] = None
    reverse_dns: Optional[str] = None
    forward_confirmed: Optional[bool] = None
    blocklists_listed: list[str] = field(default_factory=list)   # DNSBLs that list it
    blocklists_checked: list[str] = field(default_factory=list)
    tor_exit_node: Optional[bool] = None
    is_bogon: bool = False
    special_use: Optional[str] = None       # e.g. "private", "reserved", "loopback"
    abuse_confidence: Optional[int] = None  # AbuseIPDB score 0-100 (if key present)
    report_categories: list[str] = field(default_factory=list)
    fraud_score: Optional[int] = None       # Scamalytics 0-100 (if key present)
    fraud_risk: Optional[str] = None         # Scamalytics risk band (low/medium/high/very high)
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Geo:
    """Approximate geographic location. Multi-source; may disagree."""
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    postal: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    org: Optional[str] = None
    asn: Optional[int] = None
    connection_type: Optional[str] = None   # hosting / mobile / residential when known
    proxy_vpn: Optional[bool] = None        # proxy / VPN / anonymizer flag
    by_source: dict[str, str] = field(default_factory=dict)  # provider -> country
    disagreements: list[str] = field(default_factory=list)  # cross-source conflicts
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Announcement:
    """How the covering prefix is announced in BGP right now."""
    announced: Optional[bool] = None
    prefix: Optional[str] = None
    origin_asn: Optional[int] = None
    as_name: Optional[str] = None
    rpki_status: Optional[str] = None       # valid / invalid / unknown
    visibility: Optional[int] = None        # collector peers seeing the route
    upstreams: list[int] = field(default_factory=list)
    more_specifics: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Origin classification — the Metro Fabric value-add (design principle #6:
# "ISP-ORG is the trust anchor"). Heuristic, clearly labelled as such.
ISP_ORG = "isp_org"
DATACENTER = "datacenter"
MOBILE = "mobile"
RESERVED = "reserved"
UNKNOWN = "unknown"


@dataclass
class OriginClass:
    kind: str = UNKNOWN          # one of the constants above
    confidence: str = "low"      # low / medium / high
    rationale: str = ""          # human-readable why
    trust_note: str = ""         # what this means for a Certificate of Origin


@dataclass
class IPReport:
    ip: str
    generated_at: str
    ownership: Ownership = field(default_factory=Ownership)
    abuse: Abuse = field(default_factory=Abuse)
    geo: Geo = field(default_factory=Geo)
    announcement: Announcement = field(default_factory=Announcement)
    origin: OriginClass = field(default_factory=OriginClass)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
