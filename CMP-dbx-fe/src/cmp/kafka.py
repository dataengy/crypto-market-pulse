"""Kafka connection settings shared by the producer, local Spark and the Databricks pipeline.

`lookup` resolves credential names: os env locally, a Databricks secret scope in the cloud.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .settings import get


def kafka_connection(cfg: dict[str, Any], profile: str,
                     lookup: Callable[[str], str]) -> dict[str, str]:
    p = get(cfg, f"kafka.profiles.{profile}")
    conn = {
        "bootstrap": p["bootstrap"] if "bootstrap" in p else lookup(get(p, "bootstrap_env")),
        "security_protocol": get(p, "security_protocol"),
    }
    if conn["security_protocol"].startswith("SASL"):
        conn |= {"sasl_mechanism": get(p, "sasl_mechanism"),
                 "username": lookup(get(p, "username_env")),
                 "password": lookup(get(p, "password_env"))}
    return conn


def producer_config(conn: dict[str, str], client_id: str) -> dict[str, str]:
    config = {"bootstrap.servers": conn["bootstrap"], "client.id": client_id,
              "security.protocol": conn["security_protocol"]}
    if "username" in conn:
        config |= {"sasl.mechanisms": conn["sasl_mechanism"],
                   "sasl.username": conn["username"], "sasl.password": conn["password"]}
    return config


def spark_kafka_options(conn: dict[str, str], topic: str, starting_offsets: str,
                        login_module: str) -> dict[str, str]:
    """Options for spark.readStream.format("kafka"); login_module differs OSS vs Databricks (shaded)."""
    options = {"kafka.bootstrap.servers": conn["bootstrap"], "subscribe": topic,
               "startingOffsets": starting_offsets,
               "kafka.security.protocol": conn["security_protocol"]}
    if "username" in conn:
        if any('"' in conn[k] for k in ("username", "password")):
            raise ValueError("Kafka credentials must not contain double quotes (JAAS syntax)")
        options |= {"kafka.sasl.mechanism": conn["sasl_mechanism"],
                    "kafka.sasl.jaas.config": f'{login_module} required username="{conn["username"]}"'
                                              f' password="{conn["password"]}";'}
    return options
