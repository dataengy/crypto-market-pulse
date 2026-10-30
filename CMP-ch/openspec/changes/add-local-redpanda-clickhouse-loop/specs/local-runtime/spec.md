## ADDED Requirements

### Requirement: Discover before creating
`just inventory` SHALL list the running containers, compose projects, colima instances and host binaries (`clickhouse`, `rpk`) without changing anything. A compatible running Kafka or ClickHouse SHALL be reused through `.env.secrets` endpoints with project-owned DB `market_pulse_dev`, topic and group, and SHALL NOT have its existing schema, topics or groups altered.

#### Scenario: Inventory is read-only
- **WHEN** `just inventory` runs twice
- **THEN** `docker ps -a` output is identical before and after, and nothing is written to the repo

#### Scenario: Reuse an existing ClickHouse
- **WHEN** a compatible ClickHouse is already reachable at the configured endpoint
- **THEN** `just up` starts no ClickHouse container and `just ch-setup` creates only the project-owned database

### Requirement: Owned, localhost-only containers
When nothing fits, `just up` SHALL start Redpanda and ClickHouse labelled `com.crypto_market_pulse.owner=cmp-ch`, bound to `127.0.0.1`, with pinned image tags and healthchecks. Ports SHALL come from `.env.common` with no fallback.

#### Scenario: Idempotent up
- **WHEN** `just up` runs a second time
- **THEN** no new container or volume is created and both healthchecks are green

#### Scenario: Missing port variable
- **WHEN** `CMP_CH_HTTP_PORT` is unset
- **THEN** compose fails with an error naming the variable

### Requirement: Safe teardown
`just down` SHALL only stop containers carrying the owner label. It SHALL never remove volumes or prune. Volume removal SHALL require an explicit `just nuke-own` that asks for confirmation.

#### Scenario: Unlabelled container untouched
- **WHEN** an unlabelled ClickHouse container is running and `just down` runs
- **THEN** that container is still running and every `cmp-ch` volume still exists

### Requirement: Read-only debug recipes
`just dbg-*` SHALL show topic, consumer lag, ClickHouse parts, query_log errors and the raw/dedup counts. Only `dbg-rpk-produce` SHALL write.

#### Scenario: Counts recipe
- **WHEN** `just dbg-counts` runs after the fixture is loaded
- **THEN** it prints raw `count()`, `uniqExact(event_id)`, `count() FROM trades_dedup FINAL` and the latest minute per symbol
