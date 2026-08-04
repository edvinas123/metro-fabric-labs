# API keys — sign-up list

ip-intel runs **fully with zero keys**. Everything below is *optional enrichment*:
each provider turns on automatically the moment its key (or local DB) is present in
the environment, and stays off otherwise — no code change. Set them in `.env`
(copy from [`.env.example`](.env.example); `.env` is gitignored).

## What runs today with no account (already working)

| Source | Section | Notes |
|---|---|---|
| RDAP (rdap.org → RIR) | Ownership | org, CIDR, RIR, abuse contact |
| ip-api.com | Geo | country/city, ISP, ASN, proxy/hosting flag |
| ipwho.is | Geo | second opinion, disagreement flagging |
| Spamhaus / SpamCop / Barracuda (DNS) | Abuse | blocklist membership |
| Tor bulk exit list | Abuse | exit-node check |
| RIPEstat | Announcement | prefix, origin ASN, RPKI, visibility |
| BGPView | Announcement | AS name, upstreams, more-specifics |
| PeeringDB | Origin verdict | AS network type (ISP vs Content/hosting) |

## Accounts to create tomorrow (all have a free tier)

Priority = how much it improves the report per minute of signup effort.

| # | Service | Adds | Free tier | Env var | Sign up |
|---|---|---|---|---|---|
| 1 | **AbuseIPDB** | abuse confidence score + report count | 1,000 checks/day | `ABUSEIPDB_KEY` | https://www.abuseipdb.com/register |
| 2 | **ipinfo.io** | extra geo source, ASN, privacy flags (paid) | 50,000/mo | `IPINFO_TOKEN` | https://ipinfo.io/signup |
| 3 | **GreyNoise** | scanner classification (benign/malicious) | Community key | `GREYNOISE_KEY` | https://www.greynoise.io/ |
| 4 | **Shodan** | open ports + exposure tags | limited free | `SHODAN_KEY` | https://account.shodan.io/register |
| 5 | **MaxMind GeoLite2** | high-quality offline geo DB | free w/ account | `MAXMIND_DB` (file) | https://www.maxmind.com/en/geolite2/signup |
| 6 | **IP2Location LITE** | second offline geo DB (cross-check) | free download | `IP2LOCATION_DB` (file) | https://lite.ip2location.com/ |
| 7 | **Scamalytics** | fraud score + risk band | free on request | `SCAMALYTICS_BASE` + `SCAMALYTICS_KEY` | https://scamalytics.com/ |
| 8 | **IPQualityScore** | fraud score + proxy/VPN (Scamalytics alt) | 5,000/mo | `IPQS_KEY` | https://www.ipqualityscore.com/create-account |

Notes:
- **7 and 8 overlap** (both are fraud scores). Pick one to start — IPQS has the
  easier self-serve signup; Scamalytics is stronger but approval-gated. ip-intel
  uses Scamalytics first and falls back to IPQS for the score.
- **5 and 6 are local DBs**, not HTTP APIs — you download a file and point the env
  var at it. They also need an extra Python extra: `pip install ".[maxmind]"` /
  `".[ip2location]"`.
- **ipinfo privacy flags** (vpn/proxy/tor/hosting) need a paid ipinfo plan; the
  free token still gives geo + ASN, and the proxy/hosting signal is already covered
  free by ip-api.

## Minimal recommended set

If you only want a few: **AbuseIPDB + ipinfo + GreyNoise**. Those three, all free,
cover reputation, a strong second geo/ASN source, and scanner intel — the biggest
jump in report quality for three quick signups.

## After you have the keys

```bash
cd ip-intel
cp .env.example .env      # then paste your keys into .env
export $(grep -v '^#' .env | xargs)
ipintel 108.186.55.0/24   # enrichments now appear automatically
```

A provider that is set but misconfigured prints a one-line `# provider: ...` note
to stderr and is skipped — the rest of the report still runs.
