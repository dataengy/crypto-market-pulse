# Runbook: cloud deploy & verify

These are the target recipes from [add-clickhouse-cloud-clickpipes](../../openspec/changes/add-clickhouse-cloud-clickpipes/tasks.md). They are not implemented yet. Full plan: [02-cloud-deploy-test.md](../../../docs/plans/clickhouse/02-cloud-deploy-test.md). Pricing status: [design](../../openspec/changes/add-clickhouse-cloud-clickpipes/design.md#pricing-facts).

## Preconditions
- The local gate is green: `just verify` passes twice ([CH-L07](../../../docs/plans/clickhouse/tasks.md#ch-l07)).
- **User approval** covers the sign-ups, the Confluent payment method and the expected spend.
- `bw unlock` is done in this shell. The session token is never written to disk.

## Deploy
```bash
just secrets-pull                          # bw → config/.env.secrets
just tf-plan && just tf-apply              # Confluent env/cluster/topics/keys + CH service/IP list + ClickPipe
CMP_ALLOW_REMOTE_DDL=YES just ch-setup     # same sql/clickhouse/*.sql + 090_users.sql
CMP_PROFILE=cloud just produce bybit 50
just cloud-verify                          # twice: bar unchanged, raw 8 → 16
just cloud-cost                            # daily during the trial
just cloud-pause                           # whenever not demoing
just cloud-down                            # terraform destroy; then delete API keys in both consoles
```

## Failure modes
| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `secrets-pull` fails | vault locked, or item name differs | `bw status`, `config.yaml: secrets.bw_items` | `bw unlock`; fix the item name in config, not in code |
| `tf-apply` fails on Confluent | no payment method, or a wrong org/env key | Confluent console → Billing | add the payment method (approved) or fix the key in `bw` |
| TF provider schema error | breaking change in `ClickHouse/clickhouse` ≥ 3.15 | `terraform providers` | keep the pinned version; upgrade deliberately |
| `ch-setup` connection refused / 403 | IP list does not include your IP or CI egress; service idle | console → Security | add the IP via TF; retry after the service wakes |
| ClickPipe stuck in Provisioning/Failed | wrong bootstrap, SASL key or ACL (READ + group `clickpipes-*`) | ClickPipe status/errors | fix the key's ACLs in TF |
| pipe Running, `trades_raw` empty | topic or format mismatch, or the consumer group starts at latest | pipe metrics; `rpk topic describe` over SASL_SSL | re-produce the fixture; check the offset strategy |
| pipe error on `price`/`qty` | JSON string → `Decimal(38,12)` mapping rejected | pipe error text | record it in `docs/cloud-facts.md` and switch to the consumer fallback [CH-CB2](../../../docs/plans/clickhouse/tasks.md#ch-cb2) |
| `cloud-verify` times out | verify pipe disabled or not created | `TF_VAR_verify_enabled` | enable it, rerun, and confirm the pipe is disabled afterwards |
| `cloud-verify` raw 16 but bar wrong | the views were not created in `market_pulse_verify` | `SHOW TABLES FROM market_pulse_verify` | rerun `ch-setup` with `{db}=market_pulse_verify` |
| Streamlit app error naming a key | missing `st.secrets` entry | app settings | add the key; never fall back to the admin user |
| Streamlit stale badge permanently | producer not running, or the main pipe paused | `cloud-cost`, pipe status | run a bounded producer; un-pause the pipe |
| credits burning while idle | ClickPipe replicas bill hourly; storage is always billed | `just cloud-cost` | `just cloud-pause`; `just cloud-down` when done |
| trial ended with resources live | the expiry behaviour is unverified | both consoles | `just cloud-down` immediately; check billing the next day |
