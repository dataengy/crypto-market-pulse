"""Streamlit dashboard-as-code for ClickHouse local / BigQuery cloud.

Run: CMP_PROFILE=clickhouse streamlit run dashboards/app.py
     CMP_PROFILE=gcp streamlit run dashboards/app.py
No browser authentication or credentials are stored here.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import streamlit as st
from market_pulse.settings import load_settings
from market_pulse.clickhouse_sink import clickhouse_post

cfg = load_settings()
st.set_page_config(page_title="Crypto Market Pulse", layout="wide")
st.title("📈 Crypto Market Pulse")
st.caption("Public Bybit trades · 1-minute OHLCV / VWAP · educational analytics only")


@st.cache_data(ttl=5)
def query(name: str):
    if cfg.profile == "clickhouse":
        sql = (f"SELECT * FROM {cfg.clickhouse_database}.{name} "
               "ORDER BY symbol, " + ("window_start" if name == "trades_1m" else "symbol") + " DESC LIMIT 300 FORMAT JSONEachRow")
        return [json.loads(line) for line in clickhouse_post(cfg, sql).splitlines() if line.strip()]
    if cfg.profile == "gcp":
        from google.cloud import bigquery
        import os
        project = os.getenv("CMP_PUBSUB_PROJECT", cfg.pubsub_project)
        table = f"`{project}.crypto_pulse.{name}`"
        client = bigquery.Client(project=project)
        # table is derived from validated static name / explicit project setting.
        sql = f"SELECT * FROM {table} LIMIT 300"
        return [dict(row.items()) for row in client.query(sql).result()]
    st.error("Databricks uses the versioned SQL queries in sql/databricks; use AI/BI dashboard there")
    st.stop()


rows = query("trades_1m")
latest = query("trades_latest")
if not rows:
    st.warning("No market data yet. Replay fixtures or start the live producer.")
    st.stop()

symbols = sorted({str(r["symbol"]) for r in rows})
symbol = st.selectbox("Market", symbols)
selected = sorted([r for r in rows if r["symbol"] == symbol], key=lambda r: str(r["window_start"]))
latest_by_symbol = next((r for r in latest if r["symbol"] == symbol), {})
a, b, c, d = st.columns(4)
a.metric("Last price", str(latest_by_symbol.get("last_price", "—")))
b.metric("Trades (visible windows)", sum(int(r["trade_count"]) for r in selected))
c.metric("1m volume (latest)", str(selected[-1]["volume"]))
d.metric("1m VWAP (latest)", str(selected[-1]["vwap"]))

import pandas as pd
frame = pd.DataFrame(selected)
frame["window_start"] = pd.to_datetime(frame["window_start"], utc=True)
for col in ("open_price", "high_price", "low_price", "close_price", "vwap", "volume", "max_ingest_lag_ms"):
    if col in frame:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
frame = frame.set_index("window_start")
st.subheader("Market price and VWAP")
st.line_chart(frame[["close_price", "vwap"]])
st.subheader("Traded volume")
st.bar_chart(frame[["volume"]])
with st.expander("Inspect OHLCV + latency"):
    st.dataframe(frame, use_container_width=True)
st.caption("Refresh data manually (R) or change symbol. Query cache TTL = 5 s; not a WebSocket push UI.")
