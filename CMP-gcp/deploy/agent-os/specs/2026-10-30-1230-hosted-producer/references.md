# References — Hosted producer + dashboard

## Similar Implementations
- **Location:** [CMP-dbx-fe/scripts/produce.py](../../../../../CMP-dbx-fe/scripts/produce.py)
  - **Relevance:** the `--source bybit|fixture`, `--max-trades` and `--sink` interface. The local lane ports it to Pub/Sub ([L03](../../../../../docs/plans/gcp/tasks.md#gcp-l03)).
- **Location:** [CMP-dbx-fe/databricks.yml](../../../../../CMP-dbx-fe/databricks.yml)
  - **Relevance:** the scheduled job deployed **paused**, the same pattern as `paused = true` here.
- **Location:** [docs/plans/gcp/02-cloud-deploy-test.md §c6–c8](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#c6)
  - **Relevance:** the gate and acceptance criteria.
- **Docs:**
  - [Cloud Run task timeout](https://docs.cloud.google.com/run/docs/configuring/task-timeout): up to 168 h, default 10 min (verified 2026-10-30 in 02)
  - [Bybit V5 integration guide](https://bybit-exchange.github.io/docs/v5/guide): US and Mainland-China IPs get 403
