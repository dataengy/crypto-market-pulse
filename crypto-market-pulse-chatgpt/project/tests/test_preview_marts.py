"""Reference OHLCV contract incl. deduplication and time order."""
import json
from pathlib import Path
from decimal import Decimal
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parents[1]
module_spec = spec_from_file_location("preview_marts", ROOT / "scripts/preview_marts.py")
mod = module_from_spec(module_spec)
module_spec.loader.exec_module(mod)


def test_fixture_reference_marts():
    events = [json.loads(s) for s in (ROOT / "tests/fixtures/trades.jsonl").read_text().splitlines()]
    rows = mod.make_marts(events)
    assert len(rows) == 4
    assert sum(row["trade_count"] for row in rows) == 7
    assert sum(row["duplicate_count"] for row in rows) == 1
    btc = next(r for r in rows if r["symbol"] == "BTCUSDT" and r["trade_count"] == 4)
    assert Decimal(btc["open_price"]) == Decimal("70000")
    assert Decimal(btc["close_price"]) == Decimal("69990")
    assert Decimal(btc["high_price"]) == Decimal("70010")
    assert Decimal(btc["low_price"]) == Decimal("69990")
    assert Decimal(btc["volume"]) == Decimal("0.45")
    expected_notional = Decimal("70000") * Decimal("0.1") + Decimal("70010") * Decimal("0.2") + Decimal("69990") * Decimal("0.05") + Decimal("70005") * Decimal("0.1")
    assert Decimal(btc["notional"]) == expected_notional
    assert Decimal(btc["vwap"]) == expected_notional / Decimal("0.45")
