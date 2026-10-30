#!/usr/bin/env python3
"""Databricks job task: can Free Edition serverless reach the cloud Kafka? (TCP, then SASL batch read).

Free Edition limits outbound internet to trusted domains — run this before relying on the pipeline.
"""
from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="bundle files root (${workspace.file_path})")
    parser.add_argument("--secret-scope", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    sys.path.insert(0, str(root / "src"))
    from databricks.sdk.runtime import dbutils, spark

    from cmp.kafka import kafka_connection, spark_kafka_options
    from cmp.settings import get, load_config

    cfg = load_config(root)
    conn = kafka_connection(cfg, "cloud", lambda key: dbutils.secrets.get(args.secret_scope, key.lower()))
    host, port = conn["bootstrap"].split(",")[0].rsplit(":", 1)
    socket.create_connection((host, int(port)), timeout=get(cfg, "probe.tcp_timeout_s")).close()
    print(f"TCP OK: {host}:{port}")
    options = spark_kafka_options(conn, get(cfg, "kafka.topic"), "earliest",
                                  get(cfg, "kafka.jaas_login_module.databricks"))
    count = spark.read.format("kafka").options(**options).option("endingOffsets", "latest").load().count()
    print(f"Kafka SASL read OK: topic {get(cfg, 'kafka.topic')} has {count} messages")


if __name__ == "__main__":
    main()
