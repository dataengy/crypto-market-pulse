# Runbook — Databricks Free Edition deploy and verify

Specs: [002](../../specs/002-dbx-fe-pipeline-deploy/spec.md), with the fallback [003](../../specs/003-no-kafka-volume-ingest/spec.md). Tasks: [DBX-C01…C05](../../../docs/plans/dbx-fe/tasks.md#dbx-c01). Prerequisite: the local E2E is green (DBX-L05).

The **user** owns the login, the profile choice and the Kafka account. The agent never picks a Databricks profile or creates cloud resources without the user confirming.

## 1. Accounts and CLI (DBX-C01)
1. Run `databricks --version`; it must be ≥ 1.16. Then `databricks auth login --host <workspace-url> --profile <name>`.
2. `cp config/.env.secrets.demo config/.env.secrets`. Fill in `DATABRICKS_CONFIG_PROFILE` and `KAFKA_BOOTSTRAP` / `KAFKA_API_KEY` / `KAFKA_API_SECRET`.
3. Run `just dbx-validate`; it should pass. Then `CMP_PROFILE=cloud just produce fixture`, which should deliver 8 messages.

Failures:
- `warehouse lookup … not found`: the starter warehouse has a different name. Check `databricks warehouses list` and update the lookup.
- An auth error: re-run `auth login`, and check the profile name in `.env.secrets`.

## 2. Secrets and deploy
`just dbx-secrets && just dbx-deploy`. The scope `cmp` gets the keys `kafka_bootstrap`, `kafka_api_key` and `kafka_api_secret` ([contract](../../specs/002-dbx-fe-pipeline-deploy/contracts/bundle-and-secrets.md)). Never echo the values.

## 3. Gate: Kafka egress (DBX-C02)
`just dbx-probe`. A pass looks like `TCP OK: <host>:9092`, then `Kafka SASL read OK: topic market.trades.v1 has N messages`. If it passes, go to step 5.

## 4. Gate failed: Kafka egress blocked
- A timeout or `connection refused` at the TCP step means Free Edition egress does not allow the broker.
- **Any** non-trusted Kafka host will fail the same way, so switching providers will not help.
- A pass at TCP followed by a SASL/auth error is a credentials problem instead, not egress. Fix the secrets and re-run step 2.

Then:
1. Record "Kafka egress blocked (date, host)" in `README.md › Status`.
2. Stop the cloud Kafka work and switch to [spec 003](../../specs/003-no-kafka-volume-ingest/tasks.md), starting at DBX-A01.
3. Ask the user before building the shipper.

## 5. Pipeline run and fixture parity (DBX-C03, DBX-C04)
1. Make sure the topic holds **only** the fixture ([spec 002 › Edge Cases](../../specs/002-dbx-fe-pipeline-deploy/spec.md#edge-cases)).
2. `just dbx-run`. In the pipeline event log, `valid_trade` should show 0 drops for the fixture, and all 5 datasets should be materialized.
3. `just dbx-query "SELECT * FROM workspace.crypto_pulse.trades_1m WHERE symbol='BTCUSDT' ORDER BY window_start LIMIT 1"` should give `4 / 0.45 / 70000 / 70010 / 69990`. Then `SELECT COUNT(*) FROM workspace.crypto_pulse.trades_dedup` should give 7.
4. Produce again, then `just dbx-run` again: the results should be unchanged.

Failures:
- `ModuleNotFoundError: cmp` or `yaml`: `cmp.root` / sync is wrong, or the pipeline environment did not install `pyyaml`. Check `bundle validate` and the pipeline settings.
- `JAAS` / `LoginModule not found`: the pipeline must use `kafka.jaas_login_module.databricks` (the shaded one).
- `Only one active pipeline`: stop or delete the other pipeline (Free Edition allows 1 per type).
- `just dbx-query` is not available in your CLI: run the same SQL in the SQL editor on the Starter Warehouse.
- Stale generated SQL deployed: `dbx-deploy` runs `build` first. If the file was hand-edited, see the [local runbook](local-dev-debug.md#stale-generated-files).

## 6. Live data, dashboard and cleanup
1. `CMP_PROFILE=cloud just produce bybit --max-trades 200`, then `just dbx-run`. Open the "Crypto Market Pulse" dashboard.
2. For a timed demo only: unpause `cmp-refresh` in the Jobs UI.
3. **Afterwards, pause `cmp-refresh` again.** Check that no pipeline update is running and the warehouse is idle ([ADR-0005](../adr/0005-triggered-pipeline-paused-job.md)).

Failure: Bybit is geo-blocked from the producer host. Run the producer from an allowed region ([DBX-B6](../backlog/hosted-producer.md)).

## Evidence to record
For each task, record the command, the date and the key output line in `README.md › Status` and the lane [README status](../../../docs/plans/dbx-fe/README.md#status-2026-10-30). Tick the boxes in the spec `tasks.md` only after that.
