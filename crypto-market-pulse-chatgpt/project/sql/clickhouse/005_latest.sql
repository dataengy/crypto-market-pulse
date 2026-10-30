CREATE VIEW IF NOT EXISTS market_pulse.trades_latest AS
SELECT symbol,
  argMax(price, tuple(event_time_ms, event_id)) AS last_price,
  max(event_time_ms) AS latest_event_time_ms,
  count() AS total_trades
FROM market_pulse.trades_dedup
GROUP BY symbol;
