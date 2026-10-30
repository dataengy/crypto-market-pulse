## ADDED Requirements

### Requirement: One-minute OHLCV view
`trades_1m` SHALL expose, per symbol and UTC minute, computed from deduplicated trades:
- `trade_count`, `volume`
- `open`, `high`, `low`, `close`, ordering open and close by `(event_time_ms, event_id)`
- `vwap`, `buy_trades`, `max_ingest_lag_ms`

#### Scenario: Fixture bar
- **WHEN** the fixture is loaded into an isolated database
- **THEN** the BTCUSDT 2026-10-30 10:00 UTC row is `trade_count=4, volume=0.45, open=70000, high=70010, close=69990`

#### Scenario: Idempotent rerun
- **WHEN** the fixture is replayed and consumed again with the same group
- **THEN** the 10:00 bar is identical to the first run

#### Scenario: Out-of-order arrival
- **WHEN** the fixture is produced shuffled with a fixed seed
- **THEN** every bar equals the unshuffled result

### Requirement: Late events revise their minute
The marts SHALL recompute at query time. A late or out-of-order trade SHALL update its own minute, and nothing SHALL be dropped by a watermark.

#### Scenario: Late trade
- **WHEN** a BTCUSDT 10:00:59 trade arrives after 10:01 data
- **THEN** the 10:00 bar equals the pure-Python reference computed over all trades

### Requirement: Latest price view
`trades_latest` SHALL return one row per symbol with the price of the greatest `(event_time_ms, event_id)`.

#### Scenario: Latest after fixture
- **WHEN** the fixture is loaded
- **THEN** each fixture symbol has exactly one row, and its price equals the reference's last trade

### Requirement: Shared assertion
The fixture assertion SHALL be a single SQL check, run by `just verify <db>` locally and reused unchanged by the cloud verification.

#### Scenario: Verify fails loudly
- **WHEN** `just verify <db>` runs on a database whose 10:00 bar differs from the expected values
- **THEN** it exits non-zero and prints the expected and actual rows
