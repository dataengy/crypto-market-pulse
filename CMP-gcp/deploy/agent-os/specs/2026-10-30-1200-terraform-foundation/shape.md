# Terraform foundation — Shaping Notes

## Scope
- **GCP-C01:** project, billing, budget, and a re-check of the unverified prices
- **GCP-C02:** rewrite the reference `main.tf` until `fmt`/`validate`/`plan` are clean (**no apply**)
- **GCP-C11:** write the teardown recipe

Apply happens in [pubsub-bq-subscription](../2026-10-30-1210-pubsub-bq-subscription/plan.md).

Out of scope:
- the Cloud Run job and Scheduler (added in [hosted-producer](../2026-10-30-1230-hosted-producer/plan.md))
- Dataflow resources (added in [dataflow-parity](../2026-10-30-1250-dataflow-parity-timeboxed/plan.md))
- remote state (GCP-C15)

## Decisions
**How Terraform gets its config**
- Options considered: (a) a tfvars generator script; (b) `yamldecode(file(config.yaml))`; (c) duplicated `*.tfvars`.
- **Choice: (b).** It needs no code, a missing key fails at plan time, and there is a single source of truth.
- Secrets (project ID, billing account) still come in as `TF_VAR_*` from `.env.secrets`.

**Who runs Terraform**
- Options: (a) an impersonated `deployer-sa`, as [02 §c4](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#c4) planned; (b) the owner's ADC.
- **Choice: (b).** The owner is the bootstrap identity of a personal trial project anyway. It needs billing-account rights for the budget, and CI never applies (it only runs the smoke).
- This removes `deployer-sa`. Runtime least privilege is proven with `smoke-sa` impersonation ([ADR-0003](../../../docs/adr/0003-keyless-auth-wif-impersonation.md)).

**Envs**
- `for_each` over `deploy.envs` = `[live, smoke]`.
- Isolation is required because the FX minute (2026-10-30 10:00 UTC) is a real date.

**Raw table**
- `write_metadata = true`. Columns: `subscription_name STRING`, `message_id STRING`, `publish_time TIMESTAMP`, `data BYTES`, `attributes JSON`. The [API reference](https://docs.cloud.google.com/pubsub/docs/reference/rest/v1/projects.subscriptions) (verified 2026-10-30) gives the column set; that `attributes` may be typed JSON rather than STRING is **unverified**, so check it in Task 4.
- Partitioned DAY on `publish_time`, with expiration from config.
- Must equal the local lane's `001_raw.sql`.

**DLQ**
- One DLQ topic per env, **plus a pull subscription on it**, because messages sent to a topic with no subscription are lost.
- The Pub/Sub service agent gets `publisher` on the DLQ topic and `subscriber` on the source subscription.

**Location**
- `profiles.cloud.location` (planned `europe-west1`) for Pub/Sub, a **regional** dataset, and AR.
- The reference used a multi-region `EU` dataset; same-region avoids transfer charges ([pubsub/pricing](https://cloud.google.com/pubsub/pricing), verified 2026-10-30).

**Budget**
- `google_billing_budget` with `user_project_override`.
- Alerts only: a budget never stops spend.

## Context
- **Visuals:** none. The diagram is in [architecture.md](../../../docs/design/architecture.md).
- **References:** [references.md](references.md).
- **Product alignment:** roadmap phase 1. Unlocks phases 2–6.

## Standards Applied
See [standards.md](standards.md).
