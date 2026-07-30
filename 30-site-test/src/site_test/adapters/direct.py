from __future__ import annotations
from typing import Callable, Optional
from .base import EgressAdapter
from ..models import RawResult
from ..fetcher import fetch as default_fetch


class DatacenterAdapter(EgressAdapter):
    name = "datacenter"
    kind = "direct"

    def __init__(self, geos: list[str], proxy: Optional[str] = None,
                 fetch_fn: Callable = default_fetch):
        self.geos = geos
        self.proxy = proxy
        self._fetch = fetch_fn

    def supports_geo(self, geo: str) -> bool:
        return geo in self.geos

    def fetch(self, url: str, geo: str) -> RawResult:
        return self._fetch(url, proxy=self.proxy)


class IspProxyAdapter(EgressAdapter):
    name = "isp_proxy"
    kind = "direct"

    def __init__(self, geos: list[str], proxies: dict[str, str],
                 fetch_fn: Callable = default_fetch):
        self.geos = geos
        self.proxies = proxies
        self._fetch = fetch_fn

    def supports_geo(self, geo: str) -> bool:
        return geo in self.geos and geo in self.proxies

    def proxy_for(self, geo: str) -> str:
        return self.proxies[geo]

    def fetch(self, url: str, geo: str) -> RawResult:
        return self._fetch(url, proxy=self.proxy_for(geo))
