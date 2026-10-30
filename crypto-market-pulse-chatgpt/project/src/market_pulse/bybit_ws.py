"""Public market-data WebSocket connector; no trading/account API access."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import time
from typing import Any

from .domain import InvalidTrade, parse_ws_message

LOGGER = logging.getLogger(__name__)
ENDPOINT = "wss://stream.bybit.com/v5/public/{category}"


def stream_trades(settings: Any, publisher: Any, *, max_trades: int | None = None) -> int:
    """Run until interrupted or max_trades; bounded reconnect, explicit application ping."""
    from websockets.sync.client import connect
    if settings.category not in ("spot", "linear", "inverse"):
        raise ValueError("invalid websocket market category")
    topics = [f"publicTrade.{symbol}" for symbol in settings.symbol_list]
    total, backoff = 0, 1
    while max_trades is None or total < max_trades:
        try:
            with connect(ENDPOINT.format(category=settings.category),
                         open_timeout=15, close_timeout=5, max_size=8_000_000) as ws:
                ws.send(json.dumps({"op": "subscribe", "args": topics}))
                LOGGER.info("Subscribed to %s", ", ".join(topics))
                backoff, last_ping = 1, time.monotonic()
                while max_trades is None or total < max_trades:
                    if time.monotonic() - last_ping >= 20:
                        ws.send('{"op":"ping"}')
                        last_ping = time.monotonic()
                    try:
                        message = ws.recv(timeout=5)
                    except TimeoutError:
                        continue
                    received = int(datetime.now(timezone.utc).timestamp() * 1000)
                    try:
                        for event in parse_ws_message(message, category=settings.category,
                                                      received_at_ms=received):
                            publisher.publish(event)
                            total += 1
                            if max_trades is not None and total >= max_trades:
                                break
                    except InvalidTrade as exc:
                        LOGGER.warning("Quarantined malformed websocket trade: %s", exc)
        except KeyboardInterrupt:
            break
        except Exception as exc:
            LOGGER.warning("WebSocket disconnected: %s; retry in %ss", type(exc).__name__, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
    return total
