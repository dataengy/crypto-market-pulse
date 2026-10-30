# References — Cloud smoke verification

## Similar Implementations
- **Location:** [CMP-dbx-fe/tests/test_integration_kafka.py](../../../../../CMP-dbx-fe/tests/test_integration_kafka.py)
  - **Relevance:** the sibling lane's exact-bar, restart and replay-dedup checks.
  - **Key patterns:** the assertion on FX values and the replay → unchanged bar.
- **Location:** [CMP-dbx-fe/tests/fixtures/](../../../../../CMP-dbx-fe/tests/fixtures/trades.jsonl)
  - **Relevance:** 8 trades with 1 duplicate. The local lane copies it to `CMP-gcp/tests/fixtures/`.
- **Location:** [docs/plans/gcp/02-cloud-deploy-test.md §c5](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#c5)
  - **Relevance:** the step list.
