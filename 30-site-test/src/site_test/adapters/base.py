from __future__ import annotations
from abc import ABC, abstractmethod
from ..models import RawResult


class EgressAdapter(ABC):
    name: str = "base"
    kind: str = "direct"   # "direct" | "retrieval"

    @abstractmethod
    def supports_geo(self, geo: str) -> bool: ...

    @abstractmethod
    def fetch(self, url: str, geo: str) -> RawResult: ...
