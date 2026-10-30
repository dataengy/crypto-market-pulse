---
status: accepted
date: 2026-10-30
---
# Dedup: ReplacingMergeTree fed by an MV, views read with FINAL

## Context and Problem Statement
Ingest is at-least-once, both from the consumer and (assumed) from ClickPipes, so `trades_raw` holds duplicates. The 1m OHLCV and the latest price must count each `event_id` exactly once. They must also stay cheap and handle late events.

## Considered Options
1. `row_number()` dedup view over all of `trades_raw` (the reference handoff)
2. MV `trades_raw` → `trades_dedup` ReplacingMergeTree, with views over `trades_dedup FINAL`
3. AggregatingMergeTree 1m mart fed by an MV from raw
4. Insert-time dedup (`insert_deduplication_token`)

## Decision Outcome
Option 2. Both tables share the same `ORDER BY (symbol, event_time_ms, event_id)` and `PARTITION BY toYYYYMM(event time)`. A duplicate collapses within one partition, so the views run `FINAL` with `do_not_merge_across_partitions_select_final=1`. Validity filters live in the MV.

### Consequences
- Good: exact at query time whether or not merges have run; no full-raw scan; late or out-of-order trades simply revise their minute.
- Good: raw keeps physical duplicates as evidence for F1 and F3.
- Bad: with no version column, the *last* inserted copy wins, so `max_ingest_lag_ms` may reflect the replay. This is documented; OHLCV is unaffected.
- Bad: the cost of `FINAL` grows with unmerged parts. Watch it in `system.parts`.
- Rejected:
  - Option 1 scans everything on every query.
  - Option 3 double-counts duplicates, because the MV sees every insert. It is parked as [CH-LB2](../../../docs/plans/clickhouse/tasks.md#ch-lb2), with dedup upstream.
  - Option 4 only covers identical retried blocks, not Kafka replays.

## More Information
Plan: [01 §4](../../../docs/plans/clickhouse/01-local-dev-debug.md#l-schema) · specs: [storage-dedup](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/storage-dedup/spec.md), [ohlcv-marts](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/ohlcv-marts/spec.md).
