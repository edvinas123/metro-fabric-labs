from __future__ import annotations
from typing import Callable, Optional
from .base import EgressAdapter
from ..models import RawResult

# A RetrievalClient takes a target URL and returns extracted content, or None if no coverage.
RetrievalClient = Callable[[str], Optional[str]]


class RetrievalApiAdapter(EgressAdapter):
    name = "retrieval_api"
    kind = "retrieval"

    def __init__(self, client: RetrievalClient):
        self._client = client

    def supports_geo(self, geo: str) -> bool:
        return True  # retrieval APIs are geo-agnostic from our side

    def fetch(self, url: str, geo: str) -> RawResult:
        content = self._client(url)
        if content is None:
            return RawResult(status=None, html=None, latency_ms=None, error="no result")
        return RawResult(status=200, html=content, latency_ms=None, bytes=len(content.encode("utf-8")))
