CREATE TABLE IF NOT EXISTS market_pulse.trades_raw (
    schema_version UInt8,
    event_id String,
    source LowCardinality(String),
    category LowCardinality(String),
    symbol LowCardinality(String),
    trade_id String,
    event_time_ms UInt64,
    received_at_ms UInt64,
    side LowCardinality(String),
    price Decimal(38, 12),
    quantity Decimal(38, 12)
) ENGINE = MergeTree
PARTITION BY toYYYYMM(fromUnixTimestamp64Milli(toInt64(event_time_ms)))
ORDER BY (symbol, event_time_ms, event_id);
