from __future__ import annotations
from typing import Callable, Optional
from .base import EgressAdapter
from ..models import RawResult
from ..fetcher import fetch as default_fetch


class HostAdapter(EgressAdapter):
    """One 'host' = a place your agent could run / egress from (your machine, a
    cloud server, a hosting/egress provider). Built from a named profile in
    egress.yaml. `proxies` maps region -> endpoint; `default_proxy` (may be None
    = egress from this machine's own IP) is used for any region without a specific
    proxy."""
    kind = "direct"

    def __init__(self, name: str, geos: list[str],
                 proxies: Optional[dict[str, str]] = None,
                 default_proxy: Optional[str] = None,
                 fetch_fn: Callable = default_fetch):
        self.name = name
        self.geos = geos
        self.proxies = proxies or {}
        self.default_proxy = default_proxy
        self._fetch = fetch_fn

    def supports_geo(self, geo: str) -> bool:
        return geo in self.geos

    def proxy_for(self, geo: str) -> Optional[str]:
        return self.proxies.get(geo, self.default_proxy)

    def fetch(self, url: str, geo: str) -> RawResult:
        return self._fetch(url, proxy=self.proxy_for(geo))
