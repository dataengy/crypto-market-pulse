# Proposal

## Why

The ClickHouse lane exists only as a plan ([docs/plans/clickhouse](../../../../docs/plans/clickhouse/README.md)) and a reference handoff that was never run. A local loop of Redpanda, ClickHouse, a Python consumer and Streamlit has to pass the fixture gate before any cloud work: every CH-C task depends on [CH-L07](../../../../docs/plans/clickhouse/tasks.md#ch-l07).

## What Changes

- A new standalone project `CMP-ch/` (uv, py3.12, justfile) with strict config. Domain, Bybit WS and publisher code are copied from the reference/CMP-dbx-fe, with their scalars moved to config. Covers CH-L01 and CH-L02.
- Runtime discovery, plus a project-owned compose stack that is used only when no compatible service runs. Covers CH-L03 and CH-L10.
- The shared ClickHouse DDL: `trades_raw` → MV → `trades_dedup` (ReplacingMergeTree) → `trades_1m` / `trades_latest` views over `FINAL`. Covers CH-L04.
- A producer with `fixture|bybit` sources, and an at-least-once Python consumer into `trades_raw`. Covers CH-L05 and CH-L06.
- `just verify` / `just it`: the fixture assertion plus an idempotent rerun, fault-injection evidence and hermetic CI. Covers CH-L07, CH-L08 and CH-L11.
- A Streamlit dashboard with a read-only user and a stale badge. Covers CH-L09.

Out of scope:
- Kafka-engine ingest: [CH-LB1](../../../../docs/plans/clickhouse/tasks.md#ch-lb1)
- Materialized 1m mart: CH-LB2
- Grafana: CH-LB3
- Anything cloud: `add-clickhouse-cloud-clickpipes`

## Capabilities

### New Capabilities
- `project-config`: strict config and secrets loading; fail fast with the key name and the file to fill; no scalars in code.
- `local-runtime`: discover and reuse existing services, owned containers, a safe `down`, read-only debug recipes.
- `ingest`: producer to Kafka, and at-least-once Kafka → `trades_raw` with poison stop and idle exit.
- `storage-dedup`: raw keeps duplicates; dedup by `event_id`; idempotent, guarded DDL.
- `ohlcv-marts`: 1m OHLCV and latest price views, the fixture assertion, and the late/out-of-order policy.
- `dashboard`: a read-only Streamlit view of the marts with a staleness badge.

### Modified Capabilities

## Impact

- New dir `CMP-ch/` only. Nothing in `CMP-dbx-fe/` or the reference project is modified.
- Dependencies: confluent-kafka, clickhouse-connect, websockets, pyyaml, python-dotenv, streamlit, pandas, pytest.
- Docker access needs a user-approved sandbox bypass. Agents ask before `just up`.
- Decisions: [ADR-0001](../../../docs/adr/0001-python-consumer-over-kafka-engine.md), [ADR-0002](../../../docs/adr/0002-replacingmergetree-with-final-views.md), [ADR-0004](../../../docs/adr/0004-streamlit-dashboard.md).
