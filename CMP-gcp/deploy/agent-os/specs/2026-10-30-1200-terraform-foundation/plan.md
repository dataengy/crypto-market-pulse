# Terraform foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A clean, reviewed `terraform plan` for the core GCP project (APIs, per-env Pub/Sub + BigQuery + DLQ, SAs, WIF, AR, budget), plus a written teardown recipe. Nothing is applied.

**Architecture:**
- Four `.tf` files under `CMP-gcp/deploy/terraform/` read `CMP-gcp/config/config.yaml` through `yamldecode`.
- Secrets come in as `TF_VAR_*` from `config/.env.secrets`.
- `just` recipes in `CMP-gcp/deploy/justfile` wrap init/plan/apply/down.

**Tech Stack:** Terraform (pinned) + `hashicorp/google ~> 8.9`, just, gcloud.

**Spec:** [shape.md](shape.md) · tasks: GCP-C01, GCP-C02, GCP-C11 in [tasks.md](../../../../../docs/plans/gcp/tasks.md#gcp-c01)

## Global Constraints
- No `default` in any `variable`. No literal names, regions or numbers in `.tf` or the justfile except config key names and API service names.
- Provider `hashicorp/google` `~> 8.9`; commit `.terraform.lock.hcl`.
- No apply, no `-auto-approve` in this plan. The user reviews `plan` output.
- Labels from `deploy.labels` on every labelable resource.
- No SA keys; Terraform runs as the owner's ADC with `user_project_override = true`.

## Review Focus
1. **Missing config key:** `terraform plan` must fail naming the key (yamldecode attribute error). Owned by Task 3.
2. **Missing `TF_VAR_project_id` / `TF_VAR_billing_account`:** the recipe exits before calling terraform, naming `config/.env.secrets`. Owned by Task 4.
3. **DLQ topic with no subscription:** dead-lettered messages would vanish. Task 3 adds a DLQ pull subscription per env.
4. **Raw schema drift** between Terraform and `sql/bigquery/001_raw.sql`: subscription state `SCHEMA_MISMATCH` at apply time. Task 3 copies the column list from 001_raw.sql, and the verify step diffs them.
5. **`deletion_protection` left true:** `gcp-down` fails half-way. The value comes from config (`false` for trial), and the Task 4 verify step runs `plan -destroy`.

---

### Task 1: Save spec documentation
- [x] This folder: `plan.md`, `shape.md`, `standards.md`, `references.md` (2026-10-30).

### Task 2: Project, billing, price re-check (GCP-C01, user-gated)

**Files:**
- Modify: `CMP-gcp/config/.env.secrets.demo` (add the keys `GOOGLE_CLOUD_PROJECT`, `BILLING_ACCOUNT_ID`, `OWNER_MEMBER`; coordinate with the local lane)
- Modify: [cost-guardrails.md](../../standards/gcp/cost-guardrails.md#facts) (flip the unverified rows)

- [ ] **Step 1:** The user creates a trial project and links billing in the Console. The agent creates nothing.
- [ ] **Step 2:** The user fills `CMP-gcp/config/.env.secrets` (gitignored).
- [ ] **Step 3:** Re-check every **unverified** row in cost-guardrails (1 KB minimum, Scheduler free jobs, Dataflow rates) on the pricing pages or calculator. Record the URL and date.
- [ ] **Verify:** `gcloud billing projects describe "$GOOGLE_CLOUD_PROJECT" --format='value(billingEnabled)'` prints `True`. The evidence log is `…-GCP-C01.log`.

### Task 3: `deploy:` config + Terraform rewrite (GCP-C02)

**Files:**
- Modify: `CMP-gcp/config/config.yaml`. Add a `deploy:` section with these keys; the values are picked at implementation time:
  - `labels`, `envs`
  - `names.{topic,subscription,dlq_topic,dlq_subscription,dataset,raw_table,ar_repo}`, each with an `{env}` placeholder
  - `names.sa.{producer,smoke}`
  - `apis`
  - `pubsub.{message_retention_s,ack_deadline_s,max_delivery_attempts}`
  - `bigquery.{partition_expiration_days,deletion_protection,delete_contents_on_destroy}`
  - `budget.{amount_units,currency,thresholds}`
  - `wif.{pool_id,provider_id,repository}` (`repository: dataengy/crypto-market-pulse`)
  - `artifact.keep_count`
- Create: `CMP-gcp/deploy/terraform/{versions.tf,variables.tf,main.tf,outputs.tf}`
- Create: `CMP-gcp/deploy/.gitignore` (`.terraform/`, `*.tfstate*`, `.tmp/`)

**Interfaces:**
- Consumes: `profiles.cloud.location` from the local lane's config, and `sql/bigquery/001_raw.sql` for the column list.
- Produces these outputs, used by specs 2–5:
  - `topic_ids` (map env→id)
  - `subscription_ids` (map)
  - `dlq_subscription_ids` (map)
  - `dataset_ids` (map)
  - `producer_sa_email`, `smoke_sa_email`
  - `wif_provider_name`
  - `ar_repo_url`

- [ ] **Step 1:** `versions.tf`: `required_version`, the provider pin, `provider "google" { project = var.project_id, region = local.cfg.profiles.cloud.location, user_project_override = true, billing_project = var.project_id, default_labels = local.cfg.deploy.labels }`. Write it one argument per line.
- [ ] **Step 2:** `variables.tf`: `config_path`, `project_id`, `billing_account`, `owner_member` (type `string`, no default; `owner_member` = `user:<email>` from `.env.secrets` key `OWNER_MEMBER`).
- [ ] **Step 3:** `main.tf`:
  - `google_project_service` with `for_each = toset(local.cfg.deploy.apis)` and `disable_on_destroy = false`
  - per env (`for_each = toset(local.cfg.deploy.envs)`): topic, DLQ topic, DLQ pull subscription, regional dataset, raw table (DAY partition on `publish_time`), BigQuery subscription (`write_metadata = true`, `use_table_schema = false`, `dead_letter_policy`, retention)
  - IAM:
    - Pub/Sub agent → `bigquery.dataEditor` per dataset, `pubsub.publisher` per DLQ topic, `pubsub.subscriber` per source subscription
    - `producer-sa` → publisher on the `live` topic
    - `smoke-sa` → publisher on the `smoke` topic + subscriber on the smoke DLQ subscription + `bigquery.dataViewer` on the smoke dataset + project `bigquery.jobUser`
    - `var.owner_member` → `iam.serviceAccountTokenCreator` on `smoke-sa` and `producer-sa`, so the laptop can impersonate them
  - WIF: `google_iam_workload_identity_pool` + an OIDC provider (`issuer_uri` from config, `attribute_mapping` with `google.subject` and `attribute.repository`, `attribute_condition = "assertion.repository == '${local.cfg.deploy.wif.repository}'"`), plus `roles/iam.workloadIdentityUser` on `smoke-sa` for `principalSet://…/attribute.repository/<repo>`
  - `google_artifact_registry_repository` (docker, cleanup policy keep `artifact.keep_count`)
  - `google_billing_budget` (amount and thresholds from config, filter on the project)
- [ ] **Step 4:** `outputs.tf` with the Produces list above.
- [ ] **Verify:**
  - `just deploy::tf-plan` → `fmt -check` is clean, `validate` prints `Success!`, and the plan shows only `create` actions.
  - Diff against 001_raw.sql: `grep -oE '^\s+\w+ (STRING|BYTES|TIMESTAMP|JSON)' ../sql/bigquery/001_raw.sql` matches the table schema in the plan.
  - Missing-key check: temporarily rename `deploy.budget` in a scratch copy, run plan with `TF_VAR_config_path` pointing at it, and expect `Unsupported attribute` naming `budget`.

### Task 4: just recipes + gcp-down (GCP-C11 recipe)

**Files:**
- Create: `CMP-gcp/deploy/justfile`
- Modify: `CMP-gcp/justfile` (one line: `mod deploy`; coordinate)

**Interfaces:**
- Produces these recipes:
  - `deploy::tf-init`
  - `deploy::tf-plan` (writes `.tmp/tf.plan`)
  - `deploy::tf-apply` (applies only `.tmp/tf.plan`)
  - `deploy::gcp-ls` (the list commands in [teardown.md](../../../docs/runbooks/teardown.md))
  - `deploy::gcp-down`

- [ ] **Step 1:** Header: `set dotenv-load`, `set dotenv-path := "../config/.env.secrets"`. A `_env` recipe checks that `GOOGLE_CLOUD_PROJECT`, `BILLING_ACCOUNT_ID` and `OWNER_MEMBER` are set, otherwise it prints `missing <KEY> in CMP-gcp/config/.env.secrets (template: .env.secrets.demo)` and runs `exit 1`. It exports `TF_VAR_project_id`, `TF_VAR_billing_account`, `TF_VAR_owner_member`, `TF_VAR_config_path`.
- [ ] **Step 2:** `gcp-down` follows the order in [teardown.md](../../../docs/runbooks/teardown.md):
  1. pause the scheduler if it exists
  2. stop Dataflow if it exists
  3. `terraform plan -destroy -out .tmp/destroy.plan`
  4. user OK
  5. `terraform apply .tmp/destroy.plan`
  6. `gcp-ls`
- [ ] **Verify:**
  - `just deploy::tf-plan` with `GOOGLE_CLOUD_PROJECT` unset exits 1 with the message from Step 1.
  - `find_hardcoded_scalars.py CMP-gcp/deploy/justfile --exit-nonzero-on-find` exits 0.
  - `just deploy::gcp-down` before any apply shows "No changes" in the destroy plan.

### Task 5: Plan review gate
- [ ] Hand the user `.tmp/evidence/…-GCP-C02.log` (the plan text). **Stop.** Apply belongs to the next spec.
