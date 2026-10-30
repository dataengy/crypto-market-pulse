# Design

## Context

See [proposal.md](proposal.md) for why. The full plan is in [02-cloud-deploy-test.md](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md):
- decisions: [§2](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md#c-decisions)
- secrets: [§3](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md#c-secrets)
- deploy: [§4](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md#c-deploy)
- verify: [§5](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md#c-verify)
- cost: [§7](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md#c-cost)

The local change supplies the SQL, the producer, the assertion and the dashboard, which are reused unchanged.

## Goals / Non-Goals

**Goals:**
- Only transport and ingest change versus local. The cloud gate is the same SQL check, run against an isolated DB.
- Teardown is deterministic (`terraform destroy`), and that is the main cost guardrail.

**Non-Goals:**
- An always-on producer: CH-CB3
- Grafana: CH-CB4
- Alternative Kafka providers: CH-CB1
- Multi-region or HA
- Remote TF state

## Decisions

| # | Decision | Why / alternatives | ADR |
|---|---|---|---|
| 1 | ClickPipes (Kafka/Confluent source) → existing `trades_raw` | Managed, with no compute of our own. The Kafka engine on Cloud is supported but not recommended. The Python consumer on a host is the fallback (CH-CB2) | [0003](../../../docs/adr/0003-clickpipes-for-cloud-ingest.md) |
| 2 | Confluent Cloud Basic | The same provider as the dbx lane, so one topic can feed both. It is a first-class ClickPipes source and has a TF provider. Aiven free and Redpanda Serverless are the alternatives (CH-CB1) | 0003 |
| 3 | Terraform with `ClickHouse/clickhouse` ≥ 3.14 (`clickhouse_clickpipe`) and `confluentinc/confluent`, local state | Reproducible apply and destroy. Sign-up and org API keys stay manual | none |
| 4 | Producer runs on the laptop or a `workflow_dispatch` job, bounded | No always-on host needed for a demo | none |
| 5 | Streamlit Community Cloud, 1 private app | The same app as local. Its egress IPs are dynamic, so `cmp_dash` is SELECT-only with a strong password | [0004](../../../docs/adr/0004-streamlit-dashboard.md) |
| 6 | Verify via a second, count-gated ClickPipe on `market.trades.verify.v1` → `market_pulse_verify` | The fixture minutes collide with live 2026-10-30 data | none |

## Pricing facts

Checked by this change on **2026-10-30**. Re-check in CH-C01 before sign-up.

| Fact | Status | Source |
|---|---|---|
| ClickHouse Cloud trial: $300 credits / 30 days, whichever ends first, then pay-as-you-go. Basic compute $0.2181/unit-h (AWS us-east-1). 1 unit = 8 GiB / 2 vCPU | **verified** 2026-10-30 | https://clickhouse.com/pricing |
| ClickPipes streaming: $0.20 per compute-unit-hour + $0.04/GB ingested. Replica XS = 0.0625 CU = $0.0125/h | **verified** 2026-10-30 | https://clickhouse.com/docs/products/cloud/reference/billing/clickpipes/clickpipes-for-streaming-and-object-storage |
| ClickPipes **default** replica size: the same page says XS (0.0625 CU) in one place and 0.25 CU (2 GiB) in its FAQ | **conflicting**: read it off the console in CH-C01 | same |
| Confluent Basic: first eCKU free, then $0.14/eCKU-h. $0.05/GB in/out, $0.08/GB-month storage | **verified** 2026-10-30 | https://www.confluent.io/confluent-cloud/pricing/ |
| Confluent trial $400 / 30 days; a payment method is needed to create resources | unverified (from the plan) | https://docs.confluent.io/cloud/current/billing/billing-faq.html |
| Streamlit Community Cloud: 1 private app at a time | **verified** 2026-10-30 | https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app |
| Streamlit sleep after 12 h without traffic; ~1 GB memory | unverified | https://docs.streamlit.io/deploy/streamlit-community-cloud |
| ClickPipes delivery semantics, JSON string → `Decimal(38,12)` into an existing table, trial service fate at expiry, `clickhouse_service` schema in provider ≥ 3.15 | unverified: check in CH-C01 / CH-C04 | [02 §1](../../../../docs/plans/clickhouse/02-cloud-deploy-test.md#c-facts) |

**Correction to the plan's spend estimate:** 02 §1 assumes a 24/7 pipe at 1 CU, about $34 per 7 days. At the documented sizes it costs:
- XS: 7 × 24 × $0.0125 ≈ **$2.10**
- 0.25 CU: 7 × 24 × $0.05 ≈ **$8.40**

Plus about $0.04 × GB ingested. Either way it fits inside the trial.

## Risks / Trade-offs

- [ClickPipes cannot map a JSON string to Decimal in an existing table] → CH-C04 records this, and CH-CB2 consumer fallback takes over. The schema does not change.
- [The trial expires with resources running] → `cloud-cost` runs daily, a calendar reminder is set 2 days before expiry, and `cloud-down` destroys everything.
- [Streamlit IPs are dynamic, so the service must accept a broad IP list] → `cmp_dash` is SELECT-only on the views and has a strong password. Documented in ADR-0004.
- [Terraform provider breaking changes (≥ 3.15)] → pin the provider version in `required_providers`.

## Migration Plan

1. CH-C01 (approval) → C02/C03 → C04 → C05 → C06 (gate) → C07/C08 → C09.
2. Rollback at any step: `just cloud-pause` (stops billing ingest), or `just cloud-down` to destroy everything. The local loop is unaffected.
