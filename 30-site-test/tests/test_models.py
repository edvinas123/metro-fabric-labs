from site_test.models import Tier, tier_to_outcome, Attempt, attempt_to_json, Oracle, Site
import json

def test_tier_ordering():
    assert Tier.UNREACHABLE < Tier.REACHABLE < Tier.NOT_BLOCKED < Tier.CONTENT_OK

def test_tier_to_outcome_lowercases():
    assert tier_to_outcome(Tier.CONTENT_OK) == "content_ok"
    assert tier_to_outcome(Tier.NOT_BLOCKED) == "not_blocked"

def test_attempt_to_json_roundtrip():
    a = Attempt(site_id="s1", arm="datacenter", geo="DE", outcome="content_ok",
                latency_ms=812, bytes=48211, cost_usd=0.0, ts="2026-07-29T20:10:00Z", notes="ok")
    line = attempt_to_json(a)
    parsed = json.loads(line)
    assert parsed["site_id"] == "s1"
    assert parsed["outcome"] == "content_ok"
    assert parsed["cost_usd"] == 0.0

def test_site_holds_oracle():
    s = Site(id="s1", url="https://x.test", region="DE", gating_type="anti_fraud",
             requires_geo="DE", oracle=Oracle(type="css", match="div.price"))
    assert s.oracle.type == "css"
    assert s.login_gated_stop is None
