## ADDED Requirements

### Requirement: Strict configuration loading
The system SHALL read non-secret settings from `config/config.yaml`, environment values from `config/.env.common` and secrets from `config/.env.secrets`. There SHALL be no default values. Values already set in the process environment SHALL take precedence over the files.

#### Scenario: Missing YAML key
- **WHEN** a required key such as `kafka.topic` is absent from `config/config.yaml`
- **THEN** startup fails before any I/O with an error that names the key and `config/config.yaml`

#### Scenario: Missing secret
- **WHEN** `CLICKHOUSE_PASSWORD` is set neither in the environment nor in `config/.env.secrets`
- **THEN** startup fails with an error that names `CLICKHOUSE_PASSWORD` and the template `config/.env.secrets.demo`

#### Scenario: Shell environment wins
- **WHEN** `CMP_PROFILE` is exported in the shell and also set in `config/.env.common`
- **THEN** the exported value is used

### Requirement: No scalars or secrets in code or repo
Endpoints, ports, timeouts, topic and group names, IDs, SASL mechanism and validation bounds SHALL live in config. Secrets SHALL NOT be committed: only `.env.secrets.demo` with empty values is tracked.

#### Scenario: Scalar scan
- **WHEN** `find_hardcoded_scalars.py src scripts --exit-nonzero-on-find` runs
- **THEN** it exits 0

#### Scenario: Secrets file ignored
- **WHEN** `git check-ignore CMP-ch/config/.env.secrets` runs
- **THEN** the file is reported as ignored
