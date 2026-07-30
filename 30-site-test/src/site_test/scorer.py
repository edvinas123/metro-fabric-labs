from __future__ import annotations
import re
from bs4 import BeautifulSoup
from .models import Tier, RawResult, Oracle, NO_COVERAGE

# Markers that indicate a challenge / block / geo-wall page rather than real content.
BLOCK_MARKERS = [
    "just a moment...",
    "cf-browser-verification",
    "checking your browser before accessing",
    "attention required! | cloudflare",
    "captcha-delivery.com",
    "datadome",
    "px-captcha",
    "perimeterx",
    "access denied",
    "not available in your country",
    "not available in your region",
]


def is_block_page(html: str | None) -> bool:
    if not html:
        return False
    low = html.lower()
    return any(marker in low for marker in BLOCK_MARKERS)


def oracle_matches(html: str | None, oracle: Oracle) -> bool:
    if not html:
        return False
    if oracle.type == "regex":
        return re.search(oracle.match, html) is not None
    if oracle.type == "css":
        soup = BeautifulSoup(html, "html.parser")
        return len(soup.select(oracle.match)) > 0
    raise ValueError(f"unknown oracle type: {oracle.type}")


def score_direct(raw: RawResult, oracle: Oracle) -> Tier:
    if raw.error or raw.status is None or raw.html is None:
        return Tier.UNREACHABLE
    if is_block_page(raw.html):
        return Tier.REACHABLE
    if oracle_matches(raw.html, oracle):
        return Tier.CONTENT_OK
    return Tier.NOT_BLOCKED


def score_retrieval(raw: RawResult) -> str:
    """Retrieval arm scores COVERAGE, not a direct fetch."""
    if raw.error or not raw.html or not raw.html.strip():
        return NO_COVERAGE
    return "content_ok"
