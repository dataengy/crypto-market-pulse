-- Databricks AI/BI dashboard dataset; edit ONLY this file, then regenerate JSON.
SELECT window_start, symbol, CAST(close_price AS DOUBLE) AS close_price,
       CAST(vwap AS DOUBLE) AS vwap,
       CAST(volume AS DOUBLE) AS volume,
       trade_count,
       max_ingest_lag_ms
FROM `workspace`.`crypto_pulse`.trades_1m
WHERE symbol = 'BTCUSDT' -- v1 dashboard default; Streamlit supports switching symbols
ORDER BY window_start DESC
LIMIT 500
