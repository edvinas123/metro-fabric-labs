---
name: ip-intel
description: Generate a full IP information report — ownership (WHOIS/RDAP), abuse/reputation, geolocation, and BGP announcement — for one or more IP addresses or CIDRs, from free public sources. Use when the user asks to look up, profile, investigate, or triage an IP/subnet, or wants ownership/abuse/geo/routing facts about an address.
---

# ip-intel

Drive the `ipintel` CLI in this project to produce a sourced, four-section report
for any IP or CIDR, plus a one-line origin verdict (ISP-ORG vs datacenter vs mobile
vs reserved).

## When to use

The user gives an IP or subnet (or a list/file) and wants any of: who it belongs to,
whether it's on blocklists / a Tor exit / has an abuse contact, where it geolocates,
how the prefix is announced in BGP, or whether it's a clean ISP origin.

## Steps

1. From the project root, ensure the tool is available (`ipintel --help`; if missing,
   `pip install -e ".[dev]"` in a venv, or `python -m ip_intel.cli`).
2. Run it:
   - single: `ipintel <ip>`
   - subnet: `ipintel 108.186.55.0/24` (samples a representative host in the block)
   - many / file: `ipintel report --input targets.txt --out reports/ --format md,json`
   - JSON for further processing: `ipintel <ip> --format json`
3. Read the output. Lead your summary with the **origin verdict**, then the four
   sections, keeping the per-section source citations.
4. Flag anything notable: blocklist hits, RPKI `invalid`, geo≠registrant country,
   forward-DNS not confirmed, or an `unknown`/ambiguous origin.

## Guardrails

- Read-only public data only — no scanning, probing, or authentication against targets.
- Never invent a value; report blanks as "undetermined".
- Optional `ABUSEIPDB_KEY` env var adds a reputation score; do not solicit keys in chat.
