# Roadmap — CMP-gcp cloud deploy

Every phase is **gated**: the user approves before any apply, any spend, or any Dataflow launch. The local gate is [GCP-L09](../../../../docs/plans/gcp/tasks.md#gcp-l09). It must pass first, because the cloud specs reuse its `settings.py`, `sql_apply.py`, `produce.py` and `assert_fixture.py`.

| Phase | Spec | Task IDs | Depends on (local) | Gate |
|---|---|---|---|---|
| 1 | [terraform-foundation](../specs/2026-10-30-1200-terraform-foundation/plan.md) | C01, C02, C11 (recipe) | L02, L05 | user links billing; user reviews `plan` |
| 2 | [pubsub-bq-subscription](../specs/2026-10-30-1210-pubsub-bq-subscription/plan.md) | C03, C04 (laptop) | L05 | user approves apply |
| 3 | [cloud-smoke-verification](../specs/2026-10-30-1220-cloud-smoke-verification/plan.md) | C05 | L09 | — |
| 4 | [hosted-producer](../specs/2026-10-30-1230-hosted-producer/plan.md) | C06, C07, C08 | L11 | the Bybit probe passes |
| 5 | [ci-wif-cloud-smoke](../specs/2026-10-30-1240-ci-wif-cloud-smoke/plan.md) | C04 (CI), C09 | L13 | user confirms push |
| 6 | [dataflow-parity-timeboxed](../specs/2026-10-30-1250-dataflow-parity-timeboxed/plan.md) | C10 (optional) | L08, L10 | user approves the spend |
| — | teardown ([runbook](../../docs/runbooks/teardown.md)) | C11 | — | after every cloud session |

## Backlog (not scheduled)
These are the alternatives already listed in [tasks.md](../../../../docs/plans/gcp/tasks.md#backlog-alternatives-not-scheduled):
- GCP-C12: Cloud Run pull consumer
- GCP-C13: scheduled-query materialization
- GCP-C14: e2-micro producer (US-only Free Tier, and US IPs are blocked by Bybit, see [ADR-0002](../../docs/adr/0002-cloud-run-job-region.md))
- GCP-C15: GCS remote state
- GCP-C16: budget kill-switch. Check first whether native [budget spend caps](https://docs.cloud.google.com/run/docs/configuring/billing-settings) for Cloud Run cover it (unverified scope).
- GCP-C17: Dataflow Flex Template
