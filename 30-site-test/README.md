# the-30-site-test

An open, reproducible benchmark that answers one question:

> **On real geo-restricted and gated sites, how does access success (and cost) compare across a datacenter IP, a clean-ISP egress, and a retrieval API?**

It fetches each site from each "origin type," decides whether real content actually came back (not a block/captcha/geo-wall page), and reports success rates + cost-per-success + the retrieval-API coverage gap.

> **Principle:** every fetch is a plain read-only GET from a *legitimate* origin. This tool does **not** solve captchas, bypass logins, or spoof fingerprints to evade detection. It measures origin quality — it does not defeat defenses. It never fabricates a result: a site it can't run in a given region is recorded as `not_tested`, never guessed.

---

## The three arms

| Arm | What it is | How it's scored |
|---|---|---|
| `datacenter` | A fetch from a datacenter IP (your local box, or a datacenter proxy) | tiered outcome (see below) |
| `isp_proxy` | A fetch routed through clean-ISP egress, per region | tiered outcome |
| `retrieval_api` | Content returned by a retrieval API (Exa / Parallel) for the target | coverage: `content_ok` or `no_coverage` |

Direct arms (`datacenter`, `isp_proxy`) share **one** real-browser fetch path with a **fixed fingerprint** (same user-agent, viewport, locale). Only the IP origin differs — so any difference in results is attributable to the origin, not the client.

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
# 1. Run the benchmark against the default 30 sites (writes one line per attempt)
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
| `--egress` | `data/egress.yaml` | which arms exist and which regions they can egress from |
| `--costs` | `data/costs.yaml` | per-arm cost model |
| `--out` | `results.jsonl` | raw output path |
| `--rate-limit` | `2.0` | minimum seconds between hits to the same domain |

---

## Choosing what to test — the site list

The tool ships with **30 default sites** in [`data/sites.yaml`](data/sites.yaml), spread across the five gating categories. To test **your own** sites, copy that file, edit it, and point `--sites` at it:

```bash
cp data/sites.yaml my-sites.yaml
# edit my-sites.yaml
site-test run --sites my-sites.yaml --out results.jsonl
```

### `sites.yaml` schema

Each entry:

```yaml
- id: zalando-de              # unique short id (used in results)
  url: https://www.zalando.de # the exact page to fetch
  region: DE                  # human label for where this site is "from"
  gating_type: anti_fraud     # one of the 5 categories below
  requires_geo: DE            # the tool only runs arms that can egress from this region
  oracle:                     # how we know REAL content loaded (not a block page)
    type: regex               # "regex" or "css"
    match: "Zalando"          # regex: searched in the HTML | css: a selector that must exist
  login_gated_stop: at_wall   # optional; only for login_gated sites (see below)
```

**`gating_type`** — the five categories (all represented in the defaults):

| Category | Meaning |
|---|---|
| `geo_restricted` | content differs or is blocked by region (broadcasters, regional media) |
| `anti_fraud` | heavy bot-defense (e-commerce, retail, ticketing) |
| `login_gated` | real content sits behind a login wall |
| `publisher_cdn` | publisher behind a CDN / soft paywall |
| `long_tail` | permissive / niche — useful as a baseline that *should* succeed everywhere |

**`requires_geo`** — the region an arm must be able to egress from to test this site. If no configured arm can egress from that region, the attempt is recorded as `not_tested` (excluded from success rates — never counted as a failure or a fake success).

**`oracle`** — the success test. It must match **only** when the real target content loaded, so a block/captcha/geo-wall page does not score as success:
- `type: regex` — `match` is a regex searched anywhere in the returned HTML. Good for stable brand/text strings (`"Herman Melville"`, `"Zalando"`).
- `type: css` — `match` is a CSS selector that must be present (`div.product-price`, `h1`). Good when a specific element only renders on the real page.

**`login_gated_stop: at_wall`** — for `login_gated` sites, we measure whether the login page itself loads cleanly (origin not blocked *before* auth). We do **not** log in. Set the oracle to match something on the login page (e.g. the sign-in form/brand).

> ⚠️ **Tune your oracles.** An oracle that's too strict makes a page that loaded fine score `not_blocked` instead of `content_ok` — under-reporting success. The shipped defaults use best-effort brand/title strings; **validate each against a known-good fetch and adjust** before trusting a site's numbers. Fastest check: run against the `long_tail` baseline first — those should all be `content_ok`; if they're not, your setup (not the site) is the problem.

