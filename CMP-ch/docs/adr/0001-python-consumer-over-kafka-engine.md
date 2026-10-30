---
status: accepted
date: 2026-10-30
---
# Local ingest: Python consumer over the ClickHouse Kafka engine

## Context and Problem Statement
Locally, something must move Kafka `market.trades.v1` into ClickHouse. In the cloud that job goes to ClickPipes ([ADR-0003](0003-clickpipes-for-cloud-ingest.md)). We want the downstream path to be identical in both, and we want commit and poison behaviour we can test (faults F3 and F5).

## Considered Options
1. Python consumer (`confluent-kafka` + `clickhouse-connect`) → `trades_raw`
2. ClickHouse `Kafka` engine table + MV → `trades_raw`
3. Kafka Connect ClickHouse sink

## Decision Outcome
Option 1. It writes to the same table ClickPipes targets. Its commit boundary (insert, then sync commit) is in our code, so `--crash-after-insert` can inject F3. A poison message stops it instead of being skipped. The same binary is the cloud fallback ([CH-CB2](../../../docs/plans/clickhouse/tasks.md#ch-cb2)).

### Consequences
- Good: explicit at-least-once semantics, testable faults, no extra JVM.
- Good: it reuses the CMP-dbx-fe domain code.
- Bad: one more process to run. Its throughput is bounded by a single consumer, which is fine for 2 symbols.
- Neutral: option 2 stays as backlog [CH-LB1](../../../docs/plans/clickhouse/tasks.md#ch-lb1), to be compared through `system.kafka_consumers`. Option 3 is rejected: it needs a Connect cluster, which is too much infrastructure for one topic.

## More Information
Plan: [01 §5](../../../docs/plans/clickhouse/01-local-dev-debug.md#l-consumer) · spec: `ingest` in [add-local-redpanda-clickhouse-loop](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/ingest/spec.md).
