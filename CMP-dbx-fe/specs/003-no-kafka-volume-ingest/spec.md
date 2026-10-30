# Feature Specification: No-Kafka ingest via UC Volume + Auto Loader

**Feature Branch**: `feat/cmp-dbx-fe`

**Created**: 2026-10-30

**Status**: Draft (conditional). It is activated only if the [002 gate](../002-dbx-fe-pipeline-deploy/spec.md) (DBX-C02) shows that Free Edition cannot reach Kafka.

**Input**: [alt-no-kafka.md](../../../docs/plans/dbx-fe/alt-no-kafka.md), which holds the decision, steps and risks, and tasks [DBX-A01…A07](../../../docs/plans/dbx-fe/tasks.md#dbx-a). This spec adds stories and acceptance only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One probe decides the path (Priority: P1)
As the lane owner, I run one probe and know whether to use the Kafka path, the Volume path, or stop.

**Independent Test**: `just dbx-probe`, extended in DBX-A01.

**Acceptance Scenarios**:
1. **Given** the deployed probe, **When** it runs, **Then** it prints 4 results: TCP bootstrap, HTTPS Kafka REST, the trusted control host (`probe.control_url`), and `ls` of the landing Volume.
2. **Given** (a) fails and (d) works, **When** the result is read, **Then** the README status records "Volume path" and 003 starts.
3. **Given** (d) fails, **Then** stop and ask the user.

---

### User Story 2 - Fixture through the shipper gives the same bar, locally (Priority: P1) 🎯 MVP
As the developer, I ship the fixture through the shipper into `.tmp/landing` and get the same bar from `local_spark.py --bronze-source volume`.

**Independent Test**: `just it`, with a new Volume-path integration test (DBX-A05).

**Acceptance Scenarios**:
1. **Given** the fixture → Redpanda → shipper → `.tmp/landing`, **When** Spark reads it, **Then** BTCUSDT 10:00 = `4 / 0.45 / 70000 / 70010 / 69990`.
2. **Given** the same offsets are re-shipped (a crash between upload and commit), **When** Spark reruns, **Then** `trades_dedup` = 7 and the bar is unchanged.

---

### User Story 3 - Cloud over the Volume (Priority: P1)
As the lane owner, I deploy with `bronze_source=volume`, ship the fixture inbound, refresh, and get the same bar.

**Independent Test**: `just ship --source fixture && just dbx-run && just dbx-query …` (DBX-A06).

**Acceptance Scenarios**:
1. **Given** a deployed `landing` Volume, **When** the fixture is shipped and refreshed, **Then** the bar equals the DBX-C04 expectation.
2. **Given** the fixture is shipped and run a second time, **Then** the bar is unchanged.

---

### User Story 4 - Off-laptop shipper (Priority: P3)
A bounded `workflow_dispatch` GH Actions job runs Bybit → Kafka → Volume, then `bundle run` (DBX-A07).

### Edge Cases
- A poison message stops the shipper without committing, so nothing is lost.
- An idle topic: the shipper exits after `volume.idle_exit_s`.
- The Files API size limit is unknown, so `volume.max_batch_bytes` stays at a few MB.
- Many tiny files: batch for ≥ 30 s (the interval comes from config).
- `cmp.bronze_source` is unset: the pipeline fails at start. There is no default, by [constitution II](../../.specify/memory/constitution.md#ii-no-defaults-fail-fast).

## Requirements *(mandatory)*
- **FR-001**: The landing file contract is [contracts/landing-file.md](contracts/landing-file.md).
- **FR-002**: `pipelines/bronze.py` switches on `cmp.bronze_source: kafka|volume`. The Volume branch is Auto Loader `cloudFiles` JSON with `TRADE_SCHEMA`, then the same `parse_trades` projection.
- **FR-003**: Everything from silver onward is unchanged; there is no new SQL model.
- **FR-004**: `VolumePublisher` takes any target with `upload(path, bytes)`: the SDK `files.upload` in the cloud, a directory writer locally.
- **FR-005**: The shipper commits Kafka offsets only after a successful upload (at-least-once), and dedup absorbs the replays.
- **FR-006**: New values live under `config.yaml: volume.*` and `probe.*`, read strictly.

### Key Entities
See [data-model.md](data-model.md): landing Volume, landing file. All other tables are as in [001](../001-local-kafka-spark-delta/data-model.md).

## Success Criteria *(mandatory)*
- **SC-001**: `just test` covers `VolumePublisher` naming, idempotency and the bronze-source rendering.
- **SC-002**: The local and cloud bars are both equal to `4 / 0.45 / 70000 / 70010 / 69990`, and stay so after a re-ship.
- **SC-003**: `find_hardcoded_scalars.py` is clean on the new `src/` and `scripts/` files.

## Assumptions
- Volumes, the Files API and Auto Loader (directory listing) work on Free Edition serverless. **Unverified**: DBX-A01 checks them.
- Kafka stays the fan-out bus shared with the ClickHouse lane, so producer → Volume directly is only a by-product.
