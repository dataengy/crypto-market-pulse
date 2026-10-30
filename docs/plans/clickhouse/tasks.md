# CMP-ch tasks

Plans: [01-local-dev-debug.md](01-local-dev-debug.md) · [02-cloud-deploy-test.md](02-cloud-deploy-test.md) · index: [README.md](README.md)

Implementation dir: `./CMP-ch/` · branch per task group, e.g. `feat/cmp-ch-local`, `feat/cmp-ch-cloud`.

## Local (CH-L)

<a id="ch-l01"></a>
- [ ] **CH-L01** Scaffold `CMP-ch/`: uv + py3.12, justfile, config files, strict settings
  - goal: a project skeleton where a missing key fails with the key name and the file to fill
  - depends: —
  - acceptance: `uv sync` ok; `just test` runs the settings-strictness tests (missing yaml key / env var → error naming the file); no `getenv(..., default)` in `src/`
  - plan: [01-local-dev-debug.md#l-layout](01-local-dev-debug.md#l-layout)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l02"></a>
- [ ] **CH-L02** Copy core (domain, bybit_ws, publish, fixture, reference OHLCV) and externalize scalars
  - goal: the source domain logic with no hardcoded WS URL, timeouts, ping, backoff, ts bounds or SASL mechanism
  - depends: CH-L01
  - acceptance: copied `test_domain` passes; `reference.py` gives BTCUSDT 10:00 = 4 / 0.45 / 70000 / 70010 / 69990; `find_hardcoded_scalars.py --exit-nonzero-on-find` clean on `src/ scripts/`
  - plan: [01-local-dev-debug.md#l-layout](01-local-dev-debug.md#l-layout)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l03"></a>
- [ ] **CH-L03** Runtime discovery + project-owned compose (Redpanda + ClickHouse)
  - goal: reuse existing compatible services; otherwise run localhost-only, labelled `cmp-ch` containers
  - depends: CH-L01
  - acceptance: `just inventory` is read-only; `just up` is idempotent (a second run creates nothing new); healthchecks green; `just down` never uses `-v` and skips unlabelled containers; chosen runtime recorded
  - plan: [01-local-dev-debug.md#l-runtime](01-local-dev-debug.md#l-runtime)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l04"></a>
- [ ] **CH-L04** Schema & setup: raw MergeTree, RMT dedup + MV, `trades_1m` / `trades_latest` views over `FINAL`
  - goal: query-level-exact dedup with no full-raw window scan
  - depends: CH-L03
  - acceptance: `just ch-setup` is idempotent; it refuses a non-local host without `CMP_ALLOW_REMOTE_DDL=YES`; `{db}` render unit test; Decimal overflow test
  - plan: [01-local-dev-debug.md#l-schema](01-local-dev-debug.md#l-schema)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l05"></a>
- [ ] **CH-L05** Producer: `--source fixture|bybit`, `--sink kafka|stdout` (required args)
  - goal: deterministic fixture replay and a bounded live Bybit run into Kafka
  - depends: CH-L02, CH-L03
  - acceptance: `just produce fixture` → `rpk topic describe` shows +8 messages; `just produce bybit 50` publishes 50 valid events; a delivery failure exits non-zero
  - plan: [01-local-dev-debug.md#l-producer](01-local-dev-debug.md#l-producer)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l06"></a>
- [ ] **CH-L06** Python consumer: batch insert → sync commit, idle exit, poison stop, `--crash-after-insert`
  - goal: at-least-once Kafka → `trades_raw`, the same table ClickPipes targets
  - depends: CH-L04, CH-L05
  - acceptance: consumes 8 fixture messages and exits after `idle_exit_s`; a poison message → non-zero exit with the offset uncommitted; the crash hook works
  - plan: [01-local-dev-debug.md#l-consumer](01-local-dev-debug.md#l-consumer)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l07"></a>
- [ ] **CH-L07** Integration test + `just verify`: fixture assertion and idempotent rerun on an isolated DB
  - goal: the local E2E gate that every cloud task depends on
  - depends: CH-L06
  - acceptance: `just it` asserts 4 / 0.45 / 70000 / 70010 / 69990, `uniqExact=7` vs raw `8`; after replay and rerun the bar is unchanged; the test DB and topic are dropped
  - plan: [01-local-dev-debug.md#l-verify](01-local-dev-debug.md#l-verify)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l08"></a>
- [ ] **CH-L08** Fault injection F1–F5, F7, F10 with run records
  - goal: evidence for the dedup, offset, poison and late-event policies
  - depends: CH-L07, CH-L09 (for F10)
  - acceptance: each row has a filled run record (UTC, SHA, command, expected / actual, PASS / FAIL) in `CMP-ch/docs/evidence/`
  - plan: [01-local-dev-debug.md#l-faults](01-local-dev-debug.md#l-faults)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l09"></a>
- [ ] **CH-L09** Streamlit dashboard (ClickHouse only, read-only user, stale badge)
  - goal: latest price, OHLCV, VWAP and volume charts from the views
  - depends: CH-L07
  - acceptance: `just dashboard` shows the fixture bars; the stale badge appears after `stale_after_s`; TTL and limit come from config
  - plan: [01-local-dev-debug.md#l-dashboard](01-local-dev-debug.md#l-dashboard)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l10"></a>
- [ ] **CH-L10** Debug recipes: `dbg-rpk-*`, `dbg-ch`, `dbg-sys-*`, `dbg-counts`
  - goal: one-command visibility into topic, lag, parts, query_log and errors
  - depends: CH-L03
  - acceptance: each recipe runs against the local stack and is read-only (except `dbg-rpk-produce`)
  - plan: [01-local-dev-debug.md#l-debug](01-local-dev-debug.md#l-debug)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

<a id="ch-l11"></a>
- [ ] **CH-L11** Hermetic PR CI: unit + integration with service containers
  - goal: green CI without any cloud secrets
  - depends: CH-L07
  - acceptance: the GH Actions job runs `just test` + `just it` on fresh Redpanda and ClickHouse services and passes
  - plan: [01-local-dev-debug.md#l-verify](01-local-dev-debug.md#l-verify)
  - spec: [openspec add-local-redpanda-clickhouse-loop](../../../CMP-ch/openspec/changes/add-local-redpanda-clickhouse-loop/tasks.md)

### Local backlog
<a id="ch-lb1"></a>
- [ ] **CH-LB1** Alternative ingest: ClickHouse `Kafka` engine + MV → `trades_raw`
  - depends: CH-L07
  - acceptance: the same `just verify` passes with the Python consumer off; semantics compared in `system.kafka_consumers`
  - plan: [01-local-dev-debug.md#l-consumer](01-local-dev-debug.md#l-consumer)

<a id="ch-lb2"></a>
- [ ] **CH-LB2** Materialized 1m mart (AggregatingMergeTree) with dedup upstream of the MV
  - depends: CH-L08
  - acceptance: equals the view output under F1 / F3 replays, or the design is rejected with a written reason
  - plan: [01-local-dev-debug.md#l-schema](01-local-dev-debug.md#l-schema)

<a id="ch-lb3"></a>
- [ ] **CH-LB3** Grafana (local container + ClickHouse plugin) dashboard-as-code
  - depends: CH-L09
  - acceptance: a provisioned dashboard JSON shows the same panels as Streamlit
  - plan: [01-local-dev-debug.md#l-dashboard](01-local-dev-debug.md#l-dashboard)

## Cloud (CH-C)

<a id="ch-c01"></a>
- [ ] **CH-C01** Accounts, API keys in `bw`, `just secrets-pull`, verify unverified facts
  - goal: the ClickHouse Cloud trial and Confluent Cloud ready, with no secret in the repo
  - depends: CH-L07 · **needs user approval** (sign-ups, payment method for Confluent)
  - acceptance: `.env.secrets` fully populated from `bw`; `CMP-ch/docs/cloud-facts.md` lists each fact from 02 §1 with its URL and check date
  - plan: [02-cloud-deploy-test.md#c-secrets](02-cloud-deploy-test.md#c-secrets)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c02"></a>
- [ ] **CH-C02** Terraform: Confluent env, Basic cluster, topics, producer and clickpipe keys
  - depends: CH-C01
  - acceptance: `tf-apply` ok, then `tf-plan` shows no changes; `rpk`/`kcat` lists the topics over SASL_SSL with the producer key
  - plan: [02-cloud-deploy-test.md#c-deploy](02-cloud-deploy-test.md#c-deploy)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c03"></a>
- [ ] **CH-C03** Terraform: ClickHouse Cloud Basic service + IP list; apply the shared DDL + users
  - depends: CH-C01, CH-L04
  - acceptance: `CMP_ALLOW_REMOTE_DDL=YES just ch-setup` is idempotent on Cloud; the `cmp_dash` user can SELECT the views and nothing else
  - plan: [02-cloud-deploy-test.md#c-deploy](02-cloud-deploy-test.md#c-deploy)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c04"></a>
- [ ] **CH-C04** ClickPipe (Confluent → existing `trades_raw`, JSON, SASL PLAIN)
  - depends: CH-C02, CH-C03
  - acceptance: the pipe status is Running; produced events appear in `trades_raw` and `trades_dedup`; Decimal mapping is confirmed or the CH-CB2 fallback is triggered
  - plan: [02-cloud-deploy-test.md#c-deploy](02-cloud-deploy-test.md#c-deploy)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c05"></a>
- [ ] **CH-C05** Producer to cloud: `CMP_PROFILE=cloud just produce …` + `workflow_dispatch` bounded Bybit job
  - depends: CH-C02, CH-L05
  - acceptance: a bounded live run publishes N events; the GH job respects its timeout and leaks no secrets in its logs
  - plan: [02-cloud-deploy-test.md#c-decisions](02-cloud-deploy-test.md#c-decisions)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c06"></a>
- [ ] **CH-C06** Cloud verification: isolated verify DB / topic / ClickPipe, same fixture assertion + idempotency
  - depends: CH-C04, CH-C05, CH-L07
  - acceptance: `just cloud-verify` passes twice (4 / 0.45 / 70000 / 70010 / 69990; raw 8 → 16, bar unchanged); the verify ClickPipe is disabled afterwards
  - plan: [02-cloud-deploy-test.md#c-verify](02-cloud-deploy-test.md#c-verify)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c07"></a>
- [ ] **CH-C07** Streamlit Community Cloud deploy of `dashboards/app.py` with `st.secrets`
  - depends: CH-C04, CH-L09
  - acceptance: the private app shows live bars; it uses `cmp_dash`; no secret is in the repo
  - plan: [02-cloud-deploy-test.md#c-deploy](02-cloud-deploy-test.md#c-deploy)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c08"></a>
- [ ] **CH-C08** Cloud CI smoke (`workflow_dispatch`, protected `cloud` environment)
  - depends: CH-C06, CH-L11
  - acceptance: a manual run passes `cloud-verify` and uploads a redacted run log
  - plan: [02-cloud-deploy-test.md#c-ci](02-cloud-deploy-test.md#c-ci)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

<a id="ch-c09"></a>
- [ ] **CH-C09** Cost guardrails, `cloud-cost`, `cloud-pause`, `cloud-down` teardown
  - depends: CH-C04
  - acceptance: spend alerts configured where available; `cloud-down` leaves both consoles empty; billing shows no burn the next day
  - plan: [02-cloud-deploy-test.md#c-cost](02-cloud-deploy-test.md#c-cost)
  - spec: [openspec add-clickhouse-cloud-clickpipes](../../../CMP-ch/openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md)

### Cloud backlog
<a id="ch-cb1"></a>
- [ ] **CH-CB1** Kafka provider alternatives: Aiven free, Redpanda Serverless
  - depends: CH-C06
  - acceptance: a comparison note (limits, ClickPipes source type, auth, cost) plus one verify run on the chosen alternative
  - plan: [02-cloud-deploy-test.md#c-facts](02-cloud-deploy-test.md#c-facts)

<a id="ch-cb2"></a>
- [ ] **CH-CB2** Fallback ingest: the CH-L06 consumer on a host against Cloud (if ClickPipes cost or mapping blocks)
  - depends: CH-L06, CH-C03
  - acceptance: `cloud-verify` passes with the ClickPipe off
  - plan: [02-cloud-deploy-test.md#c-decisions](02-cloud-deploy-test.md#c-decisions)

<a id="ch-cb3"></a>
- [ ] **CH-CB3** Always-on hosted producer (Hetzner / Fly / Render) with reconnect monitoring
  - depends: CH-C05
  - acceptance: 24 h run with the gap / reconnect count logged; cost noted
  - plan: [02-cloud-deploy-test.md#c-decisions](02-cloud-deploy-test.md#c-decisions)

<a id="ch-cb4"></a>
- [ ] **CH-CB4** Grafana Cloud free dashboard over ClickHouse Cloud
  - depends: CH-C07, CH-LB3
  - acceptance: the same panels as Streamlit, read-only user
  - plan: [02-cloud-deploy-test.md#c-decisions](02-cloud-deploy-test.md#c-decisions)
