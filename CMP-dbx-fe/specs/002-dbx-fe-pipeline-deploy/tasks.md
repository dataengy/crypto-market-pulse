---
description: "Tasks for 002 Free Edition deploy (mapped to DBX-C*)"
---

# Tasks: Databricks Free Edition pipeline deploy and verify

**Input**: [spec.md](spec.md), [plan.md](plan.md). Lane IDs and acceptance: [docs/plans/dbx-fe/tasks.md › Cloud](../../../docs/plans/dbx-fe/tasks.md#dbx-c01). All tasks depend on [001 T006](../001-local-kafka-spark-delta/tasks.md) (DBX-L05).

## Phase 1: Setup (user-owned accounts)
- [ ] T001 (DBX-C01) Install Databricks CLI ≥ 1.16; `databricks auth login --host <url> --profile <name>`; put the profile in `config/.env.secrets` · `just dbx-validate` passes
- [ ] T002 [P] (DBX-C01) Create the Kafka cluster, topic `market.trades.v1` and an API key; fill `KAFKA_*` in `config/.env.secrets` · `CMP_PROFILE=cloud just produce fixture` delivers 8

## Phase 2: Foundational — the gate
- [ ] T003 [US1] (DBX-C02) `just dbx-secrets && just dbx-deploy && just dbx-probe` · `TCP OK` + `Kafka SASL read OK`. **If it fails: record it in the README status and stop; go to [003](../003-no-kafka-volume-ingest/tasks.md)**

## Phase 3: US2 — fixture parity 🎯 MVP
- [ ] T004 [US2] Decide how the fixture topic is isolated (spec Edge Cases, NEEDS CLARIFICATION) and ask the user
- [ ] T005 [US2] (DBX-C03) `just dbx-run`; check the event log for `valid_trade` · all 5 datasets materialize; `trades_dedup` = 7
- [ ] T006 [US2] (DBX-C04) `just dbx-query` for the BTCUSDT bar · `4 / 0.45 / 70000 / 70010 / 69990`; produce again + run again → unchanged

## Phase 4: US3 — live data and dashboard
- [ ] T007 [US3] (DBX-C05) `CMP_PROFILE=cloud just produce bybit --max-trades 200`, `just dbx-run`, open the dashboard · new bars visible
- [ ] T008 [US3] (DBX-C05) Optionally unpause `cmp-refresh` for the demo, then **pause it again** · the UI shows PAUSED; 1 pipeline, 1 warehouse

## Phase 5: Polish
- [ ] T009 [P] README and lane status: record the probe, parity and dashboard evidence (command + date)
- [ ] T010 [P] Backlog note: per-target bundle vars without defaults (plan › Constitution Check finding); only when a second target is added

## Dependencies
T001, T002 → T003 (gate) → T004 → T005 → T006 → T007 → T008. If T003 fails, go to 003 and skip T005 onward (they run again as [003 T008](../003-no-kafka-volume-ingest/tasks.md)).
