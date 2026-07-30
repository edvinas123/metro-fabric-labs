from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import urlparse
from .models import Site, Attempt, NOT_TESTED, NO_COVERAGE, tier_to_outcome
from .scorer import score_direct, score_retrieval
from .costs import cost_for


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_attempts(sites: list[Site], adapters: list, costs: dict,
                 rate_limit_s: float = 2.0,
                 on_attempt: Optional[Callable[[Attempt], None]] = None) -> list[Attempt]:
    """Run every (site x adapter). `on_attempt`, if given, is called with each
    Attempt as soon as it completes — used to stream results to disk so a crash
    mid-run keeps everything already measured. A failing fetch/oracle is recorded
    as an errored attempt for that one combo, never allowed to abort the run."""
    attempts: list[Attempt] = []
    last_hit: dict[str, float] = {}

    def emit(a: Attempt) -> None:
        attempts.append(a)
        if on_attempt:
            on_attempt(a)

    for site in sites:
        geo = site.requires_geo
        for adapter in adapters:
            is_retrieval = getattr(adapter, "kind", "direct") == "retrieval"
            if not adapter.supports_geo(geo):
                emit(Attempt(
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
            try:
                raw = adapter.fetch(site.url, geo)
                if is_retrieval:
                    outcome = score_retrieval(raw)
                else:
                    outcome = tier_to_outcome(score_direct(raw, site.oracle))
                emit(Attempt(
                    site_id=site.id, arm=adapter.name, geo=geo, outcome=outcome,
                    latency_ms=raw.latency_ms, bytes=raw.bytes,
                    cost_usd=cost_for(adapter.name, raw, costs), ts=_now_iso(),
                    notes=raw.error or ""))
            except Exception as e:  # one combo failing must not abort the whole run
                emit(Attempt(
                    site_id=site.id, arm=adapter.name, geo=geo,
                    outcome=(NO_COVERAGE if is_retrieval else "unreachable"),
                    latency_ms=None, bytes=0, cost_usd=0.0, ts=_now_iso(),
                    notes=f"error: {e}"))
    return attempts
