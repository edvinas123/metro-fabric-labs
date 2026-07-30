from site_test.fetcher import build_launch_options
from site_test.adapters.direct import HostAdapter
from site_test.adapters.retrieval import RetrievalApiAdapter
from site_test.models import RawResult

def test_launch_options_no_proxy():
    assert build_launch_options(None) == {"headless": True}

def test_launch_options_with_proxy():
    opts = build_launch_options("http://x:8000")
    assert opts["proxy"] == {"server": "http://x:8000"}
    assert opts["headless"] is True

def test_host_supports_only_its_geos():
    h = HostAdapter(name="server", geos=["US"])
    assert h.name == "server"
    assert h.kind == "direct"
    assert h.supports_geo("US") is True
    assert h.supports_geo("DE") is False

def test_host_picks_proxy_by_geo():
    h = HostAdapter(name="metro-host", geos=["US", "DE"],
                    proxies={"US": "http://us:8000", "DE": "http://de:8000"})
    assert h.supports_geo("DE") is True
    assert h.proxy_for("DE") == "http://de:8000"

def test_host_default_proxy_when_geo_absent():
    # proxy: null host -> egress from this machine's own IP (proxy_for returns None)
    h = HostAdapter(name="this-machine", geos=["US"], proxies={}, default_proxy=None)
    assert h.proxy_for("US") is None

def test_host_uses_fetch_fn():
    captured = {}
    def fake_fetch(url, proxy=None, timeout_ms=20000):
        captured["url"], captured["proxy"] = url, proxy
        return RawResult(status=200, html="ok", latency_ms=5, bytes=2)
    h = HostAdapter(name="metro-host", geos=["DE"], proxies={"DE": "http://de:8000"}, fetch_fn=fake_fetch)
    raw = h.fetch("https://x.test", "DE")
    assert raw.status == 200
    assert captured["proxy"] == "http://de:8000"

def test_retrieval_adapter_coverage():
    a = RetrievalApiAdapter(client=lambda url: "returned content")
    assert a.name == "retrieval_api"
    assert a.kind == "retrieval"
    assert a.supports_geo("anything") is True
    raw = a.fetch("https://x.test", "US")
    assert raw.html == "returned content"

def test_retrieval_adapter_no_coverage():
    a = RetrievalApiAdapter(client=lambda url: None)
    raw = a.fetch("https://x.test", "US")
    assert raw.html is None
