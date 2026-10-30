CREATE VIEW IF NOT EXISTS market_pulse.trades_1m AS
SELECT
  symbol,
  toStartOfMinute(fromUnixTimestamp64Milli(toInt64(event_time_ms))) AS window_start,
  count() AS trade_count,
  argMin(price, tuple(event_time_ms, event_id)) AS open_price,
  max(price) AS high_price,
  min(price) AS low_price,
  argMax(price, tuple(event_time_ms, event_id)) AS close_price,
  sum(quantity) AS volume,
  sum(price * quantity) AS notional,
  if(sum(quantity) > 0, sum(price * quantity) / sum(quantity), 0) AS vwap,
  countIf(side = 'Buy') AS buy_trades,
  max(received_at_ms - least(received_at_ms, event_time_ms)) AS max_ingest_lag_ms
FROM market_pulse.trades_dedup
GROUP BY symbol, window_start;
