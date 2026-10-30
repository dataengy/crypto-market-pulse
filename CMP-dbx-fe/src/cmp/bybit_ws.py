"""Public market-data WebSocket connector; no trading/account API access."""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

from .domain import InvalidTrade, parse_ws_message

LOGGER = logging.getLogger(__name__)


def stream_trades(ws: dict[str, Any], publisher: Any, *, max_trades: int | None) -> int:
    """Run until interrupted or max_trades; bounded reconnect, explicit application ping.

    `ws` is the `bybit` section of config/config.yaml.
    """
    from websockets.sync.client import connect
    category = ws["category"]
    topics = [f"publicTrade.{symbol}" for symbol in ws["symbols"]]
    total, backoff = 0, ws["backoff_initial_s"]
    while max_trades is None or total < max_trades:
        try:
            with connect(ws["endpoint_template"].format(category=category),
                         open_timeout=ws["open_timeout_s"], close_timeout=ws["close_timeout_s"],
                         max_size=ws["max_message_bytes"]) as conn:
                conn.send(json.dumps({"op": "subscribe", "args": topics}))
                LOGGER.info("Subscribed to %s", ", ".join(topics))
                backoff, last_ping = ws["backoff_initial_s"], time.monotonic()
                while max_trades is None or total < max_trades:
                    if time.monotonic() - last_ping >= ws["ping_interval_s"]:
                        conn.send('{"op":"ping"}')
                        last_ping = time.monotonic()
                    try:
                        message = conn.recv(timeout=ws["recv_timeout_s"])
                    except TimeoutError:
                        continue
                    received = int(datetime.now(UTC).timestamp() * 1000)
                    try:
                        for event in parse_ws_message(message, category=category,
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
            backoff = min(backoff * 2, ws["backoff_max_s"])
    return total
