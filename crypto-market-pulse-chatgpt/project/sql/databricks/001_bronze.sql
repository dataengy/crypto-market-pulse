-- Run once in a Databricks SQL warehouse; replace catalog/schema as needed.
CREATE SCHEMA IF NOT EXISTS workspace.crypto_pulse;
CREATE TABLE IF NOT EXISTS workspace.crypto_pulse.trades_raw (
  schema_version INT, event_id STRING, source STRING, category STRING,
  symbol STRING, trade_id STRING, event_time_ms BIGINT,
  received_at_ms BIGINT, side STRING, price DECIMAL(38, 12),
  quantity DECIMAL(38, 12)
) USING DELTA;
