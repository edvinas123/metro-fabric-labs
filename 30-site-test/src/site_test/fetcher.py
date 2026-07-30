from __future__ import annotations
import time
from typing import Optional
from .models import RawResult

# Fixed fingerprint — identical across direct arms so the IP origin is the only variable.
FIXED_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)
FIXED_VIEWPORT = {"width": 1280, "height": 800}
FIXED_LOCALE = "en-US"


def build_launch_options(proxy: Optional[str]) -> dict:
    opts: dict = {"headless": True}
    if proxy:
        opts["proxy"] = {"server": proxy}
    return opts


def fetch(url: str, proxy: Optional[str] = None, timeout_ms: int = 20000) -> RawResult:
    from playwright.sync_api import sync_playwright
    t0 = time.monotonic()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**build_launch_options(proxy))
            ctx = browser.new_context(
                user_agent=FIXED_UA, viewport=FIXED_VIEWPORT, locale=FIXED_LOCALE
            )
            try:
                page = ctx.new_page()
                resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                html = page.content()
                status = resp.status if resp else None
            finally:
                browser.close()
            latency = int((time.monotonic() - t0) * 1000)
            return RawResult(status=status, html=html, latency_ms=latency,
                             bytes=len(html.encode("utf-8")))
    except Exception as e:  # network/timeout/proxy failures -> unreachable
        latency = int((time.monotonic() - t0) * 1000)
        return RawResult(status=None, html=None, latency_ms=latency, error=str(e))
