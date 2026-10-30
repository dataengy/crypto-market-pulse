# Ponytail: least code, smallest complete change

- Reuse before writing:
  - `produce.py`, `sql_apply.py`, `assert_fixture.py`, `beam_run.py`, `settings.py` from the local lane, called with `--profile cloud`
  - the reference [main.tf](../../../../../crypto-market-pulse-chatgpt/project/infra/gcp/main.tf) as a base, fixed rather than redesigned
- Prefer platform features to code:
  - BigQuery subscription over a consumer
  - `paused = true` on Scheduler over custom toggles
  - Terraform `for_each` over copy-paste per env
  - `yamldecode` over a tfvars generator
- One file per concern. Terraform is `versions.tf`, `main.tf`, `variables.tf` and `outputs.tf`; no modules.
- No options nobody asked for. Alternatives go to the backlog (GCP-C12…C17), not behind flags. The one exception is `deploy.dataflow.enabled`, because Dataflow resources cost money and must be off by default.
- A known shortcut gets a `ponytail:` comment naming the limit and the upgrade trigger (e.g. local state → GCS backend, GCP-C15).
- Never cut validation at trust boundaries, IAM least privilege, the DLQ, or teardown.
