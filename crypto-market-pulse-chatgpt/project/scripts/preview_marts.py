#!/usr/bin/env python3
"""Deterministic offline OHLCV preview; requires no broker, DWH or credentials.

This is an executable reference for SQL mart validation, NOT a substitute
for Spark/Beam/ClickHouse integration tests.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from market_pulse.beam_pipeline import compute_stats
from market_pulse.domain import validate_event


def make_marts(events: list[dict]) -> list[dict]:
    buckets = defaultdict(list)
    for event in events:
        validate_event(event)
        window_start_ms = event["event_time_ms"] // 60_000 * 60_000
        buckets[(event["symbol"], window_start_ms)].append(event)
    rows = []
    for (symbol, window_start_ms), group in sorted(buckets.items()):
        stats = compute_stats(group)
        rows.append({
            "window_start": datetime.fromtimestamp(window_start_ms / 1000, tz=timezone.utc).isoformat(),
            "window_start_ms": window_start_ms,
            "symbol": symbol,
            **stats,
            "duplicate_count": len(group) - stats["trade_count"],
            "max_ingest_lag_ms": max(max(0, e["received_at_ms"] - e["event_time_ms"]) for e in group),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=ROOT / "tests/fixtures/trades.jsonl")
    args = parser.parse_args()
    events = [json.loads(s) for s in args.fixture.read_text(encoding="utf-8").splitlines() if s.strip()]
    for row in make_marts(events):
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
