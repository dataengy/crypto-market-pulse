# Databricks notebook source
# Run manually in DFE AFTER executing sql/databricks/001_bronze.sql.
# Only synthetic/replayed public trades; no external internet needed.
import json
from pyspark.sql import types as T

# Set the absolute fixture path to the file in your Databricks Git folder.
# This notebook is intentionally a thin entrypoint; no external WS in DFE.
dbutils.widgets.text("fixture_path", "", "Fixture JSONL path in workspace")
fixture_path = dbutils.widgets.get("fixture_path").strip()
if not fixture_path:
    raise ValueError("Set fixture_path widget to tests/fixtures/trades.jsonl in your Git folder")
with open(fixture_path, encoding="utf-8") as fixture:
    rows = [json.loads(s) for s in fixture if s.strip()]
schema = T.StructType([
    T.StructField("schema_version", T.IntegerType()),
    *[T.StructField(n, T.StringType()) for n in
      ("event_id", "source", "category", "symbol", "trade_id")],
    T.StructField("event_time_ms", T.LongType()),
    T.StructField("received_at_ms", T.LongType()),
    T.StructField("side", T.StringType()),
    T.StructField("price", T.DecimalType(38, 12)),
    T.StructField("quantity", T.DecimalType(38, 12)),
])
# Convert decimal strings into Decimal for Spark's explicit schema.
from decimal import Decimal
for r in rows:
    r["price"] = Decimal(r["price"])
    r["quantity"] = Decimal(r["quantity"])
spark.createDataFrame(rows, schema).write.mode("append").saveAsTable("workspace.crypto_pulse.trades_raw")
