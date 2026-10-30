# Runbook — deploy & verify (GCP cloud)

Status: written ahead of implementation (2026-10-30). The recipe names are the ones the specs define. Every ⛔ is a stop-and-ask gate ([verification standard](../../agent-os/standards/process/verification.md)).

## Preconditions
- The local gate [GCP-L09](../../../../docs/plans/gcp/tasks.md#gcp-l09) is green.
- `CMP-gcp/config/.env.secrets` has `GOOGLE_CLOUD_PROJECT`, `BILLING_ACCOUNT_ID` and `OWNER_MEMBER`.
- `gcloud auth application-default login` is done.
- Terraform is installed at the pinned version.

## Sequence
| # | Step | Command | Evidence |
|---|---|---|---|
| 1 | Plan | `just deploy::tf-init && just deploy::tf-plan` | plan text, create-only ⛔ review |
| 2 | Apply core | `just deploy::tf-apply` | subscriptions `ACTIVE` |
| 3 | Views | `just deploy::sql-apply smoke && just deploy::sql-apply live` | `COUNT(*)` = 0, no error |
| 4 | Smoke | `just deploy::smoke` twice, then `smoke-poison` and `dlq-peek` | FX PASS ×2, DQ +n, DLQ 0 |
| 5 | Image | `just deploy::producer-build` ⛔ first build | tag in AR |
| 6 | Job + probe | `just deploy::tf-plan` ⛔ → `tf-apply` → `just deploy::producer-probe` | `Succeeded`, trades in logs |
| 7 | Live | ⛔ `just deploy::producer-resume` … `producer-pause` | latest age < threshold |
| 8 | Dashboard | manual (Looker Studio) | URL in config, screenshot |
| 9 | CI | `just deploy::gh-vars` → ⛔ push → `gh workflow run` | green run + artifact |
| 10 | Teardown | [teardown.md](teardown.md) | empty lists |

Evidence: `CMP-gcp/.tmp/evidence/<ts>-<task>.log`.

## Failure modes
| Symptom | Likely cause | Action |
|---|---|---|
| `terraform plan`: `Unsupported attribute "x"` | missing `deploy.*` key | add the key to `config/config.yaml`; never add `try()` or a default |
| Recipe: `missing <KEY> in CMP-gcp/config/.env.secrets` | env not filled | fill the file from `.env.secrets.demo` |
| Budget create: `403` or quota-project error | ADC without a quota project / missing billing rights | `gcloud auth application-default set-quota-project $GOOGLE_CLOUD_PROJECT`; the owner needs Billing Account Costs Manager |
| `SERVICE_DISABLED` on first apply | API enablement still propagating | re-run plan/apply after a few minutes; `depends_on` on `google_project_service` |
| Subscription `PERMISSION_DENIED` | the Pub/Sub agent lacks `bigquery.dataEditor`, or IAM is still propagating | check the IAM resource in state; wait up to 5 min; don't widen roles |
| Subscription `SCHEMA_MISMATCH` | raw table ≠ `write_metadata` columns or ≠ 001_raw.sql | diff `bq show --schema` against 001_raw.sql; fix Terraform and re-apply |
| Subscription `NOT_FOUND` | raw table deleted or misnamed | re-apply; DLQ messages pile up meanwhile (`dlq-peek`) |
| Assert times out, raw empty | wrong env/topic, or impersonation can't publish | check the `--env smoke` topic id against the Terraform output; `gcloud pubsub topics publish` as `smoke-sa` |
| Assert times out, raw has rows, no bar | heartbeat or views not applied; window not closed | `sql-apply smoke`; check that the view filters only drop heartbeat/poison |
| FX off by the duplicate | dedup view not keyed on `event_id` | local-lane SQL bug: fix in L05, re-apply the views |
| Probe 403 / timeout | Bybit geo or cloud-IP block | ⛔ record, ask the user: fallback region or laptop ([ADR-0002](../adr/0002-cloud-run-job-region.md)) |
| Job `Failed` at max-seconds | publisher not flushed on SIGTERM | local lane `publish.py` drain; keep `max_seconds` < `task_timeout_s` |
| Latest age grows while running | WS reconnect loop / rate limit | Cloud Logging gap warnings; Bybit limit: ≤ 500 connections per 5 min per IP ([rate limits](https://bybit-exchange.github.io/docs/v5/rate-limit)) |
| CI: `PERMISSION_DENIED` from STS | WIF condition/binding mismatch or propagation | repo string must equal `deploy.wif.repository`; wait 5 min, retry once |
| CI: `Repository not found` with gh | wrong gh account | `GH_TOKEN=$(gh auth token --user dataengy)` |
| Bill rising unexpectedly | scheduler left running / Dataflow active | `producer-pause`, `df-stop`, then [teardown](teardown.md) |
