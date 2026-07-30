import pytest
from site_test.connectors import build_host, ConnectorError

def test_local_connector_no_proxy():
    h = build_host("laptop", {"connector": "local", "geos": ["US"]})
    assert h.name == "laptop"
    assert h.supports_geo("US")
    assert h.proxy_for("US") is None

def test_http_proxy_connector():
    h = build_host("aws", {"connector": "http_proxy", "geos": ["US"],
                           "proxies": {"US": "http://u:8000"}})
    assert h.proxy_for("US") == "http://u:8000"

def test_default_connector_inferred_local():
    h = build_host("m", {"geos": ["US"]})
    assert h.proxy_for("US") is None

def test_default_connector_inferred_http_proxy():
    h = build_host("m", {"geos": ["US"], "proxies": {"US": "http://x"}})
    assert h.proxy_for("US") == "http://x"

def test_unknown_connector_errors():
    with pytest.raises(ConnectorError):
        build_host("m", {"connector": "nope", "geos": ["US"]})

def test_metro_requires_api_key_env_when_declared(monkeypatch):
    monkeypatch.delenv("METRO_API_KEY", raising=False)
    with pytest.raises(ConnectorError):
        build_host("metro", {"connector": "metro", "geos": ["US"],
                             "api_key_env": "METRO_API_KEY",
                             "endpoints": {"US": "http://us:8000"}})

def test_metro_builds_host_with_endpoints(monkeypatch):
    monkeypatch.setenv("METRO_API_KEY", "secret")
    h = build_host("metro", {"connector": "metro", "geos": ["US", "DE"],
                             "api_key_env": "METRO_API_KEY",
                             "endpoints": {"US": "http://us:8000", "DE": "http://de:8000"}})
    assert h.supports_geo("DE")
    assert h.proxy_for("US") == "http://us:8000"

def test_metro_missing_endpoint_for_geo(monkeypatch):
    monkeypatch.setenv("METRO_API_KEY", "secret")
    with pytest.raises(ConnectorError):
        build_host("metro", {"connector": "metro", "geos": ["US", "DE"],
                             "api_key_env": "METRO_API_KEY",
                             "endpoints": {"US": "http://us:8000"}})

def test_metro_without_key_env_ok_for_ip_allowlisted(monkeypatch):
    # api_key_env is optional; omit it for an IP-allowlisted endpoint (no inline key)
    h = build_host("metro", {"connector": "metro", "geos": ["US"],
                             "endpoints": {"US": "http://us:8000"}})
    assert h.proxy_for("US") == "http://us:8000"
