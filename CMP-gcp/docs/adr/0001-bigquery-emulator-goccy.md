---
status: accepted
date: 2026-10-30
deciders: Nikolay (owner), planning agent
---
# 0001 — Local BigQuery = goccy bigquery-emulator, not DuckDB

## Context and Problem Statement
The SQL path (`sql/bigquery/*.sql`) has to run locally with no GCP account. It uses `SAFE.PARSE_JSON`, `JSON_VALUE`, `BIGNUMERIC`, `TIMESTAMP_MILLIS`, `QUALIFY` and `ARRAY_AGG(... LIMIT 1)[OFFSET(0)]`. Which local engine should run it?

## Decision Drivers
- One dialect for local and cloud (sibling rule: "don't fork the SQL").
- The same client code path (`google-cloud-bigquery` with `client_options.api_endpoint`).
- Runs on arm64 Mac, localhost only.

## Considered Options
1. `ghcr.io/goccy/bigquery-emulator` (GoogleSQL via go-zetasqlite)
2. DuckDB stand-in with a dialect layer
3. Real BigQuery sandbox/free tier

## Decision Outcome
Chosen: **option 1**. It runs GoogleSQL, speaks the BigQuery REST/insertAll API (the plan also records Storage Read/Write support), and the image is multi-arch.

### Consequences
- Good: SQL is byte-identical locally and in the cloud; `sql_apply.py` has a single code path.
- Bad: it is beta with a single maintainer. Function gaps are likely.
- Mitigation: the [GCP-L05](../../../docs/plans/gcp/tasks.md#gcp-l05) probe is the compatibility gate. Any gap gets `skip_on_emulator` plus an entry in `docs/emulator-gaps.md`, and that query is verified in the cloud at [GCP-C05](../../../docs/plans/gcp/tasks.md#gcp-c05). The SQL is never edited to suit the emulator.
- Fallback: option 2 as backlog [GCP-L14](../../../docs/plans/gcp/tasks.md#gcp-l14), only if the gaps block FX.

### Confirmation
`just sql-apply` against the emulator either succeeds for every file or lists the skipped ones. [Story 2.2](../stories/2.2.story.md).

## Pros and Cons of the Options
- **DuckDB**: fast and already on the host, but it needs a forked dialect for 6+ functions, so a local pass would prove nothing about the cloud.
- **Real BigQuery**: true fidelity, but needs an account, auth and spend. That is out of scope for local ([`../../deploy/`](../../deploy/README.md)).

## More Information
[Plan §4](../../../docs/plans/gcp/01-local-dev-debug.md#s4). Unverified until L05: support for `SAFE.PARSE_JSON`, `QUALIFY`, `BIGNUMERIC` and `ARRAY_AGG … LIMIT`.
