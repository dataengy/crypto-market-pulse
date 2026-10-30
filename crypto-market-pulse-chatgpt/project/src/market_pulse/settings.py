"""YAML settings: CLI > env > profile YAML > common YAML. No imports with side effects."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    profile: str = "clickhouse"
    symbol_list: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
    category: str = "linear"
    kafka_bootstrap: str = "localhost:19092"
    kafka_topic: str = "market.trades.v1"
    kafka_group: str = "crypto-pulse-clickhouse-debug-v1"
    clickhouse_url: str = "http://127.0.0.1:8123"
    clickhouse_database: str = "market_pulse"
    pubsub_project: str = "local-crypto-pulse"
    pubsub_topic: str = "market-trades-v1"
    databricks_catalog: str = "workspace"
    databricks_schema: str = "crypto_pulse"


def load_settings(profile: str | None = None, *, overrides: dict[str, Any] | None = None,
                  root: Path = ROOT) -> Settings:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("pip install pyyaml") from exc
    profile = profile or os.getenv("CMP_PROFILE") or "clickhouse"
    if profile not in ("clickhouse", "gcp", "databricks"):
        raise ValueError("CMP_PROFILE must be clickhouse, gcp or databricks")
    data: dict[str, Any] = {}
    for path in (root / "config/settings.yml", root / f"config/profiles/{profile}.yml"):
        if path.exists():
            payload = yaml.safe_load(path.read_text()) or {}
            if not isinstance(payload, dict):
                raise ValueError(f"settings not a mapping: {path}")
            data.update(payload)
    data["profile"] = profile
    for key in Settings.__dataclass_fields__:
        if key != "profile" and (v := os.getenv(f"CMP_{key.upper()}")) is not None:
            data[key] = v
    data.update(overrides or {})
    if isinstance(data.get("symbol_list"), str):
        data["symbol_list"] = tuple(x.strip().upper() for x in data["symbol_list"].split(",") if x.strip())
    elif isinstance(data.get("symbol_list"), list):
        data["symbol_list"] = tuple(data["symbol_list"])
    cfg = Settings(**data)
    if not cfg.symbol_list or any(not s.isalnum() for s in cfg.symbol_list):
        raise ValueError("invalid symbols")
    if cfg.category not in ("spot", "linear", "inverse"):
        raise ValueError("invalid category")
    return cfg
