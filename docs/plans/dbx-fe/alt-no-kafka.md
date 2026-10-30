# Alternate plan: Free Edition cannot read any Kafka → push-ingest via UC Volume

Lane index: [README.md](README.md) · main plan: [plan.md](plan.md) · tasks: [tasks.md#dbx-a](tasks.md#dbx-a)

## Context
Free Edition: "outbound internet access is restricted to a limited set of trusted domains", compute is serverless only, there is one active pipeline per type, and Apps are capped at 3 per account with 24 h runtime ([limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations), checked 2026-10-30).

If the [DBX-C02](tasks.md#dbx-c02) probe shows that serverless can't reach the Kafka broker, then *no* Kafka provider will work. Confluent, Aiven, Redpanda and MSK are all just another non-trusted host. A Databricks App wouldn't help either, since it sits behind the same egress policy (unverified).

So the direction flips: **something outside Databricks pulls from Kafka and pushes inbound to the workspace.** Inbound REST to the workspace is how the CLI and SDK already work, so it is not affected by the egress allowlist.

Everything from silver onwards stays unchanged: `trades_silver → trades_dedup → trades_1m → trades_latest`, the dashboard, and the fixture assertion (`4 / 0.45 / 70000 / 70010 / 69990`). Only the bronze source and one new process change.

## Decision <a id="a-decision"></a>
**Shipper (Kafka → JSONL files) → UC Volume `landing` (Files API upload) → Auto Loader in `pipelines/bronze.py`.**

| Option | Verdict |
|---|---|
| **UC Volume + Auto Loader** | **chosen.** Inbound REST only. Auto Loader tracks files with a checkpoint, so it is incremental and restart-safe. Volumes are UC-native, so this works on Free Edition (verify in [DBX-A01](tasks.md#dbx-a01)). The existing dedup absorbs any re-shipped events. |
| SQL warehouse `INSERT` via `databricks-sql-connector` into a bronze Delta table | backlog [DBX-AB1](tasks.md#dbx-ab1). Works inbound, but keeps the single 2X-Small warehouse awake (fair-usage quota) and every small INSERT is a commit. |
| Zerobus Ingest (direct gRPC push into Delta) | backlog [DBX-AB2](tasks.md#dbx-ab2). GA since 2026-02, but not confirmed on Free Edition: a community thread reports service-principal OAuth failing there because Free Edition has no account console ([thread](https://community.databricks.com/t5/administration-architecture/zerobus-ingestion-fails-in-databricks-free-edition-using-service/td-p/161228)). |
| Kafka REST proxy over 443 | only helps if the proxy host happens to be trusted. Probe it in DBX-A01; don't build on it. |
| Producer → Volume directly (`--sink volume`, no Kafka) | not as the default, because Kafka stays the single fan-out bus shared with the ClickHouse lane. It is a free by-product, since the shipper reuses the same `VolumePublisher`. |

## Steps
1. **Sharpen the gate** → [DBX-A01](tasks.md#dbx-a01). Extend `scripts/dbx_kafka_probe.py` so one run tells which path we're on:
   - (a) TCP to the bootstrap host and port
   - (b) HTTPS 443 to the Kafka REST endpoint, if the provider has one
   - (c) a control host that should be trusted (`probe.control_url` in config, e.g. pypi.org)
   - (d) `dbutils.fs.ls` on the landing Volume

   Hosts and timeouts come from `config.yaml: probe.*`. Outcome: (a) OK → main plan. (a) fails and (d) OK → this plan. (d) fails → stop and ask.
2. **Volume sink** → [DBX-A02](tasks.md#dbx-a02).
   - Add `VolumePublisher` to `src/cmp/publish.py`. It buffers events and writes `{topic}-{partition}-{first_offset}-{last_offset}.jsonl`, using `WorkspaceClient().files.upload(path, overwrite=True)`.
   - Batch size and max wait come from `config.yaml: volume.*`.
   - The Volume path is built from `catalog`/`schema` plus `volume.name`. The SDK profile comes from `DATABRICKS_CONFIG_PROFILE` in `.env.secrets`, read strictly.
3. **Shipper** → [DBX-A03](tasks.md#dbx-a03).
   - `scripts/ship_to_volume.py`: Kafka consumer (group `volume.consumer_group`), then `VolumePublisher.flush()`, then a sync offset commit. A crash between upload and commit re-ships the same offsets, and dedup absorbs them.
   - Exit after `volume.idle_exit_s` with no messages. A poison message stops it.
   - `just ship` runs it, plus `--source fixture` for a Kafka-less fixture upload.
4. **Bundle + bronze switch** → [DBX-A04](tasks.md#dbx-a04).
   - `databricks.yml`: add a `volumes:` resource `landing` in `${var.catalog}.${var.schema}`, and a pipeline configuration `cmp.bronze_source: kafka|volume`. Use a bundle var with **no default**, set per target.
   - `pipelines/bronze.py`: for `volume`, read `spark.readStream.format("cloudFiles").option("cloudFiles.format", "json").schema(TRADE_SCHEMA).load(landing_path)`, then the same `parse_trades` projection.
   - `scripts/build.py` regenerates the pipeline SQL, and the sync test keeps passing.
5. **Local parity** → [DBX-A05](tasks.md#dbx-a05).
   - `VolumePublisher` takes a target with an `upload(path, bytes)` method. The SDK client is used in cloud; a local directory writer targets `.tmp/landing`.
   - `scripts/local_spark.py --bronze-source volume` reads that directory with `readStream.json` and a checkpoint.
   - Integration test: fixture → Redpanda → shipper → `.tmp/landing` → Spark gives the same bar. Re-shipping the same offsets leaves the bar unchanged.
6. **Cloud verify** → [DBX-A06](tasks.md#dbx-a06).
   - `just dbx-deploy` with `bronze_source=volume`, `just ship --source fixture`, then `just dbx-run`.
   - `just dbx-query` on `trades_1m` should give the same BTCUSDT 10:00 bar as local. Ship again and run again: the bar is unchanged.
7. **Hosting the shipper** → [DBX-A07](tasks.md#dbx-a07). Use the laptop, or a `workflow_dispatch` GH Actions job with a bounded `timeout-minutes` and secrets in a protected `cloud` environment. Then trigger the pipeline (`bundle run`).
   - Latency is minutes per triggered run, which is enough for a demo dashboard. An always-on shipper is already covered by [DBX-B6](tasks.md#dbx-b6).

## Risks / unverified
- Volume create, Files API upload and Auto Loader on Free Edition serverless are assumed to work (all UC-native); DBX-A01 checks them.
- The Files API per-request size limit is unverified; keep `volume.max_batch_bytes` small, a few MB.
- Auto Loader on Free Edition keeps the default directory listing (no file-notification mode, which needs cloud queues).
- Many tiny files: Auto Loader handles them, but batch them every ≥ 30 s (from config) to keep the file count low.

## Verification
- `just test`: `VolumePublisher` naming and idempotency, plus the bronze-source switch rendering.
- `just it`: fixture via the shipper and landing dir gives the same bar, and re-shipping leaves it unchanged.
- Cloud: DBX-A06 with the same assertion as [DBX-C04](tasks.md#dbx-c04).
- `find_hardcoded_scalars.py` on the new `src/` and `scripts/` files.
