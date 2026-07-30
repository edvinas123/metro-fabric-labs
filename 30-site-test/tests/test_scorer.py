from pathlib import Path
from site_test.models import Tier, RawResult, Oracle
from site_test.scorer import is_block_page, oracle_matches, score_direct, score_retrieval

FIX = Path(__file__).parent / "fixtures"
def load(name): return (FIX / name).read_text()

ORACLE = Oracle(type="css", match="div.product-price")

def test_real_content_scores_content_ok():
    raw = RawResult(status=200, html=load("real_content.html"), latency_ms=100, bytes=100)
    assert score_direct(raw, ORACLE) == Tier.CONTENT_OK

def test_cloudflare_challenge_scores_reachable_not_content():
    raw = RawResult(status=200, html=load("cloudflare_challenge.html"), latency_ms=100, bytes=100)
    assert is_block_page(raw.html) is True
    assert score_direct(raw, ORACLE) == Tier.REACHABLE

def test_datadome_block_scores_reachable():
    raw = RawResult(status=200, html=load("datadome_block.html"), latency_ms=100, bytes=100)
    assert score_direct(raw, ORACLE) == Tier.REACHABLE

def test_geo_wall_scores_reachable():
    raw = RawResult(status=200, html=load("geo_wall.html"), latency_ms=100, bytes=100)
    assert score_direct(raw, ORACLE) == Tier.REACHABLE

def test_not_blocked_but_no_oracle_match():
    html = "<html><body><p>hello, no price here</p></body></html>"
    raw = RawResult(status=200, html=html, latency_ms=100, bytes=100)
    assert score_direct(raw, ORACLE) == Tier.NOT_BLOCKED

def test_error_scores_unreachable():
    raw = RawResult(status=None, html=None, latency_ms=None, error="timeout")
    assert score_direct(raw, ORACLE) == Tier.UNREACHABLE

def test_regex_oracle():
    o = Oracle(type="regex", match=r"In stock")
    raw = RawResult(status=200, html=load("real_content.html"), latency_ms=100, bytes=100)
    assert score_direct(raw, o) == Tier.CONTENT_OK

def test_retrieval_coverage():
    assert score_retrieval(RawResult(status=200, html="usable content", latency_ms=50)) == "content_ok"
    assert score_retrieval(RawResult(status=200, html="", latency_ms=50)) == "no_coverage"
    assert score_retrieval(RawResult(status=None, html=None, latency_ms=None, error="no result")) == "no_coverage"
