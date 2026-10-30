-- Dedup is query-level; a replay can be present twice physically in Silver.
CREATE OR REFRESH MATERIALIZED VIEW trades_dedup AS
SELECT schema_version, event_id, source, category, symbol, trade_id,
       event_time_ms, received_at_ms, side, price, quantity
FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY event_id ORDER BY received_at_ms, event_time_ms, trade_id
  ) AS rn
  FROM trades_silver
) WHERE rn = 1;
