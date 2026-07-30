from __future__ import annotations
from .models import RawResult

# Bandwidth is billed per GiB (2^30 bytes). The costs.yaml key is named
# `usd_per_gb` for brevity; it means dollars per GiB, matching this constant.
_GB = 1_073_741_824


def cost_for(arm: str, raw: RawResult, costs: dict) -> float:
    model = costs.get(arm)
    if not model:
        return 0.0
    per_req = model.get("usd_per_req", 0.0)
    per_gb = model.get("usd_per_gb", 0.0)
    return per_req + per_gb * (raw.bytes / _GB)
