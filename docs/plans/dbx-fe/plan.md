# CMP-dbx-fe — Crypto Market Pulse on Databricks Free Edition + local RP/Spark/MiniLake

## Context
`crypto-market-pulse-chatgpt/project` (an untracked ChatGPT handoff) has a clean domain core: Bybit WS → `normalize_trade`, with dedup by `event_id` and event-time 1m OHLCV. Its Databricks lane is the least finished part:
- the bundle has no targets and no job
- nothing writes bronze except a fixture-replay notebook
- the SQL hardcodes `workspace.crypto_pulse`
- the local Spark path reads files, not Kafka, and writes Parquet
- MiniLake is referenced, but its compose file and smoke script stayed in `baseline/weather_dfe_handoff.zip`
- none of it was ever run

The goal is a standalone `./CMP-dbx-fe/` with the same logic in two places:
- **Cloud:** a producer feeds a managed Kafka (Confluent Cloud by default; any SASL_SSL Kafka works by config), and a Databricks Free Edition serverless pipeline turns it into bronze → silver → dedup → 1m → latest, then an AI/BI dashboard.
- **Local:** dev and debug only. Redpanda → PySpark Structured Streaming → local Delta tables, plus the dmux MiniLake emulator for SDK, UC and SQL checks.

User decisions:
- The local stack is for debug only. Production goes to cloud Kafka plus Databricks.
- MiniLake uses the simplest setup now; the other options become plans and tasks.
- The user didn't answer the code-reuse question, so I'm going with a standalone copy (the recommended option).

**Main risk:** Free Edition limits serverless egress to "trusted domains". Whether the workspace can reach `*.confluent.cloud:9092` is unknown, so step 6 is a gate that checks it before cloud work continues.

## Layout (new, `CMP-dbx-fe/`)
```
README.md                  quickstart: local loop, cloud loop, debug tips
pyproject.toml             uv; py3.12; pyspark 4.0.x, delta-spark 4.0.x, confluent-kafka, websockets, databricks-sdk, pyyaml, pytest
justfile                   up/down, produce, spark, minilake-smoke, build, test, dbx-* targets
compose.yml                cmp-redpanda (127.0.0.1:19092) + minilake (ghcr.io/dmux/minilake:1.8.0, 127.0.0.1:8000, no auth)
config/config.yaml         symbols, topic, watermark, spark packages, table names, profiles.local|cloud (non-secret)
config/.env.common         CMP_PROFILE etc.
config/.env.secrets.demo   KAFKA_BOOTSTRAP / KAFKA_API_KEY / KAFKA_API_SECRET (cloud), DATABRICKS_CONFIG_PROFILE
src/cmp/
  domain.py   bybit_ws.py  publish.py      copied from source; hardcoded ping/backoff/ts-bounds → config
  settings.py                              rewritten: strict yaml + env, no defaults, fail with key + file name
  bronze.py                                pure: kafka_options(cfg, secrets), parse_trades(df) — shared by local Spark and DBX pipeline
  sql_models.py                            model_sql(name, source) renderer (pattern from weather_dfe build_pipeline_sql.py)
sql/models/{10_silver,20_dedup,30_1m,40_latest}_select.sql   portable SELECTs with one {{source}}; ported from source sql/databricks/*.sql
pipelines/bronze.py        DBX: @dp.table streaming from Kafka via cmp.bronze (secrets from scope)
pipelines/{10..40}_*.sql   GENERATED (CREATE OR REFRESH STREAMING TABLE / MATERIALIZED VIEW + EXPECT) — do not edit
scripts/produce.py         --source bybit|fixture → Kafka of the active profile
scripts/local_spark.py     Redpanda → bronze Delta (availableNow|processingTime, checkpoint) → models in batch → print/assert
scripts/minilake_smoke.py  SDK: create catalog/schema/table, insert fixture, run portable models + dashboard query
scripts/build.py           render pipelines/*.sql + dashboards/market_pulse.lvdash.json
scripts/dbx_kafka_probe.py notebook/job task: reachability check of cloud Kafka from DFE serverless
databricks.yml             vars (catalog, schema, warehouse_id, topic), target dev (mode: development, profile from env),
                           pipeline (serverless, triggered, catalog/schema set → unqualified names in SQL),
                           job (pipeline task on a cron, PAUSED by default to save quota), dashboard (dataset_catalog/schema)
tests/                     unit + integration (marker: needs docker) + fixtures/trades.jsonl
docs/backlog/*.md          plans and tasks for the alternatives (see step 8)
```

