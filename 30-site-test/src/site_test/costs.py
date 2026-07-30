from __future__ import annotations
from .models import RawResult

_GB = 1_073_741_824  # bytes in a GiB


def cost_for(arm: str, raw: RawResult, costs: dict) -> float:
    model = costs.get(arm)
    if not model:
        return 0.0
    per_req = model.get("usd_per_req", 0.0)
    per_gb = model.get("usd_per_gb", 0.0)
    return per_req + per_gb * (raw.bytes / _GB)
