# CMP-gcp — cloud deploy & test (Pub/Sub → BigQuery, optional Dataflow)

Status: plan only (2026-10-30). Nothing gets applied without the user's explicit go-ahead at each gated task. Cloud work starts only after the local loop passes ([GCP-L09](tasks.md#gcp-l09)).

## Facts checked on 2026-10-30 (with source)
| Fact | Source (last updated) |
|---|---|
| $300 credit, 90 days, no billing during the trial. Then a 30-day grace period, after which resources are deleted. No quota increases. | [free-cloud-features](https://docs.cloud.google.com/free/docs/free-cloud-features) (2026-10-27) |
| Free Tier per month: Pub/Sub 10 GiB messages; BigQuery 1 TiB query + 10 GiB storage; 1 e2-micro **only in us-west1/us-central1/us-east1**; Cloud Run 180k vCPU-s / 360k GiB-s (request-based billing); Cloud Build 2,500 min; Artifact Registry 0.5 GB. **Dataflow and Cloud Scheduler are not listed.** | same |
| BigQuery sandbox: no streaming, no DML, no Data Transfer Service; tables expire after 60 days; 10 GiB lifetime storage | [bigquery/docs/sandbox](https://docs.cloud.google.com/bigquery/docs/sandbox) (2026-10-27) |
| A BigQuery subscription writes through the Storage Write API and supports a dead-letter topic | [pubsub/docs/bigquery](https://docs.cloud.google.com/pubsub/docs/bigquery) (2026-10-26) |
| The emulator never delivers BigQuery subscriptions, has no IAM, keeps messages forever | [pubsub/docs/emulator](https://docs.cloud.google.com/pubsub/docs/emulator) (2026-10-26) |
| Cloud Run job task timeout: up to 168 h, default 10 min | [run task-timeout](https://docs.cloud.google.com/run/docs/configuring/task-timeout) (2026-10-26) |
| Bybit: requests from **US IPs are restricted (403)** | [Bybit V5 guide (zh-TW)](https://bybit-exchange.github.io/docs/zh-TW/v5/guide) |

**Unverified** (re-check in [GCP-C01](tasks.md#gcp-c01) before spending):
- The BigQuery-subscription price: $50/TiB in the [2022 launch post](https://cloud.google.com/blog/products/data-analytics/pub-sub-launches-direct-path-to-bigquery-for-streaming-analytics). Whether the 10 GiB free tier covers it: sources disagree.
- Dataflow streaming rates. The [pricing page](https://cloud.google.com/dataflow/pricing) didn't render; the [CUD doc](https://docs.cloud.google.com/dataflow/docs/cuds) gives *example* rates of ~$0.055/vCPU-h and ~$0.071/CU-h.
- Whether a Free Tier applies to Cloud Run *jobs*.
- A vendor claim that Bybit's CDN blocks cloud IP ranges.

**Consequences:**
- The sandbox can't be used: Pub/Sub needs billing, and the sandbox forbids streaming. So the plan uses a **billing-enabled trial project**, sized to fit inside the Free Tier.
- Expected load: BTC+ETH linear trades at about 300 B each, roughly 1–4 M trades a day (unmeasured). That is about 10–35 GiB a month → a few dollars a month at most.

## Decisions (one per topic; alternatives → backlog)
| Topic | Choice | Backlog |
|---|---|---|
| Ingest + transform | **Pub/Sub → BigQuery subscription → views** (dedup/1m/latest, the same SQL as local). No always-on compute, so close to free. | Cloud Run pull consumer [GCP-C12](tasks.md#gcp-c12); scheduled-query materialization [GCP-C13](tasks.md#gcp-c13) |
| Beam in the cloud | **Optional, time-boxed Dataflow parity run** on the trial credit, with the guardrails below. Not part of the always-on path. | Flex Template + scheduled runs [GCP-C17](tasks.md#gcp-c17) |
| Hosted producer | **Cloud Run job in `europe-west1`**, bounded by `--max-seconds` and triggered by Cloud Scheduler. Gated by a Bybit reachability probe. | e2-micro (Free Tier is US-only, likely geo-blocked) [GCP-C14](tasks.md#gcp-c14) |
| Region/location | `europe-west1` everywhere: Pub/Sub, a **regional** BigQuery dataset, Run, Dataflow. All values from `config.yaml`. | — |
| IaC | Terraform with local state (gitignored); `tfvars.json` generated from `config.yaml` | GCS backend [GCP-C15](tasks.md#gcp-c15) |
| Auth | No key files anywhere. Laptop: ADC + SA impersonation. CI: Workload Identity Federation. | — |
| Dashboard | Looker Studio (free) with the BigQuery connector on `trades_1m` / `trades_latest` | — |
| Spend control | Billing budget + alerts; teardown recipe; trial auto-stop | budget kill-switch [GCP-C16](tasks.md#gcp-c16) |

## Steps

### <a id="c1"></a>1. Project, billing, budget → [GCP-C01](tasks.md#gcp-c01)
- The user creates the trial project and links billing; the agent creates nothing.
- Put the non-secret project ID and region in `config/config.yaml[profiles.cloud]`, and `BILLING_ACCOUNT_ID` in `config/.env.secrets`, with the key listed in `.demo`.
- Re-verify the unverified prices above with the pricing calculator.
- Set a budget amount and thresholds from config. Note that budgets **alert, they don't stop spending**.

### <a id="c2"></a>2. Terraform rewrite + validate/plan → [GCP-C02](tasks.md#gcp-c02)
Terraform isn't installed: get a pinned version through brew or mise, following the reuse policy. Then fix the source `infra/gcp/main.tf`:
1. **Invalid HCL:** single-line blocks with several arguments (`variable "region" { type = string, default = ... }`, `provider { project = ..., region = ... }`, the `google_project_service` one-liners) fail `terraform validate`.
2. **Defaults and hardcoded names:** `region` default, `market-trades-v1`, `crypto_pulse`, `trades_raw`, `location = "EU"`. Replace them with required variables from the generated tfvars. Also: a multi-region EU dataset doesn't match `europe-west1`, so make it regional.
3. **Raw table:**
   - turn on `write_metadata = true` and add the metadata columns (exact list checked against the docs), so `message_id` and `publish_time` exist for the tie-break and pruning
   - `time_partitioning` on `publish_time`, with partition expiration from config
   - `deletion_protection` from a variable, so teardown works
4. **Dead-letter topic** plus the subscription's `dead_letter_policy`. Grant the Pub/Sub service agent publisher on the DLQ topic and subscriber on the source subscription.
5. **Service accounts, least privilege:**
   - `producer-sa`: `pubsub.publisher` on the topic
   - `dataflow-sa`: worker, subscriber, BigQuery data editor on the dataset; `count = var.enable_dataflow`
   - `deployer-sa` for CI
6. **Two environments via `for_each`: `live` and `smoke`**, each with its own topic, subscription, DLQ and dataset suffix. The fixture's BTCUSDT bucket is **2026-10-30 10:00 UTC, which is a real date**, so live trades in a shared table would break the exact assertion.
7. More resources:
   - APIs: pubsub, bigquery, iam, iamcredentials, sts, run, cloudscheduler, artifactregistry, cloudbuild, billingbudgets, dataflow (conditional)
   - `google_billing_budget`
   - WIF pool and provider (step 4)
   - Artifact Registry repo
   - Dataflow temp bucket with a lifecycle rule (conditional)
8. Pin the provider to the current major after `terraform init` (the source has `~> 6.0`; check whether 7.x is current).

Gate: `terraform fmt -check && terraform validate && terraform plan` output reviewed by the user. **No apply in this task.**

### <a id="c3"></a>3. Apply core ingest → [GCP-C03](tasks.md#gcp-c03)
- `just tf-apply` runs only after the user confirms.
- Then `sql_apply.py --profile cloud` creates the views for both environments. It is the same renderer as locally.
- Check: `bq ls`, `gcloud pubsub subscriptions describe`. The subscription state must be ACTIVE.

### <a id="c4"></a>4. Auth → [GCP-C04](tasks.md#gcp-c04)
- **Laptop:** `gcloud auth application-default login`, then run the tools with `--impersonate-service-account=<deployer-sa>` (from config). No JSON keys. The Python clients get the project from `GOOGLE_CLOUD_PROJECT` in `.env.secrets`.
- **GH Actions:**
  - `google-github-actions/auth` with `workload_identity_provider` and `service_account`
  - provider `attribute_condition = "assertion.repository == '<owner>/<repo>'"`, built from config
  - the repo is `dataengy/crypto-market-pulse`; use the **dataengy** gh account (`GH_TOKEN=$(gh auth token --user dataengy)`)
  - `permissions: id-token: write` only on the cloud workflow
- Check: an org policy blocking SA key creation is fine, because no keys are used.

### <a id="c5"></a>5. Cloud fixture verification (same assertion as local) → [GCP-C05](tasks.md#gcp-c05)
1. `produce --profile cloud --env smoke --source fixture` from the laptop. It ends with a heartbeat, which is harmless here.
2. `assert_fixture.py --profile cloud --env smoke` polls `trades_1m` and checks BTCUSDT 10:00 = `trade_count=4, volume=0.45, open 70000, high 70010, close 69990`.
3. Produce again → raw count ×2, bars unchanged.
4. Publish poison → the DQ view count goes up and the DLQ stays empty. A schema error would go to the DLQ; check this.
5. Run any query the emulator marked `skip_on_emulator` ([GCP-L05](tasks.md#gcp-l05)) here.

### <a id="c6"></a>6. Bybit reachability gate → [GCP-C06](tasks.md#gcp-c06)
- A one-off Cloud Run job in the configured region runs `produce --source bybit --sink stdout --max-trades <cfg>`.
- PASS means trades show up in the logs. A 403 or a timeout means stop: try another EU region from config, or keep the laptop or another host as the producer, and ask the user.

### <a id="c7"></a>7. Hosted producer → [GCP-C07](tasks.md#gcp-c07)
- Build the image with Cloud Build into Artifact Registry, tag = git SHA.
- The Cloud Run job runs as `producer-sa`, with task timeout and `--max-seconds` from config (< 168 h).
- Cloud Scheduler triggers it on a cron from config. The schedule is **paused** by default, like the DBX job.
- Logs go to Cloud Logging. The WS reconnect and gap warnings are visible.
- Acceptance: the live `trades_latest` age stays under the configured threshold while the job runs.

### <a id="c8"></a>8. Dashboard → [GCP-C08](tasks.md#gcp-c08)
- Looker Studio, BigQuery connector, owner's credentials, on the `live` views. Panels: last price, 1m OHLC, volume/VWAP, ingest lag, latest event age.
- Data freshness from config. Each refresh scans the partition-pruned raw table, which counts against the 1 TiB/month free query tier.
- Store the report URL in `config.yaml`; it isn't a secret.

### <a id="c9"></a>9. CI cloud smoke → [GCP-C09](tasks.md#gcp-c09)
- `workflow_dispatch` only, never on PRs. WIF auth, then step 5 against `smoke`, then upload the evidence log as an artifact.
- Concurrency group, so only one smoke runs at a time.

### <a id="c10"></a>10. Optional Dataflow parity run (gated, time-boxed) → [GCP-C10](tasks.md#gcp-c10)
- `beam_run --profile cloud --runner DataflowRunner` against `smoke`. Every value comes from config:
  - `--num_workers=1 --max_num_workers=1 --enable_streaming_engine`
  - the smallest supported `--machine_type` (verify)
  - `--dataflow_service_options=max_workflow_runtime_walltime_seconds=<cfg>` as a hard stop (verify the option is supported for streaming)
  - `--service_account_email=<dataflow-sa>`
  - labels
- `id_label=event_id` enables Pub/Sub dedup on Dataflow. Sink: `WriteToBigQuery(STORAGE_WRITE_API)` into `trades_1m_beam_panes`.
- Acceptance:
  - `trades_1m_beam` = `trades_1m` for the fixture
  - restart semantics: `gcloud dataflow jobs drain` emits the open windows, then relaunch and replay → no double count; `cancel` only for a stuck job
  - fill in the cost line in the evidence log
- `just df-stop` always runs (drain, then cancel after a timeout from config).

### <a id="c11"></a>11. Teardown & cost review → [GCP-C11](tasks.md#gcp-c11)
`just gcp-down` does, in order:
1. pause the scheduler
2. drain or cancel any Dataflow job
3. `terraform destroy` (with `deletion_protection=false` set first)
4. verify `gcloud pubsub topics list`, `bq ls`, `gcloud run jobs list` and `gcloud dataflow jobs list --status=active` are empty
5. check the billing report

Deleting the whole project is the strongest teardown. When the trial ends, everything stops by itself.

## Verification
- `terraform validate` and `plan` reviewed.
- Smoke assertion passes twice (idempotent).
- Probe PASS before the hosted producer.
- Live latest age under the threshold.
- Dashboard renders.
- After `gcp-down`, the list commands are empty and the budget report shows less than the alert.
