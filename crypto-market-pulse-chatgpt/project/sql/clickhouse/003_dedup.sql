CREATE VIEW IF NOT EXISTS market_pulse.trades_dedup AS
SELECT schema_version, event_id, source, category, symbol, trade_id,
       event_time_ms, received_at_ms, side, price, quantity
FROM (
  SELECT *, row_number() OVER (
    PARTITION BY event_id ORDER BY received_at_ms, event_time_ms, trade_id
  ) AS rn
  FROM market_pulse.trades_raw
  WHERE schema_version = 1 AND source = 'bybit'
    AND price > 0 AND quantity > 0 AND side IN ('Buy', 'Sell')
) WHERE rn = 1;
