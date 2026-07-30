"""Connectors turn a host's declared config into a working HostAdapter.

Each host in egress.yaml names a `connector`. A connector knows how to take
that host's config (and any env-var credentials) and produce the per-region
egress endpoints the runner needs — so a user never hand-assembles a provider's
plumbing. Add a new provider by adding one function here and registering it.
"""
from __future__ import annotations
import os
from .adapters.direct import HostAdapter


class ConnectorError(Exception):
    """Raised when a host's connector config is invalid or incomplete."""


def _local(name: str, profile: dict) -> HostAdapter:
    """This machine's own IP (no proxy). Run the tool from your laptop, then from
    a cloud server, to compare."""
    return HostAdapter(name=name, geos=profile.get("geos", []), proxies={}, default_proxy=None)


def _http_proxy(name: str, profile: dict) -> HostAdapter:
    """A plain proxy you already have (datacenter/cloud/residential). Endpoints
    are declared directly under `proxies` (per region) and/or `proxy` (default)."""
    return HostAdapter(name=name, geos=profile.get("geos", []),
                       proxies=profile.get("proxies", {}),
                       default_proxy=profile.get("proxy"))


def _metro_endpoints(profile: dict, api_key: str | None) -> dict:
    """Resolve Metro Fabric egress endpoints, one per region.

    SEAM: Metro Fabric does not yet expose a public egress-provisioning API. Until
    it does, endpoints are taken from config (the ones your Metro contact gave you,
    under `endpoints:`). When the API ships, replace ONLY this function body with a
    call that leases endpoints for `profile['account']` in each `profile['geos']`
    region using `api_key`. Nothing else in this file needs to change.
    """
    return profile.get("endpoints") or {}


def _metro(name: str, profile: dict) -> HostAdapter:
    """Metro Fabric host. Credentials come from an env var (never the config file);
    endpoints come from `_metro_endpoints`."""
    geos = profile.get("geos", [])
    env = profile.get("api_key_env")
    api_key = os.environ.get(env) if env else None
    if env and not api_key:
        raise ConnectorError(
            f"host '{name}': env var {env} is not set — export your Metro API key first")
    endpoints = _metro_endpoints(profile, api_key)
    missing = [g for g in geos if g not in endpoints]
    if missing:
        raise ConnectorError(
            f"host '{name}': no Metro endpoint configured for region(s) {missing}")
    return HostAdapter(name=name, geos=geos, proxies=endpoints, default_proxy=None)


CONNECTORS = {"local": _local, "http_proxy": _http_proxy, "metro": _metro}


def _default_connector(profile: dict) -> str:
    """If a host omits `connector`, infer one: declared endpoints -> http_proxy,
    otherwise local (this machine)."""
    if profile.get("proxies") or profile.get("proxy"):
        return "http_proxy"
    return "local"


def build_host(name: str, profile: dict) -> HostAdapter:
    kind = profile.get("connector") or _default_connector(profile)
    fn = CONNECTORS.get(kind)
    if not fn:
        raise ConnectorError(
            f"host '{name}': unknown connector '{kind}' (known: {', '.join(sorted(CONNECTORS))})")
    return fn(name, profile)
