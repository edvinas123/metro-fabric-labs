import json
from site_test.cli import _build_direct_adapters, cmd_aggregate
from site_test.models import Attempt, attempt_to_json

def test_build_direct_adapters_from_egress():
    egress = {"datacenter": {"geos": ["US"], "proxy": None},
              "residential": {"geos": ["US", "DE"], "proxies": {"US": "http://u", "DE": "http://d"}}}
    adapters = _build_direct_adapters(egress)
    assert [a.name for a in adapters] == ["datacenter", "residential"]
    assert adapters[1].proxy_for("DE") == "http://d"

def test_build_direct_adapters_datacenter_only():
    adapters = _build_direct_adapters({"datacenter": {"geos": ["US"], "proxy": None}})
    assert [a.name for a in adapters] == ["datacenter"]

def test_aggregate_command_roundtrip(tmp_path):
    infile = tmp_path / "results.jsonl"
    out = tmp_path / "scorecard.json"
    rows = [
        Attempt(site_id="a", arm="datacenter", geo="US", outcome="content_ok", latency_ms=1, bytes=1, cost_usd=0.0, ts="t"),
        Attempt(site_id="b", arm="datacenter", geo="DE", outcome="not_tested", latency_ms=None, bytes=0, cost_usd=0.0, ts="t"),
    ]
    infile.write_text("\n".join(attempt_to_json(r) for r in rows) + "\n")

    class Args:
        pass
    args = Args()
    args.infile = str(infile)
    args.out = str(out)
    cmd_aggregate(args)

    sc = json.loads(out.read_text())
    assert sc["arms"]["datacenter"]["tested"] == 1        # not_tested excluded
    assert sc["arms"]["datacenter"]["content_ok"] == 1
