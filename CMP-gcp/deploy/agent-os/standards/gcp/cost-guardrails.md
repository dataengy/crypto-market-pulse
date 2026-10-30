# Cost guardrails

## Facts
| Fact | Status |
|---|---|
| Pub/Sub throughput: first 10 GiB/month free, then $40/TiB. **BigQuery subscription: $50/TiB, and the first 10 GiB are *not* free.** | verified, [pubsub/pricing](https://cloud.google.com/pubsub/pricing), 2026-10-30 |
| Cloud Run **jobs** Free Tier: 240,000 vCPU-s + 450,000 GiB-s per month; jobs use instance-based billing, minimum 1 min per instance | verified, [run/pricing](https://cloud.google.com/run/pricing), 2026-10-30 |
| Dataflow `max_workflow_runtime_walltime_seconds` is **batch only** | verified, [service-options](https://docs.cloud.google.com/dataflow/docs/reference/service-options) (2026-10-26), 2026-10-30 |
| Dataflow streaming ≈ $0.069/vCPU-h; Streaming Engine ≈ $0.018/unit-h | **unverified**: third-party; the official page didn't render the table |
| Pub/Sub minimum billable size of 1 KB per request (so batch the publishes) | **unverified**: re-check in GCP-C01 |
| Cloud Scheduler: 3 free jobs per billing account | **unverified**: re-check in GCP-C01 |
| BigQuery Free Tier: 1 TiB query + 10 GiB storage per month; trial $300 / 90 days | from [02-cloud-deploy-test.md](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#facts-checked-on-2026-10-30-with-source) (verified 2026-10-30) |

**Estimate:** 10–35 GiB/month of trades → BigQuery subscription ≤ ~$1.7 + publish ≤ ~$1. Raise it to ~4× if the 1 KB minimum applies to unbatched 300-byte messages. *Re-measure in GCP-C07.*

## Rules
- **Budget:**
  - `google_billing_budget` on the project, with amount and thresholds from `deploy.budget.*`
  - email alerts to the billing admins
  - budgets **alert, they don't stop spending**
- **Labels:** every resource gets `labels = local.cfg.deploy.labels` (e.g. `app`, `lane`, `env`), so the billing report can filter on them.
- **Nothing always-on:**
  - The Scheduler job is created `paused = true`.
  - The Cloud Run job is bounded by `--max-seconds` < task timeout < Scheduler interval, with `max_retries = 0`.
- **Retention:**
  - raw partition expiration and the subscription `message_retention_duration` come from config
  - Artifact Registry cleanup policy: keep the last N images
  - the Dataflow temp bucket has a lifecycle delete rule
- **Dataflow** (only with `deploy.dataflow.enabled: true` and the user's OK):
  - `num_workers = max_num_workers = 1`, the smallest supported machine type (from config), labels set
  - batch mode with `max_workflow_runtime_walltime_seconds`
  - `just df-stop` runs in a `trap` / `finally`
- **Teardown:** follow [teardown.md](../../../docs/runbooks/teardown.md) after every cloud session. A session isn't done until its empty-list evidence is recorded.
