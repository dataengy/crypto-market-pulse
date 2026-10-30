## ADDED Requirements

### Requirement: Approval-gated provisioning
No account, API key or billable resource SHALL be created without explicit user approval recorded in the task. All billable resources SHALL be declared in Terraform with gitignored local state. That state SHALL be treated as a secret.

#### Scenario: Plan is clean after apply
- **WHEN** `just tf-apply` has succeeded and `just tf-plan` runs
- **THEN** the plan reports no changes

#### Scenario: State not tracked
- **WHEN** `git check-ignore CMP-ch/infra/cloud/terraform.tfstate` runs
- **THEN** the file is reported as ignored

### Requirement: Secrets only from Bitwarden
Cloud credentials SHALL be pulled from `bw` into `config/.env.secrets` by `just secrets-pull`, using item names from config. Terraform SHALL receive them only as `TF_VAR_*`. CI and Streamlit SHALL use their platform secret stores under the same names.

#### Scenario: Locked vault
- **WHEN** `just secrets-pull` runs without an unlocked `bw` session
- **THEN** it exits non-zero, writes nothing, and asks for `bw unlock`

#### Scenario: No secret in logs
- **WHEN** the CI smoke or producer job runs
- **THEN** its uploaded log contains no value of any `.env.secrets` key

### Requirement: Least-privilege ClickHouse users
The shared DDL SHALL be applied to Cloud only with `CMP_ALLOW_REMOTE_DDL=YES`. It SHALL create:
- `cmp_ingest`, with INSERT on `trades_raw` only
- `cmp_dash`, with SELECT on the views only

Passwords SHALL be passed as parameters, never as literals.

#### Scenario: Idempotent cloud setup
- **WHEN** `CMP_ALLOW_REMOTE_DDL=YES just ch-setup` runs twice against Cloud
- **THEN** both runs succeed and the schema is unchanged by the second

#### Scenario: Dashboard user cannot write
- **WHEN** `cmp_dash` attempts `INSERT INTO trades_raw`
- **THEN** ClickHouse rejects it

### Requirement: Isolated cloud verification
`just cloud-verify` SHALL load the fixture through a dedicated verify topic and pipe into `market_pulse_verify`, and SHALL run the same assertion as local. Afterwards it SHALL disable the verify pipe.

#### Scenario: Fixture bar in Cloud
- **WHEN** `just cloud-verify` runs on an empty verify DB
- **THEN** the BTCUSDT 10:00 bar is 4 / 0.45 / 70000 / 70010 / 69990 within `cloud.verify_timeout_s`

#### Scenario: Idempotent in Cloud
- **WHEN** `just cloud-verify` runs a second time
- **THEN** raw `count()` is 16, `uniqExact(event_id)` is 7, and the bar is unchanged

#### Scenario: Verify pipe stopped
- **WHEN** `just cloud-verify` finishes, passing or failing
- **THEN** the verify ClickPipe is removed or stopped

### Requirement: Manual cloud CI smoke
Cloud CI SHALL run only on `workflow_dispatch`, in an environment that requires a reviewer. PR CI SHALL stay hermetic with no cloud secrets.

#### Scenario: Push does not hit cloud
- **WHEN** a commit is pushed or a PR is opened
- **THEN** no job that uses cloud secrets runs

### Requirement: Cost guardrails and teardown
The lane SHALL provide:
- a read-only `just cloud-cost`
- `just cloud-pause`, which stops the main ClickPipe
- `just cloud-down`, which destroys every Terraform-managed resource

Spend alerts SHALL be enabled where the consoles offer them.

#### Scenario: Teardown leaves nothing billable
- **WHEN** `just cloud-down` completes and the API keys are deleted in both consoles
- **THEN** both consoles list no service, cluster or pipe, and billing shows no new usage the next day
