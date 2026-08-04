import json

import pytest

from ip_intel.report import (build_report, render_markdown, render_json,
                             render_html, render_dashboard)
from ip_intel.whoami import whoami
from ip_intel.models import DATACENTER


def _report(fake_fetch_json, fake_dns, tor_get):
    return build_report("8.8.8.8", fetch_json=fake_fetch_json, dns=fake_dns,
                        tor_get=tor_get, now="2026-08-03T00:00:00Z")


def test_build_report_end_to_end(fake_fetch_json, fake_dns, tor_get):
    r = _report(fake_fetch_json, fake_dns, tor_get)
    assert r.ip == "8.8.8.8"
    assert r.ownership.organization == "Google LLC"
    assert r.geo.country == "United States"
    assert r.announcement.origin_asn == 15169
    assert r.abuse.forward_confirmed is True
    assert r.origin.kind == DATACENTER   # 8.8.8.8 is Google hosting space


def test_apivoid_anonymity_feeds_verdict(fake_fetch_json, fake_dns, tor_get):
    # ip-api fixture has proxy=False; APIVoid flagging proxy should still flip the
    # geo proxy flag the classifier reads. (8.8.8.8 already reads datacenter via
    # the hosting flag, so assert the flag propagation on an object level.)
    from ip_intel import report as R
    r = R.build_report("8.8.8.8", fetch_json=fake_fetch_json, dns=fake_dns,
                       tor_get=tor_get,
                       apivoid=lambda ip: {"detections": 1, "risk": 20,
                                           "flags": ["vpn"]},
                       now="2026-08-03T00:00:00Z")
    assert "vpn" in r.abuse.anonymity_flags
    assert r.geo.proxy_vpn is True


def test_invalid_ip_raises():
    with pytest.raises(ValueError):
        build_report("not-an-ip", fetch_json=lambda u, **k: {}, tor_get=lambda: "")


def test_markdown_render(fake_fetch_json, fake_dns, tor_get):
    md = render_markdown(_report(fake_fetch_json, fake_dns, tor_get))
    assert "# IP intel report — `8.8.8.8`" in md
    assert "## 1. Ownership" in md and "## 4. Announcement" in md
    assert "network-abuse@google.com" in md
    assert "Origin verdict" in md


def test_json_render_roundtrips(fake_fetch_json, fake_dns, tor_get):
    payload = json.loads(render_json(_report(fake_fetch_json, fake_dns, tor_get)))
    assert payload["ip"] == "8.8.8.8"
    assert payload["announcement"]["rpki_status"] == "valid"


def test_html_render(fake_fetch_json, fake_dns, tor_get):
    doc = render_html(_report(fake_fetch_json, fake_dns, tor_get))
    assert doc.startswith("<!doctype html>")
    assert "8.8.8.8" in doc


def test_dashboard_render(fake_fetch_json, fake_dns, tor_get):
    r = _report(fake_fetch_json, fake_dns, tor_get)
    doc = render_dashboard([r, r])
    assert doc.startswith("<!doctype html>")
    assert "Per-host findings" in doc
    assert "8.8.8.8" in doc
    assert 'pill datacenter' in doc          # verdict pill class
    # Two reports sharing one CIDR → shared-facts panel appears.
    assert "Shared facts" in doc


def test_whoami_projection(fake_fetch_json, fake_dns, tor_get):
    out = whoami("8.8.8.8", fetch_json=fake_fetch_json, dns=fake_dns, tor_get=tor_get)
    assert out["ip"] == "8.8.8.8"
    assert out["origin_class"] == DATACENTER
    assert out["asn"] == "AS15169"
    assert out["geo"]["country"] == "United States"
