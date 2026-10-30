-- Lakeflow SQL source: append-only Delta Bronze, stream ingestion.
CREATE OR REFRESH STREAMING TABLE trades_silver (
  CONSTRAINT valid_trade EXPECT (
    schema_version = 1 AND price > 0 AND quantity > 0
    AND side IN ('Buy', 'Sell') AND event_id IS NOT NULL
  ) ON VIOLATION DROP ROW
) AS
SELECT * FROM STREAM(workspace.crypto_pulse.trades_raw);
