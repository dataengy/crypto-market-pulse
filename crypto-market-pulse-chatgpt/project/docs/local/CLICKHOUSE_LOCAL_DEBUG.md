# ClickHouse + Redpanda local debug (draft runbook)

1. `python3 scripts/discover_local_runtime.py --markdown` — inspect `~/.apps/`, `~/.app/`, PATH, Docker, Colima and ports. Choose a compatible authorized, non-production Kafka/Redpanda and ClickHouse. Do not modify others' services.
2. If none is available **and permission is given**, `docker compose -f infra/clickhouse/compose.yml up -d`. This creates only `cmp-` services. Never `down -v` on shared services.
3. Confirm Kafka bootstrap with `rpk topic list --brokers localhost:19092` (or actual endpoint); create topic `market.trades.v1` with `rpk topic create market.trades.v1 --brokers ...` if absent and owned. Check CH `SELECT version()` using configured credentials.
4. Apply idempotent SQL DDL: `CLICKHOUSE_PASSWORD=... python scripts/clickhouse_setup.py`. This only applies `CREATE DATABASE/TABLE/VIEW IF NOT EXISTS`. If the database exists in a shared instance, require approval.
5. `python scripts/produce.py --profile clickhouse --sink kafka --fixture tests/fixtures/trades.jsonl` and `python scripts/clickhouse_consumer.py --max-messages 8`.
6. Verify query `SELECT symbol, window_start, trade_count, open_price, close_price, vwap FROM market_pulse.trades_1m ORDER BY symbol,window_start;` and rerun replay to demonstrate idempotent **query** metrics. Raw row count grows; that's expected.
7. `CMP_PROFILE=clickhouse streamlit run dashboards/app.py` for a read-only live-ish dashboard with five-second query cache.

Important: Python Kafka consumer is **not** a faithful local emulation of ClickPipes. Cloud path Confluent Cloud → ClickPipes → ClickHouse Cloud needs dedicated authenticated/manual integration test. Late data can revise SQL view results; incremental MV correctness requires a different design.
