-- Typed trades from bronze; quality filter is applied by the caller (see valid_trade.sql).
SELECT schema_version, event_id, source, category, symbol, trade_id,
       event_time_ms, received_at_ms, side, price, quantity,
       kafka_partition, kafka_offset, kafka_timestamp
FROM {{source}}
