-- AI/BI dashboard dataset; edit ONLY this file, then `just build`. Catalog/schema come from the bundle.
SELECT window_start, symbol, CAST(close_price AS DOUBLE) AS close_price,
       CAST(vwap AS DOUBLE) AS vwap,
       CAST(volume AS DOUBLE) AS volume,
       trade_count,
       max_ingest_lag_ms
FROM trades_1m
WHERE symbol = '{{symbol}}'
ORDER BY window_start DESC
LIMIT 500
