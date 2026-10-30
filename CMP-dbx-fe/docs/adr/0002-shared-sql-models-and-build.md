# 0002 — One set of SQL models, generated Lakeflow SQL and dashboard

- Status: accepted (implemented, DBX-L03)
- Date: 2026-10-30
- Spec: [001](../../specs/001-local-kafka-spark-delta/spec.md), [contract](../../specs/001-local-kafka-spark-delta/contracts/sql-model.md)

## Context and Problem Statement
The same transformations run in local Spark, MiniLake (DuckDB) and Lakeflow. Hand-copied SQL drifts, and the silver quality rule is easy to forget in one of the three places.

## Considered Options
1. Portable `SELECT` files with one `{{source}}` placeholder + `scripts/build.py`, which wraps them into `CREATE OR REFRESH …` and builds `.lvdash.json`
2. Hand-written Lakeflow SQL, with local Spark parsing it
3. dbt (`dbt-databricks` + `dbt-spark`)

## Decision Outcome
Chosen: **option 1**. It is about 20 lines of renderer, there is no new dependency, and `test_generated_files_are_in_sync` together with `just verify` makes drift a test failure. `valid_trade.sql` is the single quality rule: `EXPECT … DROP ROW` in the cloud and `WHERE` locally.

### Consequences
- Good: one edit point. Generated files carry a "do not edit" header.
- Bad: a stale generated file is a classic failure; the fix is `just build`. See [runbook](../runbooks/local-dev-debug.md#stale-generated-files).
- Neutral: dbt stays out of scope. It would add a tool and two adapters, and it can't express Lakeflow streaming tables.
