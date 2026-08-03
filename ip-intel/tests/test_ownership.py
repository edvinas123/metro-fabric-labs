from ip_intel import ownership


def test_parses_rdap(fake_fetch_json):
    o = ownership.lookup("8.8.8.8", fake_fetch_json)
    assert o.network_name == "GOGL"
    assert o.cidr == "8.8.8.0/24"
    assert o.rir == "ARIN"
    assert o.country == "US"
    assert o.organization == "Google LLC"
    assert o.abuse_email == "network-abuse@google.com"
    assert o.admin_contact == "Google LLC Admin"
    assert o.tech_contact == "Google LLC Tech"
    assert o.registered == "2014-03-14T00:00:00Z"
    assert "rdap" in o.sources
    assert o.errors == []


def test_degrades_on_fetch_error():
    def boom(url, params=None, headers=None):
        raise RuntimeError("network down")
    o = ownership.lookup("8.8.8.8", boom)
    assert o.network_name is None
    assert o.errors and "rdap lookup failed" in o.errors[0]
