"""Transport adapters. No secret values printed or stored."""
from __future__ import annotations

from typing import Any

from .domain import encode_event


class StdoutPublisher:
    def publish(self, event: dict[str, Any]) -> None:
        print(encode_event(event).decode("utf-8"), flush=True)

    def close(self) -> None:
        pass


class KafkaPublisher:
    def __init__(self, producer_config: dict[str, str], topic: str, flush_timeout_s: float):
        from confluent_kafka import Producer
        self._producer = Producer(producer_config)
        self._topic = topic
        self._flush_timeout_s = flush_timeout_s
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
        undelivered = self._producer.flush(timeout=self._flush_timeout_s)
        if undelivered or self._pending_error:
            raise RuntimeError(f"Kafka flush failed / undelivered={undelivered}") from self._pending_error
