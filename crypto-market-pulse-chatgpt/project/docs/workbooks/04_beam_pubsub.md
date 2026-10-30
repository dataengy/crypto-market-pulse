# Workbook 4 — Beam event time and Pub/Sub Emulator

**Goal:** exercise Beam fixed windows and Pub/Sub transport separately. A local Pub/Sub Emulator does **not** deliver BigQuery subscriptions or emulate DataflowRunner.

### Exercise A — Beam DirectRunner/TestStream

```bash
python -m pip install -r requirements-beam.txt
PYTHONPATH=src pytest -q tests/test_beam_optional.py -v
```

Read `src/market_pulse/beam_pipeline.py` and `tests/test_beam_optional.py`. Locate `TimestampedValue`, `FixedWindows(60)`, `allowed_lateness=30` and the per-key duplicate accumulator. Observe that Beam watermark events supplied by `TestStream` control when windows are emitted.

### Questions

1. Does arrival order change window assignment when event-time is explicitly stamped?
2. What is the difference between the watermark and allowed lateness?
3. Is `CombinePerKey` enough for production high-cardinality unbounded dedup? Consider accumulator growth, state retention and large keys.
4. How should a production pipeline deal with a trade arriving beyond the watermark? Discard, quarantine or issue a correction? Where would metrics be recorded?

### Exercise B — local Pub/Sub emulator, *optional*

If a compatible `gcloud` is already installed, start its Pub/Sub emulator in a terminal:

```bash
gcloud beta emulators pubsub start --host-port=127.0.0.1:8085
```

In another terminal:

```bash
export PUBSUB_EMULATOR_HOST=127.0.0.1:8085
python -m pip install -r requirements-gcp.txt
python scripts/gcp_emulator_smoke.py
```

The smoke script **refuses** to access managed Pub/Sub without `PUBSUB_EMULATOR_HOST`. It creates a disposable local topic/subscription, publishes eight fixture events, pulls and ACKs, and checks duplicate IDs. Check that all events arrive and observe the difference between transport delivery and event-time aggregation.

### Stretch: cloud opt-in checklist

For Pub/Sub → native BigQuery Subscription, BigQuery views and optional Dataflow job, use `infra/gcp/main.tf` only after confirmed GCP project, IAM, billing, location and service account. `terraform init && terraform plan` is review-only; **never** assume safe `apply`, and never claim the emulator tested BigQuery delivery.

**Pass:** Beam test returns expected windows; Pub/Sub emulator separately passes publish/pull/ack if run. Record beam version and actual test output.
