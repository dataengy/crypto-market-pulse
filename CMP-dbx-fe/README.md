# CMP-dbx-fe — Crypto Market Pulse on Databricks Free Edition

Bybit public trades → Kafka → Lakeflow pipeline (bronze → silver → dedup → 1m OHLCV → latest) → AI/BI dashboard.
A local Redpanda + Spark + Delta + MiniLake loop runs the same code for dev and debug.
Plan and tasks: [docs/plans/dbx-fe](../docs/plans/dbx-fe/README.md) · backlog: [docs/backlog](docs/backlog).

```
Bybit WS ─ scripts/produce.py ─► Kafka ─┬─► local:  scripts/local_spark.py ─► .tmp/lake/*  (Delta, path-based)
 (or fixture)        CMP_PROFILE ┘      └─► cloud:  pipelines/bronze.py + pipelines/*.sql ─► workspace.crypto_pulse.*
```

| Shared by local and cloud | |
|---|---|
| `src/cmp/kafka.py` | connection/JAAS options; creds come from env locally and from a secret scope in the cloud |
| `src/cmp/bronze.py` | Kafka value → typed rows (`DECIMAL(38,12)` prices) |
| `sql/models/*_select.sql` | portable SELECTs with `{{source}}`; `valid_trade.sql` = the silver quality rule |
| `scripts/build.py` | wraps the models into Lakeflow SQL and builds the dashboard JSON (**generated, do not edit**) |

## Setup
Prerequisites: uv, just, Java 17, and Docker for the local stack. The first Spark run downloads the Delta and Kafka jars from Maven Central.
```bash
just sync && just test          # unit tests (Spark/Kafka/MiniLake tests are opt-in markers)
uv run pytest -m spark          # Spark + Delta check of parse_trades + models, no Kafka needed
```
Config: `config/config.yaml` holds tracked, non-secret settings. `config/.env.common` holds `CMP_PROFILE=local|cloud`. Copy `config/.env.secrets.demo` to `config/.env.secrets` and fill it for cloud runs. Missing keys fail fast and name the file to fill; there are no defaults.

## Local loop (dev and debug only)
```bash
just up                         # Redpanda :19092 + MiniLake :18000, localhost only; reuse existing ones first
just produce fixture            # 8 fixture trades (1 duplicate) → market.trades.v1
just produce bybit --max-trades 200
just spark                      # drain the topic → Delta → print trades_1m / trades_latest
just spark --follow             # keep consuming (processingTime trigger)
just spark --reset              # wipe .tmp/lake + checkpoints (only that dir)
just it                         # E2E: fixture → Redpanda → Spark, exact + restart + replay dedup
just minilake-smoke             # Databricks SDK against the emulator: UC objects, SQL, model portability
just down                       # stop only; never removes volumes
```
Debugging:
- Inspect any table with `uv run pyspark`, then ``spark.read.format("delta").load(".tmp/lake/trades_1m")``.
- Point local Spark at the **cloud** topic with `CMP_PROFILE=cloud just spark`. The same code uses the OSS JAAS module.
- MiniLake runs DuckDB SQL. `TIMESTAMP_MILLIS` / `named_struct` gaps show up as `DIALECT GAP` lines and are not forked.

## Cloud loop (Free Edition)
1. Install the Databricks CLI (≥ 1.16) and run `databricks auth login --host <workspace-url> --profile <name>`. Put the profile name in `config/.env.secrets` as `DATABRICKS_CONFIG_PROFILE`.
2. Create a Kafka cluster, the topic `market.trades.v1` and an API key. Put `KAFKA_*` in `config/.env.secrets`.
3. Run these:
```bash
just dbx-validate && just dbx-secrets && just dbx-deploy
just dbx-probe                  # GATE: can Free Edition serverless reach your Kafka? (egress = trusted domains only)
CMP_PROFILE=cloud just produce fixture
just dbx-run                    # triggered pipeline refresh
just dbx-query "SELECT * FROM workspace.crypto_pulse.trades_1m ORDER BY window_start LIMIT 5"
```
If the probe can't connect, use the Volume + Auto Loader fallback: [docs/backlog/volume-drop-ingest.md](docs/backlog/volume-drop-ingest.md).

The `cmp-refresh` job refreshes every 15 min and is deployed **paused**, to save Free quota. Free Edition allows one active pipeline per type and one 2X-Small warehouse.

## Status (2026-10-30)
Done and tested:
- unit tests
- build sync
- Spark + Delta models on the fixture: exact bar, malformed row dropped, replay deduped
- local Kafka E2E (`just it`): fixture → Redpanda → Spark exact, restart doesn't re-read, producer replay deduped
- MiniLake smoke: SDK UC objects + statements, silver/dedup PASS; `trades_1m`/`trades_latest` hit DuckDB gaps (`TIMESTAMP_MILLIS`, `named_struct`)

Written, not run:
- everything in the cloud: bundle, probe, pipeline, dashboard JSON (needs a workspace login and a Kafka account)
