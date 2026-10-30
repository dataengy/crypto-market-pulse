<!--
Sync Impact Report
- Version: none → 1.0.0 (initial ratification; principles taken from the user's global rules + the lane plan)
- Templates checked: plan-template.md (Constitution Check = the gates below), spec-template.md, tasks-template.md: no edits needed
- Follow-up: none
-->
# CMP-dbx-fe Constitution

Scope: `CMP-dbx-fe/` only — Crypto Market Pulse on Databricks Free Edition with a local Redpanda + Spark + Delta + MiniLake loop.
Lane plan: [docs/plans/dbx-fe](../../../docs/plans/dbx-fe/README.md) · specs: [specs/](../../specs) · ADRs: [docs/adr](../../docs/adr).

## Core Principles

### I. No hardcoded scalars
IDs, URLs, URL templates, topic names, timeouts, timezones, enum values and rule regexes do not appear as literals in Python, shell or justfile code.
- Non-secret, shared settings go in `config/config.yaml`, one section per feature.
- Environment and profile values go in `config/.env.common`.
- Code receives values as parameters. Thin scripts read the config.

Allowed literals: config key names (the schema), bootstrap paths to the config files, and values in tests and fixtures.
Check: `python3 ~/.ai/skills/_scripts/utils/find_hardcoded_scalars.py <file> --exit-nonzero-on-find`.

### II. No defaults, fail fast
Read config and env strictly: `cmp.settings.get(cfg, "a.b")` and `cmp.settings.env("X")`.
- A missing key raises an error that names the key and the file to fill.
- The following are forbidden outside tests: `os.getenv(x, default)`, `dict.get(k, default)` for config, `${X:-default}`, and bundle variables with a default for anything that differs per target.
- Shell and CI values win: `.env` files are loaded with `override=False`.

### III. Secrets only in `config/.env.secrets`, Bitwarden `bw`, or a Databricks secret scope
Secrets live in `config/.env.secrets`, which is git-ignored. Its template, `config/.env.secrets.demo`, has empty values.
- In the cloud, secrets are read from a Databricks secret scope (`just dbx-secrets`).
- A secret is never printed, logged, committed or embedded in generated files.
- JAAS strings are built in memory only.

### IV. Local runtime is dev/debug only, and is reused before it is created
- Production is managed Kafka + Free Edition. The local stack exists only to debug the same code.
- Reuse a compatible Redpanda or MiniLake that is already running: point `config.yaml` at it.
- Owned containers are named `cmp-dbx-*` and bind to `127.0.0.1` only. MiniLake has no auth, so it must never be bound to `0.0.0.0`.
- `just down` stops containers and never removes volumes. `--reset` wipes only `.tmp/lake`.

### V. Ponytail: least code, smallest complete change
- Reuse what exists before writing anything new. The order is: an existing helper, then the stdlib or a platform feature, then an installed dependency, then new code.
- No speculative options, wrappers or "for later" code.
- Every change still reaches all its callers, tests, fixtures and config.
- A shortcut with a known limit carries a `ponytail:` comment that names the limit.
- New non-trivial logic ships with one small test.

### VI. One codebase for local and cloud
- `cmp.bronze.parse_trades`, `cmp.kafka.*` and `sql/models/*_select.sql` are the single source of truth. The silver quality rule lives once, in `valid_trade.sql`.
- Lakeflow SQL and the dashboard JSON are **generated** by `scripts/build.py` and never hand-edited. `just verify` fails on drift.
- A dialect gap (for example MiniLake/DuckDB) is reported, not forked.

### VII. One fixture assertion, everywhere (NON-NEGOTIABLE)
`tests/fixtures/trades.jsonl` has 8 lines, 1 of them a duplicate. Every path must reproduce the same result:
- **BTCUSDT 10:00 bar = `trade_count 4 / volume 0.45 / open 70000 / high 70010 / close 69990`**
- `trades_dedup` = 7 rows
- a replay leaves the marts unchanged

This applies to unit Spark, local Kafka E2E, MiniLake, the cloud pipeline and the Volume fallback. A path is "done" only when it prints this result.

## Free Edition constraints
Source: [limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations), checked 2026-10-30.
- Serverless compute only.
- **One active pipeline per type.**
- **One 2X-Small SQL warehouse** (Serverless Starter Warehouse).
- Fair-usage quota.
- Apps are capped at 3, with a 24 h runtime.
- Outbound internet is limited to **trusted domains**. Kafka egress is unverified until [DBX-C02](../../../docs/plans/dbx-fe/tasks.md#dbx-c02) runs.

Design rules that follow from these:
- The pipeline is triggered (`continuous: false`).
- The refresh job is deployed `PAUSED`.
- No warehouse is kept awake.
- Ingest falls back to inbound push (UC Volume, [alt-no-kafka.md](../../../docs/plans/dbx-fe/alt-no-kafka.md)) if egress is blocked.

## Development workflow
The superpowers process skills, mapped onto Spec Kit:
1. **Brainstorm**, using `superpowers:brainstorming`, until the intent is clear. Then `/speckit-specify` writes `spec.md` (user stories + acceptance). Unknowns are marked `[NEEDS CLARIFICATION]`, or resolved with `/speckit-clarify`.
2. **Plan**, using `superpowers:writing-plans`, with `/speckit-plan`: `plan.md`, `research.md`, `data-model.md`, `contracts/` and `quickstart.md`. The Constitution Check below is a gate.
3. **Tasks** with `/speckit-tasks`. Each task names its exact files and its check, and carries a lane ID (`DBX-L/C/A/B`). `docs/plans/dbx-fe/tasks.md` links back with a `spec:` link.
4. **Implement** on a `feat/…` branch, in small Conventional Commits. Push and PR only after the user confirms.
5. **Verify**, using `superpowers:verification-before-completion`. A task is ticked only after its check command has run and its output shows the result. "Written, not run" is reported as exactly that.

### Constitution Check (gate for every plan.md)
- [ ] No new literals for IDs, URLs, timeouts or names; the new keys are in `config.yaml` or `.env.*` (I)
- [ ] Strict reads with no defaults; errors name the key and the file (II)
- [ ] No secret in the repo, logs or generated files (III)
- [ ] Local services are reused or `cmp-dbx-*`, bound to localhost; no volume deletion (IV)
- [ ] It is the smallest change that fully works; the skipped options are listed (V)
- [ ] It reuses `cmp.*` and `sql/models`, and generated files are rebuilt (VI)
- [ ] The fixture assertion is reproduced on the new path (VII)
- [ ] The Free Edition limits are respected (1 pipeline, 1 warehouse, paused schedule, egress)

## Governance
- This constitution overrides lane-local habits. The user's global rules (`~/.claude/rules/*.md`) override this constitution.
- Amendments: edit this file, bump the version (semver: principle removed or redefined = MAJOR, principle added = MINOR, wording = PATCH), and update the Sync Impact Report.
- Reviews check the Constitution Check list.
- Other lanes (`CMP-ch/`, `CMP-gcp/`) are out of scope.

**Version**: 1.0.0 | **Ratified**: 2026-10-30 | **Last Amended**: 2026-10-30
