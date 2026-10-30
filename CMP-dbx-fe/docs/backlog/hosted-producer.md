# DBX-B6 — Hosted producer

**Goal:** the Bybit → Kafka producer runs 24/7 without the laptop. ← [tasks](../../../docs/plans/dbx-fe/tasks.md#dbx-b6)

**Options (pick one after checking free tiers):** small VM (Hetzner/Oracle free ARM) with systemd + `uv run scripts/produce.py --source bybit --sink kafka`; GitHub Actions cron (bounded `--max-trades`, gaps between runs); a Databricks App (Free: 3 apps, 24 h runtime, and the same egress question as DBX-C02, plus Bybit reachability).

**Steps**
- [ ] Check that Bybit is reachable from the chosen region (Bybit geo-blocks some regions, e.g. US IPs)
- [ ] Secrets via the platform secret store → env (`KAFKA_*`), never in files
- [ ] Health: log a heartbeat every N trades; alert on no-trade for X min (values in config)

**Acceptance:** 24 h run with no gap > 1 min in `trades_1m` for BTCUSDT.
