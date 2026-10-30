# Crypto Market Pulse

A **SQL-first, multi-engine streaming lab** built from public Bybit V5 `publicTrade` messages. The primary deliverable is a market-monitoring application — **not a trading bot**. The project replaces Weather DFE with real market events while retaining its Databricks/Spark/Minilake reference in `baseline/`.

**Profiles:** (1) local Redpanda/Kafka → ClickHouse; managed Confluent Cloud → ClickHouse Cloud (integration guide, not provisioned); (2) local PySpark and Databricks Lakeflow → Delta; (3) Beam DirectRunner + Pub/Sub Emulator and managed Pub/Sub → BigQuery Subscription, with an optional future Dataflow stage.


## Learning & operations materials (runbooks and workbooks)

- **Start with `docs/RUN_AND_DEBUG_GUIDE.md`** — decision tree for L0 offline / L1 ClickHouse / L2 Spark+Beam / L3 cloud, exact commands and troubleshooting.
- **`docs/OPERATOR_MANUAL.md`** — data contracts, safe service reuse, lifecycle, offsets/checkpoints, failure recovery, observability and deployment gates.
- **`docs/workbooks/00_environment_inventory.md`** — read-only Mac inventory (PATH, `~/.apps/`, `~/.app/`, Docker/Colima).
- **`docs/workbooks/01_offline_market_math.md`** — duplicates, out-of-order trades, Decimal OHLCV/VWAP.
- **`docs/workbooks/02_clickhouse_redpanda.md`** — Kafka producer/consumer, query dedup, offsets, dashboard.
- **`docs/workbooks/03_spark_checkpoint.md`** — microbatch, watermark and checkpoint lab.
- **`docs/workbooks/04_beam_pubsub.md`** — Beam TestStream and optional Pub/Sub Emulator.
- **`docs/workbooks/05_fault_injection_and_evidence.md`** — safe chaos matrix + measurement template.
- **`notebooks/workbooks/01_event_time_ohlcv.ipynb`**, **`02_beam_event_time.ipynb`** — executable Jupyter labs (second requires Beam).
- **`docs/VALIDATION_REPORT.md`** — exactly what was executed, vs what remains unverified.

These files are guides for *your* environment; execution here occurs only in ChatGPT's isolated `/mnt/data` container, not on your Mac or GitHub.

## 0. Discover and reuse existing tools FIRST

```sh
python3 scripts/discover_local_runtime.py --markdown
```

Check executables in `PATH`, `~/.apps/`, `~/.app/`, then running/stopped Docker/Colima containers. Reuse **compatible, authorized** instances before starting anything. Never delete shared containers, volumes, projects, topics or databases. Inspect endpoint and version; avoid silently connecting to production. If a service is shared, use your own `market_pulse` database/topic/consumer group with consent. See `docs/LOCAL_RUNTIME_REUSE_POLICY.md`.

