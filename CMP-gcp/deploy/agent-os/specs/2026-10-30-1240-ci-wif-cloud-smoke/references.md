# References — CI cloud smoke via WIF

## Similar Implementations
- **Location:** [google-github-actions/auth README](https://github.com/google-github-actions/auth/blob/main/README.md)
  - **Relevance:** the `@v3` inputs `workload_identity_provider` + `service_account` (WIF through an SA). An attribute condition is required.
- **Location:** [WIF with deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)
  - **Relevance:** GitHub's single issuer means every GitHub org shares one issuer, so an attribute condition is mandatory.
- **Location:** [docs/plans/gcp/02-cloud-deploy-test.md §c4, §c9](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#c9)
  - **Relevance:** the original auth and CI plan. The `dataengy` account comes from the user rule `github-accounts`.
