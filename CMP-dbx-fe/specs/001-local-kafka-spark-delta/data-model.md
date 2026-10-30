# Data Model: trades pipeline (shared by local and cloud)

The column lists are owned by code: `cmp.bronze.TRADE_SCHEMA` and `sql/models/*_select.sql`. This page names the entities and their rules only.

| Entity | Kind (cloud / local) | Grain | Key rules |
|---|---|---|---|
| Trade event | Kafka value (JSON) | 1 exchange trade | [contracts/kafka-trade-event.md](contracts/kafka-trade-event.md). Kafka key = `event_id` |
| `trades_bronze` | streaming table / Delta append | 1 Kafka record | `TRADE_SCHEMA` + `kafka_partition`, `kafka_offset`, `kafka_timestamp`. Malformed → NULL fields. Append-only, so duplicates are kept |
| `trades_silver` | streaming table + `EXPECT valid_trade … DROP ROW` / Delta CTAS + `WHERE` | 1 valid record | rule: [valid_trade.sql](../../sql/models/valid_trade.sql) |
| `trades_dedup` | MV / Delta CTAS | 1 `event_id` | first arrival wins: `ORDER BY received_at_ms, event_time_ms, trade_id` |
| `trades_1m` | MV / Delta CTAS | `symbol × minute(event_time)` | OHLCV + notional, vwap, buy_trades, max_ingest_lag_ms. open/close by `(event_time_ms, event_id)` |
| `trades_latest` | MV / Delta CTAS | `symbol` | last_price, latest_event_time_ms, total_trades |

Money: `DECIMAL(38,12)` from bronze onward. The dashboard casts to DOUBLE for display only ([history.sql](../../sql/dashboard/history.sql)).

Fixture expectations ([constitution VII](../../.specify/memory/constitution.md#vii-one-fixture-assertion-everywhere-non-negotiable)):
- bronze = 8 per produce
- dedup = 7
- BTCUSDT 10:00 bar = `4 / 0.45 / 70000 / 70010 / 69990`
- latest: BTCUSDT `total_trades 5`, ETHUSDT `last_price 3502`
