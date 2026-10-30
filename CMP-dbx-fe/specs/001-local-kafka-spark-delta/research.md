# Research: Local Kafka → Spark → Delta loop

| Decision | Rationale | Alternatives (where tracked) |
|---|---|---|
| Redpanda `v24.3.10` in `--mode=dev-container` | Single binary, Kafka API, topics auto-create, `rpk` healthcheck. Same image as the ClickHouse lane | Apache Kafka KRaft container: heavier, with no benefit for debug |
| PySpark 4.0 + delta-spark 4.0, jars via `spark.jars.packages` | Matches the Databricks serverless Spark major version; no manual jar management | Spark 4.1 SDP for real pipeline parity → [DBX-B2](../../docs/backlog/spark-sdp-parity.md) (waits for delta-spark 4.1) |
| Path-based Delta in `.tmp/lake` | No Hive metastore, so state survives between runs; `--reset` is just `rmtree` | MinIO S3 paths → [DBX-B1](../../docs/backlog/minio-delta-lake.md); Iceberg → [DBX-B3](../../docs/backlog/iceberg-uniform.md) |
| `foreachBatch`: bronze append (`txnAppId/txnVersion`) + model CTAS | A replayed micro-batch is idempotent; the marts are always consistent with bronze | Streaming MVs locally do not exist in OSS Spark 4.0 |
| Query-level dedup (`ROW_NUMBER` by `event_id`) | Bronze and silver stay append-only, like the cloud; the result is identical on both sides | Streaming `dropDuplicatesWithinWatermark`: diverges from the Lakeflow MV semantics |
| MiniLake `ghcr.io/dmux/minilake:1.8.0` | A Databricks REST and SDK surface on localhost; reused from the weather_dfe handoff | none (it is only an emulator; [ADR-0004](../../docs/adr/0004-minilake-dmux-emulator.md)) |

Resolved on 2026-10-30 (`ccb8b63`):
- MiniLake gaps are exactly `trades_1m` and `trades_latest` (`TIMESTAMP_MILLIS`, `named_struct`).
- MiniLake was moved to host port 18000, because port 8000 is taken by an unrelated local process.
