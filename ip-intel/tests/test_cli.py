import json

from ip_intel import cli
from ip_intel.cli import _resolve_target
from ip_intel.models import IPReport, Ownership


class DummyHttp:
    def get_json(self, url, params=None, headers=None):
        return {}

    def get_text(self, url):
        return ""


def _fixed_report(ip, **kwargs):
    return IPReport(ip=ip, generated_at="2026-08-03T00:00:00Z",
                    ownership=Ownership(organization="Example Org"))


def test_bare_ip_defaults_to_report(monkeypatch, capsys):
    monkeypatch.setattr(cli, "HttpClient", DummyHttp)
    monkeypatch.setattr(cli, "build_report", _fixed_report)
    rc = cli.main(["8.8.8.8"])            # no subcommand → report
    assert rc == 0
    assert "IP intel report" in capsys.readouterr().out


def test_writes_all_formats(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "HttpClient", DummyHttp)
    monkeypatch.setattr(cli, "build_report", _fixed_report)
    rc = cli.main(["report", "8.8.8.8", "--format", "md,json,html",
                   "--out", str(tmp_path)])
    assert rc == 0
    for ext in ("md", "json", "html"):
        assert (tmp_path / f"8.8.8.8.report.{ext}").exists()


def test_dashboard_flag_writes_one_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "HttpClient", DummyHttp)
    monkeypatch.setattr(cli, "build_report", _fixed_report)
    out = tmp_path / "dash.html"
    rc = cli.main(["report", "8.8.8.8", "1.1.1.1", "--dashboard", str(out)])
    assert rc == 0
    assert out.exists()
    html = out.read_text()
    assert "Per-host findings" in html and "8.8.8.8" in html and "1.1.1.1" in html


def test_unknown_format_errors(monkeypatch):
    monkeypatch.setattr(cli, "HttpClient", DummyHttp)
    assert cli.main(["report", "8.8.8.8", "--format", "xml"]) == 2


def test_invalid_ip_skipped(monkeypatch, capsys):
    monkeypatch.setattr(cli, "HttpClient", DummyHttp)
    rc = cli.main(["report", "not-an-ip"])
    assert rc == 0
    assert "skipping" in capsys.readouterr().err


def test_whoami(monkeypatch, capsys):
    monkeypatch.setattr(cli, "HttpClient", DummyHttp)
    monkeypatch.setattr(cli, "whoami", lambda ip, **k: {"ip": ip or "1.2.3.4",
                                                        "origin_class": "isp_org"})
    rc = cli.main(["whoami", "1.2.3.4"])
    assert rc == 0
    assert json.loads(capsys.readouterr().out)["origin_class"] == "isp_org"


def test_resolve_cidr_samples_a_host():
    ip, note = _resolve_target("108.186.55.0/24")
    assert ip == "108.186.55.1"
    assert note and "sampling" in note


def test_resolve_plain_ip_no_note():
    ip, note = _resolve_target("1.1.1.1")
    assert ip == "1.1.1.1" and note is None
