from ip_intel.classify import classify
from ip_intel.models import (Abuse, Geo, Ownership, ISP_ORG, DATACENTER,
                             MOBILE, RESERVED, UNKNOWN)


def test_hosting_flag_is_datacenter():
    oc = classify(Ownership(organization="Google LLC"),
                  Geo(connection_type="hosting", isp="Google LLC"),
                  Abuse())
    assert oc.kind == DATACENTER
    assert oc.confidence == "high"


def test_isp_keywords_are_isp_org():
    oc = classify(Ownership(organization="Comcast Cable Communications"),
                  Geo(isp="Comcast Cable"), Abuse())
    assert oc.kind == ISP_ORG
    assert "trust anchor" in oc.trust_note


def test_datacenter_keywords():
    oc = classify(Ownership(organization="Hetzner Online GmbH"),
                  Geo(isp="Hetzner"), Abuse())
    assert oc.kind == DATACENTER


def test_mobile():
    oc = classify(Ownership(organization="T-Mobile USA"),
                  Geo(connection_type="mobile"), Abuse())
    assert oc.kind == MOBILE


def test_bogon_is_reserved():
    oc = classify(Ownership(), Geo(), Abuse(is_bogon=True, special_use="private"))
    assert oc.kind == RESERVED
    assert oc.confidence == "high"


def test_no_signal_is_unknown():
    oc = classify(Ownership(organization="Acme Widgets Inc"),
                  Geo(isp="Acme"), Abuse())
    assert oc.kind == UNKNOWN
    assert oc.confidence == "low"


def test_peeringdb_isp_type_wins():
    oc = classify(Ownership(organization="Acme"), Geo(), Abuse(),
                  peeringdb_type="Cable/DSL/ISP")
    assert oc.kind == ISP_ORG
    assert oc.confidence == "high"


def test_peeringdb_content_type_is_datacenter():
    # RAKsmart / AS54600 case: PeeringDB info_type 'Content'.
    oc = classify(Ownership(organization="PEG TECH INC"),
                  Geo(isp="PEG TECH INC"), Abuse(), peeringdb_type="Content")
    assert oc.kind == DATACENTER
    assert oc.confidence == "high"


def test_proxy_flag_is_datacenter():
    # No PeeringDB type, no hosting flag, but proxy=True (the 108.186.55.1 case).
    oc = classify(Ownership(organization="PEG TECH INC"),
                  Geo(isp="PEG TECH INC", proxy_vpn=True), Abuse())
    assert oc.kind == DATACENTER
    assert "proxy/VPN" in oc.rationale


def test_hosting_brand_keyword_fallback():
    # Even with no flags/PeeringDB, known hosting brands now match keywords.
    oc = classify(Ownership(organization="RAKsmart"),
                  Geo(isp="RAKsmart"), Abuse())
    assert oc.kind == DATACENTER
