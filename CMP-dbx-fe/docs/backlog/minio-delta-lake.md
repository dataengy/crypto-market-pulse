# DBX-B1 — MinIO + Delta as the local lake

**Goal:** local tables live on S3-compatible storage (`s3a://cmp-lake/...`) like cloud object storage, not `.tmp/lake`. ← [tasks](../../../docs/plans/dbx-fe/tasks.md#dbx-b1)

**Steps**
- [ ] Add `minio` (localhost-only bind, owned volume) + a one-shot `mc mb` bucket job to `compose.yml`
- [ ] `config.yaml`: `spark.lake_dir` accepts an `s3a://` URI; endpoint/path-style settings under `spark.s3`; keys in `.env.secrets`
- [ ] `spark_session`: add `hadoop-aws` (matching Hadoop version) + `fs.s3a.*` from config
- [ ] Make `local_spark.table()` / `--reset` work for URIs (reset = `mc rm --recursive`, never the bucket)

**Acceptance:** `just it` passes with `lake_dir: s3a://…`; restarting MinIO keeps the tables.
