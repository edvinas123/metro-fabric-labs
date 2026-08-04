from ip_intel import abuse
from tests.conftest import FakeDns


def test_clean_ip(fake_dns, tor_get):
    a = abuse.lookup("8.8.8.8", dns=fake_dns, tor_get=tor_get,
                     abuse_email="network-abuse@google.com")
    assert a.abuse_email == "network-abuse@google.com"
    assert a.reverse_dns == "dns.google"
    assert a.forward_confirmed is True
    assert a.blocklists_listed == []
    assert set(a.blocklists_checked) == {"spamhaus-zen", "spamcop", "barracuda"}
    assert a.tor_exit_node is False
    assert a.is_bogon is False


def test_listed_and_tor(tor_get):
    # DNS that lists the IP on spamhaus + a tor list containing it.
    rev_zone = "5.64.129.23.zen.spamhaus.org"
    dns = FakeDns(listed={rev_zone}, ptr=None)
    a = abuse.lookup("23.129.64.5", dns=dns, tor_get=tor_get)
    assert "spamhaus-zen" in a.blocklists_listed
    assert a.tor_exit_node is True


def test_bogon_short_circuits(tor_get):
    a = abuse.lookup("10.0.0.1", dns=FakeDns(ptr=None), tor_get=tor_get)
    assert a.is_bogon is True
    assert a.special_use == "private"
    assert a.blocklists_checked == []      # no public lookups for private space
    assert a.tor_exit_node is None


def test_abuseipdb_enrichment(fake_dns, tor_get):
    def check(ip):
        return {"abuseConfidenceScore": 42, "totalReports": 7}
    a = abuse.lookup("8.8.8.8", dns=fake_dns, tor_get=tor_get, abuseipdb=check)
    assert a.abuse_confidence == 42
    assert any("7 reports" in c for c in a.report_categories)


def test_scamalytics_enrichment(fake_dns, tor_get):
    def scam(ip):
        return {"score": 63, "risk": "high"}
    a = abuse.lookup("8.8.8.8", dns=fake_dns, tor_get=tor_get, scamalytics=scam)
    assert a.fraud_score == 63
    assert a.fraud_risk == "high"
    assert "scamalytics" in a.sources


def test_ipqs_fills_fraud_when_scamalytics_absent(fake_dns, tor_get):
    a = abuse.lookup("8.8.8.8", dns=fake_dns, tor_get=tor_get,
                     ipqs=lambda ip: {"score": 88, "proxy": True})
    assert a.fraud_score == 88
    assert "ipqs" in a.sources


def test_scamalytics_wins_over_ipqs(fake_dns, tor_get):
    a = abuse.lookup("8.8.8.8", dns=fake_dns, tor_get=tor_get,
                     scamalytics=lambda ip: {"score": 10, "risk": "low"},
                     ipqs=lambda ip: {"score": 88})
    assert a.fraud_score == 10        # scamalytics ran first; ipqs doesn't overwrite


def test_greynoise_enrichment(fake_dns, tor_get):
    a = abuse.lookup("8.8.8.8", dns=fake_dns, tor_get=tor_get,
                     greynoise=lambda ip: {"classification": "benign", "name": "Google"})
    assert a.greynoise_class == "benign"
    assert a.greynoise_name == "Google"
    assert "greynoise" in a.sources


def test_shodan_exposure(fake_dns, tor_get):
    a = abuse.lookup("8.8.8.8", dns=fake_dns, tor_get=tor_get,
                     shodan=lambda ip: {"ports": [53, 443], "tags": ["cloud"]})
    assert a.open_ports == [53, 443]
    assert a.exposure_tags == ["cloud"]
    assert "shodan" in a.sources
