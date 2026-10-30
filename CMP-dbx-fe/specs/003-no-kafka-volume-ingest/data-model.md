# Data Model: landing Volume

| Entity | Where | Rule |
|---|---|---|
| Landing Volume | `/Volumes/${catalog}/${schema}/${volume.name}/` in the cloud; `.tmp/landing/` locally | bundle `volumes:` resource; holds files only |
| Landing file | one JSONL file per shipped batch | [contracts/landing-file.md](contracts/landing-file.md) |
| `trades_bronze` (volume source) | streaming table | the same columns as the Kafka path. `kafka_partition` and `kafka_offset` come from the file name / record position, or are NULL. **[NEEDS CLARIFICATION in DBX-A04: keep them NULL, or carry them inside each JSONL record]** |

All later tables are unchanged: see [001 data-model](../001-local-kafka-spark-delta/data-model.md).
