## ADDED Requirements

### Requirement: Producer with explicit source and sink
The producer SHALL require `--source fixture|bybit` and `--sink kafka|stdout`. It SHALL publish normalized trade events to the configured topic, keyed by `event_id`. Any undelivered message at close SHALL make it exit non-zero.

#### Scenario: Fixture replay
- **WHEN** `just produce fixture` runs against an empty topic
- **THEN** the topic holds 8 messages, and the two copies of the duplicate trade share a key and a partition

#### Scenario: Bounded live run
- **WHEN** `just produce bybit 50` runs
- **THEN** exactly 50 events that pass domain validation are published and the process exits 0

#### Scenario: Missing argument
- **WHEN** the producer is started without `--sink`
- **THEN** it exits non-zero with a usage error and publishes nothing

#### Scenario: Delivery failure
- **WHEN** the broker is unreachable and the flush timeout passes
- **THEN** the producer exits non-zero and reports the undelivered count

### Requirement: At-least-once consumer into trades_raw
The consumer SHALL validate each event, insert batches into `trades_raw`, and commit offsets synchronously only after the insert succeeded. Batch size and wait come from config.

#### Scenario: Fixture consumed
- **WHEN** the consumer runs after `just produce fixture` on a fresh group
- **THEN** `trades_raw` gains 8 rows and the group lag is 0

#### Scenario: Crash between insert and commit
- **WHEN** the consumer runs with `--crash-after-insert 3` and is then restarted
- **THEN** the replayed rows appear again in `trades_raw`, while `trades_dedup FINAL` and `trades_1m` are unchanged

### Requirement: Consumer termination
The consumer SHALL exit 0 after `--max-messages` or after `kafka.idle_exit_s` without messages. It SHALL exit non-zero on a message that fails validation, leaving that offset uncommitted.

#### Scenario: Idle exit
- **WHEN** no message arrives for `kafka.idle_exit_s`
- **THEN** the consumer commits what it inserted and exits 0

#### Scenario: Poison message
- **WHEN** a non-JSON message is produced to the topic
- **THEN** the consumer exits non-zero, logs its partition and offset, and that offset is not committed
