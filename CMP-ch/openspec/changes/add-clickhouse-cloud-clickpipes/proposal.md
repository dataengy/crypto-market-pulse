# Proposal

## Why

The lane has to run as a hosted demo without a laptop. The cloud path keeps the local schema and gate and only replaces transport and ingest: Redpanda becomes Confluent Cloud, and the Python consumer becomes ClickPipes ([02 Context](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md)).

**Depends on** `add-local-redpanda-clickhouse-loop` reaching [CH-L07](../../../../docs/plans/clickhouse/tasks.md#ch-l07). **Needs user approval** for the sign-ups, the Confluent payment method and any spend.

## What Changes

- Secrets live in `bw`, are pulled with `just secrets-pull`, and are re-checked against the facts below. Covers CH-C01.
- Terraform (local state, gitignored) for the Confluent env, Basic cluster, topics and keys, plus the ClickHouse Cloud Basic service and IP list. The shared DDL and least-privilege users are applied with the remote-DDL guard. Covers CH-C02 and CH-C03.
- A ClickPipe from Confluent into the existing `trades_raw` (JSON, SASL PLAIN). Covers CH-C04.
- `CMP_PROFILE=cloud just produce …` and a bounded `workflow_dispatch` producer job. Covers CH-C05.
- `just cloud-verify`: the same fixture assertion on an isolated verify DB, topic and pipe. Covers CH-C06.
- A Streamlit Community Cloud deploy. Covers CH-C07.
- A manual cloud CI smoke. Covers CH-C08.
- Cost guardrails, pause and teardown. Covers CH-C09.

Out of scope:
- Kafka provider alternatives: [CH-CB1](../../../../docs/plans/clickhouse/tasks.md#ch-cb1)
- Consumer fallback: CH-CB2, which is triggered only if ClickPipes cost or mapping blocks
- Always-on producer: CH-CB3
- Grafana Cloud: CH-CB4

## Capabilities

### New Capabilities
- `cloud-deploy`: approval-gated provisioning, secrets handling, least-privilege users, isolated cloud verification, manual CI smoke, cost guardrails and teardown.

### Modified Capabilities
These capabilities are introduced by the local change; this change adds requirements to them (ADDED deltas). Archive the local change first.
- `ingest`: ClickPipes path into `trades_raw`; cloud producer profile.
- `dashboard`: hosted deployment with platform secrets.

## Impact

- New: `CMP-ch/infra/cloud/` (TF), `.github/workflows/cmp-ch-*.yml`, `docs/cloud-facts.md`.
- External accounts: ClickHouse Cloud, Confluent Cloud and Streamlit Community Cloud. Pricing status is in [design.md](design.md#pricing-facts).
- Decision: [ADR-0003](../../../docs/adr/0003-clickpipes-for-cloud-ingest.md). Runbook: [cloud-deploy-verify.md](../../../docs/runbooks/cloud-deploy-verify.md).
