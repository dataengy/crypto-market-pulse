# Hosted producer + dashboard — Shaping Notes

## Scope
- **GCP-C06:** the Bybit reachability gate from the GCP region
- **GCP-C07:** a bounded Cloud Run job + a paused Cloud Scheduler trigger feeding `live`
- **GCP-C08:** a Looker Studio report on the `live` views

## Decisions
**Compute**
- Options: (a) a Cloud Run **job** with `--max-seconds`; (b) a Cloud Run service with `min-instances = 1`; (c) an e2-micro VM (GCP-C14); (d) the laptop.
- **Choice: (a).** It is bounded, scales to zero, and fits the jobs Free Tier (240k vCPU-s, 450k GiB-s per month, [run/pricing](https://cloud.google.com/run/pricing), verified 2026-10-30). (b) is always-on. (c) is US-only, and US IPs are blocked by Bybit.

**Region**
- `deploy.run.region`, planned `europe-west1`, with an ordered fallback list `deploy.run.fallback_regions`.
- See [ADR-0002](../../../docs/adr/0002-cloud-run-job-region.md).

**Probe**
- The **same job**, executed once with an args override: `gcloud run jobs execute <job> --region <r> --args=<probe args from config> --wait`. It runs `produce --source bybit --sink stdout --max-trades <cfg>`.
- No second job resource.

**Who owns the job and Scheduler**
- Terraform: `google_cloud_run_v2_job` + `google_cloud_scheduler_job` with `paused = true`. Then `terraform destroy` removes everything, and teardown needs no extra gcloud steps.
- The image tag (git SHA) changes per build, so `just deploy::producer-build` writes `.tmp/producer_image.txt`. The tf recipes export `TF_VAR_producer_image` from it, and fail with "run just deploy::producer-build" if it is missing.

**Image**
- `producer.Dockerfile` (uv, py3.12, `CMD produce.py`) with the build context in `CMP-gcp/`, built by `gcloud builds submit` (Cloud Build Free Tier) into the AR repo from spec 1.
- Buildpacks `--source` deploy was considered. Rejected: uv support is **unverified**, and a 6-line Dockerfile is deterministic.

**Overlap and retries**
- Keep `max_seconds < task_timeout < scheduler interval`, and `max_retries = 0`. Duplicates are harmless anyway, because the views dedup by `event_id`.

**Scheduler identity**
- `producer-sa` with `roles/run.invoker` on the job only. `ponytail:` one SA is enough at this size; split it out if the job ever needs more than publish.

**Dashboard**
- Looker Studio, manual (no API), owner's credentials, on `live.trades_1m` and `live.trades_latest`.
- Panels: last price, 1m OHLC, volume/VWAP, ingest lag, latest event age.
- URL in `deploy.dashboard.url`; data freshness from config.

## Context
- **Visuals:** [architecture.md](../../../docs/design/architecture.md).
- **References:** [references.md](references.md).
- **Product alignment:** roadmap phase 4. Gated on the probe passing.

## Standards Applied
See [standards.md](standards.md).
