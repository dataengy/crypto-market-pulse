from market_pulse.settings import load_settings
from market_pulse.utils import safe_identifier
import pytest


def test_load_defaults():
    cfg = load_settings("clickhouse")
    assert cfg.profile == "clickhouse"
    assert cfg.symbol_list == ("BTCUSDT", "ETHUSDT")


def test_precedence(monkeypatch):
    monkeypatch.setenv("CMP_SYMBOL_LIST", "SOLUSDT")
    assert load_settings("gcp").symbol_list == ("SOLUSDT",)
    assert load_settings("gcp", overrides={"symbol_list": "BTCUSDT"}).symbol_list == ("BTCUSDT",)


def test_unsafe_identifier_and_profile():
    with pytest.raises(ValueError): safe_identifier("market_pulse; DROP DATABASE x")
    with pytest.raises(ValueError): load_settings("other")
