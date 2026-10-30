CREATE OR REPLACE VIEW crypto_pulse.trades_1m AS
SELECT
  symbol,
  TIMESTAMP_TRUNC(TIMESTAMP_MILLIS(event_time_ms), MINUTE) AS window_start,
  COUNT(*) AS trade_count,
  ARRAY_AGG(price ORDER BY event_time_ms, event_id LIMIT 1)[OFFSET(0)] AS open_price,
  MAX(price) AS high_price,
  MIN(price) AS low_price,
  ARRAY_AGG(price ORDER BY event_time_ms DESC, event_id DESC LIMIT 1)[OFFSET(0)] AS close_price,
  SUM(quantity) AS volume,
  SUM(price * quantity) AS notional,
  SAFE_DIVIDE(SUM(price * quantity), SUM(quantity)) AS vwap,
  COUNTIF(side = 'Buy') AS buy_trades,
  MAX(GREATEST(0, received_at_ms - event_time_ms)) AS max_ingest_lag_ms
FROM crypto_pulse.trades_dedup
GROUP BY symbol, window_start;
