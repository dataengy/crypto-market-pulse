"""Kafka value → typed bronze rows. Same code runs in local Spark and the Lakeflow pipeline."""
from __future__ import annotations

TRADE_SCHEMA = (
    "schema_version INT, event_id STRING, source STRING, category STRING, symbol STRING, "
    "trade_id STRING, event_time_ms BIGINT, received_at_ms BIGINT, side STRING, "
    "price DECIMAL(38,12), quantity DECIMAL(38,12)"
)


def parse_trades(kafka_df):
    """Malformed JSON yields NULL fields; silver's valid_trade expectation drops them."""
    from pyspark.sql import functions as F
    return kafka_df.select(
        F.from_json(F.col("value").cast("string"), TRADE_SCHEMA).alias("t"),
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
        F.col("timestamp").alias("kafka_timestamp"),
    ).select("t.*", "kafka_partition", "kafka_offset", "kafka_timestamp")
