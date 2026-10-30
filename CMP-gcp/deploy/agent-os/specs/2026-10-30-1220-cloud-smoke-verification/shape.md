# Cloud smoke verification — Shaping Notes

## Scope
**GCP-C05:** the same FX assertion as local, through the **real** BigQuery subscription, in the isolated `smoke` env:
- rerun idempotency
- DQ/DLQ behaviour
- the `skip_on_emulator` queries from [L05](../../../../../docs/plans/gcp/tasks.md#gcp-l05)

## Decisions
**What runs the smoke**
- Reuse the local lane's `produce.py --profile cloud --env smoke --source fixture` and `assert_fixture.py --profile cloud --env smoke`, called by one recipe `deploy::smoke`.
- No new code, apart from the recipe and the poll timeout coming from config.

**Waiting for the data**
- `assert_fixture.py` polls with `deploy.smoke.{poll_timeout_s,poll_interval_s}`. The BigQuery subscription delivers asynchronously; there is no sleep-and-hope.

**Identity**
- Run as impersonated `smoke-sa`, so the laptop run proves the exact CI permission set (spec 5).

**Idempotency**
- Produce the fixture twice, so the raw count doubles and FX stays the same.
- Dedup is in the view (`event_id`). There is no Pub/Sub exactly-once requirement.

**Poison vs DLQ**
- With `use_table_schema = false`, malformed JSON *lands* in raw (as `data BYTES`). The dedup view drops it, and the DQ view counts it.
- The DLQ only receives write failures (missing table, permission, schema), so it must stay **empty** in this test.
- The DLQ path itself is checked in the runbook: drop the raw table → messages go to the DLQ after `max_delivery_attempts`.
- **Unverified:** whether a non-JSON `data` payload is ever rejected rather than landed. Record it as an observation.

**Heartbeat**
- The producer's heartbeat message lands in raw and is filtered out by the views. Harmless.

## Context
- **Visuals:** [architecture.md](../../../docs/design/architecture.md).
- **References:** [references.md](references.md).
- **Product alignment:** roadmap phase 3, the core proof.

## Standards Applied
See [standards.md](standards.md).
