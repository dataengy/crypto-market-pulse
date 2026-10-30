# CMP-ch architecture

Ingest writes only `trades_raw`. Everything downstream is the same SQL in both environments, so local and cloud differ only in transport and ingest. Decisions: [ADR-0001](../adr/0001-python-consumer-over-kafka-engine.md) · [0002](../adr/0002-replacingmergetree-with-final-views.md) · [0003](../adr/0003-clickpipes-for-cloud-ingest.md) · [0004](../adr/0004-streamlit-dashboard.md).

```mermaid
flowchart LR
  WS["Bybit V5 publicTrade"] --> P["produce.py<br/>--source fixture|bybit"]
  FX["tests/fixtures/trades.jsonl"] --> P
  P -->|"key = event_id"| RP[("local: Redpanda<br/>market.trades.v1")]
  P -->|"CMP_PROFILE=cloud"| CF[("cloud: Confluent Basic<br/>market.trades.v1")]
  RP --> C["consume.py<br/>insert then commit"]
  CF --> CP["ClickPipe<br/>JSON, SASL PLAIN"]
  C --> RAW
  CP --> RAW
  subgraph CH["ClickHouse (local docker or Cloud Basic), same sql/clickhouse/*.sql"]
    RAW["trades_raw<br/>MergeTree, keeps duplicates"] -->|MV + validity filter| DD["trades_dedup<br/>ReplacingMergeTree"]
    DD -->|FINAL| M1["trades_1m view"]
    DD -->|FINAL| LT["trades_latest view"]
  end
  M1 --> ST["Streamlit app<br/>user cmp_dash, stale badge"]
  LT --> ST
  M1 -.->|"sql/checks/fixture_1m.sql"| V["just verify / just cloud-verify"]
```

| Boundary | Contract | Spec |
|---|---|---|
| Producer → Kafka | normalized trade JSON, key `event_id` | [ingest](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/ingest/spec.md) |
| Kafka → `trades_raw` | at-least-once, 1:1 columns | ingest (+ [cloud delta](../../openspec/changes/add-clickhouse-cloud-clickpipes/specs/ingest/spec.md)) |
| `trades_raw` → `trades_dedup` | one row per `event_id` under `FINAL` | [storage-dedup](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/storage-dedup/spec.md) |
| Views → users | bar 4 / 0.45 / 70000 / 70010 / 69990 for the fixture | [ohlcv-marts](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/ohlcv-marts/spec.md), [dashboard](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/dashboard/spec.md) |
