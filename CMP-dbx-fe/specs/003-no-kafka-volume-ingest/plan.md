# Implementation Plan: No-Kafka ingest via UC Volume + Auto Loader

**Branch**: `feat/cmp-dbx-fe` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

## Summary
A process outside Databricks pulls from Kafka and pushes inbound to a UC Volume. Auto Loader turns the files into `trades_bronze`. The step-by-step design is [alt-no-kafka.md › Steps](../../../docs/plans/dbx-fe/alt-no-kafka.md#steps) and is not repeated here.

## Technical Context
**Language/Version**: Python 3.12

**Primary Dependencies**: databricks-sdk (`WorkspaceClient().files.upload`), confluent-kafka consumer, Auto Loader (`cloudFiles`)

**Storage**: UC Volume `${catalog}.${schema}.landing` in the cloud; `.tmp/landing` locally

**Testing**: unit tests (naming, idempotency, rendering); integration test of the local Volume path; cloud DBX-A06

**Constraints**: inbound REST only; Files API request size unknown; directory-listing mode only (no file notifications)

## Constitution Check
| Gate | Plan |
|---|---|
| I. scalars | `volume.{name,consumer_group,max_batch_bytes,max_wait_s,idle_exit_s}` and `probe.control_url` go in `config.yaml` |
| II. no defaults | `cmp.bronze_source` is a bundle var **with no default**, set per target |
| III. secrets | The SDK profile comes from `DATABRICKS_CONFIG_PROFILE` in `.env.secrets`; the GH Actions secrets go in a protected `cloud` environment |
| IV. local | `.tmp/landing` is under the lane; `--reset` only touches `.tmp/` |
| V. ponytail | One class (`VolumePublisher`) + one script (`ship_to_volume.py`) + one `if` in `bronze.py`. Skipped: Zerobus ([DBX-AB2](../../../docs/plans/dbx-fe/tasks.md#dbx-ab2)), warehouse INSERT ([DBX-AB1](../../../docs/plans/dbx-fe/tasks.md#dbx-ab1)), Kafka REST proxy |
| VI. shared code | The same `parse_trades` and `sql/models`; `build.py` regenerates; the sync test stays green |
| VII. fixture | Local (A05) and cloud (A06), plus a re-ship |
| Free limits | Still 1 pipeline; no warehouse kept awake |

## Project Structure
```text
specs/003-no-kafka-volume-ingest/  spec.md plan.md research.md data-model.md quickstart.md tasks.md contracts/landing-file.md
src/cmp/publish.py                 + VolumePublisher                               (DBX-A02)
scripts/ship_to_volume.py          new                                             (DBX-A03)
pipelines/bronze.py                + cloudFiles branch on cmp.bronze_source        (DBX-A04)
databricks.yml                     + volumes.landing, var bronze_source            (DBX-A04)
scripts/local_spark.py             + --bronze-source volume                        (DBX-A05)
scripts/dbx_kafka_probe.py         + REST/control/Volume checks                    (DBX-A01)
config/config.yaml                 + volume.*, probe.control_url
tests/                             + unit and integration tests for the above
justfile                           + ship
```

## Design decisions
[ADR-0003](../../docs/adr/0003-kafka-from-pipeline-with-volume-fallback.md); alternatives are in [alt-no-kafka.md › Decision](../../../docs/plans/dbx-fe/alt-no-kafka.md#a-decision).

## Complexity Tracking
None.
