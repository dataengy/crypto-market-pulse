# Runbook — teardown & cost review (GCP-C11)

Run after **every** cloud session. `just deploy::gcp-down` does steps 1–5; step 6 is manual.

| # | Step | Command | Must show |
|---|---|---|---|
| 1 | Pause the schedule | `gcloud scheduler jobs pause <name> --location <r>`, skipped if absent | `state: PAUSED` or not found |
| 2 | Stop Dataflow | `just deploy::df-stop` (drain, then cancel after `stop_timeout_s`) | `gcloud dataflow jobs list --status=active --region <r>` empty |
| 3 | Destroy plan | `terraform plan -destroy -out .tmp/destroy.plan` | ⛔ user reviews |
| 4 | Destroy | `terraform apply .tmp/destroy.plan` | `Destroy complete!` |
| 5 | List check | `just deploy::gcp-ls` | all empty |
| 6 | Cost review | Console → Billing → Reports, filter label `lane` | spend < the first budget threshold |

`gcp-ls` runs:
```
gcloud pubsub topics list
gcloud pubsub subscriptions list
bq ls --project_id "$GOOGLE_CLOUD_PROJECT"
gcloud run jobs list --region <r>
gcloud scheduler jobs list --location <r>
gcloud dataflow jobs list --status=active --region <r>
gcloud artifacts repositories list --location <r>
gcloud storage buckets list
```

## Notes
- `deletion_protection` (BigQuery) and `delete_contents_on_destroy` come from config (`false`/`true` on the trial project). If destroy stops on a protected table, set the config value, run `tf-plan` + `tf-apply`, then destroy again. Never edit state by hand.
- `google_project_service` uses `disable_on_destroy = false`, so the APIs stay enabled. They cost nothing.
- WIF pools are soft-deleted for 30 days. Recreating one with the same ID within that window fails. Undelete it, or change `deploy.wif.pool_id`. *(30-day figure unverified; re-check if it bites.)*
- Strongest option: delete the whole project (`gcloud projects delete`, ⛔ user only). When the trial ends, everything stops by itself ([02 facts](../../../../docs/plans/gcp/02-cloud-deploy-test.md#facts-checked-on-2026-10-30-with-source)).
- Billing data can lag up to ~24 h (unverified), so re-check the report the next day.

## Failure modes
| Symptom | Action |
|---|---|
| Destroy: `Error 400: Dataset … is still in use` / not empty | `delete_contents_on_destroy` must be `true` in config: plan, apply, destroy |
| Destroy hangs on a Cloud Run job execution | `gcloud run jobs executions list` → `cancel`, then retry |
| Destroy fails on the budget (billing perms) | ADC quota project / Costs Manager role (see [deploy-verify](deploy-verify.md#failure-modes)) |
| An AR repo with images blocks destroy | the cleanup policy only prunes old images; the repo resource deletes its images on destroy. If not, `gcloud artifacts docker images delete` the leftovers |
| State lost (`terraform.tfstate` gone) | list by label (`gcloud asset search-all-resources --query="labels.lane:<lane>"`) and delete by hand, or delete the project |
