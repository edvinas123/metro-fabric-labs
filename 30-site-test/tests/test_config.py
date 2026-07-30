from pathlib import Path
from site_test.config import load_sites, load_costs, load_egress
from site_test.models import Site

DATA = Path(__file__).parents[1] / "data"

def test_load_sites_returns_site_objects():
    sites = load_sites(DATA / "sites.yaml")
    assert len(sites) == 30
    assert all(isinstance(s, Site) for s in sites)
    by_id = {s.id: s for s in sites}
    assert by_id["httpbin-html"].oracle.type == "regex"
    assert by_id["zalando-de"].requires_geo == "DE"
    # login-gated sites carry the at-wall stop marker
    assert by_id["linkedin"].login_gated_stop == "at_wall"
    # all five gating categories are represented
    assert {s.gating_type for s in sites} == {
        "geo_restricted", "anti_fraud", "login_gated", "publisher_cdn", "long_tail"}

def test_load_costs():
    costs = load_costs(DATA / "costs.yaml")
    assert costs["metro"]["usd_per_gb"] == 8.0
    assert costs["retrieval_api"]["usd_per_req"] == 0.005

def test_load_egress():
    eg = load_egress(DATA / "egress.yaml")
    assert eg["hosts"]["metro"]["geos"] == ["US", "DE"]
    assert eg["hosts"]["metro"]["connector"] == "metro"
    assert eg["hosts"]["this-machine"]["connector"] == "local"
