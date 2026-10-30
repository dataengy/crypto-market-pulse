## ADDED Requirements

### Requirement: Raw landing keeps duplicates
`trades_raw` SHALL store every delivered event, duplicates included, as evidence. It is the only table that ingest writes to, both locally and in the cloud.

#### Scenario: Replay grows raw
- **WHEN** the fixture is produced and consumed twice into a fresh database
- **THEN** `count()` on `trades_raw` is 16

### Requirement: Deduplication by event_id
Every row inserted into `trades_raw` SHALL be forwarded to `trades_dedup` if it passes the validity filters. Reads with `FINAL` SHALL return exactly one row per `event_id`.

#### Scenario: Exact dedup at query time
- **WHEN** the fixture (8 rows, 7 distinct `event_id`) is loaded
- **THEN** `count() FROM trades_dedup FINAL` is 7, whether or not a merge has run

#### Scenario: Invalid row filtered
- **WHEN** a row with a non-positive price reaches `trades_raw`
- **THEN** it is absent from `trades_dedup`

### Requirement: Idempotent, guarded schema setup
`just ch-setup` SHALL apply the ordered DDL files with a `{db}` placeholder and `IF NOT EXISTS` semantics. It SHALL refuse a non-local host unless `CMP_ALLOW_REMOTE_DDL=YES` is set.

#### Scenario: Second run is a no-op
- **WHEN** `just ch-setup` runs twice against the same database
- **THEN** the second run succeeds and `system.tables` is unchanged

#### Scenario: Remote guard
- **WHEN** `CLICKHOUSE_URL` points to a non-local host and `CMP_ALLOW_REMOTE_DDL` is not `YES`
- **THEN** setup exits non-zero before running any statement

### Requirement: Numeric safety
Prices and quantities SHALL be stored as `Decimal(38,12)`. A notional overflow SHALL fail loudly, not wrap or round silently.

#### Scenario: Large quantity
- **WHEN** the unit test inserts a row whose price × qty exceeds the result type range
- **THEN** the query raises an error
