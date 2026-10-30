# Auth: no service-account keys

Decision record: [ADR-0003](../../../docs/adr/0003-keyless-auth-wif-impersonation.md).

- **Never** create, download or commit an SA key (`*.json` credentials). Check: `git ls-files | grep -iE 'key.*\.json|credentials.*\.json'` is empty, and `gcloud iam service-accounts keys list --iam-account=<sa> --managed-by=user` is empty for every SA.
- **Terraform:** runs as the owner's own ADC (`gcloud auth application-default login`), the bootstrap identity of a personal trial project, with `user_project_override = true` and `billing_project` = project (needed by the Budgets API).
- **Runtime tools on the laptop** (produce, assert, bq): `gcloud config set auth/impersonate_service_account <smoke-sa>` for the session, or `--impersonate-service-account`. This proves that the CI permission set is enough before CI runs.
- **CI:**
  - `google-github-actions/auth@v3` with `workload_identity_provider` + `service_account`, i.e. WIF through an SA
  - `permissions: id-token: write, contents: read` only on the cloud workflow
- **WIF provider:**
  - issuer `https://token.actions.githubusercontent.com`
  - a mandatory `attribute_condition` of `assertion.repository == '<deploy.wif.repository>'`
  - the IAM binding on `principalSet://…/attribute.repository/<repo>`
  - Google [requires](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines) an attribute condition for GitHub (verified 2026-10-30)
- **SAs** (least privilege, defined in [terraform-foundation](../../specs/2026-10-30-1200-terraform-foundation/plan.md)):
  - `producer-sa`: `pubsub.publisher` on the live topic
  - `smoke-sa`: `pubsub.publisher` on the smoke topic, `bigquery.dataViewer` on the smoke dataset, `bigquery.jobUser` on the project
  - `dataflow-sa`: only when `deploy.dataflow.enabled`
  - the Pub/Sub service agent: `bigquery.dataEditor` on each dataset, plus the DLQ publisher/subscriber grants
- **GitHub repo owner:** `dataengy`. Use `GH_TOKEN=$(gh auth token --user dataengy) gh variable set …`.
