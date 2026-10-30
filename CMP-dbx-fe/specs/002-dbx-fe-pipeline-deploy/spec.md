# Feature Specification: Databricks Free Edition pipeline deploy and verify

**Feature Branch**: `feat/cmp-dbx-fe`

**Created**: 2026-10-30

**Status**: Code written (`databricks.yml`, `pipelines/`, `scripts/dbx_kafka_probe.py`, `dashboards/`). **Nothing has run in the cloud yet.**

**Input**: Lane plan [Steps 6–7](../../../docs/plans/dbx-fe/plan.md#steps), tasks [DBX-C01…C05](../../../docs/plans/dbx-fe/tasks.md#dbx-c01). Depends on [spec 001](../001-local-kafka-spark-delta/spec.md) US3.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gate: can Free Edition read our Kafka? (Priority: P1)
As the lane owner, I learn with one job run whether serverless can reach the managed Kafka broker, before investing in the cloud pipeline.

**Why this priority**: Free Edition limits egress to trusted domains. If the gate fails, the cloud ingest path changes to [spec 003](../003-no-kafka-volume-ingest/spec.md).

**Independent Test**: `just dbx-secrets && just dbx-deploy && just dbx-probe`.

**Acceptance Scenarios**:
1. **Given** filled `config/.env.secrets` and a secret scope, **When** `cmp-kafka-probe` runs, **Then** it prints `TCP OK: <host>:<port>` and `Kafka SASL read OK: … N messages`.
2. **Given** the egress is blocked, **When** the probe runs, **Then** it fails at the TCP connect with a timeout error. The decision is recorded and work moves to DBX-A01.

---

### User Story 2 - Triggered pipeline reproduces the fixture bar (Priority: P1) 🎯 MVP
As the lane owner, I deploy the bundle, produce the fixture to cloud Kafka, run the pipeline once, and get the same bar as locally.

**Independent Test**: `CMP_PROFILE=cloud just produce fixture && just dbx-run && just dbx-query "<bar query>"`.

**Acceptance Scenarios**:
1. **Given** a deployed `cmp-market-pulse`, **When** it is refreshed, **Then** all 5 datasets materialize and the event log shows `valid_trade` drops (0 for the fixture).
2. **Given** a fixture-only topic, **When** `trades_1m` is queried, **Then** BTCUSDT 10:00 = `4 / 0.45 / 70000 / 70010 / 69990` and `trades_dedup` = 7.
3. **Given** the fixture is produced again, **When** the pipeline is refreshed, **Then** the bar and dedup are unchanged.

---

### User Story 3 - Live data and dashboard within Free limits (Priority: P2)
As a viewer, I open the "Crypto Market Pulse" AI/BI dashboard and see 1-minute close, VWAP and volume for `dashboard.symbol`.

**Independent Test**: `CMP_PROFILE=cloud just produce bybit --max-trades 200`, then `just dbx-run`, then open the dashboard.

**Acceptance Scenarios**:
1. **Given** live trades, **When** one refresh completes, **Then** new bars appear on the dashboard.
2. **Given** the demo ends, **When** the owner leaves it, **Then** `cmp-refresh` is `PAUSED` and no pipeline is running.

### Edge Cases
- The fixture minute is a real timestamp (2026-10-30), so live BTCUSDT trades in that minute would change the bar. Use a fixture-only topic or cluster. **[NEEDS CLARIFICATION: the topic name is a single key `kafka.topic` read by the pipeline. Options: a temporary `config.yaml` edit on a throwaway branch, a second Kafka cluster, or a separate run before any live produce.]**
- A secret value with `"` is rejected by `spark_kafka_options`, because of the JAAS syntax.
- A second active pipeline in the workspace: Free Edition allows one per type, so the deploy or run fails. Stop the other one first.
- `Serverless Starter Warehouse` was renamed or is missing, so the `warehouse_id` lookup fails at `bundle validate`.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: Kafka creds reach the pipeline only through the secret scope `${var.secret_scope}`, with the keys `kafka_bootstrap`, `kafka_api_key` and `kafka_api_secret` ([contract](contracts/bundle-and-secrets.md)).
- **FR-002**: The pipeline is serverless and triggered. Its catalog and schema are set in the bundle, so the SQL is unqualified.
- **FR-003**: `pipelines/*.sql` and the dashboard JSON are generated (`just build` runs before `dbx-validate` and `dbx-deploy`).
- **FR-004**: The refresh job is deployed `PAUSED` ([ADR-0005](../../docs/adr/0005-triggered-pipeline-paused-job.md)).
- **FR-005**: The bronze source is the shared `cmp.bronze.parse_trades` with the shaded login module `kafka.jaas_login_module.databricks`.

### Key Entities
Same as [001 data-model](../001-local-kafka-spark-delta/data-model.md), materialized in `${catalog}.${schema}` (`workspace.crypto_pulse`).

## Success Criteria *(mandatory)*
- **SC-001**: The DBX-C02 probe result is recorded in `README.md › Status`, as either a pass or a switch to DBX-A.
- **SC-002**: The DBX-C04 query output equals the local bar.
- **SC-003**: After DBX-C05, the workspace has 1 pipeline, the 1 starter warehouse, and `cmp-refresh` PAUSED.

## Assumptions
- The user owns the Databricks Free Edition login and the Kafka account (Confluent Cloud Basic by default; provider choice is [DBX-B5](../../docs/backlog/kafka-provider-choice.md)). The agent never selects a CLI profile on its own.
- Databricks CLI ≥ 1.16 is installed. The bundle syntax (`pipelines.environment`, `dashboards.dataset_catalog`) is assumed to be current. **Unverified**: `bundle validate` is the first check.
