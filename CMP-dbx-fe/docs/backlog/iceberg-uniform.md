# DBX-B3 — Iceberg locally / UniForm in Databricks

**Goal:** the lake readable as Iceberg by other engines (DuckDB, Trino, ClickHouse). ← [tasks](../../../docs/plans/dbx-fe/tasks.md#dbx-b3)

**Steps**
- [ ] Cloud: enable UniForm (`delta.universalFormat.enabledFormats = 'iceberg'`) on `trades_1m`/`trades_latest`; check Free Edition support and the UC Iceberg REST endpoint
- [ ] Local: an Iceberg REST catalog container (e.g. `apache/iceberg-rest-fixture`) + `iceberg-spark-runtime`; a `spark.format: delta|iceberg` switch
- [ ] DuckDB `iceberg` extension reads `trades_1m` from both

**Acceptance:** the same fixture bar is read via Iceberg both locally and from the Databricks UC Iceberg endpoint.
