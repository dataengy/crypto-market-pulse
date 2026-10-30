-- Pure Spark SQL SELECT; invoked in local debug after real streaming file ingestion.
WITH valid AS (
  SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (
      PARTITION BY event_id ORDER BY received_at_ms, event_time_ms, trade_id
    ) AS rn FROM trades_raw
    WHERE schema_version = 1 AND price > 0 AND quantity > 0
      AND side IN ('Buy','Sell')
  ) WHERE rn = 1
)
SELECT symbol, DATE_TRUNC('MINUTE', TIMESTAMP_MILLIS(event_time_ms)) AS window_start,
  COUNT(*) AS trade_count,
  MIN_BY(price, named_struct('t',event_time_ms,'id',event_id)) AS open_price,
  MAX(price) AS high_price, MIN(price) AS low_price,
  MAX_BY(price,named_struct('t',event_time_ms,'id',event_id)) AS close_price,
  SUM(quantity) AS volume,
  SUM(price * quantity) / SUM(quantity) AS vwap
FROM valid
GROUP BY symbol, DATE_TRUNC('MINUTE', TIMESTAMP_MILLIS(event_time_ms))
