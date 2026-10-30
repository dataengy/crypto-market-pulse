CREATE OR REPLACE VIEW crypto_pulse.trades_latest AS
SELECT symbol,
  ARRAY_AGG(price ORDER BY event_time_ms DESC, event_id DESC LIMIT 1)[OFFSET(0)] AS last_price,
  MAX(event_time_ms) AS latest_event_time_ms,
  COUNT(*) AS total_trades
FROM crypto_pulse.trades_dedup
GROUP BY symbol;
