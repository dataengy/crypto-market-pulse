"""Strict, side-effect-free Bybit publicTrade normalization and deterministic replay."""
from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA_VERSION = 1


class InvalidTrade(ValueError):
    """Invalid or unsupported public-trade payload."""


def _decimal(value: Any, field: str, *, positive: bool = True) -> str:
    if not isinstance(value, str):
        raise InvalidTrade(f"{field}: exchange decimal must be a string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise InvalidTrade(f"{field}: invalid decimal") from exc
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        raise InvalidTrade(f"{field}: must be finite and positive")
    return str(number)


def normalize_trade(item: dict[str, Any], *, category: str,
                    received_at_ms: int | None = None) -> dict[str, Any]:
    """Build one immutable event from a Bybit publicTrade data[] entry.

    Bybit data[] may bundle multiple trades; use trade ID, NOT message ID/seq.
    """
    if category not in {"linear", "spot", "inverse"}:
        raise InvalidTrade("unsupported Bybit market category")
    try:
        symbol = item["s"]
        trade_id = item["i"]
        event_time_ms = item["T"]
        side = item["S"]
    except KeyError as exc:
        raise InvalidTrade(f"missing required field: {exc.args[0]}") from exc
    if not isinstance(symbol, str) or not symbol.isalnum() or len(symbol) > 32:
        raise InvalidTrade("invalid symbol")
    if not isinstance(trade_id, str) or not trade_id or len(trade_id) > 128:
        raise InvalidTrade("invalid trade id")
    if side not in ("Buy", "Sell"):
        raise InvalidTrade("invalid taker side")
    if not isinstance(event_time_ms, int) or isinstance(event_time_ms, bool) or not 946684800000 <= event_time_ms <= 4102444800000:
        raise InvalidTrade("event timestamp must be milliseconds between 2000 and 2100")
    price = _decimal(item.get("p"), "price")
    quantity = _decimal(item.get("v"), "quantity")
    if received_at_ms is None:
        received_at_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
    if not isinstance(received_at_ms, int) or received_at_ms < 0:
        raise InvalidTrade("invalid received_at_ms")
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": f"bybit:{category}:{symbol}:{trade_id}",
        "source": "bybit", "category": category, "symbol": symbol,
        "trade_id": trade_id, "event_time_ms": event_time_ms,
        "received_at_ms": received_at_ms, "side": side,
        "price": price, "quantity": quantity,
    }


def parse_ws_message(message: str | bytes | dict[str, Any], *, category: str,
                     received_at_ms: int | None = None) -> Iterator[dict[str, Any]]:
    """Ignore subscriptions/pongs; validate EVERY trade in the received batch."""
    try:
        envelope = json.loads(message) if isinstance(message, (str, bytes)) else message
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise InvalidTrade("invalid websocket JSON") from exc
    if not isinstance(envelope, dict):
        raise InvalidTrade("websocket message must be a JSON object")
    topic = envelope.get("topic", "")
    if not isinstance(topic, str) or not topic.startswith("publicTrade."):
        return
    entries = envelope.get("data")
    if not isinstance(entries, list):
        raise InvalidTrade("publicTrade data must be a list")
    for item in entries:
        if not isinstance(item, dict) or item.get("s") != topic.removeprefix("publicTrade."):
            raise InvalidTrade("trade symbol differs from topic")
        yield normalize_trade(item, category=category, received_at_ms=received_at_ms)


def validate_event(event: dict[str, Any]) -> None:
    """Validate our normalized replay envelope independently of the transport."""
    if event.get("schema_version") != SCHEMA_VERSION or event.get("source") != "bybit":
        raise InvalidTrade("wrong event schema/source")
    rebuilt = normalize_trade({
        "s": event.get("symbol"), "i": event.get("trade_id"),
        "T": event.get("event_time_ms"), "S": event.get("side"),
        "p": event.get("price"), "v": event.get("quantity"),
    }, category=event.get("category"), received_at_ms=event.get("received_at_ms"))
    if event.get("event_id") != rebuilt["event_id"]:
        raise InvalidTrade("event_id does not match immutable exchange trade identity")


def encode_event(event: dict[str, Any]) -> bytes:
    validate_event(event)
    return json.dumps(event, separators=(",", ":"), sort_keys=True).encode("utf-8")


def deduplicate(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Test/reference dedup semantics: first accepted arrival wins per event ID."""
    seen: set[str] = set()
    result = []
    for event in events:
        validate_event(event)
        if event["event_id"] not in seen:
            seen.add(event["event_id"])
            result.append(event)
    return result
