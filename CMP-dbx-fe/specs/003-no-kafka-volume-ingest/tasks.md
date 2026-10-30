---
description: "Tasks for 003 no-Kafka Volume ingest (mapped to DBX-A*)"
---

# Tasks: No-Kafka ingest via UC Volume + Auto Loader

**Input**: [spec.md](spec.md), [plan.md](plan.md), [alt-no-kafka.md](../../../docs/plans/dbx-fe/alt-no-kafka.md). Lane IDs: [tasks.md › DBX-A](../../../docs/plans/dbx-fe/tasks.md#dbx-a). **Start only if [002 T003](../002-dbx-fe-pipeline-deploy/tasks.md) fails.**

## Phase 1: Foundational — sharpen the gate
- [ ] T001 [US1] (DBX-A01) `scripts/dbx_kafka_probe.py`: add the HTTPS REST check, the `probe.control_url` check and `dbutils.fs.ls(landing)`; add `probe.*` to `config.yaml` · one run prints 4 results; the README status records the chosen path

## Phase 2: US2 — local Volume path 🎯 MVP
- [ ] T002 [US2] (DBX-A02) Write the test first: `tests/test_volume_publisher.py` (naming, overwrite idempotency, flush on size/time) · it fails before T003
- [ ] T003 [US2] (DBX-A02) `VolumePublisher` in `src/cmp/publish.py` + `config.yaml: volume.*` · T002 green; no hardcoded scalars
- [ ] T004 [US2] (DBX-A03) `scripts/ship_to_volume.py` + `just ship` (commit after upload, idle exit, poison stop, `--source fixture`) · a crash re-ships the same offsets; `trades_dedup` is unchanged
- [ ] T005 [US2] (DBX-A05) `scripts/local_spark.py --bronze-source volume` + an integration test in `tests/test_integration_kafka.py` · exact bar; re-ship gives no change

## Phase 3: US3 — cloud over the Volume
- [ ] T006 [US3] (DBX-A04) `databricks.yml`: `volumes.landing` + the `bronze_source` var (no default); a `cloudFiles` branch in `pipelines/bronze.py`; `just build` · `just dbx-validate` ok; the sync test is green
- [ ] T007 [US3] Resolve the [data-model NEEDS CLARIFICATION](data-model.md) on the `kafka_*` columns before T006 is merged
- [ ] T008 [US3] (DBX-A06) `just dbx-deploy`, `just ship --source fixture`, `just dbx-run`, `just dbx-query` · the bar equals DBX-C04; a second ship and run gives no change

## Phase 4: US4 — hosted shipper
- [ ] T009 [US4] (DBX-A07) GH Actions `workflow_dispatch` with `timeout-minutes` and a protected `cloud` environment, then `bundle run` · a live refresh works without the laptop

## Backlog (not planned)
- DBX-AB1 (warehouse INSERT) and DBX-AB2 (Zerobus): see [tasks.md](../../../docs/plans/dbx-fe/tasks.md#dbx-ab1)

## Dependencies
T001 → T002 → T003 → T004 → T005 (also needs 001 T006) → T007 → T006 → T008 → T009.
