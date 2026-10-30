# Contract: bundle resources, pipeline configuration, secrets

Owner: [`databricks.yml`](../../../databricks.yml). Names here are the interface between the bundle, `pipelines/bronze.py`, `scripts/dbx_kafka_probe.py` and the justfile.

| Item | Value / key | Consumed by |
|---|---|---|
| Schema | `${var.catalog}.${var.schema}` (`workspace.crypto_pulse`) | pipeline, dashboard |
| Pipeline | `cmp-market-pulse`, serverless, `continuous: false` | `just dbx-run`, job `cmp-refresh` |
| Pipeline conf `cmp.root` | `${workspace.file_path}` → `config/config.yaml` and `src/` are read from here | `pipelines/bronze.py` |
| Pipeline conf `cmp.secret_scope` | `${var.secret_scope}` | `pipelines/bronze.py` |
| Secret keys | `kafka_bootstrap`, `kafka_api_key`, `kafka_api_secret` = the env names from `kafka.profiles.cloud.*_env`, lowercased | `just dbx-secrets` writes them; bronze and the probe read them |
| Job `cmp-kafka-probe` | args `--root`, `--secret-scope` | `just dbx-probe` |
| Job `cmp-refresh` | quartz every 15 min UTC, **`PAUSED`** | unpaused only for DBX-C05 |
| Dashboard | `Crypto Market Pulse`, warehouse lookup `Serverless Starter Warehouse` | viewer |
| CLI auth | `DATABRICKS_CONFIG_PROFILE` from `config/.env.secrets` | every `dbx-*` recipe |

Adding a secret means adding it to `.env.secrets.demo` (empty), to `kafka.profiles.cloud`, and to the `dbx-secrets` loop.
