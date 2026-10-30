# Cloud smoke verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `just deploy::smoke` publishes the fixture to the `smoke` topic and asserts FX in the `smoke` dataset through the real BigQuery subscription, idempotently, as `smoke-sa`.

**Architecture:** The recipe chains the local lane's `produce.py` and `assert_fixture.py` with `--profile cloud --env smoke`. Separate `deploy::smoke-poison` and `deploy::dlq-peek` recipes cover the DQ/DLQ checks.

**Tech Stack:** just, uv, the local lane's scripts, bq, gcloud.

**Spec:** [shape.md](shape.md) · task: [GCP-C05](../../../../../docs/plans/gcp/tasks.md#gcp-c05) (depends on C03, C04, L09)

## Global Constraints
- FX: BTCUSDT `2026-10-30 10:00:00 UTC` → `trade_count=4, volume=0.45, open_price=70000, high_price=70010, close_price=69990`.
- Only the `smoke` topic and dataset. Never `live`.
- Poll timeout and interval from `deploy.smoke.*`; no defaults.

## Review Focus
1. **Assert runs before the subscription has delivered:** it must poll until the timeout, then fail and print the last row seen (not an empty traceback). Owned by Task 2.
2. **Leftover rows from an earlier session in `smoke`:** FX must still hold, because dedup is by `event_id`. Raw count checks compare a before/after delta, never absolute numbers (Task 3).
3. **Decimal compare:** `volume` is `BIGNUMERIC`, so compare as `Decimal("0.45")`, not float. This lives in the local lane's assert; check it here.
4. **Heartbeat row counted as a trade:** `trade_count` must stay 4. That 4 is the check.
5. **Poison producing a DLQ entry:** expected none. If one shows up, record it as an observation and do not fail silently (Task 4).

---

### Task 1: Save spec documentation
- [x] Done (2026-10-30).

### Task 2: `deploy::smoke` recipe (GCP-C05 steps 1–2)

**Files:**
- Modify: `CMP-gcp/deploy/justfile`
- Modify: `CMP-gcp/config/config.yaml` (`deploy.smoke.{poll_timeout_s,poll_interval_s}`)

**Interfaces:**
- Consumes: `produce.py --profile cloud --env smoke --source fixture` and `assert_fixture.py --profile cloud --env smoke` (local lane, [L03](../../../../../docs/plans/gcp/tasks.md#gcp-l03) and [L09](../../../../../docs/plans/gcp/tasks.md#gcp-l09)). The assert exits 0 on FX and 1 otherwise, printing the actual row.

- [ ] **Step 1:** Recipe `smoke`. Set `CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT` to the Terraform output `smoke_sa_email` for the recipe only, then run produce, then assert. Tee everything to `../.tmp/evidence/<ts>-GCP-C05.log`.
- [ ] **Verify:** `just deploy::smoke` exits 0, and the log contains the FX row and `PASS`.

### Task 3: Idempotent rerun (GCP-C05 step 3)
- [ ] **Step 1:** Record `SELECT COUNT(*) FROM <smoke>.<raw_table>` → `n0`. Run `just deploy::smoke` → `n1`.
- [ ] **Verify:** `n1 - n0 == fixture lines + 1 heartbeat`, and the assert passes again with an identical FX row.

### Task 4: Poison + DLQ (GCP-C05 step 4)

**Files:** Modify: `CMP-gcp/deploy/justfile` (`smoke-poison` publishes `tests/fixtures/trades_poison.jsonl`; `dlq-peek` runs `gcloud pubsub subscriptions pull <smoke dlq sub> --limit=<cfg>` without auto-ack)

- [ ] **Step 1:** Note the DQ view count `d0`. Run `just deploy::smoke-poison`, then poll until the DQ count is `d0 + poison lines` or the timeout hits.
- [ ] **Verify:** the DQ count went up by the number of poison lines, FX is unchanged, and `just deploy::dlq-peek` prints `Listed 0 items`.

### Task 5: Cloud-only queries (GCP-C05 step 5)
- [ ] **Step 1:** Run every query marked `skip_on_emulator` in the local lane's `emulator-gaps.md` ([L05](../../../../../docs/plans/gcp/tasks.md#gcp-l05)) against `smoke`.
- [ ] **Verify:** each query runs without error, and the outputs are appended to the C05 evidence log.
