from site_test.models import Site, Oracle, RawResult
from site_test.runner import run_attempts

COSTS = {"datacenter": {"usd_per_gb": 0.0, "usd_per_req": 0.0},
         "residential": {"usd_per_gb": 8.0, "usd_per_req": 0.0},
         "retrieval_api": {"usd_per_gb": 0.0, "usd_per_req": 0.005}}

class FakeAdapter:
    def __init__(self, name, kind, geos, result):
        self.name, self.kind, self._geos, self._result = name, kind, geos, result
    def supports_geo(self, geo): return geo in self._geos
    def fetch(self, url, geo): return self._result

def make_site():
    return Site(id="s1", url="https://x.test", region="DE", gating_type="anti_fraud",
                requires_geo="DE", oracle=Oracle(type="regex", match="PRICE"))

def test_geo_unsupported_is_not_tested():
    site = make_site()
    dc = FakeAdapter("datacenter", "direct", geos=["US"],
                     result=RawResult(status=200, html="PRICE", latency_ms=5, bytes=5))
    attempts = run_attempts([site], [dc], COSTS, rate_limit_s=0)
    assert len(attempts) == 1
    assert attempts[0].outcome == "not_tested"
    assert attempts[0].cost_usd == 0.0

def test_direct_content_ok_scored_and_costed():
    site = make_site()
    isp = FakeAdapter("residential", "direct", geos=["DE"],
                      result=RawResult(status=200, html="the PRICE is here", latency_ms=7, bytes=1_073_741_824))
    attempts = run_attempts([site], [isp], COSTS, rate_limit_s=0)
    assert attempts[0].outcome == "content_ok"
    assert round(attempts[0].cost_usd, 4) == 8.0  # 1 GiB * $8

def test_retrieval_coverage_scored():
    site = make_site()
    ret = FakeAdapter("retrieval_api", "retrieval", geos=["DE"],
                      result=RawResult(status=200, html="some content", latency_ms=3, bytes=12))
    attempts = run_attempts([site], [ret], COSTS, rate_limit_s=0)
    assert attempts[0].outcome == "content_ok"
    assert attempts[0].cost_usd == 0.005

def test_block_page_scored_reachable():
    site = make_site()
    isp = FakeAdapter("residential", "direct", geos=["DE"],
                      result=RawResult(status=200, html="Just a moment...", latency_ms=7, bytes=15))
    attempts = run_attempts([site], [isp], COSTS, rate_limit_s=0)
    assert attempts[0].outcome == "reachable"

def test_bad_oracle_becomes_unreachable_not_crash():
    # Invalid CSS selector raises inside scoring; the run must record one errored
    # attempt, not abort the whole run.
    site = Site(id="s1", url="https://x.test", region="DE", gating_type="anti_fraud",
                requires_geo="DE", oracle=Oracle(type="css", match="::::"))
    isp = FakeAdapter("residential", "direct", geos=["DE"],
                      result=RawResult(status=200, html="<html><body>hi</body></html>", latency_ms=5, bytes=5))
    attempts = run_attempts([site], [isp], COSTS, rate_limit_s=0)
    assert attempts[0].outcome == "unreachable"
    assert attempts[0].notes.startswith("error:")

def test_rate_limit_throttles_same_domain(monkeypatch):
    import site_test.runner as R
    slept = []
    monkeypatch.setattr(R.time, "sleep", lambda s: slept.append(s))
    s1 = Site(id="a", url="https://dom.test/1", region="US", gating_type="long_tail",
              requires_geo="US", oracle=Oracle(type="regex", match="ok"))
    s2 = Site(id="b", url="https://dom.test/2", region="US", gating_type="long_tail",
              requires_geo="US", oracle=Oracle(type="regex", match="ok"))
    dc = FakeAdapter("datacenter", "direct", geos=["US"],
                     result=RawResult(status=200, html="ok", latency_ms=1, bytes=2))
    run_attempts([s1, s2], [dc], COSTS, rate_limit_s=5)
    assert any(x > 0 for x in slept)  # second same-domain hit was throttled
