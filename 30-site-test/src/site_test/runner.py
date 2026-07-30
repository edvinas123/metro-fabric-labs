from __future__ import annotations
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from .models import Site, Attempt, NOT_TESTED, tier_to_outcome
from .scorer import score_direct, score_retrieval
from .costs import cost_for


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_attempts(sites: list[Site], adapters: list, costs: dict,
                 rate_limit_s: float = 2.0) -> list[Attempt]:
    attempts: list[Attempt] = []
    last_hit: dict[str, float] = {}
    for site in sites:
        geo = site.requires_geo
        for adapter in adapters:
            if not adapter.supports_geo(geo):
                attempts.append(Attempt(
                    site_id=site.id, arm=adapter.name, geo=geo, outcome=NOT_TESTED,
                    latency_ms=None, bytes=0, cost_usd=0.0, ts=_now_iso(),
                    notes="no live egress for this geo"))
                continue
            # per-domain rate limit (skip when rate_limit_s == 0, e.g. tests)
            domain = urlparse(site.url).netloc
            if rate_limit_s:
                wait = rate_limit_s - (time.monotonic() - last_hit.get(domain, 0.0))
                if wait > 0:
                    time.sleep(wait)
                last_hit[domain] = time.monotonic()
            raw = adapter.fetch(site.url, geo)
            if getattr(adapter, "kind", "direct") == "retrieval":
                outcome = score_retrieval(raw)
            else:
                outcome = tier_to_outcome(score_direct(raw, site.oracle))
            attempts.append(Attempt(
                site_id=site.id, arm=adapter.name, geo=geo, outcome=outcome,
                latency_ms=raw.latency_ms, bytes=raw.bytes,
                cost_usd=cost_for(adapter.name, raw, costs), ts=_now_iso(),
                notes=raw.error or ""))
    return attempts
