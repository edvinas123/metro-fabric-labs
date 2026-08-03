---
name: origin-classify
description: Classify an IP's origin as clean ISP-ORG, datacenter, mobile, or reserved space — the trust-anchor signal for weighting a Certificate of Origin (Metro Fabric design principle #6). Use when the user asks whether an IP is a real ISP/residential origin vs a datacenter/hosting IP, or how much identity weight an origin carries.
---

# origin-classify

Answer the Metro Fabric trust question for an IP: **is this a clean ISP-ORG origin,
or datacenter / mobile / reserved space?** — and what that means for a Certificate of
Origin.

## Why it matters

Design principle #6: *ISP-ORG is the trust anchor. A cert bound to a confirmed
ISP-ORG range carries real identity weight; a datacenter-IP cert does not.* This
skill produces the heuristic verdict that feeds that decision.

## Steps

1. Run the full report — the origin verdict is computed from ownership + geo signals:
   `ipintel <ip> --format json`
2. Read `origin` from the JSON: `kind` (`isp_org`/`datacenter`/`mobile`/`reserved`/
   `unknown`), `confidence`, `rationale`, `trust_note`.
3. Report the verdict, the rationale, and the trust implication. If `kind` is
   `unknown` or confidence is `low`, say the ISP-ORG range needs manual confirmation
   before a cert is trusted.

## Guardrail

The verdict is a **heuristic** (keyword + provider-flag based), not a confirmed
ISP-ORG range. Present it as a signal to weight a cert, never as proof of identity.
