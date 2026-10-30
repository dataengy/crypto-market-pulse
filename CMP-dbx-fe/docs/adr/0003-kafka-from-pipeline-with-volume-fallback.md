# 0003 — Pipeline reads Kafka directly; UC Volume push is the gated fallback

- Status: accepted. The Kafka path is the default; the fallback is pending the [DBX-C02](../../../docs/plans/dbx-fe/tasks.md#dbx-c02) gate.
- Date: 2026-10-30
- Specs: [002](../../specs/002-dbx-fe-pipeline-deploy/spec.md), [003](../../specs/003-no-kafka-volume-ingest/spec.md)

## Context and Problem Statement
Kafka is the fan-out bus shared with the ClickHouse lane. Free Edition serverless limits outbound internet to trusted domains, so whether the pipeline can reach a managed Kafka broker is unknown.

## Considered Options
1. `trades_bronze` = `spark.readStream.format("kafka")` inside the pipeline (pull)
2. Shipper (Kafka → JSONL) → UC Volume via the Files API → Auto Loader (inbound push)
3. SQL warehouse `INSERT` ([DBX-AB1](../../../docs/plans/dbx-fe/tasks.md#dbx-ab1))
4. Zerobus Ingest ([DBX-AB2](../../../docs/plans/dbx-fe/tasks.md#dbx-ab2))

## Decision Outcome
Chosen: **option 1 first**, because it has no extra process and uses the same `parse_trades` as local. A probe job decides. **Option 2 replaces only the bronze source** if the probe fails; everything from silver onward is unchanged. Option 3 keeps the single warehouse awake. Option 4 is unconfirmed on Free Edition. Details: [alt-no-kafka.md](../../../docs/plans/dbx-fe/alt-no-kafka.md#a-decision).

### Consequences
- Good: the decision is made with one cheap job run, before any pipeline debugging.
- Bad: option 2 adds a long-running shipper outside Databricks (laptop or GH Actions).
- The switch is the pipeline conf `cmp.bronze_source: kafka|volume`, with no default.
