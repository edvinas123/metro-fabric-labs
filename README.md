# Metro Fabric Labs

> Open projects, reference implementations, and developer tools for building on **Metro Fabric** — the agent-aware network. Clean, geo-distributed ISP egress + verifiable agent identity: the "legs + passport" that lets an AI agent reach the whole web from a real origin, anywhere.

This repo is a public **build list** and **task tracker**. Each item is a standalone project or tool that runs on Metro infrastructure and shows off one capability of the network. Check boxes as they ship. Contributions and forks welcome.

---

## Design principles (read before contributing)

Every project here respects the load-bearing rules of the network. A contribution that violates one will not be merged.

1. **Origin quality + identity, never "bypass."** We sell legitimate carrier-sourced IP egress and declared, signed identity. We do not frame anything as beating, evading, or defeating bot defenses. Clean ISP origin is a *quality* signal, not a trick.
2. **Passport, not wallet.** Each agent presents *its own* verifiable identity, passed transparently through the network. We do not front agents opaquely behind a single shared identity.
3. **Dedicated IP is the floor.** IP is part of identity. No rotating shared pools. Tiered egress: IPv6 `/64` per agent (default) → dedicated IPv4 (premium) → NAT/shared (bulk, "just not blocked" only).
4. **Standards-aligned.** Identity is built on [RFC 9421 (HTTP Message Signatures)](https://www.rfc-editor.org/rfc/rfc9421) and tracks the IETF web-bot-auth draft. Certs stay RFC 9421-compatible regardless of draft outcome.
5. **The network carries; it does not index or click.** Legs + passport, nothing more. Retrieval indexing and agent reasoning/automation live above us.
6. **ISP-ORG is the trust anchor.** A cert bound to a confirmed ISP-ORG range carries real identity weight; a datacenter-IP cert does not.

---

## Projects

Status: `[ ]` idea · `[~]` in progress · `[x]` shipped

### Tier 1 — Make the infra usable (SDKs & reference impls)

- [ ] **`agent-passport`** — Client SDK (TypeScript + Python) that signs outbound HTTP requests per RFC 9421 / web-bot-auth, attaches a Certificate of Origin header, and publishes/fetches keys from `.well-known/bot-auth`. The core Path A developer primitive.
  <br>*Shows off: verifiable agent identity, standards alignment.*
- [ ] **`metro-mcp`** — MCP server exposing Metro Fabric as tools any agent (or Claude) can call: request egress, issue/verify a passport, route an intent, read settlement events. Makes the whole network directly agent-consumable.
  <br>*Shows off: the network as a callable surface for agents.*
- [ ] **`passport-verifier`** — Drop-in verification middleware (Express / Fastify / Cloudflare Worker / nginx-lua) for the *publisher/CDN* side: verify a Metro-issued cert and query the whitelist registry to grant trusted-tier access. The other half of the three-sided market.
  <br>*Shows off: cross-platform whitelist registry, real-time verification.*

### Tier 2 — Prove it works (demos & benchmarks)

- [ ] **`whoami-agent`** — Public endpoint + embeddable widget (an `ipinfo.io` for agents) that returns the calling agent's verified identity, ISP-ORG tag, geo, and reputation. The clearest one-glance demo of legs + passport.
  <br>*Shows off: identity + clean ISP origin, live.*
- [~] **`the-30-site-test`** — A deliverability test for AI agents before production: fetch real geo-restricted/gated sites from each host you might run on (your machine, a cloud server, any hosting/egress provider) and compare success rate + cost, so you can choose where to host. Provider-neutral; Metro Fabric plugs in as one host. *(Framework + connectors built and tested; plug in any proxy to run it today — full provider comparison pending a live egress endpoint.)*
  <br>*Shows off: agent deliverability, host/provider comparison, measured in the open.*
- [ ] **`agents.txt`** — A spec + hosted registry where sites declare their agent-access policy and pricing; agents query it before fetching. `robots.txt` for the agent economy — the connective tissue between identity and settlement.
  <br>*Shows off: policy discovery, settlement on-ramp.*

### Tier 3 — The agent economy (settlement & trust)

- [ ] **`settlement-sandbox`** — Reference implementation of the publisher settlement API: a verified access event → automatic micropayment to the publisher. Spotify-style micro-royalty flow, end to end, with test money.
  <br>*Shows off: settlement clearing, incentive inversion (publishers earn from verified traffic).*
- [ ] **`origin-ledger`** — Public transparency log + audit explorer for Certificates of Origin: non-repudiable, court-admissible session records, browsable. The trust function made visible.
  <br>*Shows off: accountability, non-repudiation.*

### Tier 4 — Runtime & operability

- [ ] **`ephemeral-agent-runtime`** — Spin up a clean, compliant box with a pinned ISP IP, run one agent task, recycle the container (IP recycled on teardown). Compliant-egress ephemeral runtime demo.
  <br>*Shows off: managed compliant runtime, pinned-IP-per-task attribution.*
- [ ] **`geo-egress-map`** — Live status page + world map of Metro PoPs: latency, ISP coverage, IPv6 `/64` availability per region. Marketing surface doubling as a real status page.
  <br>*Shows off: geo depth, network reach.*

---

## Skills (Claude Code / agent skills for operating the network)

Skills that let an operator drive Metro infra from an agent session. Each is a `SKILL.md` + optional helper script.

- [ ] **`metro-egress`** — Request/configure clean ISP egress for a task. Picks tier by (destination IPv6-reachability × attribution need): IPv6 `/64` default, dedicated IPv4 premium, NAT bulk.
- [ ] **`metro-passport`** — Issue or verify an agent passport: RFC 9421 signing, Certificate of Origin attachment, key publication.
- [ ] **`metro-intent-route`** — Describe a task in natural language → auto-configure geo, identity, IP tier, and session policy. The intent router as a skill.
- [ ] **`metro-verify`** — Publisher side: check an incoming request's Metro cert and registry status; return grant/challenge/deny.
- [ ] **`metro-settlement`** — Register a content domain, set access pricing, and read settlement events.
- [ ] **`metro-deploy`** — Deploy an agent onto the Metro ephemeral runtime and stream its Certificate of Origin.
- [ ] **`metro-status`** — PoP health, latency, and IP-pool availability at a glance.
- [ ] **`metro-30site`** — Run the 30-site coverage/success benchmark and emit a scorecard.

---

## Repo layout (suggested)

Each project graduates to its own repo under a `metro-fabric` GitHub org. This repo stays the index.

```
labs/                 # this index (build list + task tracker)
  README.md
metro-fabric/agent-passport      # → own repo when it graduates
metro-fabric/metro-mcp           # → own repo
metro-fabric/passport-verifier   # → own repo
...
```

Convention: prototype in `labs/<name>/`, then split to a dedicated public repo once it has a README, a license, and a runnable demo.

## Contributing

- Pick an unchecked box, open an issue to claim it, move it to `[~]`.
- Keep every project **self-contained and runnable** — a `README`, a one-command demo, and no undocumented infra dependencies.
- Re-read the **Design principles** above. Origin quality + identity, passport not wallet, dedicated-IP floor, standards-aligned.

## License

MIT (placeholder — confirm before first public push).
