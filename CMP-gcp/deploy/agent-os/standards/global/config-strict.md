# Config: strict, no scalars in code

These are the user rules `no-hardcoded-scalars` and `env-no-defaults`, applied to the cloud lane.

| Value | Home |
|---|---|
| region/location, names (topic, subscription, dataset, SA ids, AR repo), cron, timeouts, budget amount and thresholds, Dataflow caps, WIF repo (`dataengy/crypto-market-pulse`), Looker URL | `CMP-gcp/config/config.yaml`, the `deploy:` section (plus the existing `profiles.cloud`) |
| `GOOGLE_CLOUD_PROJECT`, `BILLING_ACCOUNT_ID`, `OWNER_MEMBER` (`user:<email>`) | `CMP-gcp/config/.env.secrets`; keys listed in `.env.secrets.demo` |
| WIF provider name and SA email in CI | GitHub repo **variables** (IDs, not secrets), set from `terraform output` |
| Real secrets (none expected) | `.env.secrets` or Bitwarden `bw`; never in the repo |

## Rules
- **Terraform:**
  - `locals { cfg = yamldecode(file(var.config_path)) }` and then `local.cfg.deploy.x`. A missing key is a plan-time error, so there are no `lookup(..., default)` and no `try(...)` fallbacks.
  - `variable` blocks have **no `default`**. `TF_VAR_project_id` and `TF_VAR_billing_account` are exported by the just recipe from `.env.secrets`.
- **just:**
  - `set dotenv-load` + `dotenv-path`
  - no `${X:-default}`
  - a recipe checks the required env and fails with the key name and the file to fill (pattern: `CMP-dbx-fe/justfile` `dbx-secrets`)
- **Python:** reuse the local lane's `settings.load(profile)` (no defaults, raises `ValueError` naming the key and file). Don't build a second loader.
- **Allowed literals:**
  - config key names
  - the bootstrap path to `config.yaml`
  - API service names in Terraform (`pubsub.googleapis.com`), which are schema, not settings
  - fixture values in tests
- **Check:** `python3 ~/.ai/skills/_scripts/utils/find_hardcoded_scalars.py <file> --exit-nonzero-on-find` on every new script or recipe.
