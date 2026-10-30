#!/usr/bin/env python3
"""Opt-in isolated Pub/Sub Emulator smoke: fixture -> publish -> pull -> validate -> ACK.

Refuse to run if PUBSUB_EMULATOR_HOST is absent: NEVER creates real cloud resources.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from market_pulse.domain import encode_event, validate_event
from market_pulse.settings import load_settings


def main() -> None:
    from google.cloud import pubsub_v1
    from google.api_core.exceptions import AlreadyExists

    if not os.getenv("PUBSUB_EMULATOR_HOST"):
        raise SystemExit("Refusing cloud resource access: PUBSUB_EMULATOR_HOST required")
    cfg = load_settings("gcp")
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    topic = publisher.topic_path(cfg.pubsub_project, cfg.pubsub_topic)
    subscription = subscriber.subscription_path(cfg.pubsub_project, "market-trades-smoke-local")
    try:
        publisher.create_topic(request={"name": topic})
    except AlreadyExists:
        pass
    try:
        subscriber.create_subscription(request={"name": subscription, "topic": topic})
    except AlreadyExists:
        pass
    fixture = [json.loads(line) for line in (ROOT / "tests/fixtures/trades.jsonl").read_text().splitlines() if line.strip()]
    for event in fixture:
        publisher.publish(topic, encode_event(event)).result(timeout=10)
    received: dict[str, int] = {}
    ack_ids: list[str] = []
    for _ in range(12):
        res = subscriber.pull(request={"subscription": subscription, "max_messages": 100}, timeout=5)
        for message in res.received_messages:
            event = json.loads(message.message.data)
            validate_event(event)
            received[event["event_id"]] = received.get(event["event_id"], 0) + 1
            ack_ids.append(message.ack_id)
        if len(ack_ids) >= len(fixture):
            break
    if ack_ids:
        subscriber.acknowledge(request={"subscription": subscription, "ack_ids": ack_ids})
    if len(ack_ids) < len(fixture):
        raise AssertionError(f"Expected at least {len(fixture)} messages, received {len(ack_ids)}")
    if not any(count > 1 for count in received.values()):
        raise AssertionError("Expected duplicate trade ID from replay")
    print(f"Pub/Sub Emulator smoke: OK, pulled {len(ack_ids)} messages, unique IDs={len(received)}")


if __name__ == "__main__":
    main()
