# CMP-ch — Crypto Market Pulse, ClickHouse lane

Bybit trades → Kafka → ClickHouse (`trades_raw` → `trades_dedup` → `trades_1m` / `trades_latest`) → Streamlit.
- Local: Redpanda + ClickHouse + Python consumer.
- Cloud: Confluent Cloud → ClickPipes → ClickHouse Cloud → Streamlit Community Cloud.

**Status (2026-10-30): specs only, no code yet.** Plan and task IDs: [docs/plans/clickhouse](../docs/plans/clickhouse/README.md).

## Spec-driven workflow (OpenSpec 1.15.0)
| What | Where |
|---|---|
| Project context and rules (user rules, ponytail, process) | [openspec/config.yaml](openspec/config.yaml) |
| Change 1: local loop, CH-L01…L11 | [openspec/changes/add-local-redpanda-clickhouse-loop](openspec/changes/add-local-redpanda-clickhouse-loop/proposal.md) |
| Change 2: cloud via ClickPipes, CH-C01…C09 | [openspec/changes/add-clickhouse-cloud-clickpipes](openspec/changes/add-clickhouse-cloud-clickpipes/proposal.md) |
| Capability specs (as deltas until archived) | `project-config`, `local-runtime`, `ingest`, `storage-dedup`, `ohlcv-marts`, `dashboard`, `cloud-deploy` |
| Decisions | [docs/adr](docs/adr/0001-python-consumer-over-kafka-engine.md) (0001–0004) |
| Architecture | [docs/design/architecture.md](docs/design/architecture.md) |
| Runbooks | [local-dev-debug](docs/runbooks/local-dev-debug.md) · [cloud-deploy-verify](docs/runbooks/cloud-deploy-verify.md) |

`openspec/specs/` stays empty until a change is archived. Archiving moves the delta specs there, so they become the source of truth for what is built. Archive the local change first, because the cloud change adds requirements to its `ingest` and `dashboard`.

```bash
o() { npx -y @fission-ai/openspec@1.15.0 "$@"; }   # or: npm i -g @fission-ai/openspec@1.15.0
o list && o validate --all --strict
o instructions apply --change add-local-redpanda-clickhouse-loop
```
Process:
1. brainstorming → writing-plans, before editing a change's design
2. implement one task at a time (Claude skill `openspec-apply-change`)
3. verification-before-completion: tick a box only after its verify command ran
4. `openspec archive`

The Claude skills are in `.claude/skills/openspec-*`. The `/opsx:*` slash commands were not generated: the sandbox blocks `.claude/commands`, so use the skills, or rerun `openspec init --tools claude` outside the sandbox.
