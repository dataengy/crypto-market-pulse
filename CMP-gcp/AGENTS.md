<!-- bmad:context -->
<!-- Verified 2026-10-30 against 5cb9e00. Shape: bmad-project-context (BMAD v6.12.4). -->

## CMP-gcp

GCP lane of Crypto Market Pulse: Bybit trades → Pub/Sub → (BigQuery-subscription SQL path | Beam path) → 1-minute bars. Python 3.12, uv, just. This file governs `CMP-gcp/` **except `deploy/`**, which belongs to the cloud lane (Agent OS, another agent): see [deploy/README.md](deploy/README.md). Planning (BMAD): [docs/project-brief.md](docs/project-brief.md) → [docs/prd.md](docs/prd.md) → [docs/architecture.md](docs/architecture.md) → [docs/epics.md](docs/epics.md) → [docs/stories/](docs/stories/). Task IDs: [docs/plans/gcp/tasks.md](../docs/plans/gcp/tasks.md).

## Policy

- Never write into `deploy/`, `../CMP-dbx-fe/`, `../CMP-ch/`, the repo-root `CLAUDE.md`/`AGENTS.md`, or `../docs/plans/{dbx-fe,clickhouse}`. Cloud work goes to `deploy/`.
- Never hardcode scalars (IDs, URLs, ports, timeouts, window/lateness, dataset names, regexes). Put them in `config/config.yaml`, or in `config/.env.common` for env-specific values.
- Never use defaults: `os.environ["X"]`, `load_dotenv(override=False)`; a missing key raises `ValueError` naming the key and the file. Gate: `python3 ~/.ai/skills/_scripts/utils/find_hardcoded_scalars.py src scripts --exit-nonzero-on-find`.
- Secrets only in `config/.env.secrets` (git-ignored; keys listed in `.env.secrets.demo`) or Bitwarden `bw`. The local profile needs none.
- Discover and reuse local runtimes before creating any ([reuse policy](../crypto-market-pulse-chatgpt/project/docs/local/LOCAL_RUNTIME_REUSE_POLICY.md)). Bind 127.0.0.1 only. Never `docker compose down -v`, prune, or stop containers you did not start.
- Ponytail: the smallest complete change. Copy patterns from `../CMP-dbx-fe/` instead of adding abstractions. Each story's **Never** list is binding.
- No `gcloud` auth, cloud resources, Terraform or Dataflow from this lane.
- Commit, push and PR only after the user confirms; work on a `feat/` branch.

## Where things are

- Decisions: [docs/adr/](docs/adr/) (MADR). Debugging: [docs/runbooks/local-dev-debug.md](docs/runbooks/local-dev-debug.md).
- Step detail per task: [docs/plans/gcp/01-local-dev-debug.md](../docs/plans/gcp/01-local-dev-debug.md). Reference code (never run; do not copy its defaults): `../crypto-market-pulse-chatgpt/project/`.
- BMAD skills: `.claude/skills/bmad-*`; config: `_bmad/` (planning → `docs/`, stories → `docs/stories/`).

## Running and verifying

- Implement one story at a time with `bmad-build` or superpowers `executing-plans`: TDD, failing test first.
- Before marking a story done, run its **Verification** command and paste the output into its Dev Agent Record.
- TestStream tests (`tests/beam/`) must stay offline and deterministic. Emulator tests use the marker `needs_emulators`.

## Known pitfalls

- An empty Beam output with a full raw table means the watermark stalled; check the heartbeat and `timestamp_attribute` first.
- The Pub/Sub emulator never delivers BigQuery subscriptions; locally the shim does that. Emulator state is memory-only.
- Since Beam 2.68 the DirectRunner may run Prism; log the effective runner and never assert on runner internals.

<!-- /bmad:context -->
