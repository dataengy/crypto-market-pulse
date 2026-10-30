"""Apache Beam window aggregation. Optional dependency, no GCP needed for TestStream.

Run with DirectRunner to debug windowing; DataflowRunner only with explicit GCP setup.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from .domain import validate_event


def compute_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic SQL-equivalent aggregator for one symbol/window fixture."""
    chosen: dict[str, dict[str, Any]] = {}
    for e in events:
        validate_event(e)
        key = e["event_id"]
        if key not in chosen or e["received_at_ms"] < chosen[key]["received_at_ms"]:
            chosen[key] = e
    values = sorted(chosen.values(), key=lambda e: (e["event_time_ms"], e["event_id"]))
    if not values:
        return {"trade_count": 0}
    prices = [Decimal(e["price"]) for e in values]
    sizes = [Decimal(e["quantity"]) for e in values]
    volume = sum(sizes, Decimal(0))
    notional = sum((p * q for p, q in zip(prices, sizes)), Decimal(0))
    return {"symbol": values[0]["symbol"], "trade_count": len(values),
            "open_price": str(prices[0]), "close_price": str(prices[-1]),
            "high_price": str(max(prices)), "low_price": str(min(prices)),
            "volume": str(volume), "notional": str(notional),
            "vwap": str(notional / volume),
            "buy_trades": sum(e["side"] == "Buy" for e in values)}


def build_windowed(pcoll):
    """Build keyed, minute-bucketed Beam PCollection with event-time timestamps."""
    import apache_beam as beam
    from apache_beam.transforms.window import FixedWindows, TimestampedValue

    class StatsCombine(beam.CombineFn):
        def create_accumulator(self):
            return {}
        def add_input(self, accumulator, event):
            prior = accumulator.get(event["event_id"])
            if prior is None or event["received_at_ms"] < prior["received_at_ms"]:
                accumulator[event["event_id"]] = event
            return accumulator
        def merge_accumulators(self, accumulators):
            merged = {}
            for acc in accumulators:
                for event in acc.values():
                    self.add_input(merged, event)
            return merged
        def extract_output(self, accumulator):
            return compute_stats(list(accumulator.values()))

    def stamp(event):
        validate_event(event)
        return TimestampedValue((event["symbol"], event), event["event_time_ms"] / 1000)

    def with_window(kv, window=beam.DoFn.WindowParam):
        return {**kv[1], "window_start_ms": int(float(window.start) * 1000)}

    return (pcoll
        | "ValidateAndTimestamp" >> beam.Map(stamp)
        | "Window1m" >> beam.WindowInto(FixedWindows(60), allowed_lateness=30)
        | "DedupAndAggregate" >> beam.CombinePerKey(StatsCombine())
        | "WindowMetadata" >> beam.Map(with_window))
