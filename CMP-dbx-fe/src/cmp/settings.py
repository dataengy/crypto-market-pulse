"""Strict config: tracked config/config.yaml + config/.env.* files. No defaults — fail fast."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG = "config/config.yaml"
ENV_FILES = ("config/.env.common", "config/.env.secrets")
ENV_TEMPLATE = "config/.env.secrets.demo"


def load_env(root: Path = ROOT) -> None:
    """Load .env files without overriding values already set in shell/CI."""
    from dotenv import load_dotenv
    for rel in ENV_FILES:
        if (root / rel).exists():
            load_dotenv(root / rel, override=False)


def env(name: str) -> str:
    try:
        return os.environ[name]
    except KeyError:
        raise ValueError(f"env {name} is not set: fill {' / '.join(ENV_FILES)} "
                         f"(template: {ENV_TEMPLATE})") from None


def load_config(root: Path = ROOT) -> dict[str, Any]:
    import yaml
    data = yaml.safe_load((root / CONFIG).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{CONFIG} must be a mapping")
    return data


def get(cfg: dict[str, Any], dotted: str) -> Any:
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"missing config key '{dotted}' in {CONFIG}")
        node = node[part]
    return node