## Steps
0. **Branch:** `git switch -c feat/cmp-dbx-fe`. Leave `crypto-market-pulse-chatgpt/` untouched as the reference.
1. **Core copy and cleanup.**
   - Copy `domain.py`, `bybit_ws.py`, `publish.py`, `tests/fixtures/trades.jsonl` and `tests/test_domain.py` from the source `src/market_pulse/` into `src/cmp/`. Drop the ClickHouse, GCP and Beam parts.
   - Rewrite `settings.py` to read strictly, with no defaults.
   - Move the hardcoded scalars into `config/config.yaml`: the 20 s ping, the 30 s backoff cap, the timestamp bounds and the drain size.
   - Reference OHLCV for tests: carry over `beam_pipeline.compute_stats`, the pure-Python one, as `cmp/reference.py`.
2. **Shared SQL models and build.**
   - Turn source `sql/databricks/010..040` into `{{source}}` SELECTs.
   - `scripts/build.py` generates the pipeline SQL and the dashboard JSON (dashboard logic from source `scripts/build_databricks_dashboard.py`).
   - A test checks that the generated files are in sync.
3. **Local stack.**
   - `compose.yml`: Redpanda (from source `infra/clickhouse/compose.yml`, with a healthcheck added) plus MiniLake (from the weather_dfe compose). Both bind to localhost only.
   - Follow the source `LOCAL_RUNTIME_REUSE_POLICY`: reuse running containers, and `down` never removes volumes it doesn't own.
4. **Local Spark loop.**
   - `local_spark.py` runs with `spark.jars.packages` set to `spark-sql-kafka-0-10_2.13` + `delta-spark` (versions in config) and a local warehouse in `CMP-dbx-fe/.tmp/lake`.
   - It applies `cmp.bronze.parse_trades`, writes bronze Delta with a checkpoint, then runs the 4 models through `sql_models` as Delta tables.
   - Integration test: fixture → Redpanda → Spark → 1m BTCUSDT 10:00 bucket gives `trade_count=4, volume=0.45, open 70000, high 70010, close 69990`. A second run with the same checkpoint produces no double count.
5. **MiniLake smoke.** Port weather `minilake_smoke.py`: the localhost-only guard, UC objects, fixture insert, the models and the dashboard query. Where DuckDB's dialect diverges (e.g. `TIMESTAMP_MILLIS`), document it and skip that query; don't fork the SQL.
6. **Cloud gate: Kafka egress from DFE.**
   - The user installs the Databricks CLI (≥ 1.16; it isn't installed now), runs `databricks auth login`, and picks the profile. I won't auto-select one.
   - `just dbx-secrets` loads Kafka creds from `config/.env.secrets` into a secret scope.
   - Deploy and run `dbx_kafka_probe` as a job task.
   - **If blocked:** stop and switch to the Volume-drop fallback (backlog item), then ask.
7. **Databricks bundle.**
   - `databricks bundle validate`, then `deploy -t dev`.
   - Run the producer (`--source fixture`, then `bybit`) against cloud Kafka, then `bundle run` the pipeline.
   - Query `trades_1m` with `databricks experimental aitools tools query` and compare it with the local result for the fixture.
   - Dashboard deployed.
   - Free Edition limits respected: 1 active pipeline, a 2X-Small warehouse, the job paused by default.
8. **Backlog plans and tasks** in `docs/backlog/`. Each is a short md with goal, steps, acceptance and a `- [ ]` checklist:
   - `minio-delta-lake.md`: S3-compatible MinIO plus Delta as the local lake.
   - `spark-sdp-parity.md`: run the same pipeline definition locally with Spark 4.1 Declarative Pipelines.
   - `iceberg-uniform.md`: local Iceberg (REST catalog) / DBX UniForm.
   - `volume-drop-ingest.md`: fallback if DFE can't reach Kafka. A shipper writes JSONL to a UC Volume, then `STREAM read_files`.
   - `kafka-provider-choice.md`: compare Confluent, Aiven free tier, Redpanda Serverless, MSK Serverless, GCP Managed Kafka, YC/MWS Managed Kafka, and self-hosted on Hetzner.
   - `hosted-producer.md`: run the producer off the laptop (GH Actions, Hetzner, or a Databricks App, if egress allows it).
   - `ci.md`: unit + build-sync in GH Actions, plus an optional MiniLake workflow.
9. **Docs.** `README.md` covers the local loop, the cloud loop, the env files to fill and debugging. One page; no copying of the source docs.

## Verification
- `just test`: unit tests (domain, settings strictness, model rendering, build sync).
- `just up && just produce fixture && just spark`: prints the 1m bars. The integration test asserts the fixture values and idempotent rerun.
- `just minilake-smoke` → PASS.
- `just dbx-validate`, then the probe job, deploy, pipeline run, and the `trades_1m` query matching local. The cloud steps need the user's Databricks login and Kafka creds.
- `python3 ~/.ai/skills/_scripts/utils/find_hardcoded_scalars.py` on the new `src/` and `scripts/`.

## Notes / constraints
- Docker socket access is blocked by the sandbox, so `compose` commands need an approved sandbox bypass.
- Spark 4.0 needs Java 17 (present). System Python is 3.9, so use `uv` for 3.12.
- Push and PR only after the user confirms.
