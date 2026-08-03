# ip-intel

**A one-command IP intelligence report — ownership, abuse, geolocation, and BGP announcement — from free public sources.**

Point it at any IPv4/IPv6 address and it answers the four questions you actually ask about an IP:

1. **Who owns it?** — RDAP / WHOIS registration, org, RIR, allocation, abuse contact
2. **Is it dirty, and who do I report it to?** — blocklists, Tor, reverse-DNS, abuse email, optional reputation score
3. **Where is it?** — multi-provider geolocation, with cross-source disagreement flagged
4. **How is it routed right now?** — origin ASN, announced prefix, RPKI validity, visibility

On top of those four it adds one **origin verdict** — is this a clean **ISP-ORG** origin, a **datacenter**, **mobile**, or **reserved** space — which is the load-bearing signal for the rest of Metro Fabric (design principle #6: *ISP-ORG is the trust anchor*).

> **Principle:** every field is read-only OSINT from public registration, reputation, geo, and routing data. It does **not** probe, scan, log in, or attack the target. A field it cannot determine is left blank — **never guessed**. Every section cites the source it came from.

This is the reusable **core**; the [`whoami-agent`](../README.md) labs project ("an `ipinfo.io` for agents") is a thin identity endpoint on top of it (`ipintel whoami`).

---

## Install

```bash
cd ip-intel
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

No API key required. Everything below runs on free, public, no-key services.

## Quick start

```bash
# Full report to stdout (Markdown)
ipintel 8.8.8.8

# Multiple formats to a directory
ipintel 8.8.8.8 1.1.1.1 --format md,json,html --out reports/

# Batch from a file (one IP/CIDR per line, # comments allowed)
ipintel report --input targets.txt --format json --out reports/

# Identity view of your own egress IP (the whoami-agent seed)
ipintel whoami
```

`report` flags:

| Flag | Default | Meaning |
|---|---|---|
| `--format` | `md` | comma list of `md`, `json`, `html` |
| `--out` | *(stdout)* | output directory; writes `<ip>.report.<ext>` per format |
| `--input` | — | file with one IP/CIDR per line |

---

## What each section checks

### 1. Ownership — RDAP (primary), WHOIS fields
Network name, allocated **CIDR**, organization, responsible **RIR** (ARIN / RIPE / APNIC / LACNIC / AFRINIC), allocation status, registration + last-changed dates, and the **abuse / admin / tech** contacts parsed out of the RDAP jCard.
**Source:** `rdap.org` bootstrap → authoritative RIR.

### 2. Abuse & reputation *(zero-key)*
Abuse contact email, **reverse DNS** + forward-confirmed check, **DNSBL** membership (Spamhaus ZEN, SpamCop, Barracuda — queried directly over DNS), **Tor exit-node** membership, and bogon / special-use flags. Optionally an **AbuseIPDB** confidence score if a free key is present (`ABUSEIPDB_KEY`).
**Sources:** DNS, public blocklist zones, Tor bulk exit list, `ipaddress`, AbuseIPDB (optional).

### 3. Geolocation *(multi-source)*
Country, region, city, lat/lon, timezone, ISP/org, and connection type (hosting / mobile). Two providers are queried and any **country-level disagreement is surfaced**, not hidden. Geo is where the IP *resolves* — it can legitimately differ from the registrant country in §1.
**Sources:** `ip-api.com`, `ipwho.is`.

### 4. Announcement — BGP *(zero-key)*
Whether a covering prefix is **announced**, the prefix, **origin ASN** + AS holder name, **RPKI** validation state, and route **visibility** (collector peers seeing it).
**Source:** RIPEstat Data API.

### Origin verdict — the Metro Fabric value-add
A single heuristic classification — `isp_org` / `datacenter` / `mobile` / `reserved` / `unknown` — with a rationale and what it means for a Certificate of Origin. Clearly labelled a **heuristic** (keyword + provider-flag based): a signal to *weight* a cert, never a substitute for a confirmed ISP-ORG range.

---

## Output

- **Markdown** — sectioned, human-readable, source-cited (default, to stdout)
- **JSON** — the full `IPReport` structure, for piping into automation
- **HTML** — a single self-contained file

Sample (trimmed) for `8.8.8.8`:

```
Origin verdict: datacenter (high confidence) — geo provider flags this as hosting space
  Ownership   GOGL · 8.8.8.0/24 · Google LLC · ARIN · abuse network-abuse@google.com
  Abuse       rDNS dns.google (forward-confirmed) · blocklists: none · tor: no
  Geo         United States / Virginia / Ashburn · Google LLC · connection: hosting
  Announcement AS15169 GOOGLE · 8.8.8.0/24 · RPKI valid · visible to 135 peers
```

---

## Architecture

```
ip-intel/
├── src/ip_intel/
│   ├── models.py        # dataclasses: Ownership / Abuse / Geo / Announcement / OriginClass / IPReport
│   ├── net.py           # the ONLY code that touches the wire (HTTP + DNS clients, injectable)
│   ├── ownership.py     # RDAP parse
│   ├── abuse.py         # DNSBL + rDNS + Tor + optional AbuseIPDB
│   ├── geo.py           # multi-provider geo + reconciliation
│   ├── announcement.py  # RIPEstat BGP/RPKI chain
│   ├── classify.py      # origin verdict (principle #6)
│   ├── report.py        # assemble + render (md/json/html)
│   ├── whoami.py        # thin identity projection (whoami-agent seed)
│   └── cli.py           # `ipintel`
├── .claude/             # agent + skills (self-contained, travels with the project)
│   ├── agents/ip-intel.md
│   └── skills/{ip-intel,origin-classify}/SKILL.md
└── tests/               # offline: every source is fed recorded fixtures
```

**Every source function takes its network access as an injected callable** (`fetch_json`, `dns`, `tor_get`, `abuseipdb`). Real clients live in `net.py`; tests pass recorded fixtures, so the suite never touches the network and one dead source degrades gracefully instead of crashing the report.

## Tests

```bash
pytest      # 28 passing, no network
```

## As a Claude Code agent

The bundled `.claude/` ships an `ip-intel` subagent and two skills, so from any agent session you can say *"generate an IP intel report for 1.1.1.1"* or *"classify the origin of this IP"* and it drives the CLI.

## Disclaimer

Uses only publicly available registration, reputation, geolocation, and routing data. Geolocation and origin classification are approximate. Intended for legitimate network operations, abuse handling, security research, and due diligence.
