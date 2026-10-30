# Design

## Context

See [proposal.md](proposal.md) for why. The detailed plan already exists. This design only fixes the boundaries and links to it:
- layout: [01 §1](../../../../docs/plans/clickhouse/01-local-dev-debug.md#l-layout)
- runtime: [§2](../../../../docs/plans/clickhouse/01-local-dev-debug.md#l-runtime)
- schema: [§4](../../../../docs/plans/clickhouse/01-local-dev-debug.md#l-schema)
- consumer: [§5](../../../../docs/plans/clickhouse/01-local-dev-debug.md#l-consumer)
- faults: [§7](../../../../docs/plans/clickhouse/01-local-dev-debug.md#l-faults)

The reference code has known defects, listed in the 01 Context table. They are fixed when the code is copied, not carried over. The architecture diagram is in [docs/design/architecture.md](../../../docs/design/architecture.md).

## Goals / Non-Goals

**Goals:**
- One SQL set (`sql/clickhouse/*.sql`, `{db}` placeholder) that local and cloud apply unchanged.
- The ingest boundary is `trades_raw`. Everything downstream (MV, dedup, views, dashboard) is identical whether a Python consumer or ClickPipes writes it.
- Reuse before writing:
  - copy `domain.py`, `bybit_ws.py`, `publish.py`, `reference.py` and the fixture from `CMP-dbx-fe/src/cmp` and `CMP-dbx-fe/tests/fixtures`, which already have their scalars externalized
  - adapt `settings.py` from the same lane

**Non-Goals:**
- Kafka engine ingest: [CH-LB1](../../../../docs/plans/clickhouse/tasks.md#ch-lb1)
- Materialized aggregates: CH-LB2
- Grafana: CH-LB3
- WS-disconnect (F6) and schema-drift (F8) faults
- Any cloud resource

## Decisions

| # | Decision | ADR |
|---|---|---|
| 1 | Python consumer (`confluent-kafka` + `clickhouse-connect`) with insert-then-commit; Kafka engine rejected for now | [0001](../../../docs/adr/0001-python-consumer-over-kafka-engine.md) |
| 2 | `trades_raw` MergeTree → MV → `trades_dedup` ReplacingMergeTree; views read `FINAL` with `do_not_merge_across_partitions_select_final=1` | [0002](../../../docs/adr/0002-replacingmergetree-with-final-views.md) |
| 3 | Streamlit dashboard, read-only `cmp_dash` user; the same app deploys to Community Cloud | [0004](../../../docs/adr/0004-streamlit-dashboard.md) |
| 4 | Copy shared code from `CMP-dbx-fe` instead of making a shared package | none: a two-lane copy is cheaper than a package. ponytail: promote to a shared package only if a third lane copies it |
| 5 | Integration tests run on an isolated `market_pulse_it_<pid>` DB and topic, dropped afterwards, because the fixture minutes collide with live data from 2026-10-30 | none |

## Risks / Trade-offs

- [RMT without a version column keeps the *last* inserted copy, so `max_ingest_lag_ms` may reflect the replay arrival] → documented deviation. OHLCV is unaffected (ADR-0002).
- [`FINAL` cost grows with unmerged parts] → it is negligible at 2 symbols. Watch it with `dbg-sys-parts`; the materialized mart is CH-LB2.
- [Docker daemon unavailable or sandboxed, as in the sibling lane] → unit tests stay hermetic. `just it` is marked `needs_docker`, and an agent asks for a sandbox bypass before `just up`.
- [Reusing a shared ClickHouse could collide with someone's DB] → only the project-owned `market_pulse_dev` / `market_pulse_it_*` databases are created and dropped.

## Migration Plan

This is a new directory, so there is nothing to migrate. Rollback = delete `CMP-ch/` code paths. `just down` never removes volumes.
