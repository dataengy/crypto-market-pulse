---
status: accepted
date: 2026-10-30
deciders: Nikolay (owner), planning agent
---
# 0002 — Local runner = DirectRunner (whatever it actually runs is logged); Prism explicitly deferred

## Context and Problem Statement
Since Beam 2.68 the Python DirectRunner hands most pipelines to **Prism** by default ([Beam 2.68 release notes](https://github.com/apache/beam/blob/master/CHANGES.md)). The local loop needs (a) deterministic `TestStream` tests and (b) a streaming `ReadFromPubSub` against the emulator. Which runner should be targeted?

## Decision Drivers
- Determinism for windowing, lateness and dedup tests.
- `ReadFromPubSub` streaming support against `PUBSUB_EMULATOR_HOST`.
- No extra binaries or services (ponytail).

## Considered Options
1. `--runner=DirectRunner --streaming`, and log the runner that actually ran
2. `--runner=PrismRunner` explicitly
3. A Flink/Spark portable runner in Docker

## Decision Outcome
Chosen: **option 1**. The plan reads the Beam source (`direct_runner.py` 2.74) as saying that TestStream and streaming `ReadFromPubSub` fall back to the BundleBased DirectRunner, which is the path that overrides Pub/Sub for streaming. That reading is **unverified**. So the pipeline does not assume either runner: it logs which one ran, and the tests check results, never runner internals.

### Consequences
- Good: zero extra runtime; TestStream works today.
- Bad: no durable checkpoint, so restart semantics ([F3](../../../docs/plans/gcp/01-local-dev-debug.md#s10)) are only approximated locally. Real drain/update is checked in the cloud at [GCP-C10](../../../docs/plans/gcp/tasks.md#gcp-c10).
- Bad: if a future Beam routes Pub/Sub streaming through Prism, behaviour may change. The pin in `uv.lock` and the runner log line catch that.

### Confirmation
The [story 3.1](../stories/3.1.story.md) log line shows the effective runner; [story 3.2](../stories/3.2.story.md) is green on the pinned Beam.

## Pros and Cons of the Options
- **Prism explicit**: the Beam team's direction, but Python `ReadFromPubSub` support on it is unproven → [GCP-L15](../../../docs/plans/gcp/tasks.md#gcp-l15).
- **Flink/Spark in Docker**: closer to production checkpointing, but it means new containers and job-server config with no FX benefit.

## More Information
[Plan §7](../../../docs/plans/gcp/01-local-dev-debug.md#s7).
