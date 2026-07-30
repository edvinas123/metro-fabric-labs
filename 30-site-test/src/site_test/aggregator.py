from __future__ import annotations
from .models import Attempt, NOT_TESTED, NO_COVERAGE

DIRECT_TIERS = ["unreachable", "reachable", "not_blocked", "content_ok"]


def aggregate(attempts: list[Attempt]) -> dict:
    arms: dict[str, dict] = {}
    for a in attempts:
        arm = arms.setdefault(a.arm, {"tested": 0, "not_tested": 0, "total_cost": 0.0,
                                      **{t: 0 for t in DIRECT_TIERS}})
        if a.outcome == NOT_TESTED:
            arm["not_tested"] += 1
            continue
        arm["tested"] += 1
        arm["total_cost"] += a.cost_usd
        if a.outcome in DIRECT_TIERS:
            arm[a.outcome] += 1
    # derive rates
    for arm in arms.values():
        tested = arm["tested"] or 0
        arm["content_ok_rate"] = (arm["content_ok"] / tested) if tested else 0.0
        arm["cost_per_content_ok"] = (arm["total_cost"] / arm["content_ok"]) if arm["content_ok"] else None

    # coverage gap = retrieval_api no_coverage share
    ret = [a for a in attempts if a.arm == "retrieval_api" and a.outcome != NOT_TESTED]
    no_cov = sum(1 for a in ret if a.outcome == NO_COVERAGE)
    coverage_gap = {
        "tested": len(ret),
        "no_coverage": no_cov,
        "gap_rate": (no_cov / len(ret)) if ret else 0.0,
    }
    return {"arms": arms, "coverage_gap": coverage_gap}
