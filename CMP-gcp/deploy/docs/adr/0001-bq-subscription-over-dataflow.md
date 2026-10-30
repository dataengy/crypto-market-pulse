---
status: accepted
date: 2026-10-30
decision-makers: owner
---
# 0001 — Ingest with a Pub/Sub BigQuery subscription; Dataflow only as a time-boxed parity check

## Context and Problem Statement
Trades go from Pub/Sub to BigQuery, and must be deduped and aggregated into 1-minute bars. What runs the always-on path in the cloud, at close to zero cost?

## Decision Drivers
- No always-on compute (trial credit, personal project)
- The same SQL as the local emulator path ([L05](../../../../docs/plans/gcp/tasks.md#gcp-l05))
- Teardown is one `terraform destroy`
- Beam parity must still be demonstrable

## Considered Options
1. A Pub/Sub **BigQuery subscription** → raw table → SQL views
2. Dataflow streaming (Beam) Pub/Sub → BigQuery, always on
3. A Cloud Run pull consumer → BigQuery (backlog [GCP-C12](../../../../docs/plans/gcp/tasks.md#gcp-c12))

## Decision Outcome
Chosen: **option 1** for the always-on path, plus a **Dataflow batch parity run** (time-boxed, optional; [spec](../../agent-os/specs/2026-10-30-1250-dataflow-parity-timeboxed/shape.md)).

### Consequences
- Good: no compute to run. Cost is only throughput: $50/TiB for the BigQuery subscription, **no free 10 GiB** ([pubsub/pricing](https://cloud.google.com/pubsub/pricing), verified 2026-10-30). That is ≈ $1–2 a month at the expected 10–35 GiB.
- Good: the views are the same templates as local; the DLQ is native.
- Bad: dedup and aggregation run at query time, so every dashboard refresh re-scans (mitigated by partition pruning; backlog [GCP-C13](../../../../docs/plans/gcp/tasks.md#gcp-c13)).
- Bad: no streaming transform before landing. Poison JSON lands in raw, and the DQ view counts it.
- Neutral: Dataflow's hard walltime stop is **batch-only** ([service options](https://docs.cloud.google.com/dataflow/docs/reference/service-options), verified 2026-10-30). Hence batch parity first; the streaming drain/relaunch check is a separately approved stretch.

### Confirmation
[cloud-smoke-verification](../../agent-os/specs/2026-10-30-1220-cloud-smoke-verification/plan.md) passes FX twice through the real subscription.

## Pros and Cons of the Options
- **Dataflow streaming always on:** real event-time semantics, but at least one worker 24/7 (≈ $50+/month by third-party rates, **unverified**) and no server-side stop for streaming.
- **Cloud Run pull consumer:** custom validation, but new code, and either always-on or polling gaps.
