# Pub/Sub → BigQuery subscription + views — Shaping Notes

## Scope
- **GCP-C03:** apply the foundation plan; create the views in both envs
- **GCP-C04 (laptop part):** prove that `smoke-sa` impersonation works with no key files

## Decisions
**Ingest path**
- BigQuery subscription → raw table → views. No consumer compute.
- Rationale and alternatives: [ADR-0001](../../../docs/adr/0001-bq-subscription-over-dataflow.md).

**Views**
- `sql_apply.py --profile cloud --env <env>` from the local lane: one renderer and one dialect for emulator and cloud.
- Terraform does **not** manage the views. Two owners for one DDL would drift.

**Partition pruning**
- The views filter `publish_time` (local-lane SQL, [L05](../../../../../docs/plans/gcp/tasks.md#gcp-l05)).
- `require_partition_filter` stays off so the Looker views work. `ponytail:` turn it on if the bytes scanned per dashboard refresh grow past the free 1 TiB/month.

**Subscription health**
- Accept only `bigqueryConfig.state == ACTIVE`.
- `PERMISSION_DENIED`, `NOT_FOUND` and `SCHEMA_MISMATCH` are failure modes ([API states](https://docs.cloud.google.com/pubsub/docs/reference/rest/v1/projects.subscriptions), verified 2026-10-30).

## Context
- **Visuals:** [architecture.md](../../../docs/design/architecture.md).
- **References:** [references.md](references.md).
- **Product alignment:** roadmap phase 2.

## Standards Applied
See [standards.md](standards.md).
