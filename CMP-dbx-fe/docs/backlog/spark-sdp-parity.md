# DBX-B2 — Spark Declarative Pipelines locally (pipeline parity)

**Goal:** run the *pipeline definition* locally (OSS Spark 4.1 `spark-pipelines`) instead of the hand-written loop in `scripts/local_spark.py`. ← [tasks](../../../docs/plans/dbx-fe/tasks.md#dbx-b2)

**Steps**
- [ ] Spike: does Spark 4.1 SDP accept `CREATE STREAMING TABLE … AS SELECT … FROM STREAM(x)` and MVs from our generated SQL? List the gaps (`CREATE OR REFRESH`, `EXPECT … DROP ROW`)
- [ ] `build.py` emits a second flavor (`pipelines-oss/`) if the syntax differs; keep `sql/models` as the single source
- [ ] Bronze: `pyspark.pipelines` table that reuses `cmp.bronze.parse_trades`; pipeline spec YAML with local Kafka options
- [ ] Wait for delta-spark support for Spark 4.1, or use Parquet in the spike

**Acceptance:** `spark-pipelines run` produces the same `trades_1m` fixture bar; `local_spark.py` becomes optional.
