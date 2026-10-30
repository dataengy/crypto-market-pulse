# DBX-B4 — Fallback ingest: UC Volume drop + Auto Loader

**When:** [DBX-C02](../../../docs/plans/dbx-fe/tasks.md#dbx-c02) shows that Free Edition serverless cannot reach the Kafka cluster (egress is limited to trusted domains). ← [tasks](../../../docs/plans/dbx-fe/tasks.md#dbx-b4)

**Design:** laptop/hosted *shipper* consumes Kafka → writes JSONL micro-batches → `WorkspaceClient.files.upload` to `/Volumes/<catalog>/<schema>/landing/` (inbound to Databricks, so it's allowed). Bronze becomes `STREAM read_files('/Volumes/…/landing', format => 'json', schema => TRADE_SCHEMA)`; silver and later stay unchanged.

**Steps**
- [ ] Bundle: a `volumes:` resource `landing`; `pipelines/bronze.py` switches source by pipeline config `cmp.bronze_source: kafka|volume`
- [ ] `scripts/ship_to_volume.py`: Kafka consumer (committed offsets) → files named `{topic}-{partition}-{first_offset}.jsonl` (idempotent re-upload); batch size/interval in config
- [ ] Local equivalent: shipper writes to `.tmp/landing` and local Spark reads it with `readStream.json` (MiniLake Files API, if supported)

**Acceptance:** the fixture bar matches in the cloud with Kafka unreachable from the workspace; shipper restart → no duplicates in `trades_dedup`.
