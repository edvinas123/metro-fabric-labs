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
