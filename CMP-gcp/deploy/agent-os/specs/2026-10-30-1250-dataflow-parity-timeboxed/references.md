# References — Dataflow parity

## Similar Implementations
- **Location:** [crypto-market-pulse-chatgpt/project/src/market_pulse/beam_pipeline.py](../../../../../crypto-market-pulse-chatgpt/project/src/market_pulse/beam_pipeline.py) (never run)
  - **Relevance:** `StatsCombine` dedups by `event_id`; `compute_stats` is the oracle.
  - **Defects** (fixed by the local lane in [L07](../../../../../docs/plans/gcp/tasks.md#gcp-l07), see [01 Context](../../../../../docs/plans/gcp/01-local-dev-debug.md#context)): hardcoded `FixedWindows(60)` and lateness, and DISCARDING panes.
- **Location:** [docs/plans/gcp/02-cloud-deploy-test.md §c10](../../../../../docs/plans/gcp/02-cloud-deploy-test.md#c10)
  - **Relevance:** the original guardrail list. Correction: the walltime option is batch-only.
- **Docs:**
  - [Dataflow service options](https://docs.cloud.google.com/dataflow/docs/reference/service-options)
  - [Streaming Engine](https://docs.cloud.google.com/dataflow/docs/streaming-engine)
  - [stopping a pipeline](https://docs.cloud.google.com/dataflow/docs/guides/stopping-a-pipeline): drain vs cancel
