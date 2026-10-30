## ADDED Requirements

### Requirement: Managed ingest into the shared landing table
In the cloud profile, a ClickPipe SHALL read the trades topic as JSON over SASL_SSL/PLAIN and SHALL insert into the existing `trades_raw`, mapping columns 1:1. Downstream dedup and views SHALL be unchanged from local.

#### Scenario: Events flow end to end
- **WHEN** the ClickPipe status is Running and events are produced to `market.trades.v1`
- **THEN** they appear in `trades_raw` and in `trades_dedup FINAL`

#### Scenario: Decimal mapping
- **WHEN** a fixture event with string price `"70010.5"` is ingested
- **THEN** `trades_raw.price` holds `70010.5` as `Decimal(38,12)`. If the mapping is rejected, the change records that and switches to the consumer fallback (CH-CB2)

### Requirement: Cloud producer profile
With `CMP_PROFILE=cloud`, the producer SHALL publish to the managed cluster using the protocol and mechanism from `profiles.cloud`. The live job SHALL be bounded by a trade count and by a timeout taken from config.

#### Scenario: Bounded live run to cloud
- **WHEN** `CMP_PROFILE=cloud just produce bybit 50` runs
- **THEN** 50 events are published and the process exits 0

#### Scenario: Job timeout
- **WHEN** the `workflow_dispatch` producer job exceeds its configured timeout
- **THEN** the job is cancelled and leaves no running producer
