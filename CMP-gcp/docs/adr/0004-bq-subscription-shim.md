---
status: accepted
date: 2026-10-30
deciders: Nikolay (owner), planning agent
---
# 0004 — Local-only shim imitates BigQuery-subscription delivery

## Context and Problem Statement
In the cloud the SQL path is Pub/Sub → **BigQuery subscription** (`write_metadata=true`) → `trades_raw`. The Pub/Sub emulator accepts BigQuery subscriptions but never delivers them (per the plan's reading of the emulator docs, 2026-10-26). How do rows reach `trades_raw` locally?

## Considered Options
1. A small pull shim: pull → `insert_rows_json` with the same metadata columns → ack **after** insert
2. Skip the SQL path locally and test it only in the cloud
3. Have Beam also write raw rows

## Decision Outcome
Chosen: **option 1**. It is at-least-once like the real subscription, so dedup is exercised the same way. It is about 1 script, `local` profile only, and never deployed ([AD-6](../architecture.md#ad-6--local-stand-ins-never-ship)).

### Consequences
- Good: FX and the idempotent rerun are provable on the SQL path offline.
- Bad: column fidelity rests on an assumption until [GCP-C02](../../../docs/plans/gcp/tasks.md#gcp-c02) checks it against the current docs.

### Confirmation
The fixture gives 8 raw rows and 7 dedup rows ([story 2.3](../stories/2.3.story.md)).

## More Information
[Plan §6](../../../docs/plans/gcp/01-local-dev-debug.md#s6).
