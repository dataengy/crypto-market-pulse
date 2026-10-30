# Crypto Market Pulse: run, debug, and test guide

> **Execution boundaries.** The ZIP is built and offline-validated in an isolated ChatGPT Linux environment. Nothing is installed on your Mac, committed to GitHub, or deployed to a cloud account. Java and Python are available in the authoring sandbox; Kafka/Redpanda, ClickHouse, Spark/PySpark, Beam, Pub/Sub Emulator and Databricks have **not** been exercised end-to-end here. See `VALIDATION_REPORT.md` for exact evidence.

## 0. Choose what you want to prove

| Level | Environment | What this proves | What it DOES NOT prove |
| --- | --- | --- | --- |
| L0 | Python offline | Schema, parser, deterministic OHLCV/VWAP, fixtures | Broker, stream runtime, actual DWH |
| L1 | Local Redpanda+ClickHouse | Producer, Kafka offsets, sink, dedup query, dashboard | ClickPipes cloud, full exactly-once |
| L2 | Local Spark | Microbatches, checkpointed file stream, watermark, Spark SQL | Always-on Kafka ingestion, cluster SLA |
| L2 | Beam DirectRunner | Event-time windows and test harness | DataflowRunner, actual GCP Pub/Sub→BQ |
| L2 | Pub/Sub Emulator | Push/pull/ack transport | BigQuery subscription delivery |
| L3 | Optional cloud | Databricks/GCP/ClickHouse-specific integration | Portability without further validation |

## 1. Safe environment discovery (always run first)

On your **Mac**, from the unpacked `crypto_market_pulse/` directory:

```bash
pwd
python3 scripts/discover_local_runtime.py --markdown
command -v java spark-submit pyspark rpk docker colima gcloud terraform || true
docker context ls  # only if docker is installed; read-only
# Optional: inspect ownership and version of a discovered service
# docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

Priority: (1) already installed OS binaries / apps in PATH, `~/.apps/`, `~/.app/`; (2) already existing **authorized** Docker/Colima containers; (3) isolated new containers only if necessary; (4) OS installation as last resort. Never stop a shared container, run `docker compose down -v`, change remote DDL, or use real databases/credentials without checking ownership. Capture your findings in `docs/workbooks/00_environment_inventory.md` (use it as a template, not an inventory of your actual Mac).

## 2. Fastest run: offline fixture, 5–10 minutes

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
PYTHONPATH=src pytest -q tests --ignore=tests/test_beam_optional.py
python scripts/preview_marts.py
python scripts/produce.py --sink stdout --fixture tests/fixtures/trades.jsonl
```

Expected: 18 offline tests (number may grow), 4 market/minute aggregate rows, including BTCUSDT 10:00 UTC with `trade_count=4`, `volume=0.45`, `open_price=70000.0`, `close_price=69990.0`, and `duplicate_count=1`. Fixture events are **synthetic**, not current market prices. For more precision on trade ordering, see Workbook 1.

## 3. Live public WebSocket: safe bounded probe

```bash
python scripts/produce.py --sink stdout --max-trades 20
```

Needs internet access to Bybit public WS; no account tokens are needed. Check `event_id`, `event_time_ms`, symbol, `price` and quantity. This does **not** save trades unless you select a sink. It may encounter regional network or exchange restrictions. Never conflate reconnect success with recovery of missed trades during producer downtime.

## 4. Redpanda + ClickHouse local end-to-end

First choose existing Kafka bootstrap and ClickHouse HTTP URL. Export `CMP_KAFKA_BOOTSTRAP`, `CMP_CLICKHOUSE_URL`, optionally `CMP_CLICKHOUSE_DATABASE`, `CMP_KAFKA_GROUP`, `CLICKHOUSE_USER/PASSWORD` for that **authorized isolated** environment. Do not just copy these defaults into shared or production infrastructure.

Only if no compatible services exist and you approve starting project-owned containers:

```bash
docker compose -f infra/clickhouse/compose.yml up -d
export CLICKHOUSE_PASSWORD=local_only_change_me
# Verify owned containers and connectivity; compose publishes localhost:19092/8123.
docker ps --filter name=cmp-
docker exec cmp-redpanda rpk topic create market.trades.v1 --brokers localhost:9092
```

For existing Redpanda, use installed `rpk` with your broker address instead. Verify namespace/topic and whether it already exists; don't overwrite it. Then:

