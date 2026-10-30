#!/usr/bin/env python3
"""Real local Spark Structured Streaming: JSON files -> checkpointed Parquet -> SQL mart."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    from pyspark.sql import SparkSession, functions as F, types as T
    spark = (SparkSession.builder.master("local[2]").appName("CryptoMarketPulseDebug")
             .config("spark.sql.shuffle.partitions", "2").getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    schema = T.StructType([
        T.StructField("schema_version", T.IntegerType()),
        *[T.StructField(name, T.StringType()) for name in
          ("event_id", "source", "category", "symbol", "trade_id", "side")],
        T.StructField("event_time_ms", T.LongType()),
        T.StructField("received_at_ms", T.LongType()),
        T.StructField("price", T.DecimalType(38, 12)),
        T.StructField("quantity", T.DecimalType(38, 12)),
    ])
    try:
        with tempfile.TemporaryDirectory(prefix="cmp-spark-") as tmp:
            directory = Path(tmp)
            incoming = directory / "incoming"
            incoming.mkdir()
            output, checkpoint = directory / "output", directory / "checkpoint"
            fixture = [json.loads(line) for line in (ROOT / "tests/fixtures/trades.jsonl").read_text().splitlines()]
            for i, event in enumerate(fixture):
                (incoming / f"event-{i:03}.json").write_text(json.dumps(event) + "\n")
            df = (spark.readStream.schema(schema).option("maxFilesPerTrigger", 2)
                  .json(str(incoming)))
            stream = (df
                      .withColumn("event_time", F.expr("timestamp_millis(event_time_ms)"))
                      .withWatermark("event_time", "3 minutes")
                      .dropDuplicatesWithinWatermark(["event_id"])
                      .drop("event_time")
                      .writeStream.format("parquet")
                      .option("checkpointLocation", str(checkpoint))
                      .outputMode("append").trigger(availableNow=True)
                      .start(str(output)))
            stream.awaitTermination(timeout=120)
            if stream.isActive:
                stream.stop()
                raise RuntimeError("local stream timed out")
            raw = spark.read.parquet(str(output))
            raw.createOrReplaceTempView("trades_raw")
            query = (ROOT / "sql/spark/ohlcv.sql").read_text()
            result = spark.sql(query)
            result.show(truncate=False)
            if result.count() == 0:
                raise AssertionError("empty OHLCV result")
            print("Spark event-time streaming + checkpoint + SQL mart: OK")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
