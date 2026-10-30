# Implementation Plan: Local Kafka → Spark → Delta loop

**Branch**: `feat/cmp-dbx-fe` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: [spec.md](spec.md). Approved lane plan: [docs/plans/dbx-fe/plan.md](../../../docs/plans/dbx-fe/plan.md) (Steps 0–5). This file records the *as-built* design and does not repeat that plan.

## Summary
The producer sends fixture or Bybit trades to Kafka (Redpanda locally). `scripts/local_spark.py` reads them with Structured Streaming (`availableNow` or `processingTime`) and `foreachBatch`. Each batch is appended to path-based bronze Delta, then the four shared models are rebuilt as Delta CTAS. The same `cmp.*` code and the same `sql/models` are used by the cloud pipeline ([spec 002](../002-dbx-fe-pipeline-deploy/spec.md)).

## Technical Context
**Language/Version**: Python 3.12 (uv), Java 17

**Primary Dependencies**: pyspark 4.0.x, delta-spark 4.0.x, confluent-kafka, websockets, pyyaml, python-dotenv, databricks-sdk (MiniLake)

**Storage**: path-based Delta under `spark.lake_dir` (`.tmp/lake`)

**Testing**: pytest. The markers `spark`, `integration` and `minilake` are opt-in (`pyproject.toml addopts`).

**Target Platform**: a dev laptop (macOS) with Docker for Redpanda `v24.3.10` and MiniLake `1.8.0`

**Project Type**: data pipeline (CLI scripts + library `src/cmp`)

**Constraints**: localhost-only services; the first run downloads jars from Maven Central; no metastore between runs

**Scale/Scope**: 2 symbols; a fixture of 8 events; live Bybit only for smoke runs

## Constitution Check
| Gate | Status |
|---|---|
| I. no hardcoded scalars | pass. WS, Kafka, Spark and MiniLake values are in `config.yaml`. The checker flags only schema constants (DBX-L02) |
| II. no defaults | pass. `settings.get` / `settings.env` are strict (`test_strict_config_and_env`) |
| III. secrets | pass. The local profile is PLAINTEXT with no creds; the cloud creds come only from `.env.secrets` |
| IV. local reuse | pass. `compose.yml` uses `cmp-dbx-*` names, `127.0.0.1` binds and `down` = `stop` |
| V. ponytail | pass. There is no pipeline framework locally; a 90-line loop replaces SDP until [DBX-B2](../../docs/backlog/spark-sdp-parity.md) |
| VI. shared code | pass. `parse_trades`, `kafka.*`, `sql/models` and `build.py` are shared |
| VII. fixture | pass: unit Spark (US4) and Kafka E2E (US3). MiniLake asserts dedup = 7 only, because of the dialect gaps (US5) |

## Project Structure
### Documentation (this feature)
```text
specs/001-local-kafka-spark-delta/
├── spec.md  plan.md  research.md  data-model.md  quickstart.md  tasks.md
└── contracts/  kafka-trade-event.md  sql-model.md
```
### Source Code (as built)
```text
src/cmp/      settings.py domain.py bybit_ws.py publish.py kafka.py bronze.py sql_models.py reference.py
sql/models/   10_silver_select.sql 20_dedup_select.sql 30_1m_select.sql 40_latest_select.sql valid_trade.sql
scripts/      produce.py local_spark.py build.py minilake_smoke.py
tests/        test_domain.py test_config_and_build.py test_spark_models.py test_integration_kafka.py fixtures/trades.jsonl
compose.yml justfile config/
```
**Structure Decision**: a single uv project. Generated files (`pipelines/*.sql`, `dashboards/*.json`) belong to spec 002 but are built from this feature's models.

## Design decisions
- Path-based Delta + CTAS rebuild locally: [ADR-0001](../../docs/adr/0001-path-based-delta-locally.md)
- Shared `sql/models` + `build.py` generator: [ADR-0002](../../docs/adr/0002-shared-sql-models-and-build.md)
- MiniLake (dmux) as an SDK/UC emulator, not as a lake: [ADR-0004](../../docs/adr/0004-minilake-dmux-emulator.md)
- Architecture diagram: [docs/design/architecture.md](../../docs/design/architecture.md)

## Complexity Tracking
None.
