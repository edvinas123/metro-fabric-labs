from site_test.models import RawResult
from site_test.costs import cost_for

COSTS = {
    "datacenter":    {"usd_per_gb": 0.0, "usd_per_req": 0.0},
    "isp_proxy":     {"usd_per_gb": 8.0, "usd_per_req": 0.0},
    "retrieval_api": {"usd_per_gb": 0.0, "usd_per_req": 0.005},
}

def test_isp_proxy_cost_by_bytes():
    raw = RawResult(status=200, html="x", latency_ms=10, bytes=1_000_000)  # ~1MB
    # 1MB = 1/1024 GB * $8 = 0.0078125
    assert round(cost_for("isp_proxy", raw, COSTS), 6) == round(8.0 * (1_000_000 / 1_073_741_824), 6)

def test_retrieval_cost_per_req():
    raw = RawResult(status=200, html="x", latency_ms=10, bytes=50)
    assert cost_for("retrieval_api", raw, COSTS) == 0.005

def test_datacenter_zero():
    raw = RawResult(status=200, html="x", latency_ms=10, bytes=999999)
    assert cost_for("datacenter", raw, COSTS) == 0.0

def test_unknown_arm_zero():
    raw = RawResult(status=200, html="x", latency_ms=10, bytes=10)
    assert cost_for("mystery", raw, COSTS) == 0.0
