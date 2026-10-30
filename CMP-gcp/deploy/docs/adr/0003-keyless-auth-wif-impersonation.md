---
status: accepted
date: 2026-10-30
decision-makers: owner
---
# 0003 — Keyless auth: owner ADC for Terraform, `smoke-sa` impersonation on the laptop, WIF through `smoke-sa` in CI

## Context and Problem Statement
Three actors need GCP access: the owner applying Terraform, local smoke runs, and GitHub Actions on `dataengy/crypto-market-pulse`. The user rule forbids SA key files. Which identities, and how?

## Decision Drivers
- No long-lived credentials anywhere
- Least privilege, tested before CI depends on it
- The fewest moving parts

## Considered Options
1. Terraform as an impersonated `deployer-sa` (the plan in [02 §c4](../../../../docs/plans/gcp/02-cloud-deploy-test.md#c4)); CI applies too
2. **Terraform as owner ADC; runtime as `smoke-sa`/`producer-sa`; CI only runs the smoke, through WIF → `smoke-sa`**
3. Direct WIF: grant roles to the `principalSet` itself, no SA

## Decision Outcome
Chosen: **option 2**.
- **Terraform:**
  - runs as the owner's ADC, with `user_project_override = true` and `billing_project` set for the Budgets API
  - the owner is the trial project's bootstrap identity and already holds the billing rights the budget needs
- **Laptop runtime:** `auth/impersonate_service_account = smoke-sa`. The owner gets `serviceAccountTokenCreator` on that SA through Terraform.
- **CI:**
  - `google-github-actions/auth@v3` with `workload_identity_provider` + `service_account = smoke-sa`
  - the provider's `attribute_condition` is `assertion.repository == 'dataengy/crypto-market-pulse'`, which is mandatory for GitHub ([docs](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines), verified 2026-10-30)
  - the binding is on `principalSet://…/attribute.repository/<repo>`
- **Hosted job:** runs as the attached `producer-sa`, with no keys in the image.

### Consequences
- Good: zero key files. The CI permission set is exercised locally first. No `deployer-sa` to secure.
- Bad: CI can't apply Terraform. That's intended for a one-owner trial; revisit with GCS state ([GCP-C15](../../../../docs/plans/gcp/tasks.md#gcp-c15)).
- Bad: any branch can run the smoke (no `assertion.ref` check). Accepted, because `smoke-sa` only reaches the `smoke` env.

### Confirmation
- `gcloud iam service-accounts keys list --managed-by=user` is empty for all SAs.
- Cross-env access is denied ([pubsub-bq Task 4](../../agent-os/specs/2026-10-30-1210-pubsub-bq-subscription/plan.md)).
- The CI run is green ([ci spec Task 4](../../agent-os/specs/2026-10-30-1240-ci-wif-cloud-smoke/plan.md)).

## Pros and Cons of the Options
- **deployer-sa + CI apply:** automation-ready, but needs billing-account IAM for an SA and remote state. More surface for no current need.
- **Direct WIF:** one less SA, but the laptop path would differ from CI, and some APIs limit federated principals ([WIF overview](https://cloud.google.com/iam/docs/workload-identity-federation)).
