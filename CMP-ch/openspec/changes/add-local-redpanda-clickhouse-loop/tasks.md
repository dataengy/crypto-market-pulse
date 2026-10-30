# Tasks

Task IDs mirror [docs/plans/clickhouse/tasks.md](../../../../docs/plans/clickhouse/tasks.md). Tick both places together.

## 1. Scaffold and core (CH-L01, CH-L02)

- [ ] 1.1 CH-L01 Create `pyproject.toml` (uv, py3.12), `justfile`, `config/config.yaml`, `config/.env.common`, `config/.env.secrets.demo` and `.gitignore`, then adapt the strict `settings.py` from CMP-dbx-fe. Verify: `uv sync && just test` passes the settings-strictness tests (missing yaml key or env var → error naming the file), `git check-ignore config/.env.secrets` succeeds, and `rg 'getenv\(.*,' src` is empty.
- [ ] 1.2 CH-L02 Copy `domain`, `bybit_ws`, `publish`, `reference` and `tests/fixtures/trades.jsonl` from CMP-dbx-fe, plus `test_domain`. Verify: `just test` is green; `reference.py` gives BTCUSDT 10:00 = 4 / 0.45 / 70000 / 70010 / 69990; `find_hardcoded_scalars.py src scripts --exit-nonzero-on-find` exits 0.

## 2. Runtime and debug (CH-L03, CH-L10) — needs docker

- [ ] 2.1 CH-L03 `just inventory` (read-only) and `compose.yml`: labelled, 127.0.0.1-only, pinned tags, healthchecks, `${VAR:?}` ports. Verify: a second `just up` creates nothing; `just down` leaves unlabelled containers and all volumes intact; the chosen runtime is recorded in the run log.
- [ ] 2.2 CH-L10 `dbg-rpk-*`, `dbg-ch`, `dbg-sys-*`, `dbg-counts`. Verify: each recipe runs against the stack, and only `dbg-rpk-produce` writes.

## 3. Schema (CH-L04)

- [ ] 3.1 CH-L04 Write `sql/clickhouse/010…050` (one statement per file, `{db}`) and `scripts/ch_setup.py` with the remote-DDL guard, plus unit tests for `{db}` rendering and Decimal overflow. Verify: `just ch-setup` runs twice cleanly, and a non-local URL without `CMP_ALLOW_REMOTE_DDL=YES` exits non-zero.

## 4. Producer and consumer (CH-L05, CH-L06)

- [ ] 4.1 CH-L05 `scripts/produce.py` with required `--source` / `--sink`. Verify: `just produce fixture` → `rpk topic describe` shows +8; `just produce bybit 50` publishes 50; with the broker down it exits non-zero.
- [ ] 4.2 CH-L06 `scripts/consume.py`: batch insert, then a sync commit; idle exit; poison stop; `--crash-after-insert`. Verify: 8 rows land and the consumer exits after `idle_exit_s`; poison → non-zero with the offset uncommitted (`rpk group describe`).

## 5. E2E gate (CH-L07) — blocks every cloud task

- [ ] 5.1 CH-L07 `sql/checks/fixture_1m.sql`, `just verify <db>`, and `tests/it` (`needs_docker`, isolated DB and topic, dropped at the end). Verify: `just it` asserts 4 / 0.45 / 70000 / 70010 / 69990 and `uniqExact=7` vs raw `8`, the rerun leaves the bar unchanged, and `just up && just ch-setup && just produce fixture && just consume && just verify market_pulse_dev` passes twice.

## 6. Evidence, dashboard, CI (CH-L08, CH-L09, CH-L11)

- [ ] 6.1 CH-L09 `dashboards/app.py` (ClickHouse only, `cmp_dash`, TTL and limit from config, stale badge). Verify: `just dashboard` shows the fixture bar, and the badge appears after `stale_after_s`.
- [ ] 6.2 CH-L08 Fault runs F1–F5, F7 and F10 per the [runbook](../../../docs/runbooks/local-dev-debug.md#fault-injection). Verify: one filled run record per fault (UTC, SHA, command, expected / actual, PASS / FAIL) in `docs/evidence/`.
- [ ] 6.3 CH-L11 GH Actions job: `just test` + `just it` on fresh Redpanda and ClickHouse service containers, with no secrets. Verify: the job is green on a PR.

## Workflow follow-up

- `openspec archive add-local-redpanda-clickhouse-loop` after 5.1 and 6.x pass. This moves the six capability specs into `openspec/specs/`.
