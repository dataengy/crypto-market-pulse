# Mission — CMP-gcp cloud deploy

Prove that the GCP lane of Crypto Market Pulse works on real GCP, cheaply and reversibly:
1. Bybit `publicTrade` → Pub/Sub → BigQuery subscription → views
2. the same fixture assertion as local
3. a bounded hosted producer
4. a Looker Studio dashboard
5. one-command teardown

## Users
- **The owner (one person):** runs gated deploys from a laptop and reviews every `terraform plan`.
- **CI (GitHub Actions on `dataengy/crypto-market-pulse`):** runs the cloud smoke on demand, keyless.

## Use cases
- Verify that the cloud path reproduces the fixture bar (BTCUSDT 2026-10-30 10:00 UTC: `4 / 0.45 / 70000 / 70010 / 69990`) in an isolated `smoke` env.
- Watch live BTC/ETH 1-minute bars in Looker Studio while a scheduled, bounded producer runs.
- Optionally confirm Beam parity on Dataflow, once and time-boxed.
- Tear everything down and confirm that the bill stays under budget.

## Differentiators / non-goals
- Close to free: no always-on compute; the trial credit is a safety net, not a budget to spend.
- **Non-goals:**
  - production SLOs
  - multi-region
  - remote TF state (backlog GCP-C15)
  - an automatic kill-switch (backlog GCP-C16)
