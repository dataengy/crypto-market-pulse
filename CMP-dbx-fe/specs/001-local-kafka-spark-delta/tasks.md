---
description: "Tasks for 001 local Kafka → Spark → Delta (mapped to DBX-L*)"
---

# Tasks: Local Kafka → Spark → Delta loop

**Input**: [spec.md](spec.md), [plan.md](plan.md). Lane IDs and acceptance live in [docs/plans/dbx-fe/tasks.md](../../../docs/plans/dbx-fe/tasks.md). A box is ticked only after its check has run (constitution workflow, step 5).

Format: `[ID] [P?] [Story] (lane ID) Description · check`

## Phase 1: Setup
- [x] T001 [US1] (DBX-L01) uv project, `justfile`, `config/config.yaml`, `config/.env.common`, `.env.secrets.demo`, strict `src/cmp/settings.py` · `just test` → `test_strict_config_and_env`

## Phase 2: Foundational
- [x] T002 [US1] (DBX-L02) Copy `domain.py`, `bybit_ws.py`, `publish.py` and `reference.py`; move the WS/Kafka scalars to config · `tests/test_domain.py` green; `find_hardcoded_scalars.py src scripts`
- [x] T003 [US2] (DBX-L03) `sql/models/*_select.sql` + `valid_trade.sql`, `src/cmp/sql_models.py`, `scripts/build.py` · `just verify` gives no diff

## Phase 3: US4 — Spark + Delta without Kafka (P2, done first: no Docker)
- [x] T004 [US4] (DBX-L04) `src/cmp/bronze.py`, `scripts/local_spark.py` (`spark_session`, `build_models`, `run`), `tests/test_spark_models.py` · `uv run pytest -m spark`: exact bar, malformed row dropped, replay unchanged

## Phase 4: US3 — Kafka E2E 🎯 MVP
- [x] T005 [US3] (DBX-L05) Get a working Docker daemon (Docker Desktop restart, or `colima start`), then `just up` · `docker ps` shows `cmp-dbx-redpanda` as healthy (done 2026-10-30)
- [x] T006 [US3] (DBX-L05) `just it` (`tests/test_integration_kafka.py`) · 8 → 8 (restart) → 16 bronze, dedup 7, exact bar
- [x] T007 [P] [US3] (DBX-L05) Manual loop: `just produce fixture && just spark --reset`, then `just spark` · the printed `trades_1m` matches the bar

## Phase 5: US5 — MiniLake (P3)
- [x] T008 [US5] (DBX-L06) `just minilake-smoke` · `MiniLake smoke PASS`, dedup = 7
- [x] T009 [US5] (DBX-L06) Record the printed `DIALECT GAP` list in `README.md › Debugging` (one line, no SQL fork)

## Phase 6: Polish
- [x] T010 [P] Update `README.md › Status` and the [lane README status](../../../docs/plans/dbx-fe/README.md#status-2026-10-30) with the T006/T008 results (evidence: command + date; done in `ccb8b63`)

## Dependencies
T001 → T002 → T003 → T004 → T005 → T006 → T008. T007 and T010 can run once T006 is done. Cloud work ([spec 002](../002-dbx-fe-pipeline-deploy/tasks.md)) depends on T006.
