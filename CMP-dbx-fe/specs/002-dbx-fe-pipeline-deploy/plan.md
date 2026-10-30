# Implementation Plan: Databricks Free Edition pipeline deploy and verify

**Branch**: `feat/cmp-dbx-fe` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary
The code is in place. What remains is an ordered, gated cloud run:
1. accounts
2. probe (the gate)
3. deploy
4. fixture parity
5. live data and dashboard

No new code is planned unless a step fails. Each failure has a branch in [runbooks/dbx-fe-deploy-verify.md](../../docs/runbooks/dbx-fe-deploy-verify.md).

## Technical Context
**Language/Version**: Python 3.12 locally; serverless pipeline and job environment `4` in the cloud

**Primary Dependencies**: Databricks CLI ≥ 1.16 (bundles), Lakeflow Declarative Pipelines (`pyspark.pipelines`), Kafka source (shaded client), AI/BI dashboards

**Storage**: UC managed tables in `workspace.crypto_pulse`

**Testing**: the probe job; `just dbx-query` against the bar; the pipeline event log

**Target Platform**: Databricks Free Edition (serverless only)

**Constraints**: 1 active pipeline per type; one 2X-Small warehouse; fair-usage quota; egress to trusted domains only

## Constitution Check
| Gate | Status |
|---|---|
| I. scalars | pass for the code. **Finding:** `databricks.yml` has var defaults (`catalog`, `schema`, `secret_scope`), and `just dbx-secrets scope="cmp"` repeats the scope name. That is acceptable while there is one target. Backlog: move them to per-target values when a second target appears (do not fix in this diff) |
| II. no defaults | pass in Python. The bundle var defaults are noted above |
| III. secrets | pass. `.env.secrets` → secret scope; values are never printed (`dbx-secrets` passes them as `--string-value`) |
| IV. local | n/a |
| V. ponytail | pass. One bundle, one target, no CI deploy |
| VI. shared code | pass. `pipelines/bronze.py` imports `cmp.*` from `${workspace.file_path}/src` |
| VII. fixture | **pending**: DBX-C04 |
| Free limits | pass by design: triggered pipeline, `PAUSED` job, starter warehouse lookup |

## Project Structure
```text
specs/002-dbx-fe-pipeline-deploy/  spec.md plan.md research.md quickstart.md tasks.md contracts/bundle-and-secrets.md
databricks.yml  pipelines/{bronze.py,10_silver.sql,20_dedup.sql,30_1m.sql,40_latest.sql}
scripts/dbx_kafka_probe.py  dashboards/market_pulse.lvdash.json  sql/dashboard/history.sql
```
Data model: reused from [001](../001-local-kafka-spark-delta/data-model.md); there is no separate file.

## Design decisions
- [ADR-0003](../../docs/adr/0003-kafka-from-pipeline-with-volume-fallback.md): the pipeline reads Kafka directly, with the Volume push as the fallback
- [ADR-0005](../../docs/adr/0005-triggered-pipeline-paused-job.md): triggered pipeline + paused schedule

## Complexity Tracking
None.
