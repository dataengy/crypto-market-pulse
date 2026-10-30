SELECT symbol,
  MAX_BY(price, named_struct('t', event_time_ms, 'id', event_id)) AS last_price,
  MAX(event_time_ms) AS latest_event_time_ms,
  COUNT(*) AS total_trades
FROM {{source}}
GROUP BY symbol
