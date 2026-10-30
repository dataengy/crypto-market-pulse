"""Pure-Python OHLCV for one symbol/window — the oracle the SQL models are tested against."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from .domain import validate_event


def compute_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
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
