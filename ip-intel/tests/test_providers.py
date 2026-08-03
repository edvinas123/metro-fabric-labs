from ip_intel import providers


def test_peeringdb_returns_info_type_and_caches():
    calls = []

    def fetch(url, params=None, headers=None):
        calls.append(params["asn"])
        return {"data": [{"info_type": "Content", "name": "RAKsmart"}]}

    pdb = providers.make_peeringdb(fetch)
    assert pdb(54600) == "Content"
    assert pdb(54600) == "Content"      # cached
    assert calls == [54600]             # fetched once


def test_peeringdb_missing_asn_is_none():
    pdb = providers.make_peeringdb(lambda url, params=None, headers=None: {"data": []})
    assert pdb(99999) is None


def test_scamalytics_disabled_without_env(monkeypatch):
    monkeypatch.delenv("SCAMALYTICS_BASE", raising=False)
    monkeypatch.delenv("SCAMALYTICS_KEY", raising=False)
    assert providers.make_scamalytics(lambda *a, **k: {}) is None


def test_scamalytics_parses_flat_and_nested(monkeypatch):
    monkeypatch.setenv("SCAMALYTICS_BASE", "https://api11.scamalytics.com/user")
    monkeypatch.setenv("SCAMALYTICS_KEY", "k")

    flat = providers.make_scamalytics(
        lambda url, params=None, headers=None: {"score": "63", "risk": "high"})
    assert flat("1.2.3.4") == {"score": 63, "risk": "high"}

    nested = providers.make_scamalytics(
        lambda url, params=None, headers=None: {
            "scamalytics": {"scamalytics_score": "10", "scamalytics_risk": "low"}})
    assert nested("1.2.3.4") == {"score": 10, "risk": "low"}


def test_geo_dbs_disabled_without_env(monkeypatch):
    monkeypatch.delenv("MAXMIND_DB", raising=False)
    monkeypatch.delenv("IP2LOCATION_DB", raising=False)
    assert providers.make_maxmind() is None
    assert providers.make_ip2location() is None


def test_abuseipdb_disabled_without_env(monkeypatch):
    monkeypatch.delenv("ABUSEIPDB_KEY", raising=False)
    assert providers.make_abuseipdb(lambda *a, **k: {}) is None