---

## Egress config — which arms run, and where

[`data/egress.yaml`](data/egress.yaml) declares the arms and the regions each can reach:

```yaml
datacenter:
  geos: ["US"]            # regions this arm can egress from
  proxy: null             # null = your local machine; or "http://user:pass@host:port"
isp_proxy:
  geos: ["US", "DE"]
  proxies:                # one proxy endpoint per region
    US: "http://user:pass@us.egress:8000"
    DE: "http://user:pass@de.egress:8000"
retrieval_api:
  provider: "exa"         # see "Retrieval arm" below — not yet wired into `run`
```

A site with `requires_geo: DE` is only attempted by an arm whose `geos` include `DE`. Everything else for that site → `not_tested`. This is how "limited regions" is handled honestly: you get real numbers for the regions you can actually egress from, and explicit `not_tested` for the rest.

## Cost config

[`data/costs.yaml`](data/costs.yaml) — per-arm pricing, used to compute cost-per-success:

```yaml
datacenter:    { usd_per_gb: 0.0, usd_per_req: 0.0 }
isp_proxy:     { usd_per_gb: 8.0, usd_per_req: 0.0 }   # usd_per_gb = dollars per GiB
retrieval_api: { usd_per_gb: 0.0, usd_per_req: 0.005 }
```

(Shipped values are placeholders — replace with your real rates before quoting cost numbers.)

---

## Reading the results

### `results.jsonl` — one line per attempt

```json
{"site_id": "zalando-de", "arm": "isp_proxy", "geo": "DE", "outcome": "content_ok",
 "latency_ms": 812, "bytes": 48211, "cost_usd": 0.0007, "ts": "2026-07-30T20:10:00Z", "notes": ""}
```

| Field | Meaning |
|---|---|
| `site_id` / `arm` / `geo` | which site, which origin type, which region |
| `outcome` | the tier (below) |
| `latency_ms` | fetch time (null if not tested / errored) |
| `bytes` | size of returned HTML |
| `cost_usd` | cost of this attempt from the cost model |
| `notes` | error text, or "no live egress for this geo" for `not_tested` |

### Outcome tiers

Direct arms (`datacenter`, `isp_proxy`), best → worst:

| Outcome | Meaning |
|---|---|
| `content_ok` | real target content loaded (oracle matched, status < 400, not a block page) |
| `not_blocked` | page loaded, not a block page, but the oracle didn't match (check your oracle) |
| `reachable` | got a response, but it's a block/captcha/geo-wall page **or** an HTTP error status |
| `unreachable` | no usable response (timeout, connection error, crash) |
| `not_tested` | no configured arm could egress from this site's region — excluded from all rates |

Retrieval arm: `content_ok` (returned usable content) or `no_coverage` (couldn't return the target).

### `scorecard.json` — the aggregate

```json
{
  "arms": {
    "datacenter": {
      "tested": 24, "not_tested": 6, "total_cost": 0.0,
      "unreachable": 3, "reachable": 9, "not_blocked": 2, "content_ok": 10,
      "content_ok_rate": 0.4167, "cost_per_content_ok": 0.0
    },
    "isp_proxy": { "...": "..." }
  },
  "coverage_gap": { "tested": 30, "no_coverage": 11, "gap_rate": 0.3667 }
}
```

- **`content_ok_rate`** — the headline success number per arm (`content_ok / tested`; `not_tested` excluded from the denominator).
- **`cost_per_content_ok`** — dollars per successful fetch (`null` if the arm had zero successes). This is the "do we beat X on success *and* cost" number.
- **`coverage_gap`** — share of targets the retrieval API could **not** return at all. A high gap is the signal that direct egress is needed for those targets.

---

## Retrieval arm status

The `RetrievalApiAdapter` is implemented and unit-tested, but the CLI wires only the two direct arms until Exa / Parallel credentials exist. To enable it, build a `RetrievalClient` (`Callable[[str], Optional[str]]`) around the provider SDK and add a `RetrievalApiAdapter(client=...)` to the adapter list in `cli._build_direct_adapters`.

## Tests

```bash
pytest      # 39 passing
```