## 1. No-infrastructure replay (works offline)

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=src pytest -q tests --ignore=tests/test_beam_optional.py
python3 scripts/preview_marts.py  # OHLCV/VWAP + duplicate count with no dependencies
python3 scripts/produce.py --sink stdout --fixture tests/fixtures/trades.jsonl
```

Replay contains duplicates, out-of-order arrival, and multiple one-minute windows. Synthetic prices must not be interpreted as market observations.

## 2. Redpanda + ClickHouse (recommended first E2E)

Use existing compatible broker and database; the compose file is an **opt-in last resort**.

```sh
pip install -r requirements-clickhouse.txt
# Last resort only, if inventory found no compatible services:
docker compose -f infra/clickhouse/compose.yml up -d
# For the dedicated local compose stack only:
export CLICKHOUSE_PASSWORD=local_only_change_me
# Create Kafka topic using an installed rpk/kafka CLI; e.g. with the dedicated container:
docker exec cmp-redpanda rpk topic create market.trades.v1 --brokers localhost:9092
python3 scripts/clickhouse_setup.py
python3 scripts/produce.py --profile clickhouse --sink kafka --fixture tests/fixtures/trades.jsonl
python3 scripts/clickhouse_consumer.py --max-messages 8
CMP_PROFILE=clickhouse streamlit run dashboards/app.py
```

The Kafka consumer commits offsets only after a successful ClickHouse insert. Replay creates physically duplicated raw rows; query-level `trades_dedup` prevents double counting. **These are views, not continuously materialized aggregates**. For a shared broker you must supply its actual bootstrap endpoint and security configuration; don't create a new broker automatically.

## 3. Spark Structured Streaming locally

```sh
pip install -r requirements-spark.txt
python3 scripts/local_spark_debug.py
```

Requires a working Java runtime; checks JSON file stream, event-time watermark, checkpointed output, restart/replay considerations and a pure SQL mart. The sample is bounded `availableNow`, not an always-on Kafka stream. See `docs/local/SPARK_DEBUG.md` for extending to Kafka.

## 4. Beam / Pub/Sub Emulator locally

```sh
pip install -r requirements-beam.txt
PYTHONPATH=src pytest -q tests/test_beam_optional.py
# Optional: if Google Cloud SDK (gcloud) is already installed
# gcloud beta emulators pubsub start --host-port=127.0.0.1:8085
# export PUBSUB_EMULATOR_HOST=127.0.0.1:8085
# python3 scripts/gcp_emulator_smoke.py
```

Beam TestStream covers windowing with event time and duplicates offline. The Pub/Sub Emulator covers producer/pull/ack, **but cannot simulate a BigQuery Subscription delivery**. For cloud, review `infra/gcp/main.tf`, enable billing deliberately, and run a manual smoke test. Terraform is never auto-applied by CI.

## 5. Databricks / Free Edition

- Execute `sql/databricks/001_bronze.sql` once, with catalog/schema adjusted.
- Use `notebooks/01_replay_bronze.py` to populate Delta Bronze from fixture events (update checkout path).
- `databricks.yml` defines a **serverless SQL Lakeflow pipeline** for Silver, dedup and 1m/latest materialized views, and AI/BI dashboard JSON.
- `databricks bundle validate --var 'warehouse_id=YOUR_ID'` then explicit `bundle deploy` after confirming DFE compatibility, quota and permissions.
- Live Bybit producer writes to Kafka/Pub/Sub; to feed Delta Bronze from cloud Kafka, wire a separate supported ingestion job. The notebook is only the reproducible Bronze demo: no direct external WebSocket from DFE is assumed.

**Continuous Lakeflow** and even supported serverless compute can be subject to Free Edition limits; do not assume production-grade uninterrupted service. Do not interpret SQL materialized views as low-latency per-event updates without validating refresh cadence.

## 6. Dashboard as code

```sh
pip install -r requirements-dashboard.txt
CMP_PROFILE=clickhouse streamlit run dashboards/app.py
```

The Streamlit dashboard displays last price, last-minute OHLCV, volume and VWAP, with a five-second query cache. It does not stream pixels via WebSocket and its data frequency is governed by the data pipeline. For Databricks, `dashboards/market_pulse.lvdash.json` is included in a bundle; its SQL source is `sql/databricks/dashboard_history.sql`.

## Data contract and mathematical semantics

- Market: Bybit **linear** perpetual public trade stream; `BTCUSDT`, `ETHUSDT` by default.
- Identity: `event_id = bybit:{category}:{symbol}:{trade_id}` (not message ID or `seq`).
- Time: exchange trade `T` = `event_time_ms`, ingestion `received_at_ms` generated on receive, UTC milliseconds.
- Decimal strings for `price` and `quantity` preserve precision in transport; databases cast to DECIMAL/BIGNUMERIC.
- Window: `floor(event_time_ms / 60_000) * 60_000` (tumbling, event time).
- OHLC ordered by `(event_time_ms, event_id)`; high/low price; volume=sum(quantity); notional=sum(price*quantity); VWAP=notional/volume; taker buy count.
- Idempotency: query-level choose the first received duplicate per `event_id` in SQL; bounded event-time dedup in Beam/Spark has a **finite watermark/retention guarantee** and is *not globally exactly-once*.
- Batch replay after producer outage may miss original WebSocket events: Kafka replay only protects events **already ingested**. Do not claim guaranteed gapless market history.

## Status / honest limitations

Locally validated: 18 offline unit tests, four deterministic OHLCV/VWAP rows, JSON/YAML parsing and the first Jupyter lab (see `docs/VALIDATION_REPORT.md`). Spark/Beam/Docker/Databricks execution requires the relevant runtime and credentials. Minilake is preserved as a reference and possible SDK/SQL sandbox, **not** a Kafka/Lakeflow/Dataflow emulator. Cloud Terraform and SQL require dry-run/validation in the target project. Public trade data is not financial advice; application never places orders.

## Reference docs

- [Bybit V5 publicTrade](https://bybit-exchange.github.io/docs/v5/websocket/public/trade)
- [Bybit WS endpoints](https://bybit-exchange.github.io/docs/v5/ws/connect)
- [Databricks Lakeflow SQL](https://docs.databricks.com/gcp/en/ldp/developer/ldp-sql-ref-create-streaming-table)
- [Google Pub/Sub BigQuery Subscription](https://docs.cloud.google.com/pubsub/docs/bigquery)
- [Google Pub/Sub Emulator limitations](https://docs.cloud.google.com/pubsub/docs/emulator)
