-- Silver quality rule (boolean expression only). Cloud: EXPECT ... ON VIOLATION DROP ROW; local: WHERE.
schema_version = 1 AND event_id IS NOT NULL AND price > 0 AND quantity > 0
AND side IN ('Buy', 'Sell')
