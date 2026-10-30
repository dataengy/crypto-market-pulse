---
status: accepted
date: 2026-10-30
deciders: Nikolay (owner), planning agent
---
# 0003 — Dedup by event_id; late data via ACCUMULATING panes + append-only pane sink; heartbeat closes windows

## Context and Problem Statement
Pub/Sub delivers at least once, and the fixture contains a duplicate. Trades can arrive late or out of order. The reference pipeline used the default trigger with DISCARDING panes, so a late pane would *replace* the bar with only the late trades. A finite replay also never advances the watermark past the last window. How should duplicates, late data and window closing be handled without DML?

## Decision Drivers
- The bar must be correct after duplicates, reordering and late data within lateness.
- Idempotent sink without MERGE/UPDATE (the emulator supports little DML; this also keeps the sink sandbox-safe).
- Deterministic tests.

## Considered Options
1. ACCUMULATING + `AfterWatermark(late=AfterCount(1))`; append panes; a view picks the max `pane_index`
2. DISCARDING panes + MERGE of deltas into the bar table
3. No lateness (drop all late data) + nightly SQL correction

## Decision Outcome
Chosen: **option 1**, plus:
- **Dedup**: the combiner keeps the first-received copy per `event_id`. This is valid because `event_id` → a fixed `event_time` → exactly one window. SQL uses `QUALIFY ROW_NUMBER()` with `message_id` as a deterministic tie-break.
- **Beyond lateness**: dropped by Beam and **measured, not counted inside Beam**: reconciliation = `trades_1m` (SQL over raw, which keeps everything) minus `trades_1m_beam`.
- **Heartbeat**: after a fixture replay the producer emits one `kind=heartbeat` message with `event_time_ms = last + window_s + allowed_lateness_s + 1s`. Both paths drop it.
- `window_s` and `allowed_lateness_s` come from config ([AD-2](../architecture.md#ad-2--strict-config-no-defaults-adopted)).

### Consequences
- Good: a LATE pane carries full totals; reruns are idempotent; no DML.
- Bad: the pane table grows by one row per firing (negligible locally). The combiner's dedup state grows with the number of distinct ids per window, which is fine at this scale and a cloud concern.
- Neutral: `id_label` dedup is Dataflow-only; locally the combiner does the dedup.

### Confirmation
TestStream cases 1–6 ([story 3.2](../stories/3.2.story.md)); fault F1/F2/F7 ([story 4.2](../stories/4.2.story.md)).

## Pros and Cons of the Options
- **DISCARDING + MERGE**: smaller panes, but needs DML on the emulator and makes rerun idempotency much harder.
- **No lateness**: simplest, but loses the main thing the Beam path exists to show.

## More Information
[Plan §3, §7, §8](../../../docs/plans/gcp/01-local-dev-debug.md#s7).
