from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import IntEnum
from typing import Optional
import json


class Tier(IntEnum):
    UNREACHABLE = 0
    REACHABLE = 1
    NOT_BLOCKED = 2
    CONTENT_OK = 3


# Non-ordinal outcomes (not part of the direct-fetch ladder)
NOT_TESTED = "not_tested"
NO_COVERAGE = "no_coverage"


def tier_to_outcome(tier: Tier) -> str:
    return tier.name.lower()


@dataclass
class RawResult:
    status: Optional[int]
    html: Optional[str]
    latency_ms: Optional[int]
    bytes: int = 0
    error: Optional[str] = None


@dataclass
class Oracle:
    type: str   # "css" | "regex"
    match: str


@dataclass
class Site:
    id: str
    url: str
    region: str
    gating_type: str
    requires_geo: str
    oracle: Oracle
    login_gated_stop: Optional[str] = None


@dataclass
class Attempt:
    site_id: str
    arm: str
    geo: str
    outcome: str
    latency_ms: Optional[int]
    bytes: int
    cost_usd: float
    ts: str
    notes: str = ""


def attempt_to_json(a: Attempt) -> str:
    return json.dumps(asdict(a))
