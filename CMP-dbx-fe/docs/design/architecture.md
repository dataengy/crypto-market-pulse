# Architecture — CMP-dbx-fe

One codebase and two runtimes. The local stack is for dev and debug only; production is managed Kafka + Databricks Free Edition. The rules are in the [constitution](../../.specify/memory/constitution.md) and the entities in the [data model](../../specs/001-local-kafka-spark-delta/data-model.md).

```mermaid
flowchart LR
  WS[Bybit WS publicTrade] --> P[scripts/produce.py<br/>cmp.domain.normalize_trade]
  FX[tests/fixtures/trades.jsonl] --> P
  P -->|CMP_PROFILE=local| RP[(Redpanda<br/>127.0.0.1:19092)]
  P -->|CMP_PROFILE=cloud| CK[(Managed Kafka<br/>market.trades.v1)]

  subgraph Shared[shared code]
    PT[cmp.bronze.parse_trades]
    SM[sql/models/*_select.sql<br/>valid_trade.sql]
    B[scripts/build.py]
  end
  SM --> B

  RP --> LS[scripts/local_spark.py<br/>foreachBatch]
  LS -.uses.-> PT
  LS -.uses.-> SM
  LS --> LD[(.tmp/lake Delta<br/>bronze to latest)]
  SM -.portability.-> ML[MiniLake emulator<br/>SDK + UC + DuckDB SQL]

  CK -->|gate DBX-C02| BR[pipelines/bronze.py<br/>trades_bronze]
  CK -.blocked: DBX-A.-> SH[ship_to_volume.py] --> VOL[(UC Volume landing<br/>Auto Loader)] --> BR
  BR -.uses.-> PT
  B -->|generates| PS[pipelines/10..40_*.sql<br/>silver, dedup, 1m, latest]
  BR --> PS --> UC[(workspace.crypto_pulse)]
  B -->|generates| DB[AI/BI dashboard<br/>Starter Warehouse]
  UC --> DB
  J[job cmp-refresh PAUSED] -.triggers.-> PS
```

| Concern | Decision |
|---|---|
| Local tables | [ADR-0001](../adr/0001-path-based-delta-locally.md): path-based Delta + CTAS |
| SQL reuse | [ADR-0002](../adr/0002-shared-sql-models-and-build.md): `sql/models` + `build.py` |
| Cloud ingest | [ADR-0003](../adr/0003-kafka-from-pipeline-with-volume-fallback.md): Kafka pull, with the Volume push as the fallback |
| Emulator | [ADR-0004](../adr/0004-minilake-dmux-emulator.md): MiniLake for the SDK/SQL smoke only |
| Cost | [ADR-0005](../adr/0005-triggered-pipeline-paused-job.md): triggered pipeline, paused job |

Runbooks: [local dev/debug](../runbooks/local-dev-debug.md) · [Free Edition deploy/verify](../runbooks/dbx-fe-deploy-verify.md).
