# ClickHouse lane — Crypto Market Pulse (`./CMP-ch/`)

Data flow: Bybit V5 `publicTrade` → `normalize_trade` → Kafka `market.trades.v1` → ClickHouse `trades_raw` → RMT `trades_dedup` → 1m OHLCV view → latest view → Streamlit.
- **Local, dev/debug:** Redpanda + ClickHouse in docker (existing services are reused first), Python consumer.
- **Cloud:** Confluent Cloud Basic → ClickPipes → ClickHouse Cloud (trial) → Streamlit Community Cloud.

Both paths use the same SQL files and the same fixture assertion (BTCUSDT 10:00 bar = `4 / 0.45 / 70000 / 70010 / 69990`). The reference source is `crypto-market-pulse-chatgpt/project`, which was never executed. The sibling lane is the Databricks Free Edition plan (`CMP-dbx-fe/`).

| Doc | Content |
|---|---|
| [01-local-dev-debug.md](01-local-dev-debug.md) | layout, runtime reuse, producer, schema/SQL, consumer, dashboard, fault injection, debug tooling, tests |
| [02-cloud-deploy-test.md](02-cloud-deploy-test.md) | verified free-tier facts (2026-10-30), decisions, secrets, TF provisioning, cloud verification, CI smoke, cost and teardown |
| [tasks.md](tasks.md) | `CH-L01…L11` local, `CH-C01…C09` cloud, `CH-LB*` / `CH-CB*` backlog |

## Status
| Group | Tasks | Status |
|---|---|---|
| Local scaffold & core | [CH-L01](tasks.md#ch-l01)–[CH-L02](tasks.md#ch-l02) | not started |
| Local stack, schema, I/O | [CH-L03](tasks.md#ch-l03)–[CH-L06](tasks.md#ch-l06) | not started |
| Local E2E gate | [CH-L07](tasks.md#ch-l07) | not started — blocks all cloud tasks |
| Local faults, dashboard, debug, CI | [CH-L08](tasks.md#ch-l08)–[CH-L11](tasks.md#ch-l11) | not started |
| Cloud provisioning | [CH-C01](tasks.md#ch-c01)–[CH-C04](tasks.md#ch-c04) | not started — needs user approval for sign-ups/spend |
| Cloud verify, dashboard, CI, cost | [CH-C05](tasks.md#ch-c05)–[CH-C09](tasks.md#ch-c09) | not started |
| Backlog | [CH-LB1–3](tasks.md#ch-lb1), [CH-CB1–4](tasks.md#ch-cb1) | parked |
