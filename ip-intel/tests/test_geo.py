from ip_intel import geo
from ip_intel.geo import parse_ipapi


def test_parses_ipapi(fake_fetch_json):
    g = geo.lookup("8.8.8.8", fake_fetch_json)
    assert g.country == "United States"
    assert g.city == "Ashburn"
    assert g.latitude == 39.03
    assert g.connection_type == "hosting"
    assert "ip-api" in g.sources
    assert "ipwho.is" in g.sources
    assert g.disagreements == []


def test_flags_country_disagreement():
    def fetch(url, params=None, headers=None):
        if "ip-api" in url:
            return {"status": "success", "country": "United States"}
        return {"success": True, "country": "Canada"}
    g = geo.lookup("8.8.8.8", fetch)
    assert g.disagreements
    assert "ip-api=United States" in g.disagreements[0]


def test_failed_status_records_error():
    g = parse_ipapi({"status": "fail", "message": "reserved range"})
    assert g.country is None
    assert g.errors and "reserved range" in g.errors[0]


def test_parses_asn_and_proxy(fake_fetch_json):
    g = geo.lookup("8.8.8.8", fake_fetch_json)
    assert g.asn == 15169          # from ip-api "as": "AS15169 Google LLC"
    assert g.postal is None or isinstance(g.postal, str)
    assert g.proxy_vpn is False


def test_maxmind_and_ip2location_merge_and_disagree():
    def fetch(url, params=None, headers=None):
        if "ip-api" in url:
            return {"status": "success", "country": "United States"}
        return {"success": True, "country": "United States"}
    mm = lambda ip: {"country": "United States", "city": "Mountain View",
                     "postal": "94043"}
    i2l = lambda ip: {"country": "Canada"}   # deliberately conflicting
    g = geo.lookup("8.8.8.8", fetch, maxmind=mm, ip2location=i2l)
    assert g.city == "Mountain View"         # filled from maxmind
    assert set(g.by_source) == {"ip-api", "ipwho.is", "maxmind", "ip2location"}
    assert any("ip2location=Canada" in d for d in g.disagreements)


def test_registrant_country_crosscheck():
    def fetch(url, params=None, headers=None):
        if "ip-api" in url:
            return {"status": "success", "country": "United States"}
        return {"success": True, "country": "United States"}
    g = geo.lookup("8.8.8.8", fetch, registrant_country="Germany")
    assert any("registrant=Germany" in d for d in g.disagreements)
