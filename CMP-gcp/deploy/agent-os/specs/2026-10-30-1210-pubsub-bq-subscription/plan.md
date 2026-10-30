# Pub/Sub → BigQuery subscription + views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The live and smoke ingest paths exist in GCP with ACTIVE BigQuery subscriptions and views, and the laptop reaches them by impersonating `smoke-sa`.

**Architecture:**
- Apply the reviewed plan from [terraform-foundation](../2026-10-30-1200-terraform-foundation/plan.md).
- Then render the local lane's SQL templates against each cloud dataset.

**Tech Stack:** Terraform, gcloud, bq, the local lane's `scripts/sql_apply.py`.

**Spec:** [shape.md](shape.md) · tasks: [GCP-C03](../../../../../docs/plans/gcp/tasks.md#gcp-c03), [GCP-C04](../../../../../docs/plans/gcp/tasks.md#gcp-c04) (laptop part)

## Global Constraints
- Apply only `.tmp/tf.plan`, the one the user reviewed. Re-plan if the config changed.
- Views come only from `sql_apply.py --profile cloud`. No hand-run DDL.
- No SA key file is created at any point.

## Review Focus
1. **Subscription not ACTIVE right after apply** (IAM propagation can take minutes): Task 2 polls `state` with a timeout from config. It does not re-apply.
2. **The views query an empty raw table:** they must return 0 rows, not error. Task 3 runs `SELECT COUNT(*)` on each view.
3. **Impersonation without `roles/iam.serviceAccountTokenCreator`** for the owner on `smoke-sa`: Task 4 fails clearly. Grant it in Terraform (foundation Task 3), not by hand.
4. **Applying with a stale plan after a config edit:** `terraform apply` rejects a stale plan. Re-run `tf-plan`.
5. **The `live` subscription receiving smoke fixtures** by mistake: the smoke tools take `--env smoke` from config; Task 3 asserts that the live raw count is 0.

---

### Task 1: Save spec documentation
- [x] Done (2026-10-30).

### Task 2: Apply core ingest (GCP-C03, user-gated)
- [ ] **Step 1:** `just deploy::tf-plan`. The user reviews it and says "apply".
- [ ] **Step 2:** `just deploy::tf-apply`.
- [ ] **Verify**, for each env:
  - `gcloud pubsub subscriptions describe <subscription> --format='value(bigqueryConfig.state)'` prints `ACTIVE`
  - `bq ls --project_id "$GOOGLE_CLOUD_PROJECT"` lists both datasets
  - `gcloud pubsub subscriptions list --filter='name~dlq'` shows the DLQ pull subscriptions

### Task 3: Views per env (GCP-C03)

**Interfaces:**
- Consumes: `sql_apply.py --profile cloud --env {live|smoke}` (local lane, [L05](../../../../../docs/plans/gcp/tasks.md#gcp-l05)) and `dataset_ids` from Terraform outputs.
- Produces: the views `trades_dedup`, `trades_1m`, `trades_latest` and the DQ view in each dataset. Specs 3, 4 and 6 use them.

- [ ] **Step 1:** Add the recipe `deploy::sql-apply env` → `uv run --project .. python ../scripts/sql_apply.py --profile cloud --env {{env}}`.
- [ ] **Step 2:** Run it for `smoke`, then for `live`.
- [ ] **Verify:**
  - `bq query --nouse_legacy_sql 'SELECT COUNT(*) FROM <dataset>.trades_1m'` returns `0` for both envs, with no error.
  - `bq show --schema <dataset>.<raw_table>` equals the 001_raw.sql columns.

### Task 4: Laptop impersonation (GCP-C04, laptop part)
- [ ] **Step 1:** `gcloud auth application-default login` (user). Then `gcloud config set auth/impersonate_service_account "$(terraform -chdir=terraform output -raw smoke_sa_email)"` for the session.
- [ ] **Verify:**
  - `bq ls <smoke_dataset>` succeeds as `smoke-sa`.
  - `bq query 'SELECT 1 FROM <live_dataset>.trades_1m LIMIT 1'` fails with `Access Denied`, which proves least privilege.
  - `gcloud iam service-accounts keys list --iam-account=<smoke_sa> --managed-by=user` is empty.
  - Unset the impersonation afterwards.
