"""Explicit transport adapters. No secret values printed or stored."""
from __future__ import annotations

from typing import Any
from .domain import encode_event


class StdoutPublisher:
    def publish(self, event: dict[str, Any]) -> None:
        print(encode_event(event).decode("utf-8"), flush=True)

    def close(self) -> None:
        pass


class KafkaPublisher:
    def __init__(self, settings: Any):
        from confluent_kafka import Producer
        import os
        config = {"bootstrap.servers": settings.kafka_bootstrap, "client.id": "crypto-market-pulse"}
        if os.getenv("KAFKA_SECURITY_PROTOCOL"):
            config.update({"security.protocol": os.environ["KAFKA_SECURITY_PROTOCOL"],
                           "sasl.mechanisms": "PLAIN",
                           "sasl.username": os.environ["KAFKA_SASL_USERNAME"],
                           "sasl.password": os.environ["KAFKA_SASL_PASSWORD"]})
        self._producer = Producer(config)
        self._topic = settings.kafka_topic
        self._pending_error: Exception | None = None

    def publish(self, event: dict[str, Any]) -> None:
        def delivery(error, _message):
            if error:
                self._pending_error = RuntimeError(f"Kafka delivery failed: {error}")
        self._producer.poll(0)
        self._producer.produce(self._topic, key=event["event_id"].encode(),
                               value=encode_event(event), on_delivery=delivery)
        if self._pending_error:
            raise self._pending_error

    def close(self) -> None:
        undelivered = self._producer.flush(timeout=30)
        if undelivered or self._pending_error:
            raise RuntimeError(f"Kafka flush failed / undelivered={undelivered}") from self._pending_error


class PubSubPublisher:
    def __init__(self, settings: Any):
        from google.cloud import pubsub_v1
        self._client = pubsub_v1.PublisherClient()
        self._topic = self._client.topic_path(settings.pubsub_project, settings.pubsub_topic)
        self._futures: list[Any] = []

    def publish(self, event: dict[str, Any]) -> None:
        self._futures.append(self._client.publish(self._topic, encode_event(event),
                                                 symbol=event["symbol"]))
        if len(self._futures) >= 100:
            self._drain()

    def _drain(self) -> None:
        for future in self._futures:
            future.result(timeout=30)  # fail rather than silently losing messages
        self._futures.clear()

    def close(self) -> None:
        self._drain()


def make_publisher(name: str, settings: Any):
    if name == "stdout":
        return StdoutPublisher()
    if name == "kafka":
        return KafkaPublisher(settings)
    if name == "pubsub":
        return PubSubPublisher(settings)
    raise ValueError("sink must be stdout, kafka, pubsub")
