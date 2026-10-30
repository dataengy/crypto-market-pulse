#!/usr/bin/env python3
"""Live public Bybit trades or deterministic fixture replay to stdout/Kafka/PubSub."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from market_pulse.bybit_ws import stream_trades
from market_pulse.domain import validate_event
from market_pulse.publish import make_publisher
from market_pulse.settings import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=["clickhouse", "gcp", "databricks"], default=None)
    parser.add_argument("--sink", choices=["stdout", "kafka", "pubsub"], default="stdout")
    parser.add_argument("--fixture", type=Path, help="Replay deterministic normalized JSONL instead of live WS")
    parser.add_argument("--max-trades", type=int, default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = load_settings(args.profile)
    if args.max_trades is not None and args.max_trades < 1:
        parser.error("--max-trades must be >= 1")
    publisher = make_publisher(args.sink, cfg)
    try:
        if args.fixture:
            count = 0
            with args.fixture.open(encoding="utf-8") as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    validate_event(event)
                    publisher.publish(event)
                    count += 1
                    if args.max_trades and count >= args.max_trades:
                        break
            logging.info("Replayed %s trades", count)
        else:
            stream_trades(cfg, publisher, max_trades=args.max_trades)
    finally:
        publisher.close()


if __name__ == "__main__":
    main()
