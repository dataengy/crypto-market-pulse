# DBX-B5 — Managed Kafka provider choice

**Goal:** pick the cloud Kafka by cost, free-tier terms, SASL/PLAIN support and **reachability from Free Edition** (DBX-C02). ← [tasks](../../../docs/plans/dbx-fe/tasks.md#dbx-b5)

| Provider | Check |
|---|---|
| Confluent Cloud (Basic) | current default; trial credits vs real free tier; `*.confluent.cloud` egress from Free Edition |
| Aiven for Kafka (free plan) | throughput limits; SASL vs mTLS-only (we need SASL/PLAIN or SCRAM → add `sasl_mechanism` SCRAM support) |
| Redpanda Serverless | free-trial terms; SASL/SCRAM |
| AWS MSK Serverless | IAM auth only → not with plain Spark Kafka JAAS; likely ✗ |
| GCP Managed Kafka | SASL/OAUTHBEARER via Google creds → extra login module; likely ✗ for now |
| Yandex Cloud / MWS Managed Kafka | SASL/SCRAM + CA cert; egress from Free Edition |
| Self-hosted Redpanda on Hetzner | cheapest always-on; TLS + SASL setup, our own ops |

**Steps:** [ ] verify each row's free-tier terms with current docs (cite date) · [ ] run DBX-C02 against the top 2 · [ ] add `SCRAM-SHA-512` to `cmp.kafka` if the winner needs it · [ ] record the decision in `docs/plans/dbx-fe/plan.md`.
