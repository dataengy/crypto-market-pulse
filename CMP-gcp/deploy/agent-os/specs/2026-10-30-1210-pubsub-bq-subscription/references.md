# References — Pub/Sub → BigQuery subscription + views

## Similar Implementations
- **Location:** [crypto-market-pulse-chatgpt/project/sql/bigquery/](../../../../../crypto-market-pulse-chatgpt/project/sql/bigquery/002_dedup.sql)
  - **Relevance:** the dedup, 1m and latest views decode `data` with `SAFE.PARSE_JSON(SAFE_CONVERT_BYTES_TO_STRING(data))`.
  - **Key patterns:** `QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id …) = 1`.
  - **Defect:** hardcoded `crypto_pulse.`. The local lane templates it as `{{dataset}}` ([L05](../../../../../docs/plans/gcp/tasks.md#gcp-l05)).
- **Location:** [docs/plans/gcp/02-cloud-deploy-test.md §c3](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#c3)
  - **Relevance:** the apply and check steps.
- **Docs:** [BigQuery subscriptions](https://docs.cloud.google.com/pubsub/docs/bigquery): Storage Write API, DLQ behaviour on schema errors.
