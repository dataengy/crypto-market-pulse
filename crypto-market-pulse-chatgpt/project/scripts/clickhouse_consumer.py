#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from market_pulse.clickhouse_sink import kafka_consume
from market_pulse.settings import load_settings

p = argparse.ArgumentParser()
p.add_argument("--max-messages", type=int, default=None)
a = p.parse_args()
print(f"Consumed {kafka_consume(load_settings('clickhouse'), max_messages=a.max_messages)} messages")
