-- Query-level dedup: a replay can be present twice physically in silver; first arrival wins.
SELECT schema_version, event_id, source, category, symbol, trade_id,
       event_time_ms, received_at_ms, side, price, quantity
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY event_id ORDER BY received_at_ms, event_time_ms, trade_id
  ) AS rn
  FROM {{source}}
) AS ranked
WHERE rn = 1
