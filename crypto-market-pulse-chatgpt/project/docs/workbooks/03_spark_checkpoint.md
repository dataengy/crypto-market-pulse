# Workbook 3 — Real local Spark Structured Streaming

**Goal:** understand micro-batches, watermark and checkpoint semantics. Requires a compatible Java + Spark/PySpark runtime. Reuse an installed one before installing dependencies or creating a container.

### Exercise A — run the bounded file stream

```bash
java -version
python -V
python -m pip install -r requirements-spark.txt  # only if suitable Spark/PySpark is not already available
python scripts/local_spark_debug.py
```

Review `scripts/local_spark_debug.py`: it creates temporary file source and checkpoint directories, processes JSON files by `readStream`, uses `withWatermark("event_time", "3 minutes")`, and writes Parquet via `trigger(availableNow=True)`. It then runs `sql/spark/ohlcv.sql`. The temp directory is removed automatically at the end.

### Exercise B — predict before running

1. Why must `readStream.json()` have a fixed schema?
2. What does `maxFilesPerTrigger=2` limit? Does it guarantee exactly two records per batch?
3. What does `availableNow=True` guarantee? Can this script be called a 24×7 Kafka streaming job?
4. What persists in Spark's checkpoint directory, and why must a restart use the **same** location to resume one existing query?
5. How does `dropDuplicatesWithinWatermark(["event_id"])` differ from unbounded query-level SQL dedup?

### Exercise C — persistent checkpoint experiment

The supplied script intentionally uses a temporary directory. For an actual restart test, **copy it to your own scratch file** and change it to use a dedicated non-shared path (for example `./.tmp/spark_replay_lab/`); split the fixture into first and second groups, run the stream twice with the same checkpoint and output path, adding the second group between runs. Record each result and query progress. Do not delete shared checkpoints to fake a fresh run.

### Evidence

Capture `query.lastProgress`, `query.recentProgress`, batch input rows, state operator info and checkpoint path (exclude secrets). Compare Spark SQL aggregate results to the reference offline preview for the same synthetic events. Note that processing time and watermark progress depend on batch scheduling and event-time distribution.

**Pass:** real Spark query starts and terminates cleanly; persisted results/metrics are correct; checkpoint behavior explained with actual observations. **Not proven:** Kafka continuous processing, late trades beyond watermark, full production state-store performance.
