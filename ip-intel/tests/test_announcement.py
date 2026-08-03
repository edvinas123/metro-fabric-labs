from ip_intel import announcement


def test_parses_bgp_chain(fake_fetch_json):
    a = announcement.lookup("8.8.8.8", fake_fetch_json)
    assert a.announced is True
    assert a.prefix == "8.8.8.0/24"
    assert a.origin_asn == 15169
    assert a.as_name == "GOOGLE, US"
    assert a.rpki_status == "valid"
    assert a.visibility == 300
    assert a.errors == []


def test_not_announced_when_no_prefix():
    def fetch(url, params=None, headers=None):
        return {"data": {"prefix": None, "asns": []}}
    a = announcement.lookup("192.0.2.1", fetch)
    assert a.announced is False
    assert any("no covering prefix" in e for e in a.errors)
