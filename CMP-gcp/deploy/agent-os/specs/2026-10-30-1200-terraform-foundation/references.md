# References — Terraform foundation

## Similar Implementations
- **Location:** [crypto-market-pulse-chatgpt/project/infra/gcp/main.tf](../../../../../crypto-market-pulse-chatgpt/project/infra/gcp/main.tf) (never executed)
  - **Relevance:** the base file to fix.
  - **Key patterns:** a BigQuery subscription with an unschematized `data BYTES` table; the Pub/Sub agent identity is `service-<number>@gcp-sa-pubsub.iam.gserviceaccount.com`.
  - **Defects:**
    - comma-separated one-line blocks (invalid HCL)
    - a `default` on `region`
    - hardcoded `market-trades-v1`, `crypto_pulse`, `trades_raw` and `EU`
    - `write_metadata = false`
    - no partitioning, DLQ, SAs or budget
    - `deletion_protection = true` blocks teardown
- **Location:** [docs/plans/gcp/02-cloud-deploy-test.md §c2](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#c2)
  - **Relevance:** the defect list and the resource list this spec implements.
- **Location:** [CMP-dbx-fe/config/config.yaml](../../../../../CMP-dbx-fe/config/config.yaml), [CMP-dbx-fe/justfile](../../../../../CMP-dbx-fe/justfile)
  - **Key patterns:**
    - grouped config sections with a one-line comment each
    - `set dotenv-load`
    - a recipe that checks env keys and fails naming the file to fill (`dbx-secrets`)
- **Docs:**
  - [google_pubsub_subscription](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/pubsub_subscription): `bigquery_config.write_metadata`, `dead_letter_policy`
  - [create BigQuery subscription](https://docs.cloud.google.com/pubsub/docs/create-bigquery-subscription): metadata column types
  - [WIF with deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
