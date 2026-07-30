# the-30-site-test

**A deliverability test for AI agents — before you move to production.**

Your agent works great when you build it on your laptop. You deploy it to a cloud server, and suddenly it's blocked, rate-limited, or served empty pages. Same code — different result — because the sites now see a **datacenter IP** instead of the **home/residential IP** your laptop had.

This benchmark measures that gap *before* you ship, and helps you **choose where to host** your agent. It fetches a set of real geo-restricted and gated sites from each place your agent could run, decides whether real content actually came back (not a block/captcha/geo-wall page), and reports how often each host succeeds — plus what it costs.

> **Principle:** every fetch is a plain read-only GET from a *legitimate* origin. This tool does **not** solve captchas, bypass logins, or spoof fingerprints to evade detection. It measures how reachable the open web is from a given host — it does not defeat defenses. It never fabricates a result: a site it can't run from a given region is recorded as `not_tested`, never guessed.

---

## What it compares — "hosts"

A **host** is anywhere your agent could run and reach the web from. You define as many as you want and the benchmark scores each one. The two you'll almost always compare:

| Host | What it represents | Typical result |
|---|---|---|
| your machine (`this-machine`, home / laptop) | a residential IP | works — few blocks |
| a cloud server (`server`) | a datacenter IP | more blocks, captchas, empty pages |
| a hosting/egress provider (e.g. `metro`) | the provider's IPs | *this is what you're evaluating* |

Add one host per option you're weighing (your laptop, AWS, GCP, a residential-egress provider, Metro Fabric…) and the scorecard tells you which keeps your agent deliverable.

All hosts share **one** real-browser fetch path with a **fixed fingerprint** (same user-agent, viewport, locale). Only the IP origin differs — so any difference in results is attributable to *where you run*, not to the client.

> There's also an optional **`retrieval_api`** comparison — instead of hosting a fetcher at all, use a data API (Exa / Parallel). It scores *coverage* (could it return the page or not). Built and tested; wired into `run` once you add API keys.

---

## Two ways to run it

