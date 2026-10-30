# Databricks Free Edition lane — Crypto Market Pulse (`./CMP-dbx-fe/`)

Data flow: Bybit V5 `publicTrade` → `normalize_trade` → Kafka `market.trades.v1` → Lakeflow pipeline
`trades_bronze` (Python, Kafka source) → `trades_silver` (streaming table + `EXPECT`) → `trades_dedup` → `trades_1m` → `trades_latest` (MVs) → AI/BI dashboard.
- **Local, dev/debug:** Redpanda + PySpark 4.0 Structured Streaming → path-based Delta tables under `.tmp/lake`, plus the dmux MiniLake emulator for SDK/UC/SQL checks.
- **Cloud:** managed Kafka (Confluent Cloud by default; any SASL_SSL/PLAIN Kafka works) → serverless triggered pipeline on Free Edition → dashboard on the Serverless Starter Warehouse.

The same code runs on both sides: `cmp.bronze.parse_trades`, `cmp.kafka.*` and the `sql/models/*_select.sql` SELECTs. `scripts/build.py` wraps them for Lakeflow, and local Spark runs them as Delta CTAS. The fixture assertion is the same as in the other lanes: BTCUSDT 10:00 bar = `4 / 0.45 / 70000 / 70010 / 69990`.

| Doc | Content |
|---|---|
| [plan.md](plan.md) | the approved plan: layout, steps, verification |
| [tasks.md](tasks.md) | `DBX-L*` local, `DBX-C*` cloud, `DBX-B*` backlog (each B task has its own plan in `CMP-dbx-fe/docs/backlog/`) |
| [../../../CMP-dbx-fe/README.md](../../../CMP-dbx-fe/README.md) | how to run it |

## Status (2026-10-30)
| Group | Tasks | Status |
|---|---|---|
| Local core, models, build, Spark+Delta | [DBX-L01](tasks.md#dbx-l01)–[DBX-L04](tasks.md#dbx-l04) | done: 14 tests green |
| Local Kafka E2E, MiniLake | [DBX-L05](tasks.md#dbx-l05)–[DBX-L06](tasks.md#dbx-l06) | code written; blocked on the local Docker daemon (HTTP 500) |
| Cloud gate: Kafka egress from Free Edition | [DBX-C01](tasks.md#dbx-c01)–[DBX-C02](tasks.md#dbx-c02) | not started: needs Databricks CLI + login + Kafka account |
| Cloud deploy, run, verify | [DBX-C03](tasks.md#dbx-c03)–[DBX-C05](tasks.md#dbx-c05) | not started |
| Backlog | [DBX-B1](tasks.md#dbx-b1)–[DBX-B7](tasks.md#dbx-b7) | parked |
