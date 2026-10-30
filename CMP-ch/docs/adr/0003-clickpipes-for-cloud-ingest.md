---
status: accepted
date: 2026-10-30
---
# Cloud ingest: Confluent Cloud Basic → ClickPipes → existing trades_raw

## Context and Problem Statement
In ClickHouse Cloud, something must read the managed Kafka topic into `trades_raw` without our own long-running compute. Everything downstream of `trades_raw` stays as in [ADR-0002](0002-replacingmergetree-with-final-views.md).

## Considered Options
1. ClickPipes (Kafka/Confluent source, JSON) into the existing `trades_raw`
2. Kafka table engine on ClickHouse Cloud
3. The Python consumer ([ADR-0001](0001-python-consumer-over-kafka-engine.md)) on a host, writing to Cloud

## Decision Outcome
Option 1, with Confluent Cloud Basic as the broker. ClickPipes is managed and supported on the Basic tier. It is defined in Terraform (`clickhouse_clickpipe`, provider ≥ 3.14), and Confluent is a first-class source. The default replica size costs:
- **$0.0125/h** at XS (0.0625 CU), or $0.05/h at 0.25 CU (the docs conflict on which size is the default)
- plus $0.04/GB ingested

Verified 2026-10-30; [pricing table](../../openspec/changes/add-clickhouse-cloud-clickpipes/design.md#pricing-facts).

### Consequences
- Good: no ingest process to host. The same MV, dedup and views; the same assertion.
- Bad: the pipe bills per hour even when idle, so `just cloud-pause` / `cloud-down` are mandatory guardrails ([CH-C09](../../../docs/plans/clickhouse/tasks.md#ch-c09)).
- Bad: unverified items:
  - delivery semantics (dedup covers at-least-once either way)
  - JSON string → `Decimal(38,12)` mapping into an existing table
  - If the mapping fails, option 3 becomes active ([CH-CB2](../../../docs/plans/clickhouse/tasks.md#ch-cb2)).
- Rejected: option 2. It is supported, but ClickHouse recommends ClickPipes, and it would run a different code path from local.

## More Information
Plan: [02 §2](../../../docs/plans/clickhouse/02-cloud-deploy-test.md#c-decisions) · Kafka alternatives: [CH-CB1](../../../docs/plans/clickhouse/tasks.md#ch-cb1) · spec: [ingest delta](../../openspec/changes/add-clickhouse-cloud-clickpipes/specs/ingest/spec.md).
