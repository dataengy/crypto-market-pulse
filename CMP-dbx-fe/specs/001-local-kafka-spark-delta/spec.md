# Feature Specification: Local Kafka → Spark → Delta loop

**Feature Branch**: `feat/cmp-dbx-fe`

**Created**: 2026-10-30

**Status**: Implemented and verified. All five stories were green on 2026-10-30 (commit `ccb8b63` for US3 and US5).

**Input**: Reverse-spec of the existing `CMP-dbx-fe/` local loop. Plan: [plan.md](../../../docs/plans/dbx-fe/plan.md), tasks [DBX-L01…L06](../../../docs/plans/dbx-fe/tasks.md#dbx-l01).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Strict config and normalized trades (Priority: P1)
As the lane developer, I get Bybit `publicTrade` messages normalized into immutable events with `event_id = bybit:<category>:<symbol>:<trade_id>`. Every setting comes from `config/config.yaml` and `.env` files, and nothing falls back to a default.

**Why this priority**: every later layer depends on the event shape and on fail-fast config.

**Independent Test**: `just test` (tests `test_domain.py` and `test_config_and_build.py`).

**Acceptance Scenarios**:
1. **Given** a missing config key or env var, **When** it is read, **Then** a `ValueError` names the key and the file to fill.
2. **Given** a WS batch with several trades, **When** it is parsed, **Then** every trade is validated and gets a unique `event_id`. Pings and subscription acks are ignored.

---

### User Story 2 - Shared models, generated cloud SQL (Priority: P1)
As the developer, I edit a SELECT once in `sql/models/` and use it unchanged in local Spark, MiniLake and Lakeflow.

**Why this priority**: it is what makes the local loop a faithful stand-in for the cloud.

**Independent Test**: `just verify`. It rebuilds the generated files, runs the unit tests, and runs `git diff --exit-code` on `pipelines/` and `dashboards/`.

**Acceptance Scenarios**:
1. **Given** a model edit, **When** `just build` has not been run, **Then** `test_generated_files_are_in_sync` fails and names the stale file.
2. **Given** `valid_trade.sql`, **When** it is built, **Then** it becomes the `EXPECT … ON VIOLATION DROP ROW` in the cloud and a `WHERE` locally.

---

### User Story 3 - Fixture through Redpanda gives the exact bar (Priority: P1) 🎯 MVP
As the developer, I run `just up && just produce fixture && just spark` and see the BTCUSDT 10:00 bar `4 / 0.45 / 70000 / 70010 / 69990`.

**Why this priority**: this is the end-to-end proof that the local stack is debuggable.

**Independent Test**: `just it`.

**Acceptance Scenarios**:
1. **Given** a fresh isolated topic with the fixture, **When** `local_spark.run` runs with `availableNow`, **Then** bronze has 8 rows and the bar is exact.
2. **Given** the same checkpoint, **When** it is rerun with no new messages, **Then** bronze still has 8 rows (no double read).
3. **Given** the fixture is produced again, **When** it is rerun, **Then** bronze has 16 rows and `trades_dedup` stays at 7.

---

### User Story 4 - Spark + Delta check without Kafka (Priority: P2)
As the developer, I can verify `parse_trades` and the models on Kafka-shaped rows without Docker.

**Independent Test**: `uv run pytest -m spark`.

**Acceptance Scenarios**:
1. **Given** fixture lines plus `"not json"`, **When** the models are built, **Then** the malformed row is dropped in silver, dedup = 7, and the bar is exact.
2. **Given** a full replay, **When** the models are rebuilt, **Then** the marts are unchanged. `trades_latest`: ETHUSDT `last_price 3502`, BTCUSDT `total_trades 5`.

---

### User Story 5 - MiniLake SDK smoke (Priority: P3)
As the developer, I can exercise the Databricks SDK, the UC object calls and the SQL statement API against a local emulator.

**Independent Test**: `just minilake-smoke`.

**Acceptance Scenarios**:
1. **Given** MiniLake on `127.0.0.1:18000`, **When** the smoke runs, **Then** the catalog and schema are created via the SDK and the table via SQL (`tables.create` needs `storage_location` in newer SDKs), the fixture INSERT succeeds, and silver and dedup PASS with dedup = 7.
2. **Given** a DuckDB dialect gap (`TIMESTAMP_MILLIS`, `named_struct`), **When** a model fails, **Then** a `DIALECT GAP <model>` line is printed and no SQL is forked.
3. **Given** a non-localhost `minilake.host`, **When** the smoke starts, **Then** it refuses to run.

### Edge Cases
- A malformed Kafka value becomes NULL fields in bronze, which silver drops.
- A duplicate `event_id` from a producer replay: first arrival wins (ordered by `received_at_ms, event_time_ms, trade_id`).
- Credentials containing `"` are rejected, since they would break the JAAS syntax.
- `CMP_PROFILE=cloud just spark` reads the cloud topic with the OSS login module.
- The first Spark run needs Maven Central (Kafka and Delta jars). Offline, it fails at session start.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Config is read strictly from `config/config.yaml` and `config/.env.{common,secrets}`; a missing key raises an error naming it ([constitution II](../../.specify/memory/constitution.md#ii-no-defaults-fail-fast)).
- **FR-002**: The Kafka value contract is [contracts/kafka-trade-event.md](contracts/kafka-trade-event.md).
- **FR-003**: `parse_trades` yields bronze columns with `DECIMAL(38,12)` prices plus `kafka_partition/offset/timestamp`.
- **FR-004**: The models follow [contracts/sql-model.md](contracts/sql-model.md): exactly one `{{source}}` each.
- **FR-005**: Local tables are path-based Delta under `spark.lake_dir`. Bronze appends are idempotent per micro-batch (`txnAppId/txnVersion`), and the marts are rebuilt with CTAS ([ADR-0001](../../docs/adr/0001-path-based-delta-locally.md)).
- **FR-006**: Local services bind to localhost; `just down` never removes volumes ([constitution IV](../../.specify/memory/constitution.md#iv-local-runtime-is-devdebug-only-and-is-reused-before-it-is-created)).

### Key Entities
See [data-model.md](data-model.md): trade event, `trades_bronze`, `trades_silver`, `trades_dedup`, `trades_1m`, `trades_latest`.

## Success Criteria *(mandatory)*
- **SC-001**: `just test` and `uv run pytest -m spark` are green. Done: 14 tests, 2026-10-30.
- **SC-002**: `just it` is green. Done: 2026-10-30.
- **SC-003**: `just minilake-smoke` prints `MiniLake smoke PASS`, with gaps on `trades_1m` and `trades_latest`. Done: 2026-10-30.
- **SC-004**: `find_hardcoded_scalars.py` on `src/` and `scripts/` flags only schema and bootstrap constants.

## Assumptions
- Java 17, uv and just are installed. Docker (Desktop or Colima) works for US3 and US5.
- PySpark 4.0.x with delta-spark 4.0.x. The Kafka connector version follows `pyspark.__version__`.
