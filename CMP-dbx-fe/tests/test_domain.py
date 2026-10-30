import json
from decimal import Decimal
from pathlib import Path

import pytest

from cmp.domain import InvalidTrade, deduplicate, normalize_trade, parse_ws_message, validate_event
from cmp.reference import compute_stats

FIXTURE = Path(__file__).resolve().parent / "fixtures/trades.jsonl"


def items():
    return [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]


def test_ws_multi_trade_and_ping():
    first = items()[0]
    trade = {"T": first["event_time_ms"], "s": first["symbol"], "i": first["trade_id"],
             "S": first["side"], "p": first["price"], "v": first["quantity"]}
    message = {"topic": "publicTrade.BTCUSDT", "data": [trade, {**trade, "i": "other"}]}
    output = list(parse_ws_message(message, category="linear", received_at_ms=first["received_at_ms"]))
    assert len(output) == 2
    assert output[0]["event_id"] == first["event_id"]
    assert list(parse_ws_message({"op": "pong"}, category="linear")) == []


@pytest.mark.parametrize("price,quantity", [("0", "1"), ("nan", "1"), ("1", "-1"), ("1", "inf")])
def test_bad_numbers(price, quantity):
    with pytest.raises(InvalidTrade):
        normalize_trade({"T": 1782813600000, "s": "BTCUSDT", "i": "a", "S": "Buy",
                         "p": price, "v": quantity}, category="linear")


def test_unique_identity_and_replay():
    fixture = items()
    assert len(fixture) > len(deduplicate(fixture))
    for e in fixture:
        validate_event(e)
    with pytest.raises(InvalidTrade):
        validate_event({**fixture[0], "event_id": "forged"})
    with pytest.raises(InvalidTrade):
        validate_event({k: v for k, v in fixture[0].items() if k != "category"})


def test_reference_ohlcv_on_fixture():
    first_minute = items()[0]["event_time_ms"] // 60000
    bucket = [e for e in items() if e["symbol"] == "BTCUSDT" and e["event_time_ms"] // 60000 == first_minute]
    stats = compute_stats(bucket)
    assert stats["trade_count"] == 4
    assert Decimal(stats["open_price"]) == Decimal("70000.0")
    assert Decimal(stats["close_price"]) == Decimal("69990.0")
    assert Decimal(stats["high_price"]) == Decimal("70010.0")
    assert Decimal(stats["volume"]) == Decimal("0.45")


def test_invalid_messages_and_topic():
    with pytest.raises(InvalidTrade):
        list(parse_ws_message({"topic": "publicTrade.ETHUSDT", "data": [{"s": "BTCUSDT"}]}, category="linear"))
    with pytest.raises(InvalidTrade):
        list(parse_ws_message("not json", category="linear"))