```bash
python -m pip install -r requirements-clickhouse.txt
python scripts/clickhouse_setup.py
python scripts/produce.py --profile clickhouse --sink kafka --fixture tests/fixtures/trades.jsonl
python scripts/clickhouse_consumer.py --max-messages 8
# Use your existing ClickHouse SQL client or read-only HTTP query with valid local credentials:
# SELECT symbol, window_start, trade_count, open_price, close_price, vwap
# FROM market_pulse.trades_1m ORDER BY symbol, window_start;
python -m pip install -r requirements-dashboard.txt
CMP_PROFILE=clickhouse streamlit run dashboards/app.py
```

The consumer is bounded with `--max-messages 8`; an infinite consumer without traffic will keep running. **To test replay**, publish the fixture *again*, then run the consumer without incorrectly expecting a reset offset. Query-level dedup should preserve OHLCV while `trades_raw` gains physical copies. Use `docs/workbooks/02_clickhouse_redpanda.md` for failure/offset/lag exercises. For Docker, `docker compose up` is not an automatic prerequisite: it is last resort.

## 5. Local Spark and Beam

**Spark:** identify existing Java and Spark, install into an isolated virtualenv only if missing and approved, then:

```bash
python -m pip install -r requirements-spark.txt
python scripts/local_spark_debug.py
```

This uses **real Spark** readStream of JSON files, bounded `availableNow`, watermark, checkpointed Parquet and a Spark SQL mart. It is not continuously reading from Kafka. Validate actual Spark/Python/Java version compatibility first. Workbook 3 shows how to inspect checkpoints and change failure inputs.

**Beam:** (prefer installed environment; otherwise isolated venv)

```bash
python -m pip install -r requirements-beam.txt
PYTHONPATH=src pytest -q tests/test_beam_optional.py
```

This is a DirectRunner `TestStream` validation of event-time windows. It is not the deployed DataflowRunner and does not prove cloud late-event semantics under load. Workbook 4 covers event-time and watermark experiments.

**Pub/Sub Emulator** (optional if `gcloud` already installed):

```bash
# In one terminal:
gcloud beta emulators pubsub start --host-port=127.0.0.1:8085
# In a second terminal:
export PUBSUB_EMULATOR_HOST=127.0.0.1:8085
python -m pip install -r requirements-gcp.txt
python scripts/gcp_emulator_smoke.py
```

This tests only publish/pull/ack on the emulator. **It does not send records to BigQuery subscriptions.** Cloud Terraform runs only after explicit owner/billing approval.

## 6. Troubleshooting map

| Symptom | Likely cause | First check / non-destructive remedy |
| --- | --- | --- |
| `ModuleNotFoundError: market_pulse` | PYTHONPATH unset in CLI/test session | `PYTHONPATH=src pytest ...`; scripts add `src` to path |
| Bybit WS fails / no messages | ISP/geoblock, WS closed, wrong category/symbol | Test bounded stdout probe; inspect retry logs, DNS, TLS; do not assume live WS always available |
| Kafka connection refused | Wrong bootstrap port/context or broker stopped | `docker context show`, `rpk topic list`; check existing broker before starting new |
| Kafka replay doesn't appear | Same consumer group committed offsets | Inspect group offsets; produce new messages; do not reset shared groups |
| ClickHouse 401/403 | Wrong user/password | Validate credentials using read-only `SELECT version()` |
| ClickHouse 404 / unknown table | DDL not applied / wrong database | Confirm target database, then project-scoped DDL only |
| Duplicate raw rows | At-least-once sink semantics | Inspect `trades_dedup`; aggregate should remain stable after replay |
| Spark Java gateway error | Java/PySpark version mismatch | Check `java -version`, `spark-submit --version`, `python -V` |
| Spark no output | Checkpoint recovered old files / no new files | Use a **fresh isolated** temp fixture path; never delete shared checkpoints |
| Beam test hangs or fails | Different Beam SDK / runner settings | Run optional Beam test alone; capture version and stack trace |
| Pub/Sub smoke contacts cloud | Missing emulator env var | Script refuses without `PUBSUB_EMULATOR_HOST` |
| Dashboard shows old data | Five-second cache and no new ingestion | Check sink counts and Streamlit query refresh independently |
| SQL dialect error | ClickHouse, Spark, BigQuery and Databricks differ | Run each SQL only in its target engine, compare expected fixture results |

## 7. What to record after each run

Record: UTC timestamp, commit hash, OS/architecture, container/Java/Python versions, endpoints *without secrets*, command, test count, row counts, expected vs actual OHLCV, duplicate count, exception traces, raw/silver/gold lag, offset/checkpoint state, and explicit PASS / FAIL / NOT RUN. Use `docs/workbooks/05_fault_injection_and_evidence.md`.

**Stop criteria:** Any unexpected remote endpoint, non-owned service, private credentials, paid cloud operation, destructive cleanup, or unresolved trade identity/precision issue → stop and inspect before continuing.
