---
status: accepted
date: 2026-10-30
---
# Dashboard: Streamlit, locally and on Streamlit Community Cloud

## Context and Problem Statement
We need a latest-price and 1m OHLCV view that runs locally against the dev stack and is hosted for free in the cloud. It must be read-only and must flag stale data (F10).

## Considered Options
1. Streamlit (`dashboards/app.py` from the reference, with the GCP and DBX branches removed)
2. Grafana with the ClickHouse plugin (local container / Grafana Cloud free)
3. ClickHouse Cloud SQL console saved queries

## Decision Outcome
Option 1. It is one Python app for both environments, reuses the reference code, and gets a free hosted private app (1 private app at a time, verified 2026-10-30, https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app). It connects as `cmp_dash`, which is SELECT-only on the views. TTL, row limit and `stale_after_s` come from config.

### Consequences
- Good: no extra host, and the same code path is tested locally.
- Bad: Community Cloud egress IPs are dynamic, so the ClickHouse IP list cannot pin them. The mitigation is a strong password plus SELECT-only grants on views.
- Bad: the app sleeps when idle, and the sleep policy is unverified. Fine for a demo.
- Neutral:
  - Option 2 is parked as [CH-LB3](../../../docs/plans/clickhouse/tasks.md#ch-lb3) / [CH-CB4](../../../docs/plans/clickhouse/tasks.md#ch-cb4).
  - Option 3 is the no-host fallback.

## More Information
Plan: [01 §6](../../../docs/plans/clickhouse/01-local-dev-debug.md#l-dashboard) · specs: [local](../../openspec/changes/add-local-redpanda-clickhouse-loop/specs/dashboard/spec.md), [hosted](../../openspec/changes/add-clickhouse-cloud-clickpipes/specs/dashboard/spec.md).
