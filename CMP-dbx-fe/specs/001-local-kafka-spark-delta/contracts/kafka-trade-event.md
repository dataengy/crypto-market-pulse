# Contract: Kafka trade event v1 (`market.trades.v1`)

The owner is [`src/cmp/domain.py`](../../../src/cmp/domain.py): `normalize_trade`, `validate_event` and `encode_event`. The topic name comes from `config.yaml: kafka.topic`. The topic is shared with the ClickHouse lane, so this contract is cross-lane.

- **Key**: `event_id` (UTF-8)
- **Value**: compact JSON with sorted keys and these fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | int | `1` |
| `event_id` | string | `bybit:<category>:<symbol>:<trade_id>`; immutable identity |
| `source` | string | `bybit` |
| `category` | string | `linear` \| `spot` \| `inverse` |
| `symbol` | string | alphanumeric, ≤ 32 chars |
| `trade_id` | string | non-empty, ≤ 128 chars |
| `event_time_ms` | int | epoch ms between the years 2000 and 2100 |
| `received_at_ms` | int | ≥ 0 |
| `side` | string | `Buy` \| `Sell` |
| `price`, `quantity` | string decimal | finite and > 0. Kept as strings so no precision is lost; bronze parses them to `DECIMAL(38,12)` |

Compatibility:
- Adding a field is non-breaking, because bronze uses an explicit schema and ignores extra fields.
- Changing a type or the identity rule needs `schema_version: 2`, plus a new silver rule.
