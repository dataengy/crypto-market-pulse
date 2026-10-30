#!/usr/bin/env python3
"""Local Lakeflow stand-in: Kafka (Redpanda or cloud) → bronze Delta → silver/dedup/1m/latest Delta.

Path-based Delta tables under spark.lake_dir, so no metastore is needed between runs.
Each micro-batch appends bronze idempotently (txnAppId/txnVersion) and rebuilds the models.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cmp.bronze import parse_trades
from cmp.kafka import kafka_connection, spark_kafka_options
from cmp.settings import env, get, load_config, load_env
from cmp.sql_models import model_sql, valid_trade_predicate


def spark_session(cfg: dict):
    import pyspark
    from delta import configure_spark_with_delta_pip
    from pyspark.sql import SparkSession
    builder = (SparkSession.builder.appName("cmp-dbx-fe-local")
               .master(get(cfg, "spark.master"))
               .config("spark.sql.shuffle.partitions", get(cfg, "spark.shuffle_partitions"))
               .config("spark.sql.session.timeZone", "UTC")
               .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
               .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog"))
    kafka_pkg = f"org.apache.spark:spark-sql-kafka-0-10_2.13:{pyspark.__version__}"
    return configure_spark_with_delta_pip(builder, extra_packages=[kafka_pkg]).getOrCreate()


def table(lake: Path, name: str) -> str:
    return f"delta.`{lake / name}`"


def build_models(spark, lake: Path) -> None:
    t = lambda name: table(lake, name)
    steps = [
        ("trades_silver", (f"SELECT * FROM ({model_sql('10_silver', t('trades_bronze'))}) AS s "
                           f"WHERE {valid_trade_predicate()}")),
        ("trades_dedup", model_sql("20_dedup", t("trades_silver"))),
        ("trades_1m", model_sql("30_1m", t("trades_dedup"))),
        ("trades_latest", model_sql("40_latest", t("trades_dedup"))),
    ]
    for name, sql in steps:
        spark.sql(f"CREATE OR REPLACE TABLE {t(name)} USING DELTA AS {sql}")


def run(spark, kafka_options: dict, lake: Path, *, follow_interval: str | None) -> None:
    """follow_interval=None → availableNow (drain topic, then stop)."""
    def batch(df, batch_id: int) -> None:
        (df.write.format("delta").mode("append")
           .option("txnAppId", "cmp-local-bronze").option("txnVersion", batch_id)
           .save(str(lake / "trades_bronze")))
        build_models(df.sparkSession, lake)

    stream = parse_trades(spark.readStream.format("kafka").options(**kafka_options).load())
    writer = stream.writeStream.foreachBatch(batch).option(
        "checkpointLocation", str(lake / "_checkpoints/trades_bronze"))
    writer = writer.trigger(processingTime=follow_interval) if follow_interval else writer.trigger(availableNow=True)
    writer.start().awaitTermination()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--follow", action="store_true", help="keep consuming (processingTime trigger)")
    parser.add_argument("--reset", action="store_true", help="delete the local lake + checkpoints first")
    args = parser.parse_args()
    load_env()
    cfg = load_config()
    lake = ROOT / get(cfg, "spark.lake_dir")
    if args.reset and lake.exists():
        shutil.rmtree(lake)
    options = spark_kafka_options(kafka_connection(cfg, env("CMP_PROFILE"), env), get(cfg, "kafka.topic"),
                                  get(cfg, "kafka.starting_offsets"), get(cfg, "kafka.jaas_login_module.oss"))
    spark = spark_session(cfg)
    spark.sparkContext.setLogLevel("WARN")
    run(spark, options, lake, follow_interval=get(cfg, "spark.follow_trigger_interval") if args.follow else None)
    rows = get(cfg, "spark.show_rows")
    for name in ("trades_1m", "trades_latest"):
        print(f"== {name}")
        spark.sql(f"SELECT * FROM {table(lake, name)} ORDER BY 1, 2").show(rows, truncate=False)


if __name__ == "__main__":
    main()
