# 0001 — Path-based Delta tables + CTAS rebuild for the local loop

- Status: accepted (implemented, DBX-L04)
- Date: 2026-10-30
- Spec: [001](../../specs/001-local-kafka-spark-delta/spec.md)

## Context and Problem Statement
Local Spark has to stand in for Lakeflow streaming tables and MVs. It has to persist between runs, support `--reset`, and stay idempotent under Kafka replays. It cannot need any services beyond Redpanda.

## Considered Options
1. Path-based Delta (`` delta.`<lake>/<table>` ``): bronze append in `foreachBatch`, then CTAS of the four models
2. A Hive metastore / Derby `spark-warehouse` with named tables
3. MinIO + S3A paths ([DBX-B1](../backlog/minio-delta-lake.md))
4. Spark 4.1 Declarative Pipelines ([DBX-B2](../backlog/spark-sdp-parity.md))

## Decision Outcome
Chosen: **option 1**, because it needs no catalog state, reset is `rmtree(.tmp/lake)`, and replay-safety comes from Delta `txnAppId/txnVersion` (bronze) plus query-level dedup (marts).

### Consequences
- Good: zero extra containers; tests use `tmp_path`; a table opens with `spark.read.format("delta").load(path)`.
- Bad: it is not real pipeline semantics, since the marts are fully rebuilt every batch. That is fine for debug volumes, but it is not a perf proxy.
- Bad: the paths differ from the cloud's UC names. The models hide this behind `{{source}}` ([ADR-0002](0002-shared-sql-models-and-build.md)).
