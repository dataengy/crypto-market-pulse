## ADDED Requirements

### Requirement: Read-only market dashboard
The dashboard SHALL show:
- the latest price per symbol
- 1m OHLCV, VWAP and volume charts from `trades_1m` / `trades_latest`

Query TTL and row limit SHALL come from config. It SHALL connect as a user that can only SELECT those views.

#### Scenario: Fixture bars visible
- **WHEN** `just dashboard` runs against a database loaded with the fixture
- **THEN** the BTCUSDT 10:00 bar is shown with the fixture values

#### Scenario: Least privilege
- **WHEN** the dashboard user attempts `INSERT` or a `SELECT` on `trades_raw`
- **THEN** ClickHouse rejects it with an access error

### Requirement: Staleness badge
The dashboard SHALL show a stale-data badge when now minus the latest event time exceeds `dashboard.stale_after_s`.

#### Scenario: Producer stopped
- **WHEN** no new trade arrives for longer than `dashboard.stale_after_s`
- **THEN** the stale badge is displayed on the next refresh
