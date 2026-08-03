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
