from __future__ import annotations

"""Ownership section — RDAP (primary), with the fields WHOIS would also give.

RDAP returns structured JSON via the rdap.org bootstrap, which redirects to the
authoritative RIR. We parse the network object, its events, and its contact
entities (registrant / abuse / admin / tech), pulling names and emails out of
the jCard (vcardArray) format.
"""

from typing import Callable, Optional

from .models import Ownership

RDAP_BOOTSTRAP = "https://rdap.org/ip/{ip}"

_RIR_HINTS = {
    "arin": "ARIN",
    "ripe": "RIPE NCC",
    "apnic": "APNIC",
    "lacnic": "LACNIC",
    "afrinic": "AFRINIC",
}


def _vcard_field(vcard_array: list, name: str) -> Optional[str]:
    """Pull a single value (e.g. 'fn', 'email') out of a jCard array."""
    if not vcard_array or len(vcard_array) < 2:
        return None
    for entry in vcard_array[1]:
        if isinstance(entry, list) and entry and entry[0] == name:
            return entry[3] if len(entry) > 3 else None
    return None


def _find_entity(entities: list, role: str) -> Optional[dict]:
    """Depth-first search for the first entity holding `role` (abuse contacts
    are often nested inside the registrant entity)."""
    for ent in entities or []:
        if role in (ent.get("roles") or []):
            return ent
        nested = _find_entity(ent.get("entities") or [], role)
        if nested:
            return nested
    return None


def _contact(entities: list, role: str) -> tuple[Optional[str], Optional[str]]:
    ent = _find_entity(entities, role)
    if not ent:
        return None, None
    vcard = ent.get("vcardArray")
    return _vcard_field(vcard, "fn"), _vcard_field(vcard, "email")


def _event_date(events: list, action: str) -> Optional[str]:
    for ev in events or []:
        if ev.get("eventAction") == action:
            return ev.get("eventDate")
    return None


def _rir_from_links(data: dict) -> Optional[str]:
    haystack = (data.get("port43") or "").lower()
    for link in data.get("links") or []:
        if link.get("rel") == "self":
            haystack += " " + (link.get("href") or "").lower()
    for hint, name in _RIR_HINTS.items():
        if hint in haystack:
            return name
    return None


def _cidr(data: dict) -> Optional[str]:
    blocks = data.get("cidr0_cidrs") or []
    if blocks:
        b = blocks[0]
        prefix = b.get("v4prefix") or b.get("v6prefix")
        length = b.get("length")
        if prefix and length is not None:
            return f"{prefix}/{length}"
    start, end = data.get("startAddress"), data.get("endAddress")
    if start and end:
        return f"{start} - {end}"
    return None


def parse_rdap(data: dict) -> Ownership:
    entities = data.get("entities") or []
    _, abuse_email = _contact(entities, "abuse")
    admin_name, _ = _contact(entities, "administrative")
    tech_name, _ = _contact(entities, "technical")
    reg_name, reg_email = _contact(entities, "registrant")
    org = reg_name or _vcard_field(
        (_find_entity(entities, "registrant") or {}).get("vcardArray"), "org")

    return Ownership(
        network_name=data.get("name"),
        handle=data.get("handle"),
        cidr=_cidr(data),
        organization=org,
        rir=_rir_from_links(data),
        country=data.get("country"),
        allocation_status=data.get("type") or ", ".join(data.get("status") or []) or None,
        registered=_event_date(data.get("events"), "registration"),
        last_changed=_event_date(data.get("events"), "last changed"),
        abuse_email=abuse_email or reg_email,
        admin_contact=admin_name,
        tech_contact=tech_name,
        sources=["rdap"],
    )


def lookup(ip: str, fetch_json: Callable[[str], dict]) -> Ownership:
    try:
        data = fetch_json(RDAP_BOOTSTRAP.format(ip=ip))
    except Exception as e:  # noqa: BLE001 — degrade, never crash the report
        return Ownership(errors=[f"rdap lookup failed: {e}"])
    return parse_rdap(data)
