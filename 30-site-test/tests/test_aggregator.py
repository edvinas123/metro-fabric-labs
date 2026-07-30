from site_test.models import Attempt
from site_test.aggregator import aggregate

def test_rates_exclude_not_tested():
    rows = [
        Attempt(site_id="a", arm="datacenter", geo="DE", outcome="content_ok", latency_ms=1, bytes=1, cost_usd=0.0, ts="t"),
        Attempt(site_id="b", arm="datacenter", geo="DE", outcome="reachable",  latency_ms=1, bytes=1, cost_usd=0.0, ts="t"),
        Attempt(site_id="c", arm="datacenter", geo="US", outcome="not_tested", latency_ms=None, bytes=0, cost_usd=0.0, ts="t"),
    ]
    sc = aggregate(rows)
    dc = sc["arms"]["datacenter"]
    assert dc["tested"] == 2                 # not_tested excluded
    assert dc["content_ok"] == 1
    assert dc["content_ok_rate"] == 0.5

def test_cost_per_success():
    rows = [
        Attempt(site_id="a", arm="isp_proxy", geo="DE", outcome="content_ok", latency_ms=1, bytes=1, cost_usd=0.01, ts="t"),
        Attempt(site_id="b", arm="isp_proxy", geo="DE", outcome="reachable",  latency_ms=1, bytes=1, cost_usd=0.01, ts="t"),
    ]
    sc = aggregate(rows)
    isp = sc["arms"]["isp_proxy"]
    # total cost 0.02 over 1 content_ok = 0.02
    assert round(isp["cost_per_content_ok"], 4) == 0.02

def test_coverage_gap_for_retrieval():
    rows = [
        Attempt(site_id="a", arm="retrieval_api", geo="DE", outcome="content_ok", latency_ms=1, bytes=1, cost_usd=0.005, ts="t"),
        Attempt(site_id="b", arm="retrieval_api", geo="DE", outcome="no_coverage", latency_ms=None, bytes=0, cost_usd=0.005, ts="t"),
    ]
    sc = aggregate(rows)
    assert sc["coverage_gap"]["no_coverage"] == 1
    assert sc["coverage_gap"]["tested"] == 2
    assert sc["coverage_gap"]["gap_rate"] == 0.5
