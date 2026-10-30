# CMP-ch — SaaS deploy & test (Confluent Cloud → ClickPipes → ClickHouse Cloud)

Lane index: [README.md](README.md) · tasks: [tasks.md](tasks.md) · local: [01-local-dev-debug.md](01-local-dev-debug.md)

## Context
The cloud path keeps the local schema and SQL unchanged and swaps only transport and ingest:
- **Transport:** managed Kafka replaces Redpanda.
- **Ingest:** ClickPipes replaces the Python consumer, writing into the same `trades_raw`, with the same MV → `trades_dedup` → views.

Every cloud task depends on the local loop being green first ([CH-L07](tasks.md#ch-l07)). Nothing is provisioned until the user approves the accounts and spend.

## 1. Free-tier / pricing facts (checked 2026-10-30, re-verify before sign-up) <a id="c-facts"></a>

| Service | Fact | Source |
|---|---|---|
| ClickHouse Cloud | Trial: **$300 credits over 30 days**, no card required; afterwards the account moves to pay-as-you-go. **No permanent free tier.** | https://clickhouse.com/pricing |
| ClickHouse Cloud Basic | single replica, 1 AZ, 8–12 GiB total memory, ≤ 1 TB storage, 1 backup / 24 h kept 1 day. ClickPipes is available on Basic. Compute idles to zero; storage is always billed. | https://clickhouse.com/docs/cloud/manage/cloud-tiers, /pricing |
| ClickPipes (Kafka) | **$0.20 / h per compute unit + $0.04 / GB ingested**. Sources: Apache Kafka, Confluent Cloud, Redpanda, MSK, Event Hubs, WarpStream. Formats: JSON, AvroConfluent, Protobuf. | https://clickhouse.com/pricing, https://clickhouse.com/docs/integrations/clickpipes/kafka/reference |
| Confluent Cloud Basic | "First eCKU free, then $0.14/eCKU-h". Ingress and egress $0.05/GB, storage $0.08/GB-month. Trial **$400 / 30 days**; a payment method is required to create resources. | https://www.confluent.io/confluent-cloud/pricing/, https://docs.confluent.io/cloud/current/billing/billing-faq.html |
| Aiven Kafka free | 1 service per org, 5 topics × 2 partitions, no card. Powers off when idle. No Kafka Connect. Docs conflict on throughput (125 vs 250 KiB/s). | https://aiven.io/docs/products/kafka/free-tier/kafka-free-tier |
| Redpanda Serverless | $100 credits / 14 days; add a card within 7 days of expiry or the data is deleted. | https://redpanda.com/product/serverless (via search, not fetched) |
| Streamlit Community Cloud | 1 private app per workspace, unlimited public apps. Apps sleep after 12 h without traffic. Secrets live in app settings and surface as `st.secrets`. Memory is about 1 GB (unverified). | https://docs.streamlit.io/deploy/streamlit-community-cloud |
| Grafana Cloud Free | 3 users; the ClickHouse plugin can be installed. | https://grafana.com/grafana/plugins/grafana-clickhouse-datasource/ |
| Terraform | `ClickHouse/clickhouse` provider: `clickhouse_clickpipe` is GA from **v3.14.0**, and the provider authenticates with a Cloud API key. `confluentinc/confluent` covers env, cluster, topic and keys. | https://clickhouse.com/docs/integrations/clickpipes/programmatic-access/terraform |

**Unverified, to be checked in the console during [CH-C01](tasks.md#ch-c01):**
1. ClickPipes delivery semantics (assumed at-least-once; the dedup design covers it either way).
2. ClickPipes compute-unit size for the smallest replica, i.e. the real hourly cost.
3. ClickPipes JSON string → `Decimal(38,12)` mapping into an *existing* table.
4. `clickhouse_service` resource schema in provider v3.15+, which has breaking changes.
5. Whether a trial service is stopped or deleted at expiry.
6. Confluent Basic exact limits.

**Rough spend for a 7-day demo.** A ClickPipe running 24/7 at 1 CU costs about $34. Kafka for 2 symbols is about 2 GB/day each way, roughly $0.20/day. ClickHouse compute idles. All of this fits inside the two trials.

## 2. Decisions <a id="c-decisions"></a>
1. **Managed Kafka: Confluent Cloud Basic.**
   - It is the same provider as the Databricks lane, so one cluster and one topic can feed both.
   - ClickPipes lists it as a first-class source.
   - Terraform provider exists, and the trial credit covers the demo.
   - Alternatives: Aiven free (no card, but idle power-off and a "generic Kafka" source) and Redpanda Serverless → [CH-CB1](tasks.md#ch-cb1).
2. **Ingest: ClickPipes (Kafka) → existing `trades_raw`.** It is managed and needs no compute of our own. The MV and dedup are reused as-is.
   - The self-hosted consumer from [CH-L06](tasks.md#ch-l06), run on a host against the cloud, is the fallback if ClickPipes cost or the mapping blocks → [CH-CB2](tasks.md#ch-cb2).
   - Kafka engine on Cloud: the docs list it as supported, but ClickHouse recommends ClickPipes, so it is not used.
3. **Producer host: laptop / CI, bounded runs.** `just produce bybit <N>` runs locally against `profile=cloud`, plus a `workflow_dispatch` GH Actions job with a timeout from config.
   - An always-on producer (Hetzner, Fly, Render) → [CH-CB3](tasks.md#ch-cb3).
4. **Dashboard: Streamlit Community Cloud**, the same `dashboards/app.py` as local. It reads with the read-only `cmp_dash` user.
   - Fallback with no extra host: ClickHouse Cloud SQL console saved queries. Grafana Cloud → [CH-CB4](tasks.md#ch-cb4).
5. **IaC: Terraform, local state (gitignored) in `CMP-ch/infra/cloud/`.** It covers the Confluent env, cluster, topic and keys, plus the ClickHouse service and ClickPipe.
   - Why: `terraform destroy` makes teardown deterministic, which is the main cost guardrail.
   - Account sign-up and the Cloud API key are created by hand ([CH-C01](tasks.md#ch-c01)).
6. **Cloud verification = local assertion.** The same `sql/checks/fixture_1m.sql` runs on an isolated database fed by its own topic ([§5](#c-verify)).

## 3. Secrets & config <a id="c-secrets"></a>
→ [CH-C01](tasks.md#ch-c01)
- `config/.env.secrets` (gitignored) holds these keys; `.env.secrets.demo` lists the same keys with empty values:
  - `KAFKA_BOOTSTRAP`, `KAFKA_API_KEY`, `KAFKA_API_SECRET`
  - `CLICKHOUSE_URL`, `CLICKHOUSE_USER`, `CLICKHOUSE_PASSWORD`, `CLICKHOUSE_DASH_PASSWORD`
  - `CLICKHOUSE_CLOUD_ORG_ID`, `CLICKHOUSE_CLOUD_API_KEY_ID`, `CLICKHOUSE_CLOUD_API_KEY_SECRET`
  - `CONFLUENT_CLOUD_API_KEY`, `CONFLUENT_CLOUD_API_SECRET`
- `just secrets-pull` fills it from Bitwarden with `bw get item <name>`. The item names live in `config/config.yaml: secrets.bw_items`. Run `bw unlock` first; the session token is never written to disk.
- Terraform gets credentials only from `TF_VAR_*`, exported by `just tf-*` from `.env.secrets`. There is no `terraform.tfvars` holding secrets, and the state file is gitignored and treated as a secret.
- Least-privilege ClickHouse users, created by `sql/clickhouse/090_users.sql`, with passwords passed as parameters, never literals:
  - `cmp_ingest`: INSERT on `trades_raw`, used by ClickPipes
  - `cmp_dash`: SELECT on the views only
- The admin user runs DDL only.
- CI uses GH Actions secrets with the same names. Streamlit uses `st.secrets` mapped into `os.environ` at startup, with a strict read.
- `profiles.cloud` in config sets `kafka.security_protocol: SASL_SSL` and `sasl_mechanism: PLAIN`. No endpoint or ID is ever written in code.

## 4. Provision & deploy <a id="c-deploy"></a>
1. **Accounts** → [CH-C01](tasks.md#ch-c01):
   - The user signs up for the ClickHouse Cloud trial and Confluent Cloud, and creates the org-level API keys.
   - Store them in `bw`.
   - Verify the unverified facts from [§1](#c-facts) and record them with dates in `CMP-ch/docs/cloud-facts.md`.
2. **Confluent via TF** → [CH-C02](tasks.md#ch-c02):
   - Create env `cmp`, a Basic cluster (region next to the CH service) and topics `market.trades.v1` and `market.trades.verify.v1`.
   - Create two service-account keys: producer (WRITE) and clickpipe (READ, plus group `clickpipes-*`).
   - `just tf-plan` / `tf-apply`.
3. **ClickHouse service via TF** → [CH-C03](tasks.md#ch-c03):
   - Basic tier, idle scaling on, same cloud and region as Kafka.
   - IP access list: the dev IP and CI egress. Streamlit Cloud IPs are dynamic, so `cmp_dash` gets a strong password and SELECT-only grants. This trade-off is documented.
   - Then `CMP_ALLOW_REMOTE_DDL=YES just ch-setup` applies the same `sql/clickhouse/*.sql` plus `090_users.sql`.
4. **ClickPipe via TF** → [CH-C04](tasks.md#ch-c04):
   - `clickhouse_clickpipe` (provider ≥ 3.14): type `confluent`, topic `market.trades.v1`, JSON, existing table `market_pulse.trades_raw`, column mapping 1:1, auth SASL PLAIN with the clickpipe key.
   - If TF cannot target an existing table, create it in the console and import it into state.
5. **Producer** → [CH-C05](tasks.md#ch-c05): `CMP_PROFILE=cloud just produce bybit <N>`. The GH Actions `produce-bybit.yml` (`workflow_dispatch`, `timeout-minutes` from repo vars) runs the same recipe.
6. **Dashboard** → [CH-C07](tasks.md#ch-c07):
   - Deploy `CMP-ch/dashboards/app.py` from the GitHub repo to Streamlit Community Cloud as the 1 allowed private app.
   - Put the secrets in the app settings.
   - Check the stale badge and the latest price.

## 5. Cloud verification <a id="c-verify"></a>
→ [CH-C06](tasks.md#ch-c06)

The fixture's 10:00 minute is 2026-10-30 10:00 UTC, which collides with live data from that date. Verification is therefore isolated:
1. `just cloud-verify` makes sure the DB `market_pulse_verify` exists, using the same DDL files with `{db}=market_pulse_verify`.
2. A second ClickPipe `cmp-verify` (TF, `count=var.verify_enabled`) reads `market.trades.verify.v1` into it.
3. Produce the fixture to the verify topic, wait until `count() FROM trades_raw ≥ 8` (timeout `cloud.verify_timeout_s`), and run `sql/checks/fixture_1m.sql`. The expected bar is the same as local: `4 / 0.45 / 70000 / 70010 / 69990`.
4. Re-produce the fixture. Raw grows to 16, while `uniqExact` and the bar stay unchanged (idempotency).
5. `TF_VAR_verify_enabled=false just tf-apply` removes the verify ClickPipe so it stops billing, and `TRUNCATE` cleans the verify DB.

## 6. CI smoke <a id="c-ci"></a>
→ [CH-C08](tasks.md#ch-c08)
- `.github/workflows/cmp-ch-cloud-smoke.yml` uses `workflow_dispatch` only, never runs on push, and runs in a `cloud` environment that requires a manual reviewer.
- Steps: `uv sync` → secrets from GH env → `just cloud-verify` → upload the run log artifact (redacted).
- The hermetic PR CI from [CH-L11](tasks.md#ch-l11) stays docker-only.

## 7. Cost guardrails & teardown <a id="c-cost"></a>
→ [CH-C09](tasks.md#ch-c09)
- Turn on spend notifications in both consoles. Exact options are unverified; record what exists in `cloud-facts.md`.
- ClickHouse: Basic tier, idle scaling on, minimal ClickPipe replicas. **Pause the main ClickPipe when not demoing** (`just cloud-pause` → TF `stopped` state or console).
- Confluent: Basic only, retention on our topics capped in config (`kafka.cloud_retention_ms`), 1 partition.
- `just cloud-cost`: read-only, prints current usage via the ClickHouse Cloud API org cost endpoint and the Confluent billing CLI. Run it daily during the trial.
- Teardown: `just cloud-down` runs `terraform destroy`, then you delete the API keys in both consoles by hand and confirm $0 burn in billing the next day.
- Calendar reminder: 2 days before either trial ends.

**Done when:** `just cloud-verify` passes twice (bar plus idempotency) on the verify DB, the live bars are visible in the Streamlit Cloud app, `cloud-cost` reports usage within the trials, and `cloud-down` leaves both consoles empty.
