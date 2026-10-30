import json
from pathlib import Path
from market_pulse.domain import normalize_trade

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_as_code_is_synchronized():
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("cmp_dashboard_builder", ROOT / "scripts/build_databricks_dashboard.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    actual = json.loads((ROOT / "dashboards/market_pulse.lvdash.json").read_text())
    assert actual == module.build()
    assert "trades_1m" in actual["datasets"][0]["query"]


def test_raw_trade_identity_is_source_stable():
    raw = {"T": 1793354405000, "s": "BTCUSDT", "i": "x", "S": "Buy", "p": "3.0", "v": "0.1"}
    a = normalize_trade(raw, received_at_ms=1793354406000)
    b = normalize_trade(raw, received_at_ms=1793354410000)
    assert a["event_id"] == b["event_id"]
    assert a["received_at_ms"] != b["received_at_ms"]
