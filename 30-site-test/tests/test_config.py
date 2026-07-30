from pathlib import Path
from site_test.config import load_sites, load_costs, load_egress
from site_test.models import Site

DATA = Path(__file__).parents[1] / "data"

def test_load_sites_returns_site_objects():
    sites = load_sites(DATA / "sites.yaml")
    assert all(isinstance(s, Site) for s in sites)
    by_id = {s.id: s for s in sites}
    assert by_id["httpbin-html"].oracle.type == "regex"
    assert by_id["example-shop-de"].requires_geo == "DE"

def test_load_costs():
    costs = load_costs(DATA / "costs.yaml")
    assert costs["isp_proxy"]["usd_per_gb"] == 8.0
    assert costs["retrieval_api"]["usd_per_req"] == 0.005

def test_load_egress():
    eg = load_egress(DATA / "egress.yaml")
    assert eg["isp_proxy"]["geos"] == ["US", "DE"]
    assert eg["datacenter"]["proxy"] is None
