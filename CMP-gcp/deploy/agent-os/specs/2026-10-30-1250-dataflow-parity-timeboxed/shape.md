# Dataflow parity (optional, time-boxed) — Shaping Notes

## Scope
**GCP-C10 (optional):** show that the local lane's Beam pipeline gives `trades_1m_beam = trades_1m` for FX on Dataflow, at a bounded and recorded cost. Not part of the always-on path ([ADR-0001](../../../docs/adr/0001-bq-subscription-over-dataflow.md)).

## Decisions
**Run mode**
- Options: (a) a streaming job from the `smoke` Pub/Sub topic with a watchdog; (b) a **batch** job over the fixture JSONL in a GCS temp bucket.
- **Primary: (b).** The only hard server-side stop, `max_workflow_runtime_walltime_seconds`, is **batch only** ([service options](https://docs.cloud.google.com/dataflow/docs/reference/service-options), verified 2026-10-30). It exercises the same event-time windowing, dedup and sink transforms.
- **Stretch: (a)**, only with a second explicit OK. It is the only way to cover the drain/relaunch acceptance item in [C10](../../../../../docs/plans/gcp/tasks.md#gcp-c10). It runs with a client-side watchdog: `timeout <deploy.dataflow.max_walltime_s> just deploy::df-wait || true; just deploy::df-stop`.

**Source switch**
- The local lane's `beam_run.py` gets one bounded-source branch (`--source gcs-jsonl --input <uri>` → `ReadFromText` + `TimestampedValue`).
- **Coordinate with [L07](../../../../../docs/plans/gcp/tasks.md#gcp-l07).** This is the only code change in this spec, and it belongs to the local lane.

**Resources**
- With `deploy.dataflow.enabled: true`, Terraform adds a temp bucket with a lifecycle delete rule and `dataflow-sa` (worker, `storage.objectAdmin` on the bucket, `bigquery.dataEditor` on smoke; plus `pubsub.subscriber` for the stretch).
- Off by default, so it costs nothing.

**Caps (all from config)**
- `num_workers = max_num_workers = 1`
- `machine_type`: smallest supported; re-check at run time
- `--enable_streaming_engine` (stretch only), labels
- `deploy.dataflow.region` = the Pub/Sub/BigQuery location

**Cost**
- Streaming ≈ $0.069/vCPU-h (**unverified**: third-party; the official table didn't render).
- 1 worker × 2 vCPU × 1 h is well under $1. The risk is a forgotten job, so the walltime/watchdog and the `df-stop` trap matter more than the rate.

## Context
- **Visuals:** [architecture.md](../../../docs/design/architecture.md).
- **References:** [references.md](references.md).
- **Product alignment:** roadmap phase 6, optional.

## Standards Applied
See [standards.md](standards.md).
