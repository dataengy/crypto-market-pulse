# Dataflow parity (optional, time-boxed) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One capped Dataflow **batch** run of the local lane's Beam pipeline over the fixture writes `trades_1m_beam` in `smoke`, equal to `trades_1m` for FX. The cost is recorded and every Dataflow resource is gone afterwards. The streaming drain/relaunch check is an optional stretch.

**Architecture:**
- `deploy.dataflow.enabled` gates a temp bucket and `dataflow-sa` in Terraform.
- `beam_run.py --runner DataflowRunner --source gcs-jsonl` runs with walltime and worker caps.
- `df-stop` always runs.

**Tech Stack:** Apache Beam Python (version pinned by the local lane), Dataflow, Terraform, gcloud, bq.

**Spec:** [shape.md](shape.md) · task: [GCP-C10](../../../../../docs/plans/gcp/tasks.md#gcp-c10) (depends on C05, L08, L10, and the user's approval of the spend)

## Global Constraints
- **Two user OKs:** one before `enabled: true` + apply, one before each launch. A separate OK covers the streaming stretch.
- The batch run carries `--dataflow_service_options=max_workflow_runtime_walltime_seconds=<deploy.dataflow.max_walltime_s>`.
- `--num_workers=1 --max_num_workers=1 --machine_type=<cfg> --service_account_email=<dataflow-sa> --labels=<deploy.labels>`.
- Only the `smoke` dataset. Afterwards `deploy.dataflow.enabled: false` + apply, which removes the bucket and the SA.

## Review Focus
1. **The batch job exceeds walltime:** Dataflow cancels it, and the evidence records `JOB_STATE_CANCELLED` and the cost. The run must not be relaunched without asking.
2. **Window output on bounded input:** the watermark goes to +∞ at end of input, so all windows fire. No heartbeat is needed in batch. Check that FX is present.
3. **Sink duplicates on retry:** compare via the latest-pane view (`trades_1m_beam`), never the pane table (`trades_1m_beam_panes`).
4. **`df-stop` with no active job:** must exit 0 (idempotent), so the trap never masks the real error.
5. **Streaming stretch left running:** the watchdog + `df-stop` trap, then `gcloud dataflow jobs list --status=active --region <r>` must be empty, as part of the teardown evidence.

---

### Task 1: Save spec documentation
- [x] Done (2026-10-30).

### Task 2: Conditional resources (user-gated apply)

**Files:**
- Modify: `CMP-gcp/deploy/terraform/main.tf` (`count = local.cfg.deploy.dataflow.enabled ? 1 : 0` for the bucket, `dataflow-sa` and their IAM)
- Modify: `CMP-gcp/config/config.yaml` (`deploy.dataflow.{enabled,region,machine_type,max_walltime_s,stop_timeout_s,temp_lifecycle_days}`)

- [ ] **Step 1:** Add the resources: bucket with a lifecycle `age = temp_lifecycle_days` → Delete, `uniform_bucket_level_access`, `force_destroy = true`; `dataflow-sa` with `dataflow.worker`, `storage.objectAdmin` on the bucket, and `bigquery.dataEditor` on smoke.
- [ ] **Verify:** with `enabled: false`, the plan shows 0 Dataflow resources. With `enabled: true`, it shows exactly bucket + SA + IAM. Apply only after the user's OK.

### Task 3: Batch parity run (GCP-C10)

**Interfaces:**
- Consumes: `beam_run.py --profile cloud --env smoke --runner DataflowRunner --source gcs-jsonl --input <gs://…/trades.jsonl>` (local lane L07, plus the bounded-source branch from [shape.md](shape.md)).
- Produces: `<smoke>.trades_1m_beam` rows.

- [ ] **Step 1:** Recipe `df-batch`:
  - `gcloud storage cp ../tests/fixtures/trades.jsonl gs://<bucket>/fixtures/`
  - `trap 'just deploy::df-stop' EXIT`
  - launch with the Global Constraints flags plus the walltime option
  - wait for `JOB_STATE_DONE`
- [ ] **Step 2:** Recipe `df-stop`: list the active jobs carrying our label, drain each, then wait up to `stop_timeout_s` and cancel. With no jobs it exits 0.
- [ ] **Verify:**
  - `bq query` comparing FX on `trades_1m_beam` vs `trades_1m` for BTCUSDT 10:00 → identical (`4, 0.45, 70000, 70010, 69990`)
  - `gcloud dataflow jobs list --status=active --region <r>` is empty
  - the job's cost from the Billing report is written to the C10 log (it may show up with up to 24 h delay; note the time checked)

### Task 4 (stretch, separate OK): streaming drain/relaunch
- [ ] **Step 1:** Launch `--streaming --enable_streaming_engine` from the `smoke` subscription, with `timeout <max_walltime_s> just deploy::df-wait; just deploy::df-stop`. Replay the fixture, drain, relaunch, replay again.
- [ ] **Verify:** `trades_1m_beam` FX unchanged after relaunch (no double count). The active list is empty at the end.

### Task 5: Disable
- [ ] Set `deploy.dataflow.enabled: false`, then plan, OK, apply.
- [ ] **Verify:** `gcloud storage buckets list --filter=<bucket>` is empty and `gcloud iam service-accounts list` has no `dataflow-sa`.
