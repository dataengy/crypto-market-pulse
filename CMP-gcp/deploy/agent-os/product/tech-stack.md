# Tech stack — CMP-gcp cloud deploy

| Layer | Choice | Notes |
|---|---|---|
| Language/runtime | Python 3.12 via uv; `just` | the same as `CMP-dbx-fe/` and the local lane |
| IaC | Terraform with the `hashicorp/google` provider **`~> 8.9`** | latest is 8.9.0 (2026-10-27) per the [registry](https://registry.terraform.io/providers/hashicorp/google/latest/docs/guides/provider_versions.html) (verified 2026-10-30). Local state, gitignored. |
| Config | `CMP-gcp/config/config.yaml` (tracked) + `config/.env.common` + `config/.env.secrets` | Terraform reads the YAML with `yamldecode`; secrets come in as `TF_VAR_*` from `.env.secrets` |
| Messaging | Pub/Sub: topic + BigQuery subscription + dead-letter topic, per env (`live`, `smoke`) | [ADR-0001](../../docs/adr/0001-bq-subscription-over-dataflow.md) |
| Warehouse | BigQuery, a **regional** dataset per env; raw table partitioned on `publish_time`; views from the local lane's SQL templates | |
| Producer | Cloud Run **job** (bounded `--max-seconds`) + Cloud Scheduler (paused by default); image in Artifact Registry, built by Cloud Build | [ADR-0002](../../docs/adr/0002-cloud-run-job-region.md) |
| Optional | Dataflow (Beam Python), a batch-mode parity run with a hard walltime | [dataflow spec](../specs/2026-10-30-1250-dataflow-parity-timeboxed/shape.md) |
| Auth | ADC + SA impersonation on the laptop; WIF from GitHub OIDC in CI; **no SA keys** | [ADR-0003](../../docs/adr/0003-keyless-auth-wif-impersonation.md) |
| BI | Looker Studio with the BigQuery connector | manual setup; URL stored in config |
| Spend | `google_billing_budget` alerts + `just gcp-down` | [cost standard](../standards/gcp/cost-guardrails.md) |
