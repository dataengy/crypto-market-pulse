# PySpark streaming local debug

Prefer Spark already installed on the OS or an authorized existing Spark container; inspect Java/Spark/Python versions first. Only then install a matching PySpark in a virtual environment. Run `python3 scripts/local_spark_debug.py`.

The local test uses `readStream.schema(...).json(...)` on replay fixture files, event-time watermark, a bounded `availableNow` trigger, checkpointed Parquet and SQL against the persisted result. This tests real Spark Structured Streaming machinery, but **does not use Kafka or an unbounded always-on stream**. It does not establish consumer backpressure characteristics or source-side recovery.

Next feature: local Spark-Kafka connector with compatible `spark-sql-kafka-0-10` matching installed Spark, proper offsets/checkpoint, restart under producer traffic, and `dropDuplicatesWithinWatermark` with documented retention. Prefer no additional Docker if existing Spark and Redpanda are suitable. Cross-validate OHLCV on the fixture against `tests/test_domain.py`.
