from __future__ import annotations
from pathlib import Path
import yaml
from .models import Site, Oracle


def load_sites(path: str | Path) -> list[Site]:
    raw = yaml.safe_load(Path(path).read_text()) or []
    sites = []
    for e in raw:
        o = e["oracle"]
        sites.append(Site(
            id=e["id"], url=e["url"], region=e["region"],
            gating_type=e["gating_type"], requires_geo=e["requires_geo"],
            oracle=Oracle(type=o["type"], match=o["match"]),
            login_gated_stop=e.get("login_gated_stop"),
        ))
    return sites


def load_costs(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text()) or {}


def load_egress(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text()) or {}
