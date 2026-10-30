# 0005 — Triggered serverless pipeline + refresh job deployed PAUSED

- Status: accepted. It is in `databricks.yml` and not yet deployed (DBX-C03, DBX-C05).
- Date: 2026-10-30
- Spec: [002](../../specs/002-dbx-fe-pipeline-deploy/spec.md)

## Context and Problem Statement
Free Edition has a fair-usage quota, one active pipeline per type, and one 2X-Small warehouse. A continuous pipeline or an always-on schedule would burn the quota while nobody is looking at the dashboard.

## Considered Options
1. `continuous: false` + job `cmp-refresh` (every 15 min) deployed `pause_status: PAUSED`
2. A continuous pipeline
3. A triggered pipeline with an active schedule

## Decision Outcome
Chosen: **option 1**. Refreshes are on demand (`just dbx-run`). The schedule is unpaused only for a live demo and paused again afterwards (DBX-C05). A latency of minutes is enough for a 1-minute-bar dashboard.

### Consequences
- Good: there is no idle compute and it stays within Free limits.
- Bad: the dashboard is only as fresh as the last refresh. Someone has to remember to pause after the demo (in the [runbook](../runbooks/dbx-fe-deploy-verify.md#6-live-data-dashboard-and-cleanup)).
- The cron and timezone are in `databricks.yml`. Move them to bundle vars with no default if a second target appears.
