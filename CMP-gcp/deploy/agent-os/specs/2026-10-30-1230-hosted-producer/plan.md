# Hosted producer + dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A bounded, scheduled Cloud Run job streams live Bybit trades into the `live` env, after a probe proves that the region can reach Bybit. A Looker Studio report shows the bars.

**Architecture:**
- Cloud Build pushes the image to AR.
- Terraform adds a `google_cloud_run_v2_job` running as `producer-sa`, and a paused `google_cloud_scheduler_job`.
- The probe is the same job executed with overridden args.

**Tech Stack:** Docker (built remotely by Cloud Build), Terraform, gcloud, Looker Studio.

**Spec:** [shape.md](shape.md) · tasks: [GCP-C06](../../../../../docs/plans/gcp/tasks.md#gcp-c06), [GCP-C07](../../../../../docs/plans/gcp/tasks.md#gcp-c07), [GCP-C08](../../../../../docs/plans/gcp/tasks.md#gcp-c08)

## Global Constraints
- Region from `deploy.run.region`. **Never** a `us-*`, `northamerica-*`, `asia-east2` (Hong Kong) or `asia-southeast1` (Singapore) region; Bybit restricts those jurisdictions ([ADR-0002](../../../docs/adr/0002-cloud-run-job-region.md)).
- `deploy.run.max_seconds < deploy.run.task_timeout_s < scheduler interval`; `max_retries = 0`.
- The Scheduler is created with `paused = true`. Unpausing is a user-gated step.
- No credentials in the image. The job runs as `producer-sa`, and `produce.py` gets its project from env set on the job.

## Review Focus
1. **Probe returns HTTP 403 or times out:** stop, record it, and ask the user. Do not cycle regions automatically (Task 3).
2. **WS disconnects mid-run:** the producer must reconnect with backoff and log a gap warning. Visible in Cloud Logging (Task 5 verify).
3. **The job ends at `--max-seconds` mid-batch:** the publisher must flush before exit (local lane `publish.py` drain). The check is that the job execution status is `Succeeded`, not `Failed` on SIGTERM.
4. **Missing `.tmp/producer_image.txt`:** tf recipes fail with a clear message (Task 2).
5. **Dashboard scans the full raw table each refresh:** check the bytes billed per refresh in the BigQuery job history. If it grows, go to backlog GCP-C13.

---

### Task 1: Save spec documentation
- [x] Done (2026-10-30).

### Task 2: Image build (user-gated first build)

**Files:**
- Create: `CMP-gcp/deploy/producer.Dockerfile`
- Modify: `CMP-gcp/deploy/justfile` (`producer-build`)

- [ ] **Step 1:** Dockerfile: a `python:3.12-slim` + uv base pinned by digest, `uv sync --frozen --no-dev`, `ENTRYPOINT ["uv","run","python","scripts/produce.py"]`. Build context `CMP-gcp/`.
- [ ] **Step 2:** `producer-build` runs `gcloud builds submit .. --tag <ar_repo_url>/<deploy.run.image_name>:$(git rev-parse --short HEAD)` and writes the full tag to `../.tmp/producer_image.txt`. The tf recipes read that file, or fail with `run just deploy::producer-build`.
- [ ] **Verify:** `gcloud artifacts docker images list <ar_repo_url>` shows the tag.

### Task 3: Job + paused Scheduler in Terraform, then the probe (GCP-C06)

**Files:**
- Modify: `CMP-gcp/deploy/terraform/{main.tf,variables.tf,outputs.tf}` (`variable "producer_image"`, required)
- Modify: `CMP-gcp/config/config.yaml`:
  - `deploy.run.{region,fallback_regions,job,image_name,cpu,memory,task_timeout_s,max_seconds,probe_args}`
  - `deploy.scheduler.{name,cron,time_zone}`

- [ ] **Step 1:** `google_cloud_run_v2_job`:
  - `location = deploy.run.region`, `service_account = producer-sa`, `max_retries = 0`, `timeout = task_timeout_s`
  - env: `CMP_PROFILE=cloud`, `GOOGLE_CLOUD_PROJECT`, `--env live`
  - args: `--source bybit --max-seconds <cfg>`
- [ ] **Step 2:** `google_cloud_scheduler_job` (`paused = true`, HTTP target = the Run Admin API `jobs:run` URI, OAuth as `producer-sa`), plus `roles/run.invoker` for `producer-sa` on the job.
- [ ] **Step 3:** Plan, user review, apply.
- [ ] **Step 4 (probe):** Recipe `producer-probe` runs `gcloud run jobs execute <job> --region <r> --args=<probe_args> --wait`. Add `producer-resume` and `producer-pause`, which wrap `gcloud scheduler jobs resume|pause`.
- [ ] **Verify:** the execution status is `Succeeded`, and `gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="<job>"' --limit=50` shows trade JSON lines. On a 403 or a timeout, write a FAIL evidence log and **stop**.

### Task 4: Hosted live ingestion (GCP-C07, user-gated unpause)
- [ ] **Step 1:** The user approves. Run `just deploy::producer-resume`, which wraps `gcloud scheduler jobs resume <name> --location <r>`. Terraform keeps `paused = true`, so any later `apply` re-pauses the schedule: safe by default, and intended.
- [ ] **Verify:**
  - During a run, `SELECT TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), TIMESTAMP_MILLIS(MAX(latest_event_time_ms)), SECOND) FROM <live>.trades_latest` stays below `deploy.run.max_latest_age_s`.
  - Afterwards, `just deploy::producer-pause` runs, and `describe` shows `state: PAUSED`.

### Task 5: Looker Studio dashboard (GCP-C08, manual)
- [ ] **Step 1:** The user creates the report: BigQuery connector → `<live>.trades_1m` and `trades_latest`, owner's credentials. Panels as listed in [shape.md](shape.md). Freshness from `deploy.dashboard.freshness_min`.
- [ ] **Step 2:** Store the report URL in `deploy.dashboard.url`.
- [ ] **Verify:** the report renders the current minutes while the job runs. Screenshot path goes in the C08 evidence log, along with the bytes billed per refresh from the BigQuery job history.
