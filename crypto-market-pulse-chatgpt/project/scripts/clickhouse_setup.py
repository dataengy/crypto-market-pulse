#!/usr/bin/env python3
"""Opt-in setup; refuse remote URLs unless explicitly allowed."""
from pathlib import Path
import os
import sys
from urllib.parse import urlparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from market_pulse.clickhouse_sink import clickhouse_post
from market_pulse.settings import load_settings

cfg = load_settings("clickhouse")
url = urlparse(cfg.clickhouse_url)
if url.hostname not in {"localhost", "127.0.0.1", "::1"} and os.getenv("CMP_ALLOW_REMOTE_DDL") != "YES":
    raise SystemExit("Remote DDL disabled. Set CMP_ALLOW_REMOTE_DDL=YES after reviewing endpoint")
root = Path(__file__).resolve().parents[1] / "sql" / "clickhouse"
for file in sorted(root.glob("*.sql")):
    if file.name.startswith("0"):
        for statement in file.read_text().split(";\n"):
            statement = statement.strip().rstrip(";")
            if statement:
                clickhouse_post(cfg, statement.replace("market_pulse.", f"{cfg.clickhouse_database}."))
        print("Applied", file.name)
