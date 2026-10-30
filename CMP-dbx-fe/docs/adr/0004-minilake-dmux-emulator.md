# 0004 — MiniLake (dmux) as a local Databricks SDK/UC/SQL emulator only

- Status: accepted. Verified on 2026-10-30 (DBX-L06, `ccb8b63`).
- Date: 2026-10-30
- Spec: [001 US5](../../specs/001-local-kafka-spark-delta/spec.md)

## Context and Problem Statement
The SDK calls (catalogs, schemas, tables, statement execution) and model portability need a check without a cloud login. MiniLake (`ghcr.io/dmux/minilake:1.8.0`) emulates the Databricks REST API on DuckDB. It has no auth, no Delta, no Lakeflow and no Kafka.

## Considered Options
1. MiniLake for the SDK and SQL smoke only, with dialect gaps reported and no SQL fork
2. MiniLake as the local lake, instead of Spark + Delta
3. No emulator; check the SDK only against the real workspace

## Decision Outcome
Chosen: **option 1**, the simplest setup (a user decision in the [plan](../../../docs/plans/dbx-fe/plan.md#context)). Spark + Delta remains the semantic reference ([ADR-0001](0001-path-based-delta-locally.md)).

### Consequences
- Good: the SDK code path can be tested offline. `minilake_smoke.py` refuses any non-localhost host.
- Bad: DuckDB lacks `TIMESTAMP_MILLIS` and `named_struct`, so `trades_1m` and `trades_latest` report `DIALECT GAP` (confirmed). Only silver and dedup are asserted.
- Security: the port is bound to `127.0.0.1:18000` only, because there is no authentication.
- Bad: newer SDKs require `storage_location` for `tables.create`, so the smoke creates bronze with SQL instead.
