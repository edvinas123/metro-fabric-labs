from __future__ import annotations

import json
from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


# URL substring → fixture file. The fake fetcher routes on these so a whole
# report can be assembled offline from recorded responses.
_ROUTES = {
    "rdap.org/ip": "rdap_8888.json",
    "ip-api.com": "ipapi_8888.json",
    "ipwho.is": "ipwhois_8888.json",
    "network-info": "ripe_network_info.json",
    "as-overview": "ripe_as_overview.json",
    "routing-status": "ripe_routing_status.json",
    "rpki-validation": "ripe_rpki.json",
}


@pytest.fixture
def fake_fetch_json():
    def fetch(url: str, params=None, headers=None) -> dict:
        for needle, fixture in _ROUTES.items():
            if needle in url:
                return _load(fixture)
        raise AssertionError(f"no fixture for URL: {url}")
    return fetch


@pytest.fixture
def tor_get():
    return lambda: (FIX / "tor_exitlist.txt").read_text()


class FakeDns:
    """Deterministic DNS: no blocklist hits, a clean PTR, forward-confirmed."""
    def __init__(self, listed=(), ptr="dns.google", forward=("8.8.8.8",)):
        self.listed = set(listed)
        self.ptr = ptr
        self._forward = list(forward)

    def resolves(self, name: str) -> bool:
        return name in self.listed

    def reverse(self, ip: str):
        return self.ptr

    def forward(self, name: str):
        return self._forward


@pytest.fixture
def fake_dns():
    return FakeDns()
