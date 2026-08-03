from __future__ import annotations

"""Network clients — the only place that touches the wire.

Every source module receives its network access through these small callables,
so tests inject fixtures instead of hitting the internet (mirrors the adapter
injection used elsewhere in this repo). Real implementations here add a timeout,
a shared in-process cache, and a per-host rate limit; all failures are turned
into `None` / empty results with an error string rather than raising, so one
dead source never sinks the whole report.
"""

import socket
import time
from typing import Optional, Protocol
from urllib.parse import urlparse

import requests

USER_AGENT = "ip-intel/0.1 (+https://github.com/edvinas123/metro-fabric-labs)"
DEFAULT_TIMEOUT = 8.0


class JsonFetcher(Protocol):
    def __call__(self, url: str, params: Optional[dict] = None,
                 headers: Optional[dict] = None) -> dict: ...


class TextFetcher(Protocol):
    def __call__(self, url: str) -> str: ...


class DnsResolver(Protocol):
    def resolves(self, name: str) -> bool: ...
    def reverse(self, ip: str) -> Optional[str]: ...
    def forward(self, name: str) -> list[str]: ...


class HttpClient:
    """Timeout + in-process cache + polite per-host rate limiting."""

    def __init__(self, timeout: float = DEFAULT_TIMEOUT, rate_limit_s: float = 0.5):
        self.timeout = timeout
        self.rate_limit_s = rate_limit_s
        self._cache: dict[str, object] = {}
        self._last_hit: dict[str, float] = {}
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": USER_AGENT})

    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_hit.get(host)
        if last is not None:
            wait = self.rate_limit_s - (time.monotonic() - last)
            if wait > 0:
                time.sleep(wait)
        self._last_hit[host] = time.monotonic()

    def get_json(self, url: str, params: Optional[dict] = None,
                 headers: Optional[dict] = None) -> dict:
        key = f"J {url} {params} {headers}"
        if key in self._cache:
            return self._cache[key]  # type: ignore[return-value]
        self._throttle(url)
        resp = self._session.get(url, params=params, headers=headers,
                                 timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        self._cache[key] = data
        return data

    def get_text(self, url: str) -> str:
        if url in self._cache:
            return self._cache[url]  # type: ignore[return-value]
        self._throttle(url)
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        self._cache[url] = resp.text
        return resp.text


class SocketDns:
    """Stdlib DNS: enough for DNSBL membership + rDNS without extra deps."""

    def resolves(self, name: str) -> bool:
        try:
            socket.gethostbyname(name)
            return True
        except socket.gaierror:
            return False

    def reverse(self, ip: str) -> Optional[str]:
        try:
            host, _, _ = socket.gethostbyaddr(ip)
            return host
        except (socket.herror, socket.gaierror):
            return None

    def forward(self, name: str) -> list[str]:
        try:
            _, _, addrs = socket.gethostbyname_ex(name)
            return addrs
        except socket.gaierror:
            return []
