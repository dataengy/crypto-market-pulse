"""Local Kafka -> ClickHouse adapter for debugging, not ClickPipes emulation."""
from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse
from .domain import validate_event, encode_event
from .utils import safe_identifier


def _auth():
    user = os.getenv("CLICKHOUSE_USER", "default")
    password = os.getenv("CLICKHOUSE_PASSWORD", "")
    return user, password


def clickhouse_post(settings: Any, query: str, body: bytes = b"") -> str:
    import requests
    url = settings.clickhouse_url
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("ClickHouse URL must use http(s)")
    response = requests.post(url, params={"query": query}, data=body,
                             auth=_auth(), timeout=30)
    response.raise_for_status()
    return response.text


def insert_events(settings: Any, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    database = safe_identifier(settings.clickhouse_database)
    payload = b"\n".join(encode_event(event) for event in events) + b"\n"
    clickhouse_post(settings, f"INSERT INTO {database}.trades_raw FORMAT JSONEachRow", payload)


def kafka_consume(settings: Any, *, max_messages: int | None = None) -> int:
    """Commit consumer offsets only after successful CH HTTP insert.

    At-least-once is intentional: crash after insert/before commit may replay.
    Query-level dedup must prevent double-counting; see SQL marts.
    """
    from confluent_kafka import Consumer, KafkaException
    import json
    conf = {"bootstrap.servers": settings.kafka_bootstrap,
            "group.id": settings.kafka_group,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest"}
    if os.getenv("KAFKA_SECURITY_PROTOCOL"):
        conf.update({"security.protocol": os.environ["KAFKA_SECURITY_PROTOCOL"],
                     "sasl.mechanisms": "PLAIN",
                     "sasl.username": os.environ["KAFKA_SASL_USERNAME"],
                     "sasl.password": os.environ["KAFKA_SASL_PASSWORD"]})
    consumer = Consumer(conf)
    consumer.subscribe([settings.kafka_topic])
    processed = 0
    try:
        while max_messages is None or processed < max_messages:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            try:
                event = json.loads(msg.value())
                validate_event(event)
            except (ValueError, UnicodeError) as exc:
                # STOP: no silent skipping; operator must inspect/quarantine.
                raise RuntimeError("Poison message; offset not committed") from exc
            insert_events(settings, [event])
            consumer.commit(message=msg, asynchronous=False)
            processed += 1
    finally:
        consumer.close()
    return processed
