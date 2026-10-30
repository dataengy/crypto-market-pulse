#!/usr/bin/env python3
"""Live public Bybit trades or deterministic fixture replay → Kafka of CMP_PROFILE (or stdout)."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from cmp.bybit_ws import stream_trades
from cmp.domain import validate_event
from cmp.kafka import kafka_connection, producer_config
from cmp.publish import KafkaPublisher, StdoutPublisher
from cmp.settings import env, get, load_config, load_env


def replay(path: Path, publisher, max_trades: int | None) -> int:
    count = 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            validate_event(event)
            publisher.publish(event)
            count += 1
            if max_trades and count >= max_trades:
                break
    return count


def kafka_publisher(cfg: dict, profile: str, topic: str) -> KafkaPublisher:
    conn = kafka_connection(cfg, profile, env)
    return KafkaPublisher(producer_config(conn, get(cfg, "kafka.client_id")), topic,
                          get(cfg, "kafka.flush_timeout_s"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["fixture", "bybit"], required=True)
    parser.add_argument("--fixture", type=Path, help="normalized JSONL (required for --source fixture)")
    parser.add_argument("--sink", choices=["kafka", "stdout"], required=True)
    parser.add_argument("--max-trades", type=int)
    args = parser.parse_args()
    if args.max_trades is not None and args.max_trades < 1:
        parser.error("--max-trades must be >= 1")
    if args.source == "fixture" and not args.fixture:
        parser.error("--fixture is required with --source fixture")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_env()
    cfg = load_config()
    profile = env("CMP_PROFILE")
    publisher = (kafka_publisher(cfg, profile, get(cfg, "kafka.topic")) if args.sink == "kafka"
                 else StdoutPublisher())
    try:
        if args.source == "fixture":
            count = replay(args.fixture, publisher, args.max_trades)
        else:
            count = stream_trades(get(cfg, "bybit"), publisher, max_trades=args.max_trades)
    finally:
        publisher.close()
    logging.info("published %s trades (profile=%s, sink=%s)", count, profile, args.sink)


if __name__ == "__main__":
    main()
