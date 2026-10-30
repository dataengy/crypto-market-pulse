# Tasks

Task IDs mirror [docs/plans/clickhouse/tasks.md](../../../../docs/plans/clickhouse/tasks.md). Tick both places together. Every group needs the local gate (CH-L07) to be green. Procedures are in [cloud-deploy-verify.md](../../../docs/runbooks/cloud-deploy-verify.md).

## 1. Accounts and secrets (CH-C01) — needs user approval

- [ ] 1.1 CH-C01 With user approval: ClickHouse Cloud trial, Confluent Cloud, org API keys stored in `bw`, `config.yaml: secrets.bw_items`, and `just secrets-pull`. Verify: `.env.secrets` has every key from `.env.secrets.demo`, and a locked vault makes `secrets-pull` exit non-zero.
- [ ] 1.2 CH-C01 Re-check every unverified or conflicting row of the design's [Pricing facts](design.md#pricing-facts) and write them to `docs/cloud-facts.md` with URL and date. Verify: no row is left unverified.

## 2. Provisioning (CH-C02, CH-C03) — spends credits

- [ ] 2.1 CH-C02 TF: Confluent env, Basic cluster, topics `market.trades.v1` and `market.trades.verify.v1`, producer and clickpipe service-account keys, and a pinned provider. Verify: `just tf-apply`, then `just tf-plan` shows no changes; `rpk topic list` over SASL_SSL with the producer key lists both topics.
- [ ] 2.2 CH-C03 TF: ClickHouse Cloud Basic service (idle scaling, same region) and IP list. Then `CMP_ALLOW_REMOTE_DDL=YES just ch-setup` plus `090_users.sql`. Verify: the second setup run is a no-op; `cmp_dash` can SELECT the views, and its INSERT is rejected.

## 3. Ingest and producer (CH-C04, CH-C05)

- [ ] 3.1 CH-C04 TF `clickhouse_clickpipe`: Confluent → `trades_raw`, JSON, SASL PLAIN, `cmp_ingest`. Verify: status Running; produced events appear in `trades_raw` and in `trades_dedup FINAL`; the Decimal mapping is confirmed, or CH-CB2 is opened with the error text.
- [ ] 3.2 CH-C05 `CMP_PROFILE=cloud just produce bybit <N>` and `.github/workflows/cmp-ch-produce.yml` (`workflow_dispatch`, timeout from repo vars). Verify: N events published; a manual run respects its timeout and its log has no secret values.

## 4. Cloud gate (CH-C06)

- [ ] 4.1 CH-C06 `just cloud-verify`: verify DB and pipe, fixture to the verify topic, wait ≤ `cloud.verify_timeout_s`, `sql/checks/fixture_1m.sql`, then disable the pipe. Verify: it passes twice (4 / 0.45 / 70000 / 70010 / 69990; raw 8 → 16, bar unchanged), and the verify pipe is gone afterwards.

## 5. Dashboard and CI (CH-C07, CH-C08)

- [ ] 5.1 CH-C07 Deploy `dashboards/app.py` to Streamlit Community Cloud (private), with secrets in app settings. Verify: live bars are shown without a stale badge, and `git grep` finds no secret value.
- [ ] 5.2 CH-C08 `.github/workflows/cmp-ch-cloud-smoke.yml` (`workflow_dispatch`, `cloud` environment with a required reviewer). Verify: a manual run passes `cloud-verify` and uploads a redacted log; pushes trigger no cloud job.

## 6. Cost and teardown (CH-C09)

- [ ] 6.1 CH-C09 `just cloud-cost` (read-only), `cloud-pause`, `cloud-down`, spend alerts, and a calendar reminder 2 days before trial end. Verify: after `cloud-down` and deleting the keys, both consoles are empty, and billing shows no new usage the next day.

## Workflow follow-up

- Archive after 4.1 and 6.1 pass, and only after `add-local-redpanda-clickhouse-loop` is archived, so the `ingest` and `dashboard` deltas apply to existing specs.