1. **Same agent, two places (the home-vs-server test).** Configure one host with `connector: local` (uses the current machine's IP). Run the tool **from your laptop**, then **from your cloud server**, and compare the two scorecards. This is the most literal "will it still work in production?" test.
2. **Many hosts, one run (provider selection).** Configure a host per option, each pointing at that provider's egress endpoint, and run once. The scorecard ranks them side by side.

---

## Requirements

### Software
- Python ≥ 3.11
- Playwright + Chromium (`python -m playwright install chromium`)
- A machine with outbound network access (macOS or Linux)

### To compare a hosting / egress provider
For any host that isn't "this machine," you configure a **connector** (see [Connectors](#connectors)) — `metro` for Metro Fabric, or `http_proxy` for any proxy you already have. Per region you want to test, you need:

- **An egress endpoint** for that region, reachable as `scheme://[user:pass@]host:port` (for `metro`, your Metro contact provides these; for `http_proxy`, it's your own proxy).
- **Auth constraint (worth knowing up front):** Chromium can't do username/password auth on SOCKS5 proxies. So the endpoint must be either **(a) an HTTP/HTTPS proxy with basic auth**, or **(b) an endpoint that authorizes you by source IP** (no inline username/password). A username/password SOCKS5 endpoint will silently fail.

### Optional
- **Retrieval arm:** Exa and/or Parallel API keys (adapter is built + tested; wired into `run` once keys exist).

---

## Install

```bash
cd 30-site-test
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
```

## Quick start

```bash
# 1. Run against the default 30 sites, from the hosts in egress.yaml (one line per attempt)
site-test run --sites data/sites.yaml --egress data/egress.yaml --out results.jsonl

# 2. Aggregate the raw results into a scorecard
site-test aggregate --in results.jsonl --out scorecard.json

# 3. Read it
cat scorecard.json
```

`run` flags (all optional, defaults shown):

| Flag | Default | Meaning |
|---|---|---|
| `--sites` | `data/sites.yaml` | the site list to test |
| `--egress` | `data/egress.yaml` | the hosts to compare + regions each can reach |
| `--costs` | `data/costs.yaml` | per-host cost model |
| `--out` | `results.jsonl` | raw output path |
| `--rate-limit` | `2.0` | minimum seconds between hits to the same domain |

---

## Configuring hosts — `egress.yaml`

[`data/egress.yaml`](data/egress.yaml) lists the hosts to compare. Each host names a **connector** — the piece that turns config/credentials into a working egress, so you never hand-assemble a provider's plumbing:

```yaml
hosts:
  this-machine:            # your own IP — run from home, then from a server
    connector: local
    geos: ["US"]           # the region this machine is in — edit to match

  metro:                   # Metro Fabric egress
    connector: metro
    geos: ["US", "DE"]
    account: "your-metro-account"
    api_key_env: METRO_API_KEY   # export METRO_API_KEY=...  (never commit the key)
    endpoints:                   # provided by your Metro Fabric contact
      US: "http://us.metro-egress:8000"
      DE: "http://de.metro-egress:8000"

  # aws-server:            # any plain cloud/datacenter proxy you already have
  #   connector: http_proxy
  #   geos: ["US"]
  #   proxies: { US: "http://user:pass@us.datacenter:8000" }

retrieval_api:             # optional; not wired into `run` until keys exist
  provider: "exa"
```

A site with `requires_geo: DE` is only attempted by a host whose `geos` include `DE`. Everything else → `not_tested`. Add regions to a host as its coverage grows — no code change. A host whose connector can't build (e.g. a missing credential) is **skipped with a message**, so your other hosts still run.

### Connectors

| Connector | Connects you to | Config |
|---|---|---|
| `local` | this machine's own IP | just `geos` — run the tool from wherever you want that origin to be |
| `http_proxy` | any proxy you already have (cloud, datacenter, residential) | `proxies:` (per region) and/or `proxy:` (default) |
| `metro` | **Metro Fabric egress** | `geos`, `account`, `api_key_env` (secret read from env), `endpoints:` per region |

**Connecting to Metro Fabric:**
1. Get your Metro **account** + **API key** and the **egress endpoint(s)** for the regions you need from your Metro Fabric contact.
2. Put the account, the endpoints, and the *name* of the env var holding your key in `egress.yaml` (see above). **The key itself goes in the environment, never the file:** `export METRO_API_KEY=...`.
3. Run. The `metro` connector validates your credentials + endpoints and routes each fetch for those regions through Metro.

> Metro Fabric's self-serve egress API is still being built. Until it ships, you supply the endpoints your contact gives you; when the API is live, only the `metro` connector's `_metro_endpoints()` function changes (it will lease endpoints automatically) — your `egress.yaml` and everything else stay the same. To add another provider, add one function in [`src/site_test/connectors.py`](src/site_test/connectors.py) and register it.

**Secrets — do not commit real endpoints or keys.** Keep API keys in env vars (`api_key_env`), and put any inline endpoints/creds in an untracked local file:

```bash
cp data/egress.yaml egress.local.yaml   # gitignored; real endpoints here
export METRO_API_KEY=...                 # key in the environment, not the file
site-test run --egress egress.local.yaml
```

---

## Choosing what to test — the site list

Ships with **30 default sites** in [`data/sites.yaml`](data/sites.yaml), across five gating categories. To test **your own** sites, copy the file, edit it, and point `--sites` at it:

```bash
cp data/sites.yaml my-sites.yaml
# edit my-sites.yaml
site-test run --sites my-sites.yaml --out results.jsonl
```

### `sites.yaml` schema

```yaml
- id: zalando-de              # unique short id (used in results)
  url: https://www.zalando.de # the exact page to fetch
  region: DE                  # human label for where this site is "from"
  gating_type: anti_fraud     # one of the 5 categories below
  requires_geo: DE            # only hosts that can egress from this region test it
  oracle:                     # how we know REAL content loaded (not a block page)
    type: regex               # "regex" or "css"
    match: "Zalando"          # regex: searched in the HTML | css: a selector that must exist
  login_gated_stop: at_wall   # optional; only for login_gated sites (see below)
```

**`gating_type`** — the five categories (all in the defaults):

| Category | Meaning |
|---|---|
| `geo_restricted` | content differs or is blocked by region (broadcasters, regional media) |
| `anti_fraud` | heavy bot-defense (e-commerce, retail, ticketing) |
| `login_gated` | real content sits behind a login wall |
| `publisher_cdn` | publisher behind a CDN / soft paywall |
| `long_tail` | permissive / niche — a baseline that *should* succeed from anywhere |

**`requires_geo`** — the region a host must reach to test this site. If no configured host covers it, the attempt is `not_tested` (excluded from success rates — never a failure or a fake success).

**`oracle`** — the success test. Matches **only** when the real target content loaded, so a block/captcha/geo-wall page does not score as success:
- `type: regex` — a regex searched in the returned HTML (`"Herman Melville"`, `"Zalando"`).
- `type: css` — a CSS selector that must be present (`div.product-price`, `h1`).

**`login_gated_stop: at_wall`** — for `login_gated` sites, we measure whether the login page loads cleanly (host not blocked *before* auth). We do **not** log in. Point the oracle at something on the login page.

> ⚠️ **Tune your oracles.** An oracle that's too strict makes a page that loaded fine score `not_blocked` instead of `content_ok` — under-reporting success. The defaults use best-effort brand/title strings; **validate each and adjust** before trusting a site's numbers. Fastest check: run the `long_tail` baseline first — those should all be `content_ok`; if not, it's your setup, not the site.

---

## Cost config

[`data/costs.yaml`](data/costs.yaml) — per-host pricing (keyed by the host names in `egress.yaml`), used to compute cost-per-successful-fetch:

```yaml
this-machine:  { usd_per_gb: 0.0, usd_per_req: 0.0 }
metro:    { usd_per_gb: 8.0, usd_per_req: 0.0 }   # usd_per_gb = dollars per GiB
retrieval_api: { usd_per_gb: 0.0, usd_per_req: 0.005 }
```

(Placeholders — replace with real rates before quoting cost numbers.)

---

## Reading the results

### `results.jsonl` — one line per attempt

```json
{"site_id": "zalando-de", "arm": "metro", "geo": "DE", "outcome": "content_ok",
 "latency_ms": 812, "bytes": 48211, "cost_usd": 0.0007, "ts": "2026-07-30T20:10:00Z", "notes": ""}
```

| Field | Meaning |
|---|---|
| `site_id` / `arm` / `geo` | which site, which host, which region (`arm` = the host name) |
| `outcome` | the tier (below) |
| `latency_ms` | fetch time (null if not tested / errored) |
| `bytes` | size of returned HTML |
| `cost_usd` | cost of this attempt from the cost model |
| `notes` | error text, or "no live egress for this geo" for `not_tested` |

### Outcome tiers

Hosts, best → worst:

| Outcome | Meaning |
|---|---|
| `content_ok` | real target content loaded (oracle matched, status < 400, not a block page) |
| `not_blocked` | page loaded, not a block page, but the oracle didn't match (check your oracle) |
| `reachable` | got a response, but it's a block/captcha/geo-wall page **or** an HTTP error status |
| `unreachable` | no usable response (timeout, connection error, crash) |
| `not_tested` | no configured host could egress from this site's region — excluded from all rates |

Retrieval arm: `content_ok` (returned usable content) or `no_coverage` (couldn't return the target).

### `scorecard.json` — the aggregate

```json
{
  "arms": {
    "server": {
      "tested": 24, "not_tested": 6, "total_cost": 0.0,
      "unreachable": 3, "reachable": 9, "not_blocked": 2, "content_ok": 10,
      "content_ok_rate": 0.4167, "cost_per_content_ok": 0.0
    },
    "metro": { "...": "..." }
  },
  "coverage_gap": { "tested": 30, "no_coverage": 11, "gap_rate": 0.3667 }
}
```

- **`content_ok_rate`** — the headline success number per host (`content_ok / tested`; `not_tested` excluded from the denominator). **This is what you compare between hosts to pick where to run.**
- **`cost_per_content_ok`** — dollars per successful fetch (`null` if the host had zero successes).
- **`coverage_gap`** — share of targets the retrieval API could **not** return at all.

---

## Retrieval arm status

The `RetrievalApiAdapter` is implemented and unit-tested, but `run` wires only the hosts under `egress.yaml`'s `hosts:` until Exa / Parallel credentials exist. To enable it, build a `RetrievalClient` (`Callable[[str], Optional[str]]`) around the provider SDK and add a `RetrievalApiAdapter(client=...)` to the adapter list in `cli._build_host_adapters`.

## Tests

```bash
pytest      # 40 passing
```
