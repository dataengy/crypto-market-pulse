CREATE OR REPLACE VIEW crypto_pulse.trades_dedup AS
WITH decoded AS (
  SELECT SAFE.PARSE_JSON(SAFE_CONVERT_BYTES_TO_STRING(data)) AS payload
  FROM crypto_pulse.trades_raw
), typed AS (
  SELECT
    JSON_VALUE(payload, '$.event_id') AS event_id,
    JSON_VALUE(payload, '$.source') AS source,
    JSON_VALUE(payload, '$.category') AS category,
    JSON_VALUE(payload, '$.symbol') AS symbol,
    JSON_VALUE(payload, '$.trade_id') AS trade_id,
    SAFE_CAST(JSON_VALUE(payload, '$.schema_version') AS INT64) AS schema_version,
    SAFE_CAST(JSON_VALUE(payload, '$.event_time_ms') AS INT64) AS event_time_ms,
    SAFE_CAST(JSON_VALUE(payload, '$.received_at_ms') AS INT64) AS received_at_ms,
    JSON_VALUE(payload, '$.side') AS side,
    SAFE_CAST(JSON_VALUE(payload, '$.price') AS BIGNUMERIC) AS price,
    SAFE_CAST(JSON_VALUE(payload, '$.quantity') AS BIGNUMERIC) AS quantity
  FROM decoded
)
SELECT * FROM typed
WHERE schema_version = 1 AND source = 'bybit'
  AND event_id IS NOT NULL AND event_time_ms IS NOT NULL
  AND side IN ('Buy','Sell') AND price > 0 AND quantity > 0
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY event_id ORDER BY received_at_ms, event_time_ms, trade_id
) = 1;
