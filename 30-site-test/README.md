# the-30-site-test

Open, reproducible benchmark measuring access success and cost across three origin
types — datacenter IPs, clean-ISP egress, and retrieval APIs — on curated
geo-restricted and gated sites. Measured from legitimate origins only; this benchmark
does not evade or defeat defenses.

## Install
    cd 30-site-test
    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    python -m playwright install chromium

## Run
    site-test run --sites data/sites.yaml --out results.jsonl
    site-test aggregate --in results.jsonl --out scorecard.json

## Test
    pytest
