# CMP-dbx-fe tasks

Plan: [plan.md](plan.md) · index: [README.md](README.md) · implementation: `./CMP-dbx-fe/` (branch `feat/cmp-dbx-fe`)

## Local (DBX-L)

<a id="dbx-l01"></a>
- [x] **DBX-L01** Scaffold: uv + py3.12, justfile, `config/config.yaml` + `.env.common` + `.env.secrets.demo`, strict settings
  - acceptance: a missing key or env var fails with the key name and the file to fill (`tests/test_config_and_build.py`)
  - plan: [plan.md › Steps 0–1](plan.md#steps)

<a id="dbx-l02"></a>
- [x] **DBX-L02** Core copy (domain, bybit_ws, publish, reference OHLCV) with WS/Kafka scalars in config
  - acceptance: `tests/test_domain.py` green; `find_hardcoded_scalars.py` only flags schema/bootstrap constants
  - plan: [plan.md › Step 1](plan.md#steps)

<a id="dbx-l03"></a>
- [x] **DBX-L03** Shared SQL models + `scripts/build.py` (Lakeflow SQL + dashboard JSON) + sync test
  - acceptance: `just verify` shows no diff; the quality rule lives once, in `sql/models/valid_trade.sql`
  - plan: [plan.md › Step 2](plan.md#steps)

<a id="dbx-l04"></a>
- [x] **DBX-L04** Spark + Delta check of `parse_trades` + models (Kafka-shaped rows)
  - acceptance: `uv run pytest -m spark`: fixture bar exact, malformed row dropped, full replay leaves marts unchanged
  - plan: [plan.md › Step 4](plan.md#steps)

<a id="dbx-l05"></a>
- [x] **DBX-L05** Local Kafka E2E: `just up && just it`
  - depends: DBX-L04 and a working Docker daemon (Docker Desktop returned HTTP 500 on 2026-10-30; Colima profile is stopped)
  - acceptance: fixture → Redpanda → `local_spark.run` (availableNow) is exact; a restart doesn't re-read; producer replay is deduped
  - plan: [plan.md › Steps 3–4](plan.md#steps)

<a id="dbx-l06"></a>
- [x] **DBX-L06** MiniLake smoke: `just minilake-smoke`
  - depends: DBX-L05 (same compose)
  - acceptance: SDK creates the catalog/schema/table, fixture INSERT works, silver/dedup run (dedup = 7); DuckDB dialect gaps (expected for `TIMESTAMP_MILLIS`, `named_struct`) are listed in the README instead of forking the SQL
  - plan: [plan.md › Step 5](plan.md#steps)

## Cloud (DBX-C) — all depend on DBX-L05

<a id="dbx-c01"></a>
- [ ] **DBX-C01** Accounts + CLI: install Databricks CLI ≥ 1.16, `databricks auth login` (user picks the profile), create the Kafka cluster/topic/API key, fill `config/.env.secrets`
  - acceptance: `just dbx-validate` passes; `CMP_PROFILE=cloud just produce fixture` delivers 8 messages

<a id="dbx-c02"></a>
- [ ] **DBX-C02** **Gate:** Free Edition serverless → Kafka egress (`just dbx-secrets && just dbx-deploy && just dbx-probe`)
  - acceptance: the probe prints `TCP OK` and `Kafka SASL read OK`. **If it is blocked: stop and switch to the alternate plan [alt-no-kafka.md](alt-no-kafka.md) ([DBX-A01](#dbx-a01)…)**
  - plan: [plan.md › Step 6](plan.md#steps)

<a id="dbx-c03"></a>
- [ ] **DBX-C03** Pipeline run: `just dbx-run`; check the event log for `valid_trade` drops
  - depends: DBX-C02 · acceptance: all 5 datasets materialize; `trades_dedup` = 7 rows for the fixture topic

<a id="dbx-c04"></a>
- [ ] **DBX-C04** Cloud = local parity: `just dbx-query "SELECT * FROM workspace.crypto_pulse.trades_1m WHERE symbol='BTCUSDT' ORDER BY window_start LIMIT 1"`
  - acceptance: `4 / 0.45 / 70000 / 70010 / 69990`, same as `just spark`. Use an isolated topic, because the fixture's minute is a real date

<a id="dbx-c05"></a>
- [ ] **DBX-C05** Live data + dashboard: `CMP_PROFILE=cloud just produce bybit`, unpause `cmp-refresh`, open the dashboard
  - acceptance: bars appear within one refresh; Free Edition limits respected (1 pipeline, the 2X-Small warehouse); `cmp-refresh` paused again after the demo

<a id="dbx-a"></a>
## Alternate path (DBX-A): no Kafka reachable from Free Edition → push via UC Volume — plan: [alt-no-kafka.md](alt-no-kafka.md)

<a id="dbx-a01"></a>
- [ ] **DBX-A01** Extend the probe: TCP bootstrap / HTTPS Kafka REST / trusted control host / `ls` on the landing Volume → decides which path to take
  - depends: DBX-C01 · acceptance: one probe run prints all 4 results; the chosen path is recorded in the README status · plan: [alt-no-kafka.md#a-decision](alt-no-kafka.md#a-decision)
<a id="dbx-a02"></a>
- [ ] **DBX-A02** `VolumePublisher` in `cmp.publish`: offset-named JSONL files, `files.upload(overwrite=True)`, batch settings from `config.yaml: volume.*`
  - depends: DBX-A01 · acceptance: unit tests for naming and idempotent re-upload; no hardcoded scalars
<a id="dbx-a03"></a>
- [ ] **DBX-A03** `scripts/ship_to_volume.py` + `just ship`: Kafka → Volume, commit after upload, idle exit, poison stop; `--source fixture` uploads without Kafka
  - depends: DBX-A02 · acceptance: a crash between upload and commit re-ships the same offsets; `trades_dedup` is unchanged
<a id="dbx-a04"></a>
- [ ] **DBX-A04** Bundle `volumes: landing` + pipeline config `cmp.bronze_source: kafka|volume` (var with no default); Auto Loader branch in `pipelines/bronze.py`
  - depends: DBX-A02 · acceptance: `just dbx-validate` ok; the build-sync test is green
<a id="dbx-a05"></a>
- [ ] **DBX-A05** Local parity: shipper → `.tmp/landing` → `local_spark.py --bronze-source volume`
  - depends: DBX-A03, DBX-L05 · acceptance: the fixture bar is `4 / 0.45 / 70000 / 70010 / 69990`; re-shipping leaves it unchanged
<a id="dbx-a06"></a>
- [ ] **DBX-A06** Cloud verify over the Volume: deploy (`bronze_source=volume`) → `just ship --source fixture` → `just dbx-run` → `just dbx-query`
  - depends: DBX-A04, DBX-A05 · acceptance: same bar as DBX-C04; a second ship and run leaves the bar unchanged
<a id="dbx-a07"></a>
- [ ] **DBX-A07** Hosted shipper run: GH Actions `workflow_dispatch` (bounded), then `bundle run`
  - depends: DBX-A06 · acceptance: a live Bybit → Kafka → Volume → dashboard refresh works without the laptop
<a id="dbx-ab1"></a>
- [ ] **DBX-AB1** (backlog) Bronze via SQL warehouse `INSERT` (databricks-sql-connector) instead of the Volume; measure the warehouse-quota impact
<a id="dbx-ab2"></a>
- [ ] **DBX-AB2** (backlog) Zerobus Ingest: check whether it is available and whether auth works on Free Edition (PAT / U2M rather than service principal); if it does, it replaces the shipper's upload step

## Backlog (DBX-B) — each has a plan in `CMP-dbx-fe/docs/backlog/`

<a id="dbx-b1"></a>
- [ ] **DBX-B1** MinIO + Delta as the local lake (S3 paths like the cloud) → [minio-delta-lake.md](../../../CMP-dbx-fe/docs/backlog/minio-delta-lake.md)

<a id="dbx-b2"></a>
- [ ] **DBX-B2** Spark 4.1 Declarative Pipelines locally, for real pipeline parity → [spark-sdp-parity.md](../../../CMP-dbx-fe/docs/backlog/spark-sdp-parity.md)

<a id="dbx-b3"></a>
- [ ] **DBX-B3** Iceberg (REST catalog) locally / UniForm in Databricks → [iceberg-uniform.md](../../../CMP-dbx-fe/docs/backlog/iceberg-uniform.md)

<a id="dbx-b4"></a>
- [ ] **DBX-B4** Fallback ingest via UC Volume + Auto Loader if Kafka egress is blocked → [volume-drop-ingest.md](../../../CMP-dbx-fe/docs/backlog/volume-drop-ingest.md) — **promoted to [DBX-A01…A07](#dbx-a)**

<a id="dbx-b5"></a>
- [ ] **DBX-B5** Kafka provider choice (Confluent / Aiven / Redpanda Serverless / MSK / GCP / YC / MWS / Hetzner) → [kafka-provider-choice.md](../../../CMP-dbx-fe/docs/backlog/kafka-provider-choice.md)

<a id="dbx-b6"></a>
- [ ] **DBX-B6** Hosted producer (off the laptop) → [hosted-producer.md](../../../CMP-dbx-fe/docs/backlog/hosted-producer.md)

<a id="dbx-b7"></a>
- [ ] **DBX-B7** CI: unit + build-sync + Spark test; optional MiniLake workflow → [ci.md](../../../CMP-dbx-fe/docs/backlog/ci.md)
